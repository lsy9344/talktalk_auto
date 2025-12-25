# Implementation Notes - 실수 방지 메모

네이버 톡톡(TalkTalk) 연동에서 자주 실수하는 포인트를 정리한 문서입니다. 운영/배포 전에 장애나 무한 루프를 방지하기 위해 작성되었습니다.

> **참고**: 이 문서는 시스템 구현자를 위한 핵심 주의사항입니다. 전체 아키텍처는 [architecture.md](../architecture.md)를 참고하세요.

---

## 1. `user_id`는 변하지 않는 사용자 식별값

### 핵심 원칙

- **`user_id`는 영구적이고 불변하는 사용자 식별값입니다.**
- 톡톡 채널 내에서 동일 사용자는 항상 같은 `user_id`를 가집니다.
- 이 값은 상태 관리 및 중복 방지 키 설계에 필수적으로 사용됩니다.

### 시스템에서의 사용

**중복 방지 키 (DeduplicationRecord):**
```python
dedup_key = f"{channel_id}#{user_id}#{message_hash}"
```
- `channel_id`: 톡톡 채널 식별자
- `user_id`: 사용자 영구 식별값 (변하지 않음)
- `message_hash`: 메시지 내용 해시

**집계 상태 키 (AggregationState):**
```python
pk = f"{channel_id}#{user_id}"
```

### 관련 코드 위치

- **중복 방지 Repository**: `src/layers/shared/python/talktalk_shared/repositories/deduplication.py`
- **테스트**: `tests/unit/test_deduplication.py`
- **아키텍처 문서**: [docs/architecture.md#deduplicationrecord-중복-방지](../architecture.md#deduplicationrecord-중복-방지)

### 주의사항

❌ **잘못된 사용**:
```python
# user_id를 세션 키처럼 취급 (잘못됨)
session_key = f"{user_id}_{timestamp}"
```

✅ **올바른 사용**:
```python
# user_id를 영구적인 사용자 식별값으로 사용
user_key = f"{channel_id}#{user_id}"
```

---

## 2. Send API: text/image/composite 중 하나만 선택

### 핵심 원칙

- **`send` 이벤트로 메시지를 보낼 때는 `textContent`, `imageContent`, `compositeContent` 중 정확히 하나만 포함해야 합니다.**
- 여러 타입을 동시에 사용하면 API 오류가 발생합니다.

### 현재 구현

**현재 시스템은 `textContent`만 사용합니다:**

```python
payload = {
    "event": "send",
    "user": user_id,
    "textContent": {
        "text": text
    }
}
# imageContent, compositeContent는 포함하지 않음
```

### 관련 코드 위치

- **TalkTalk Send API Client**: `src/layers/shared/python/talktalk_shared/clients/talktalk_client.py`
  - `send_text_message()` 메서드 (88-92줄)
- **테스트**: `tests/unit/test_talktalk_client.py`
  - `test_send_text_message_success_200()` - payload 검증 (38-41줄)
  - `test_send_text_message_only_textcontent_no_image_or_composite()` - 타입 단독성 검증
- **아키텍처 문서**: [docs/architecture.md#naver-talktalk-send-api](../architecture.md#naver-talktalk-send-api)

### 향후 확장 시 주의사항

향후 이미지나 복합 메시지를 추가할 때도 **한 번에 하나의 타입만** 전송해야 합니다:

```python
# 이미지 메시지 예시 (향후 구현 시)
payload = {
    "event": "send",
    "user": user_id,
    "imageContent": {
        "imageUrl": "https://...",
        "imageLink": "https://..."
    }
    # textContent는 포함하지 않음
}
```

### 테스트 검증

유닛 테스트에서 다음을 검증합니다:
- ✅ `textContent`가 존재함
- ✅ `imageContent`가 없음
- ✅ `compositeContent`가 없음

---

## 3. `echo` 이벤트: 무한 루프 위험

### 핵심 원칙

- **`echo` 이벤트는 "우리가 보낸 메시지"가 다시 Webhook으로 들어오는 이벤트입니다.**
- 처리하지 않으면 **무한 루프**가 발생할 수 있습니다:
  ```
  고객 질문 → 봇 응답 (send) → echo 이벤트 수신 → 또 응답 → echo → 무한 반복
  ```

### 권장 설정

**✅ 가장 안전한 방법: 네이버 파트너센터에서 `echo` 이벤트 비활성화**

1. 네이버 톡톡 파트너센터 접속
2. 채널 설정 → Webhook 이벤트 설정
3. `echo` 이벤트 체크 해제 (비활성화)

### 코드 레벨 방어

**Ingest Lambda에서 `send` 이벤트만 처리:**

```python
# src/functions/ingest/app.py
if event_type != "send":
    logger.info("Ignoring non-send event", extra={"event": event_type})
    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Event ignored"})
    }
    # SQS enqueue도 하지 않음
```

### 관련 코드 위치

- **Ingest Lambda**: `src/functions/ingest/app.py` - 이벤트 필터링 로직
- **테스트**: `tests/unit/test_ingest_lambda.py`
  - `test_ingest_ignores_echo_event()`
  - `test_ingest_ignores_open_event()`
  - `test_ingest_ignores_leave_event()`
- **아키텍처 문서**: [docs/architecture.md#naver-talktalk-webhook-api](../architecture.md#naver-talktalk-webhook-api)

### 처리 흐름

```
echo/open/leave 이벤트 → Ingest Lambda
                              ↓
                        200 OK 즉시 반환
                              ↓
                    SQS enqueue 하지 않음 (처리 중단)
```

### 주의사항

- ⚠️ `echo` 이벤트를 활성화한 채로 배포하면 무한 루프 위험
- ✅ 파트너센터에서 비활성화 + 코드에서도 무시 (이중 방어)

---

## 4. Webhook 타임아웃: 즉시 200 OK + 비동기 처리

### 핵심 원칙

- **네이버 톡톡 Webhook은 엄격한 타임아웃을 가지고 있습니다:**
  - Connection timeout: **3초**
  - Read timeout: **5초**
- **5초 안에 200 OK를 반환하지 않으면 톡톡이 재시도 → 중복 처리 발생**

### 시스템 설계 원칙

**"즉시 ACK + 비동기 처리" 패턴:**

```
Webhook 요청 → Ingest Lambda (가볍게 검증)
                     ↓
               SQS에 메시지 enqueue
                     ↓
          200 OK 즉시 반환 (< 1초)

SQS → Worker Lambda (무거운 처리)
           ↓
      RAG + LLM + Sheets + Send API
      (30~120초 소요 가능)
```

### 타이밍 목표

| 단계 | 목표 시간 | 비고 |
|-----|----------|------|
| Ingest Lambda 전체 | **< 1초** | 스키마 검증 + SQS enqueue |
| SQS enqueue | < 100ms | 네이티브 AWS 서비스 |
| 200 OK 반환 | < 1초 | 톡톡 타임아웃(5초) 대비 충분한 여유 |
| Worker Lambda | 30~120초 | 비동기 처리 (타임아웃 무관) |

### Ingest Lambda 구현 원칙

**✅ 해야 할 일 (가벼운 작업만):**
- 스키마 검증 (Pydantic)
- 채널 활성화 확인 (DynamoDB 1회 조회)
- 중복 체크 (DynamoDB 1회 조회)
- SQS enqueue
- 200 OK 반환

**❌ 하지 말아야 할 일 (무거운 작업):**
- OpenAI API 호출
- Google Docs/Sheets 접근
- RAG 검색
- LLM 답변 생성
- 복잡한 비즈니스 로직

### 관련 코드 위치

- **Ingest Lambda**: `src/functions/ingest/app.py`
  - 즉시 ACK 패턴 구현
- **Worker Lambda**: `src/functions/worker/app.py`
  - 비동기 무거운 처리
- **테스트**: `tests/unit/test_ingest_lambda.py`
  - 응답 시간 검증은 통합 테스트에서 수행
- **아키텍처 문서**: [docs/architecture.md#naver-talktalk-webhook-api](../architecture.md#naver-talktalk-webhook-api)

### 타임아웃 실패 시 영향

**문제점:**
- 톡톡이 Webhook 재시도 → 동일 메시지 중복 수신
- 중복 방지 로직(DeduplicationRecord)이 있어도 불필요한 부하 발생

**해결책:**
- Ingest Lambda는 **항상 가볍게 유지**
- 무거운 작업은 **모두 Worker Lambda로 위임**

### 중복 방지 메커니즘

타임아웃으로 인한 재시도에도 안전:
```python
# 중복 체크 (DynamoDB - TTL 10분)
dedup_key = f"{channel_id}#{user_id}#{message_hash}"
if dedup_repo.exists(dedup_key):
    return {"statusCode": 200, "body": "Duplicate - ignored"}
```

---

## 참고 자료

### 관련 문서
- [PRD - 구현자에게 중요한 메모](../prd/13-구현자에게-중요한-메모실수-방지.md)
- [Architecture - Naver TalkTalk Webhook API](../architecture.md#naver-talktalk-webhook-api)
- [Architecture - Naver TalkTalk Send API](../architecture.md#naver-talktalk-send-api)
- [Story 7.4](../stories/7.4.story.md) - 이 문서 작성 배경

### 코드 위치 요약

| 주제 | 주요 파일 |
|-----|---------|
| **user_id 사용** | `repositories/deduplication.py` |
| **Send API (text만)** | `clients/talktalk_client.py` |
| **echo 이벤트 무시** | `functions/ingest/app.py` |
| **즉시 ACK 패턴** | `functions/ingest/app.py` |
| **테스트** | `tests/unit/test_*.py` |

### 버전 이력

| 날짜 | 버전 | 변경 내용 |
|-----|------|----------|
| 2025-12-26 | 1.0 | 초기 작성 (Story 7.4) |
