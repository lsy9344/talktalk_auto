# Epic 7: Testing & Production Deployment

## Story 7.1: TEST 모드 필수 통과 조건

* 톡톡으로 **자동 발송 0건**
* `send` 이벤트 수신 시 **Sheets row 100% 생성**
* 불확실/오류 케이스에서 Telegram 알림이 **누락 없이 도착**
* Webhook은 타임아웃 없이 안정적으로 200 OK 반환(3s/5s 제약 준수) ([GitHub][1])

## Story 7.2: PROD 전환 전 "안전장치"

* threshold를 높게(보수적으로) 시작: 0.85 권장
* risk_level HIGH는 무조건 무응답+알림
* echo 이벤트 비활성 유지(루프 위험) ([GitHub][1])

## Story 7.3: Go-Live 절차(운영 관점)

1. 16개 채널 모두 `channel_mode=TEST`, `global_mode=TEST`로 시작
2. 1~2주간 Sheet 검증(초안 품질/근거 적절성/알림 빈도 확인)
3. 채널별로 문서 보강(월 1회 업데이트 플로우에 반영)
4. 일부 채널만 `channel_mode=PROD`로 올려 "부분 준비"
5. 마지막에 `global_mode=PROD` 전환
6. 초기 1~3일은 Telegram 알림을 촘촘히 모니터링하며 threshold 튜닝

## Story 7.4: 구현자에게 중요한 메모(실수 방지)

* `user_id`는 변하지 않는 사용자 식별값으로 문서에 명시되어 있으며(대화 상대 식별), 이를 키로 상태/중복방지를 설계합니다. ([GitHub][1])
* `send` 이벤트는 text/image/composite 중 **하나만 선택**해야 합니다(발송 시). ([GitHub][1])
* echo는 루프 위험이 명시되어 있으므로 기본 비활성 권장 ([GitHub][1])
* Webhook 타임아웃(3s/5s) 때문에 "즉시 ACK + 비동기"가 안전합니다. ([GitHub][1])

---

원하면 다음 단계로 **PRD v1.2**도 바로 확장해드릴 수 있어요(질문 없이 진행 가능):

* "채널별 금지 키워드/리스크 룰" 초기 세트(환불/분쟁/개인정보 등)
* "RAG 품질을 올리는 문서 작성 가이드(운영자용)"
* "Sheet 기반으로 간단한 QA 워크플로(검수 상태: PASS/FAIL/수정필요)" 설계

원하시는 방향이 **(A) 리스크 룰부터**인지, **(B) 문서 작성 가이드부터**인지, 아니면 **둘 다**인지 한 줄로만 답 주시면 그걸로 이어서 v1.2까지 정리해드릴게요.

[1]: https://github.com/navertalk/chatbot-api "GitHub - navertalk/chatbot-api: 네이버톡톡 챗봇API V1"
[2]: https://guide.ncloud-docs.com/release-20250918/docs/en/chatbot-chatbot-5-3 "Connect to TalkTalk"
