# Epic 2: Message Processing Pipeline

## Story 2.1: 파이프라인 상태 머신

* `RECEIVED` (Webhook 수신)
* `QUEUED` (SQS 적재)
* `PROCESSING` (Worker 처리 중)
* `LOGGED` (Sheets 기록 완료)
* `SENT` (PROD 발송 성공)
* `NOT_SENT` (정책상 무응답)
* `ALERTED` (Telegram 전송 완료)
* `FAILED` (재시도 후 실패/데드레터)

## Story 2.2: 자동 발송(send_to_user=true) 허용 조건

아래 모두 충족 시에만 발송:

1. `GLOBAL_MODE == PROD`
2. `CHANNEL_MODE[channel_id] == PROD`
3. `confidence >= threshold` (초기 권장 0.75~0.85로 보수적 시작)
4. `risk_level != HIGH`
5. `policy_flags`에 금지 항목 없음

## Story 2.3: 무응답 + Telegram 알림 트리거(운영자 개입 필요)

* RAG 근거 부족(검색 결과 부실/유사도 낮음)
* 주문/결제/개인정보/분쟁 등 리스크 HIGH로 분류
* 이미지/복합 메시지인데 텍스트 부재
* 질문이 지나치게 짧거나("?", "ㅇㅇ", "문의요") 정보 부족
* LLM 출력 검증 실패(JSON 파싱 실패 등)
* 외부 연동 실패(OpenAI/Sheets/Send API 오류)

## Story 2.4: PROD 전송(보내기 API) 명세

### 2.4.1 요청 형태(공식 예시 기반)

```bash
curl -X POST \
  -H "Content-Type: application/json;charset=UTF-8" \
  -H "Authorization: <CHANNEL_AUTH_TOKEN>" \
  -d '{ "event": "send", "user": "<USER_ID>", "textContent": { "text": "hello world" } }' \
  "https://gw.talk.naver.com/chatbot/v1/event"
```

([GitHub][1])

* Authorization 토큰은 파트너센터에서 생성/재설정 가능 ([GitHub][1])
* Naver Cloud 문서에서도 이 값이 channel access token으로 사용됨을 언급 ([NCloud Docs][2])

### 2.4.2 비동기 처리 원칙

* Webhook은 200 OK로 즉시 응답 후, Worker에서 send API 호출
* 동기식은 5초 내 응답 가능할 때만 권장(공식) ([GitHub][1])

## Story 2.5: Message Aggregation (30초 타임 윈도우)

### 2.5.1 배경

고객이 하나의 질문을 여러 개의 메시지로 나눠서 보내는 패턴 발견:

**예시:**
```
메시지 1: "안녕하세요"
메시지 2: "내일 예약하려고 하는데"
메시지 3: "인화지가 총"
메시지 4: "몇장 제공되는지"
메시지 5: "문의드려요"
```

현재 시스템은 각 메시지를 독립적으로 처리하여 문맥 손실 발생.

### 2.5.2 목표

동일 사용자의 여러 메시지를 **30초 타임 윈도우** 동안 수집하여 하나의 질문으로 조합 후 처리.

### 2.5.3 요구사항

#### 기능 요구사항

1. **메시지 수집**
   * 첫 메시지 수신 시 30초 타이머 시작
   * 동일 `channel_id + user_id`의 후속 메시지 수집
   * 최대 10개 메시지까지 수집 (DoS 방지)

2. **집계 완료 조건**
   * 30초 타이머 만료 시
   * 이미지/파일 메시지 수신 시 즉시 종료 (조합 불가)
   * (Phase 2) 종료 표현 감지 시 ("문의드립니다", "이상입니다" 등)

3. **메시지 조합**
   * 시간순으로 정렬
   * 줄바꿈(`\n`)으로 연결
   * 최대 길이 제한 적용 (LLM 토큰 제한)
   * **최종 문의 텍스트는 500자 이하** (500자 넘으면 뒤에서 500자만 사용)

4. **통합 처리**
   * 조합된 텍스트로 기존 RAG + LLM 파이프라인 실행
   * 하나의 응답 생성

#### 비기능 요구사항

* **응답 지연**: 최대 30초 허용
* **메시지 순서 보장**: timestamp 기반 정렬
* **집계 상태 관리**: DynamoDB 활용
* **롤백 가능**: Feature Flag로 활성화/비활성화

### 2.5.4 기술 스펙

#### A. DynamoDB 테이블: `AggregationState`

**스키마:**
```python
{
  "pk": "{channel_id}#{user_id}",      # Partition Key
  "aggregation_id": "2025-12-24T...",  # Sort Key (시작 시간)
  "messages": [
    {
      "timestamp": "2025-12-24T10:30:00Z",
      "text": "안녕하세요",
      "webhook_event": {...}
    }
    # ... 최대 10개
  ],
  "status": "AGGREGATING",  # AGGREGATING | COMPLETED | CANCELLED
  "started_at": "2025-12-24T10:30:00Z",
  "expires_at": "2025-12-24T10:30:30Z",
  "ttl": 1735123800  # 집계 완료 5분 후 자동 삭제
}
```

**인덱스:**
* PK: `{channel_id}#{user_id}`
* GSI (옵션): `status` (모니터링용)

#### B. SQS 큐: `AggregationTriggerQueue`

**설정:**
* DelaySeconds: 30
* VisibilityTimeout: 60
* MessageRetentionPeriod: 300

**메시지 포맷:**
```json
{
  "action": "FINALIZE_AGGREGATION",
  "user_key": "channel123#user456",
  "aggregation_id": "2025-12-24T10:30:00Z"
}
```

#### C. Worker Lambda 로직 변경

**처리 흐름:**
1. SQS 메시지 수신
2. 메시지 유형 판별:
   * 집계 트리거 메시지 → 집계 완료 처리
   * Webhook 메시지 → 집계 로직 실행
3. 집계 로직:
   * 활성 집계 조회
   * 없으면: 집계 시작 + 30초 트리거 전송
   * 있으면: 메시지 추가
4. 집계 완료:
   * 메시지 조합
   * RAG + LLM 처리
   * 응답 생성

### 2.5.5 예외 처리

* **단일 메시지만 수신**: 30초 대기 후 정상 처리
* **타임아웃 후 추가 메시지**: 새로운 집계 세션 시작
* **이미지 메시지**: 즉시 집계 종료 및 처리
* **최대 메시지 수 초과**: 10개 이후 메시지 무시 또는 경고

### 2.5.6 파이프라인 상태 확장

기존 상태에 집계 관련 상태 추가 고려:

* `AGGREGATING` (집계 진행 중 - 30초 대기)
* 기존 상태는 집계 완료 후 적용

### 2.5.7 성공 지표

| 지표 | 목표 |
|-----|------|
| LLM 호출 횟수 감소 | 66-80% 감소 (평균 메시지 3-5개 기준) |
| 응답 품질 개선 | +20% |
| 월 비용 절감 | -50% LLM 비용 |

### 2.5.8 참고 문서

* **Change Proposal**: `docs/change-proposals/2025-12-24-message-aggregation-proposal.md`
* **Story**: `docs/stories/2.5.story.md`

---
