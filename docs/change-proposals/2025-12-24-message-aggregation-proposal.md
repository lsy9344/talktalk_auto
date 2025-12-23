# Change Proposal: Message Aggregation System (30초 타임 윈도우)

## 메타데이터

| 항목 | 내용 |
|------|------|
| **제안일** | 2025-12-24 |
| **제안자** | System Architect |
| **우선순위** | High |
| **영향도** | Medium (메시지 처리 파이프라인 변경) |
| **예상 구현 기간** | 2-3 sprints |
| **상태** | Proposed |

---

## 1. 배경 (Background)

### 1.1 현재 상황

네이버 톡톡 메신저를 통한 자동 문의 응답 시스템은 현재 **각 메시지를 개별적으로 처리**하는 구조입니다.

**현재 아키텍처:**
```
사용자 메시지 → Ingest Lambda → SQS → Worker Lambda → RAG + LLM → 응답
    (개별)        (즉시 응답)    (버퍼)   (개별 처리)
```

**파이프라인 상태:** RECEIVED → QUEUED → PROCESSING → LOGGED → SENT/NOT_SENT

### 1.2 발견된 문제

고객이 메신저 사용 시 **하나의 질문을 여러 개의 메시지로 나눠서 보내는 패턴**이 관찰되었습니다.

**실제 사례:**

**패턴 A: 1문장 → 1메시지 (이상적)**
```
"내일 예약하려고 하는데 인화지가 몇장 제공되나요?"
```

**패턴 B: 1질문 → 여러 메시지 (실제 발생)**
```
메시지 1: "안녕하세요"
메시지 2: "내일 예약하려고 하는데"
메시지 3: "인화지가 총"
메시지 4: "몇장 제공되는지"
메시지 5: "문의드려요"
```

### 1.3 문제 영향

현재 시스템은 각 메시지를 독립적으로 처리하므로:

1. **문맥 손실**: "안녕하세요"만으로는 질문 의도 파악 불가
2. **불필요한 LLM 호출**: 각 메시지마다 RAG + LLM 실행 (비용 증가)
3. **응답 품질 저하**: 불완전한 질문에 대한 부적절한 응답 생성
4. **사용자 경험 저하**: 중간 메시지에 대한 불필요한 응답

**예시:**
- 메시지 "안녕하세요" → LLM: "안녕하세요! 무엇을 도와드릴까요?"
- 메시지 "내일 예약하려고 하는데" → LLM: "예약 관련 문의이신가요? 구체적으로..."
- 메시지 "인화지가 총" → LLM: "인화지 수량에 대해 문의하시는 건가요?"
- ❌ **실제로 원했던 것**: 전체 문맥을 이해한 하나의 정확한 답변

---

## 2. 제안 솔루션 (Proposed Solution)

### 2.1 핵심 아이디어: 시간 기반 메시지 집계 (Time-Window Aggregation)

**30초 타임 윈도우** 동안 동일 사용자의 메시지를 수집하여 하나의 질문으로 조합한 후 처리합니다.

### 2.2 목표 아키텍처

```
사용자 메시지들 → Ingest Lambda → SQS → Message Aggregator → Worker Lambda → RAG + LLM → 응답
  (여러 개)         (즉시 응답)    (버퍼)  (30초 수집/조합)    (통합 처리)
                                              ↓
                                        DynamoDB
                                    (집계 상태 관리)
```

### 2.3 동작 흐름

1. **첫 메시지 수신** (T=0s)
   - DynamoDB에 집계 세션 생성
   - 30초 타이머 시작 (SQS Delay Queue 활용)
   - 상태: AGGREGATING

2. **후속 메시지 수신** (T=5s, 10s, 15s...)
   - 동일 사용자의 활성 집계 세션에 메시지 추가
   - DynamoDB 업데이트

3. **타이머 만료** (T=30s)
   - 집계된 모든 메시지 결합
   - 조합된 텍스트로 RAG + LLM 처리
   - 하나의 통합 응답 생성

### 2.4 메시지 조합 예시

**입력 (5개 메시지):**
```
1. "안녕하세요"
2. "내일 예약하려고 하는데"
3. "인화지가 총"
4. "몇장 제공되는지"
5. "문의드려요"
```

**조합 결과:**
```
안녕하세요
내일 예약하려고 하는데
인화지가 총
몇장 제공되는지
문의드려요
```

**또는 (옵션: 스마트 조합):**
```
내일 예약하려고 하는데 인화지가 총 몇장 제공되는지 문의드려요
```

---

## 3. 기술적 접근 방법 (Technical Approach)

### 3.1 새로운 컴포넌트

#### A. DynamoDB 테이블: `AggregationState`

**목적:** 집계 세션 상태 관리

**스키마:**
```python
{
  "pk": "channel123#user456",          # Partition Key: channel_id + user_id
  "aggregation_id": "2025-12-24T10:30:00Z",  # Sort Key: 집계 시작 시간
  "messages": [
    {
      "timestamp": "2025-12-24T10:30:00Z",
      "text": "안녕하세요",
      "webhook_event": {...}  # 원본 webhook 이벤트
    },
    {
      "timestamp": "2025-12-24T10:30:05Z",
      "text": "내일 예약하려고 하는데",
      "webhook_event": {...}
    }
    # ... 최대 10개 메시지까지 수집 (안전장치)
  ],
  "status": "AGGREGATING",  # AGGREGATING | COMPLETED | CANCELLED
  "started_at": "2025-12-24T10:30:00Z",
  "expires_at": "2025-12-24T10:30:30Z",  # 30초 후
  "ttl": 1735123800  # 집계 완료 5분 후 자동 삭제
}
```

**인덱스:**
- PK: `{channel_id}#{user_id}` (사용자별 집계 조회)
- GSI (옵션): `status` (활성 집계 모니터링용)

#### B. SQS 큐: `AggregationTriggerQueue`

**목적:** 30초 후 집계 완료 트리거

**설정:**
- DelaySeconds: 30
- VisibilityTimeout: 60
- MessageRetentionPeriod: 300 (5분)

**메시지 포맷:**
```json
{
  "action": "FINALIZE_AGGREGATION",
  "user_key": "channel123#user456",
  "aggregation_id": "2025-12-24T10:30:00Z"
}
```

### 3.2 Worker Lambda 로직 변경

**기존:**
```python
def lambda_handler(event):
    webhook_event = parse_sqs_message(event)
    # 즉시 RAG + LLM 처리
    process_message(webhook_event)
```

**변경 후:**
```python
def lambda_handler(event):
    message = parse_sqs_message(event)

    if is_aggregation_trigger(message):
        # 30초 타이머 만료 - 집계 완료
        finalize_and_process_aggregation(message)
    else:
        # 일반 webhook 메시지
        webhook_event = parse_webhook(message)
        handle_aggregation(webhook_event)

def handle_aggregation(webhook_event):
    user_key = f"{channel_id}#{user_id}"
    agg_state = aggregation_repo.get_active(user_key)

    if not agg_state:
        # 첫 메시지 - 집계 시작
        aggregation_repo.create(user_key, webhook_event)
        send_delayed_trigger(user_key, delay=30)
    else:
        # 후속 메시지 - 집계에 추가
        aggregation_repo.add_message(user_key, webhook_event)

def finalize_and_process_aggregation(trigger_message):
    user_key = trigger_message['user_key']
    agg_state = aggregation_repo.get(user_key)

    if not agg_state or agg_state.status != 'AGGREGATING':
        return  # 이미 처리됨

    # 메시지 조합
    combined_text = combine_messages(agg_state.messages)

    # 기존 RAG + LLM 처리
    process_message(combined_text, original_events=agg_state.messages)

    # 집계 상태 정리
    aggregation_repo.complete(user_key)
```

### 3.3 메시지 조합 알고리즘

```python
def combine_messages(messages: List[Message]) -> str:
    """
    시간순으로 정렬된 메시지들을 하나의 텍스트로 조합

    규칙:
    1. 메시지 간 줄바꿈으로 연결
    2. 중복 인사말 제거 (선택적)
    3. 최대 길이 제한 (LLM 토큰 제한)
    4. 최종 문의 텍스트는 500자 이하 (500자 넘으면 뒤에서 500자만 사용)
    """
    # 시간순 정렬
    sorted_messages = sorted(messages, key=lambda m: m.timestamp)

    # 텍스트 추출
    texts = [m.text for m in sorted_messages if m.text]

    # 조합 (줄바꿈)
    combined = "\n".join(texts)

    # 옵션: 중복 인사말 제거
    # if combined.startswith("안녕하세요\n"):
    #     combined = combined[7:]  # "안녕하세요\n" 제거

    combined = combined.strip()

    # 최종 길이 제한: 500자
    if len(combined) > 500:
        combined = combined[-500:]

    return combined
```

---

## 4. 영향받는 컴포넌트 (Impact Analysis)

### 4.1 변경 필요 컴포넌트

| 컴포넌트 | 변경 유형 | 변경 내용 |
|---------|---------|---------|
| **Epic 2** | 수정 | Story 2.5 추가: Message Aggregation |
| **Worker Lambda** | 수정 | 집계 로직 추가, 타이머 처리 |
| **DynamoDB** | 신규 | AggregationState 테이블 생성 |
| **SQS** | 신규 | AggregationTriggerQueue 생성 |
| **SAM Template** | 수정 | 인프라 리소스 추가 |
| **Architecture 문서** | 수정 | Message Aggregator 컴포넌트 추가 |

### 4.2 변경 불필요 컴포넌트 (영향 없음)

- **Ingest Lambda**: 변경 없음 (기존대로 SQS 전송)
- **RAG 시스템**: 변경 없음 (조합된 텍스트 입력만 받음)
- **LLM 프롬프트**: 변경 없음 (또는 최소 변경)
- **Google Sheets 로깅**: 변경 없음
- **Telegram 알림**: 변경 없음

---

## 5. 예상 효과 (Expected Benefits)

### 5.1 기능적 개선

1. **문맥 이해 향상**: 전체 질문을 파악하여 정확한 응답 생성
2. **응답 품질 향상**: 완전한 질문에 대한 완전한 답변
3. **사용자 경험 개선**: 불필요한 중간 응답 제거

### 5.2 비용 절감

- **LLM 호출 감소**: 5개 메시지 → 1번 호출 (80% 절감)
- **RAG 검색 감소**: 벡터 검색 횟수 감소
- **예상 절감**: 월 $0.5 ~ $1.0 (메시지 패턴에 따라 다름)

### 5.3 성능 개선

- **처리량 감소**: 불필요한 중간 처리 제거
- **CloudWatch Logs 감소**: 로그 양 감소

---

## 6. 리스크 및 고려사항 (Risks & Considerations)

### 6.1 리스크

| 리스크 | 영향도 | 완화 방안 |
|-------|-------|---------|
| **응답 지연** (최대 30초) | High | 사용자에게 "답변 준비 중..." 타이핑 인디케이터 표시 (네이버 톡톡 API 지원 확인 필요) |
| **메시지 순서 보장** | Medium | DynamoDB timestamp 기반 정렬 |
| **집계 상태 관리 복잡도** | Medium | 명확한 상태 머신 설계, 충분한 테스트 |
| **타이머 정확도** | Low | SQS Delay는 최대 15분까지 정확, 30초는 안정적 |
| **동시성 이슈** (동일 사용자 메시지 동시 처리) | Medium | DynamoDB 조건부 쓰기, 낙관적 잠금 |

### 6.2 엣지 케이스

1. **30초 내 메시지 1개만 수신**
   - 처리: 정상적으로 단일 메시지 처리 (기존과 동일)

2. **30초 후 추가 메시지 수신**
   - 처리: 새로운 집계 세션 시작

3. **이미지/파일 메시지 수신 시**
   - 처리: 즉시 집계 종료 및 처리 (이미지는 조합 불가)

4. **메시지가 너무 많은 경우** (DoS 방지)
   - 처리: 최대 10개 메시지까지만 수집, 이후 무시 또는 즉시 처리

5. **타이머 만료 전 명확한 종료 신호**
   - 예: "이상입니다", "문의드립니다" 등의 종료 표현 감지
   - 처리: (옵션) 즉시 집계 종료 (Phase 2)

### 6.3 롤백 계획

**Feature Flag 도입:**
```python
# 환경 변수: ENABLE_MESSAGE_AGGREGATION
if os.getenv('ENABLE_MESSAGE_AGGREGATION', 'false') == 'true':
    handle_aggregation(webhook_event)
else:
    # 기존 즉시 처리 로직
    process_message(webhook_event)
```

**롤백 시나리오:**
1. Feature Flag를 `false`로 변경
2. Lambda 재배포 없이 즉시 기존 동작 복원
3. 활성 집계 세션은 자연스럽게 만료 (TTL)

---

## 7. 구현 계획 (Implementation Plan)

### 7.1 Phase 1: 기본 집계 (MVP)

**목표:** 30초 타임 윈도우 기반 메시지 수집 및 조합

**작업:**
1. DynamoDB 테이블 생성 (SAM template)
2. AggregationRepository 구현
3. Worker Lambda 집계 로직 추가
4. SQS Delay Queue 활용한 타이머 구현
5. 단순 메시지 조합 (줄바꿈 연결)
6. 테스트 작성

**예상 기간:** 1 sprint

### 7.2 Phase 2: 스마트 집계 (Enhancement)

**목표:** 종료 신호 감지, 스마트 조합

**작업:**
1. 종료 표현 감지 로직 추가 ("문의드립니다", "이상입니다" 등)
2. 스마트 메시지 조합 (중복 인사말 제거, 자연스러운 연결)
3. LLM 프롬프트 최적화 (조합된 메시지임을 명시)

**예상 기간:** 1 sprint

### 7.3 Phase 3: 모니터링 및 최적화

**목표:** 집계 효과 측정 및 최적화

**작업:**
1. 집계 성공률 메트릭 추가
2. 평균 집계 메시지 수 모니터링
3. 30초 타이머 최적화 (필요 시 조정)
4. 비용 절감 효과 측정

**예상 기간:** 0.5 sprint

---

## 8. 테스트 전략 (Testing Strategy)

### 8.1 유닛 테스트

- `combine_messages()` 함수 테스트
- `AggregationRepository` CRUD 테스트
- 타이머 트리거 메시지 파싱 테스트

### 8.2 통합 테스트

1. **단일 메시지 시나리오**
   - 입력: 1개 메시지
   - 기대: 30초 대기 후 정상 처리

2. **다중 메시지 시나리오**
   - 입력: 5개 메시지 (0s, 5s, 10s, 15s, 20s)
   - 기대: 30초 대기 후 조합된 텍스트로 처리

3. **타임아웃 후 추가 메시지**
   - 입력: 메시지 A (0s), 메시지 B (35s)
   - 기대: 메시지 A 처리 (30s), 메시지 B 새 집계 시작

4. **이미지 메시지 즉시 처리**
   - 입력: 텍스트 3개 + 이미지 1개
   - 기대: 이미지 수신 시 즉시 집계 종료

### 8.3 E2E 테스트

- TEST 모드에서 실제 네이버 톡톡 Webhook 시뮬레이션
- Google Sheets 로깅 확인
- Telegram 알림 확인

---

## 9. 성공 지표 (Success Metrics)

| 지표 | 현재 | 목표 | 측정 방법 |
|-----|------|------|---------|
| **LLM 호출 횟수** | 100% (모든 메시지) | 20-30% (집계 후) | CloudWatch Metrics |
| **평균 응답 품질** | Baseline | +20% 개선 | 수동 샘플링 평가 |
| **사용자 만족도** | Baseline | +15% 개선 | 피드백 수집 |
| **월 비용** | Baseline | -50% LLM 비용 | AWS Cost Explorer |
| **응답 지연 시간** | 2-5초 | 30-35초 (허용) | CloudWatch Metrics |

---

## 10. 대안 검토 (Alternatives Considered)

### 10.1 대안 A: 클라이언트 측 메시지 조합

**설명:** 네이버 톡톡 클라이언트에서 사용자가 엔터 키를 누를 때까지 대기

**장점:**
- 서버 측 복잡도 제거
- 즉시 응답 가능

**단점:**
- 네이버 톡톡 클라이언트 수정 불가능 (외부 서비스)
- ❌ **실현 불가능**

### 10.2 대안 B: LLM 기반 종료 감지

**설명:** 각 메시지를 LLM으로 분석하여 질문 완료 여부 판단

**장점:**
- 정확한 종료 시점 감지

**단점:**
- 모든 메시지마다 LLM 호출 (비용 증가)
- 레이턴시 증가
- ❌ **비용 효율성 낮음**

### 10.3 선택한 솔루션: 타임 윈도우 기반 집계

**이유:**
- ✅ 구현 단순
- ✅ 비용 효율적
- ✅ 대부분의 사용자 패턴에 적합
- ✅ 롤백 가능

---

## 11. 승인 및 다음 단계 (Approval & Next Steps)

### 11.1 승인 필요 사항

- [ ] 제품 오너 승인 (30초 지연 허용 여부)
- [ ] 아키텍트 승인 (기술적 접근 방법)
- [ ] 개발 팀 승인 (구현 계획)

### 11.2 다음 단계

1. **Epic 2 업데이트**: Story 2.5 추가
2. **Architecture 문서 업데이트**: Message Aggregator 컴포넌트 문서화
3. **Story 2.5 생성**: 상세 구현 계획 작성
4. **SAM Template 설계**: 인프라 리소스 정의
5. **개발 시작**: Phase 1 MVP 구현

---

## 12. 참고 문서 (References)

- **Epic 2**: `docs/prd/epic-2-message-processing-pipeline.md`
- **Architecture**: `docs/architecture.md`
- **Tech Stack**: `docs/architecture/tech-stack.md`
- **Ingest Lambda**: `src/functions/ingest/app.py`
- **Worker Lambda**: `src/functions/worker/`
- **PRD**: `docs/prd/`

---

**작성자:** BMad Master
**작성일:** 2025-12-24
**문서 버전:** 1.0
**상태:** Proposed → Pending Approval
