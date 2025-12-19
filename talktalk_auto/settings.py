import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    aws_region: str
    sqs_queue_url: str
    channel_config_table: str
    dedup_table: str
    global_mode_param: str
    openai_api_key: str
    openai_model: str
    embedding_model: str
    rag_top1_threshold: float
    rag_topk_avg_threshold: float
    min_text_length: int
    forbidden_keywords: list[str]
    common_index_s3_uri: str
    sheet_enable_prod: bool
    default_sheet_id: str
    default_sheet_tab: str
    telegram_bot_token: str
    telegram_bot_token_secret_arn: str
    default_telegram_target: str
    alert_on_not_sent: bool
    dedup_ttl_seconds: int
    max_context_chunks: int
    index_cache_ttl_seconds: int
    log_level: str


_SETTINGS: Settings | None = None


def _get_bool(value: str, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _get_list(value: str, default: list[str]) -> list[str]:
    if not value:
        return default
    return [item.strip() for item in value.split(",") if item.strip()]


def get_settings() -> Settings:
    global _SETTINGS
    if _SETTINGS is not None:
        return _SETTINGS

    _SETTINGS = Settings(
        aws_region=os.environ.get("AWS_REGION", "ap-northeast-2"),
        sqs_queue_url=os.environ.get("SQS_QUEUE_URL", ""),
        channel_config_table=os.environ.get("CHANNEL_CONFIG_TABLE", ""),
        dedup_table=os.environ.get("DEDUP_TABLE", ""),
        global_mode_param=os.environ.get("GLOBAL_MODE_PARAM", "TT_GLOBAL_MODE"),
        openai_api_key=os.environ.get("OPENAI_API_KEY", ""),
        openai_model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        embedding_model=os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small"),
        rag_top1_threshold=float(os.environ.get("RAG_TOP1_THRESHOLD", "0.8")),
        rag_topk_avg_threshold=float(os.environ.get("RAG_TOPK_AVG_THRESHOLD", "0.7")),
        min_text_length=int(os.environ.get("MIN_TEXT_LENGTH", "4")),
        forbidden_keywords=_get_list(
            os.environ.get(
                "FORBIDDEN_KEYWORDS",
                "refund,cancel,dispute,legal,privacy,order,card,payment,phone,account,"
                "\\ud658\\ubd88,\\ucde8\\uc18c,\\ubd84\\uc7c1,\\ubc95\\uc801,\\uc18c\\uc1a1,"
                "\\uac1c\\uc778\\uc815\\ubcf4,\\uc8fc\\ubb38\\uc870\\ud68c,\\uce74\\ub4dc,\\uacb0\\uc81c,"
                "\\uc804\\ud654\\ubc88\\ud638,\\uacc4\\uc88c",
            ),
            [],
        ),
        common_index_s3_uri=os.environ.get("COMMON_INDEX_S3_URI", ""),
        sheet_enable_prod=_get_bool(os.environ.get("SHEET_ENABLE_PROD"), True),
        default_sheet_id=os.environ.get("DEFAULT_SHEET_ID", ""),
        default_sheet_tab=os.environ.get("DEFAULT_SHEET_TAB", "Sheet1"),
        telegram_bot_token=os.environ.get("TELEGRAM_BOT_TOKEN", ""),
        telegram_bot_token_secret_arn=os.environ.get("TELEGRAM_BOT_TOKEN_SECRET_ARN", ""),
        default_telegram_target=os.environ.get("DEFAULT_TELEGRAM_TARGET", ""),
        alert_on_not_sent=_get_bool(os.environ.get("ALERT_ON_NOT_SENT"), False),
        dedup_ttl_seconds=int(os.environ.get("DEDUP_TTL_SECONDS", "600")),
        max_context_chunks=int(os.environ.get("MAX_CONTEXT_CHUNKS", "6")),
        index_cache_ttl_seconds=int(os.environ.get("INDEX_CACHE_TTL_SECONDS", "600")),
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
    )
    return _SETTINGS
