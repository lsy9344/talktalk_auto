# Sprint Change Proposal: Story 2.4 (PO 검토 반영)

## 1) 이슈 요약

Story 2.4는 큰 문제는 없지만, 개발자가 헷갈릴 수 있는 부분이 3개 있었습니다.

1. Send API 실패 시 Telegram 알림을 “누가/어디서” 보내는지 애매함
2. “보내도 됨” 조건일 때만 Send API 호출되는지 테스트가 빠져 있음
3. 로컬/테스트에서 토큰을 인자로 넣는 방법이 Task에 더 명확히 적혀 있으면 좋음

## 2) 영향 범위

- Epic 영향: 없음 (문서 보완 수준)
- 바뀌는 아티팩트:
  - [x] `docs/stories/2.4.story.md` (수정)
  - [ ] PRD/Architecture (변경 없음)

## 3) 추천 진행 방법

- Option 1 (Direct Adjustment): [x] 선택
- Option 2 (Rollback): [N/A]
- Option 3 (MVP 재조정): [N/A]

## 4) 구체 수정 내용 (Story 2.4)

### A. Task 3 명확화

- `send_answer_if_allowed(...)` 위치를 파일로 고정: `src/functions/worker/send_answer.py`
- 로컬/테스트에서 토큰을 바로 넣을 수 있는 옵션 인자 추가 안내
- 실패 시 `E006`을 상위로 넘기고, **이 함수 안에서 Telegram을 직접 보내지 않음**을 명시

### B. Task 4 테스트 추가

- `tests/unit/test_send_answer_if_allowed.py` 추가:
  - `send_to_user=true` + `action="SEND_LOG_NO_ALERT"`일 때만 Send API 호출되는지 검증

### C. Change Log 업데이트

- 1.3 버전 항목 추가

## 5) 체크리스트 기록(요약)

- 1. Trigger/Context: [x] PO 검토(Should-Fix) 반영 필요
- 2. Epic 영향: [x] 영향 없음
- 3. 아티팩트 영향: [x] Story 문서만 수정
- 4. Path Forward: [x] Direct Adjustment

## 6) 다음 단계

- 이 변경은 문서 보완이 끝입니다.
- 개발(코드 작업)은 `dev` 에이전트가 Story 2.4가 `Approved`가 된 뒤 진행하면 됩니다.
