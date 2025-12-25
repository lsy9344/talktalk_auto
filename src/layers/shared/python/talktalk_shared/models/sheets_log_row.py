"""
Google Sheets inbox_log 로그 row 모델.

Story 5.2: inbox_log 컬럼 정의(권장 스키마)
PRD 8.2와 동일한 컬럼 순서를 유지합니다.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from pydantic import BaseModel, Field

# AC1: 컬럼 이름/순서를 PRD 8.2와 동일하게 유지
INBOX_LOG_COLUMNS: list[str] = [
    "row_id",
    "created_at_kst",
    "channel_id",
    "channel_name",
    "user_id",
    "event",
    "aggregation_id",
    "message_count",
    "question_raw",
    "question_masked",
    "kb_used",
    "draft_answer",
    "confidence",
    "risk_level",
    "send_to_user",
    "global_mode",
    "channel_mode",
    "action_taken",
    "talktalk_send_result",
    "telegram_alert_sent",
    "telegram_reason",
    "latency_ms_total",
    "error_summary",
]


def truncate_from_end(text: str, max_length: int = 500) -> str:
    """
    AC3: 텍스트를 500자로 제한 (뒤에서 500자만 사용).

    Args:
        text: 원본 텍스트
        max_length: 최대 길이 (기본 500자)

    Returns:
        뒤에서 max_length만큼 잘린 텍스트
    """
    if len(text) <= max_length:
        return text
    return text[-max_length:]


def combine_messages(messages: list[str]) -> str:
    """
    AC3: 메시지 조합 - 시간순 정렬 후 줄바꿈(`\\n`)으로 연결.

    Args:
        messages: 메시지 리스트 (이미 시간순 정렬 가정)

    Returns:
        줄바꿈으로 연결된 텍스트
    """
    return "\n".join(messages)


class SheetsLogRow(BaseModel):
    """
    AC2: Google Sheets inbox_log 로그 row 1줄을 나타내는 도메인 모델.

    PRD 8.2 컬럼 스키마와 1:1 매핑.
    """

    # 1. row_id
    row_id: str = Field(
        ...,
        description="내부 식별자 (YYYYMMDD-######). 예: 20251219-000123",
    )

    # 2. created_at_kst
    created_at_kst: str = Field(
        ...,
        description="기록 시각 (KST, YYYY-MM-DD HH:MM:SS). 예: 2025-12-19 14:22:11",
    )

    # 3. channel_id
    channel_id: str = Field(..., description="채널 식별. 예: wc******")

    # 4. channel_name
    channel_name: str = Field(..., description="사람이 알아보기 위한 이름. 예: A스토어")

    # 5. user_id
    user_id: str = Field(..., description="톡톡 사용자 식별값. 예: al-...")

    # 6. event
    event: str = Field(..., description="이벤트명. 예: send")

    # 7. aggregation_id
    aggregation_id: str = Field(
        ...,
        description="메시지 조합 세션 id (첫 메시지 시각). 단일 메시지는 '-'",
    )

    # 8. message_count
    message_count: int = Field(
        ...,
        description="이번 질문에 모인 메시지 수. 단일 메시지는 1",
    )

    # 9. question_raw
    question_raw: str = Field(
        ...,
        description="고객 원문 (조합 시 \\n 연결, 500자 제한 - 넘으면 뒤에서 500자만)",
    )

    # 10. question_masked
    question_masked: str = Field(
        ...,
        description="로그/텔레그램용 마스킹 버전 (조합/500자 제한 동일)",
    )

    # 11. kb_used
    kb_used: str = Field(..., description="사용한 chunk 요약(내부용). 예: doc123:c_04;doc999:c_02")

    # 12. draft_answer
    draft_answer: str = Field(..., description="LLM 답변 초안. 예: 안녕하세요 ...")

    # 13. confidence
    confidence: float = Field(..., description="0~1")

    # 14. risk_level
    risk_level: str = Field(..., description="LOW/MEDIUM/HIGH")

    # 15. send_to_user
    send_to_user: bool = Field(..., description="자동 발송 여부(결과)")

    # 16. global_mode
    global_mode: str = Field(..., description="TEST/PROD")

    # 17. channel_mode
    channel_mode: str = Field(..., description="TEST/PROD/DISABLED")

    # 18. action_taken
    action_taken: str = Field(..., description="NOT_SENT/SENT/FAILED")

    # 19. talktalk_send_result
    talktalk_send_result: str = Field(
        ...,
        description="PROD일 때 API 응답(성공/코드). 없으면 '-'",
    )

    # 20. telegram_alert_sent
    telegram_alert_sent: bool = Field(..., description="알림 여부")

    # 21. telegram_reason
    telegram_reason: str = Field(..., description="알림 사유. 없으면 '-'")

    # 22. latency_ms_total
    latency_ms_total: int = Field(
        ...,
        description="처리 총 시간 (메시지 조합 대기 포함, ms)",
    )

    # 23. error_summary
    error_summary: str = Field(..., description="오류 있으면 요약. 없으면 '-'")

    def to_sheets_values(self) -> list:
        """
        AC2: 컬럼 순서대로 값 리스트를 만든다.

        Google Sheets append API에 그대로 넣을 수 있는 형태.

        Returns:
            컬럼 순서대로 정렬된 값 리스트 (23개)
        """
        return [
            self.row_id,  # 1
            self.created_at_kst,  # 2
            self.channel_id,  # 3
            self.channel_name,  # 4
            self.user_id,  # 5
            self.event,  # 6
            self.aggregation_id,  # 7
            self.message_count,  # 8
            self.question_raw,  # 9
            self.question_masked,  # 10
            self.kb_used,  # 11
            self.draft_answer,  # 12
            self.confidence,  # 13
            self.risk_level,  # 14
            self.send_to_user,  # 15
            self.global_mode,  # 16
            self.channel_mode,  # 17
            self.action_taken,  # 18
            self.talktalk_send_result,  # 19
            self.telegram_alert_sent,  # 20
            self.telegram_reason,  # 21
            self.latency_ms_total,  # 22
            self.error_summary,  # 23
        ]

    @staticmethod
    def generate_row_id() -> str:
        """
        AC1: row_id를 YYYYMMDD-###### 형태로 생성.

        KST 날짜 + 6자리 증가값 (타임스탬프 기반).

        Returns:
            예: "20251219-000123"
        """
        kst = timezone(timedelta(hours=9))
        now_kst = datetime.now(kst)
        date_part = now_kst.strftime("%Y%m%d")
        # 6자리 값: 시간 기반 (HHMMSS)
        time_part = now_kst.strftime("%H%M%S")
        return f"{date_part}-{time_part}"

    @staticmethod
    def format_created_at_kst(dt: Optional[datetime] = None) -> str:
        """
        AC1: created_at_kst를 YYYY-MM-DD HH:MM:SS 형태로 포맷.

        Args:
            dt: datetime 객체 (None이면 현재 시각)

        Returns:
            예: "2025-12-19 14:22:11"
        """
        kst = timezone(timedelta(hours=9))
        if dt is None:
            dt = datetime.now(kst)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
