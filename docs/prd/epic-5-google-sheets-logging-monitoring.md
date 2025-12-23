# Epic 5: Google Sheets Logging & Monitoring

## Story 5.1: 시트 구성(권장)

* Google Spreadsheet 1개 파일
* 탭(시트) 2개 권장:

  * `inbox_log` : 모든 기록(질문/답변/상태)
  * `config_snapshot` : (선택) 현재 채널 모드/전역 모드 스냅샷(읽기용)

> 탭을 1개만 쓰고 싶으면 `inbox_log`만 운영해도 됩니다.

## Story 5.2: inbox_log 컬럼 정의(권장 스키마)

| 컬럼명                  | 타입       | 예시                        | 설명                                 |
| -------------------- | -------- | ------------------------- | ---------------------------------- |
| row_id               | string   | `20251219-000123`         | 내부 식별자(시간+증가값)                     |
| created_at_kst       | datetime | `2025-12-19 14:22:11`     | 기록 시각                              |
| channel_id           | string   | `wc******`                | 채널 식별                              |
| channel_name         | string   | `A스토어`                    | 사람이 알아보기 위한 이름                     |
| user_id              | string   | `al-...`                  | 톡톡 사용자 식별값(변하지 않는 값) ([GitHub][1]) |
| event                | string   | `send`                    | 이벤트명                               |
| question_raw         | string   | `교환 어떻게 해요?`              | 고객 원문(원문 저장 허용)                    |
| question_masked      | string   | `교환 어떻게 해요?`              | 로그/텔레그램용 마스킹 버전                    |
| kb_used              | string   | `doc123:c_04;doc999:c_02` | 사용한 chunk 요약(내부용)                  |
| draft_answer         | string   | `안녕하세요 😊 ...`            | LLM 답변 초안                          |
| confidence           | number   | `0.86`                    | 0~1                                |
| risk_level           | string   | `LOW`                     | LOW/MEDIUM/HIGH                    |
| send_to_user         | boolean  | `FALSE`                   | 자동 발송 여부(결과)                       |
| global_mode          | string   | `TEST`                    | TEST/PROD                          |
| channel_mode         | string   | `TEST`                    | TEST/PROD/DISABLED                 |
| action_taken         | string   | `NOT_SENT`                | NOT_SENT/SENT/FAILED               |
| talktalk_send_result | string   | `-`                       | PROD일 때 API 응답(성공/코드)              |
| telegram_alert_sent  | boolean  | `TRUE`                    | 알림 여부                              |
| telegram_reason      | string   | `KB 부족`                   | 알림 사유                              |
| latency_ms_total     | number   | `8421`                    | 처리 총 시간                            |
| error_summary        | string   | `-`                       | 오류 있으면 요약                          |

## Story 5.3: 운영 규칙

* **TEST 모드**: `send_to_user`는 항상 `FALSE`, `action_taken=NOT_SENT`
* **PROD 모드**: 발송 성공 시 `action_taken=SENT`, 실패 시 `FAILED` + Telegram 알림
* PII 정책:

  * `question_raw`는 원문 저장 허용(요구사항)
  * `question_masked`는 마스킹 적용(텔레그램/로그에 사용)

---
