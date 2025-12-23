# 5.2 자동 발송(send_to_user=true) 허용 조건

아래 모두 충족 시에만 발송:

1. `GLOBAL_MODE == PROD`
2. `CHANNEL_MODE[channel_id] == PROD`
3. `confidence >= threshold` (초기 권장 0.75~0.85로 보수적 시작)
4. `risk_level != HIGH`
5. `policy_flags`에 금지 항목 없음

* (메시지 조합 사용 시) 위 판단은 **조합된 최종 질문** 기준으로 합니다. (Epic 2 / Story 2.5)
