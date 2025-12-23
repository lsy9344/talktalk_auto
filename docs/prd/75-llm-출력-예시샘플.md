# 7.5 LLM 출력 예시(샘플)

## (A) 자동 발송 가능(LOW)

```json
{
  "draft_answer": "안녕하세요 😊 교환은 상품 수령 후 7일 이내에 가능하세요. 교환 접수는 ① 주문번호 ② 교환 사유 ③ 희망 옵션을 알려주시면 순서대로 도와드릴게요!",
  "confidence": 0.86,
  "send_to_user": true,
  "needs_operator": false,
  "risk_level": "LOW",
  "reasons": ["KB에 교환 기간/절차가 명확히 기재됨"],
  "citations": [
    {"doc_id":"doc123","doc_title":"교환/환불 정책","section_path":"교환 > 접수 방법","chunk_id":"c_04"}
  ],
  "followup_questions_for_operator": [],
  "suggested_quick_reply": ["주문번호를 알려주세요", "교환 사유를 알려주세요"]
}
```

## (B) 애매/리스크(무응답 + Telegram)

```json
{
  "draft_answer": "확인해보면 더 정확히 안내드릴 수 있어요 😊 주문번호(또는 구매 채널)와 문제가 된 상황(불량/오배송/단순변심 등)을 알려주시면 처리 절차를 정리해드릴게요.",
  "confidence": 0.42,
  "send_to_user": false,
  "needs_operator": true,
  "risk_level": "HIGH",
  "reasons": ["주문/개인정보/결제 관련 가능성", "KB 근거 부족"],
  "citations": [],
  "followup_questions_for_operator": ["고객 주문번호 확인 필요", "결제/환불 상태 확인 필요", "채널별 정책 예외 여부 확인 필요"],
  "suggested_quick_reply": ["주문번호를 알려주세요", "구매처(스마트스토어/자사몰)를 알려주세요"]
}
```

---
