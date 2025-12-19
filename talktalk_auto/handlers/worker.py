import json
import time
from datetime import datetime

from talktalk_auto.channel_config import get_channel_config
from talktalk_auto.dedup_store import build_dedup_key, claim_dedup
from talktalk_auto.global_mode import get_global_mode
from talktalk_auto.llm_parser import parse_llm_result
from talktalk_auto.logger import get_logger
from talktalk_auto.masking import mask_pii
from talktalk_auto.models import Decision, TalkTalkEvent
from talktalk_auto.openai_client import generate_llm_json
from talktalk_auto.rag import build_context, chunks_to_citations, retrieve, summarize_sources
from talktalk_auto.settings import get_settings
from talktalk_auto.sheets import append_row
from talktalk_auto.telegram import send_alert
from talktalk_auto.talktalk_send import resolve_auth_token, send_message
from talktalk_auto.text_utils import contains_forbidden, is_too_short, normalize_text


logger = get_logger(__name__)


def _now_kst_iso() -> str:
    return datetime.now().astimezone().isoformat()


def _should_write_sheet(global_mode: str) -> bool:
    settings = get_settings()
    if global_mode == "TEST":
        return True
    return settings.sheet_enable_prod


def _build_telegram_message(
    channel_name: str,
    channel_id: str,
    user_id: str,
    question: str,
    draft_answer: str,
    reasons: list[str],
) -> str:
    parts = [
        f"Channel: {channel_name} ({channel_id})",
        f"User: {user_id}",
        f"Question: {question}",
        f"Draft: {draft_answer}",
        f"Reasons: {', '.join(reasons) if reasons else 'N/A'}",
    ]
    return "\n".join(parts)


def _derive_decision(
    llm_result,
    rag_top1: float,
    rag_topk_avg: float,
    policy_blocked: bool,
    mode_blocked: bool,
) -> Decision:
    settings = get_settings()
    reasons = []
    if policy_blocked:
        reasons.append("policy_blocked")
    rag_ok = rag_top1 >= settings.rag_top1_threshold and rag_topk_avg >= settings.rag_topk_avg_threshold
    if not rag_ok:
        reasons.append("rag_thresholds_not_met")
    if llm_result:
        reasons.extend(llm_result.reasons)

    send_to_user = bool(
        llm_result
        and llm_result.send_to_user
        and rag_ok
        and not policy_blocked
        and not mode_blocked
    )
    needs_operator = bool(policy_blocked or not rag_ok or (llm_result and llm_result.needs_operator))
    return Decision(
        send_to_user=send_to_user,
        needs_operator=needs_operator,
        reasons=reasons,
        blocked_by_mode=mode_blocked,
        blocked_by_policy=policy_blocked or not rag_ok,
    )


def _process_message(message: dict) -> None:
    settings = get_settings()
    channel_id = message.get("channel_id", "")
    payload = message.get("payload") or {}

    event = TalkTalkEvent.from_payload(payload)
    if event.event != "send":
        return

    if not channel_id:
        logger.warning("Missing channel_id")
        return

    if not event.user_id:
        logger.warning("Missing user_id")
        return

    text = event.text or ""
    normalized = normalize_text(text)
    time_bucket = int(time.time() / settings.dedup_ttl_seconds)
    dedup_key = build_dedup_key(channel_id, event.user_id, normalized, time_bucket)
    if not claim_dedup(dedup_key, settings.dedup_ttl_seconds):
        logger.info("Duplicate message skipped")
        return

    channel_config = get_channel_config(channel_id)
    if not channel_config:
        send_alert(
            settings.default_telegram_target,
            _build_telegram_message(
                channel_name="unknown",
                channel_id=channel_id,
                user_id=event.user_id,
                question=mask_pii(text),
                draft_answer="",
                reasons=["missing_channel_config"],
            ),
        )
        return

    global_mode = get_global_mode()
    channel_mode = channel_config.channel_mode.upper() if channel_config.channel_mode else "TEST"
    mode_blocked = not (global_mode == "PROD" and channel_mode == "PROD")

    policy_blocked = False
    reasons: list[str] = []
    if event.has_image or event.has_composite or not event.has_text:
        policy_blocked = True
        reasons.append("non_text_message")
    if event.has_text and is_too_short(text):
        policy_blocked = True
        reasons.append("too_short")
    if event.has_text and contains_forbidden(text):
        policy_blocked = True
        reasons.append("forbidden_keyword")

    rag_top1 = 0.0
    rag_topk_avg = 0.0
    rag_chunks = []
    llm_result = None

    if not policy_blocked and event.has_text:
        try:
            rag_result = retrieve(text, channel_config.index_s3_uri, channel_config.index_version)
            rag_top1 = rag_result.top1
            rag_topk_avg = rag_result.topk_avg
            rag_chunks = rag_result.chunks
            if rag_chunks:
                context = build_context(rag_chunks)
                llm_json = generate_llm_json(text, context)
                llm_result = parse_llm_result(llm_json)
            else:
                reasons.append("no_rag_context")
                policy_blocked = True
        except Exception:
            logger.exception("RAG/LLM failure")
            reasons.append("rag_or_llm_error")
            policy_blocked = True

    decision = _derive_decision(llm_result, rag_top1, rag_topk_avg, policy_blocked, mode_blocked)

    draft_answer = llm_result.draft_answer if llm_result else ""
    confidence = llm_result.confidence if llm_result else 0.0
    citations = llm_result.citations if llm_result else []

    send_status = "NOT_SENT"
    telegram_sent = "N"
    errors = []

    if decision.send_to_user:
        if not draft_answer.strip():
            errors.append("empty_draft_answer")
            decision.needs_operator = True
        else:
            try:
                auth_token = resolve_auth_token(channel_config.talktalk_auth_secret_arn)
                send_message(auth_token, event.user_id, draft_answer)
                send_status = "SENT"
            except Exception:
                logger.exception("Failed to send TalkTalk message")
                errors.append("talktalk_send_failed")
                decision.needs_operator = True

    if decision.needs_operator or (settings.alert_on_not_sent and send_status == "NOT_SENT"):
        try:
            message = _build_telegram_message(
                channel_name=channel_config.channel_name,
                channel_id=channel_id,
                user_id=event.user_id,
                question=text,
                draft_answer=draft_answer,
                reasons=list(set(reasons + decision.reasons + errors)),
            )
            target = channel_config.telegram_target or settings.default_telegram_target
            send_alert(target, message)
            telegram_sent = "Y"
        except Exception:
            logger.exception("Failed to send Telegram alert")
            errors.append("telegram_failed")

    if _should_write_sheet(global_mode):
        try:
            sheet_id = channel_config.sheet_id or settings.default_sheet_id
            sheet_tab = channel_config.sheet_tab or settings.default_sheet_tab
            sources = summarize_sources(rag_chunks)
            row = [
                _now_kst_iso(),
                channel_id,
                channel_config.channel_name,
                event.user_id,
                text,
                draft_answer,
                confidence,
                global_mode,
                channel_mode,
                send_status,
                telegram_sent,
                sources,
                ",".join(list(set(reasons + decision.reasons + errors))),
                rag_top1,
                rag_topk_avg,
            ]
            append_row(sheet_id, sheet_tab, row)
        except Exception:
            logger.exception("Failed to write to sheet")


def handler(event, _context):
    records = event.get("Records", [])
    for record in records:
        body = record.get("body")
        if not body:
            continue
        try:
            message = json.loads(body)
        except json.JSONDecodeError:
            logger.warning("Invalid SQS message body")
            continue
        _process_message(message)

    return {"statusCode": 200}
