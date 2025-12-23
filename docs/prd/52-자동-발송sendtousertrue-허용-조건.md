# 5.2 자동 발송(send_to_user=true) 허용 조건

아래 모두 충족 시에만 발송:

1. `GLOBAL_MODE == PROD`
2. `CHANNEL_MODE[channel_id] == PROD`
3. `confidence >= threshold` (초기 권장 0.75~0.85로 보수적 시작)
4. `risk_level != HIGH`
5. `policy_flags`에 금지 항목 없음
