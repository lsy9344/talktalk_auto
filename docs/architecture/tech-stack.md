# Tech Stack

이 문서는 `docs/architecture.md`에서 **Tech Stack** 부분만 따로 뽑아 만든 파일입니다.

## 클라우드 인프라

- **Provider:** AWS
- **핵심 서비스:** Lambda, API Gateway, SQS, DynamoDB, S3, EventBridge, SSM Parameter Store
- **배포 리전:** ap-northeast-2 (서울)

## 기술 스택 테이블

| 카테고리 | 기술 | 버전 | 용도 | 선택 근거 |
|---------|------|------|------|----------|
| **언어** | Python | 3.11 | 주 개발 언어 | AWS Lambda 안정적 지원, RAG/ML 라이브러리 생태계 최고, 개발 생산성 |
| **런타임** | AWS Lambda Python | 3.11 | 서버리스 실행 환경 | 초저비용 (월 10-30건 처리시 프리티어), 자동 스케일링, 인프라 관리 불필요 |
| **IaC** | AWS SAM | 1.108.0+ | 인프라 코드화 | Lambda 특화 도구, YAML 간단, CloudFormation 기반, 로컬 테스트 지원 |
| **패키지 관리** | pip | 23.3+ | 의존성 관리 | requirements.txt 방식, Lambda 배포 최적화, 추가 도구 불필요 |
| **벡터 검색** | FAISS (CPU) | 1.7.4 | 벡터 유사도 검색 | PDF 5장 수준 소량 데이터에도 효율적, 무료, S3 저장 가능 |
| **임베딩 모델** | OpenAI text-embedding-3-small | API | 텍스트 벡터화 | $0.02/1M tokens (월 $0.05 미만 예상), 뛰어난 품질, 관리 불필요 |
| **LLM** | OpenAI gpt-4o-mini | API | 답변 생성 | PRD 명시, 저비용 ($0.150/1M input tokens), 한국어 성능 우수 |
| **데이터베이스** | DynamoDB | On-Demand | 채널 설정/중복 방지 | 완전 관리형, 온디맨드 요금제 (월 <$1 예상), 서버리스 친화적 |
| **메시지 큐** | SQS Standard | - | 이벤트 버퍼링 | 저비용 (100만건/월 무료), 높은 처리량, Lambda 네이티브 통합 |
| **스토리지** | S3 Standard | - | 벡터 인덱스 저장 | 극소량 데이터 (<5MB) 저장 비용 무시 가능, 내구성 99.999999999% |
| **스케줄러** | EventBridge Scheduler | - | 주간 문서 동기화 | 완전 관리형, 크론 표현식 지원, Lambda 트리거 |
| **비밀 관리** | AWS SSM Parameter Store (SecureString) | - | API 키/토큰 저장 | 비용 절감, Lambda IAM 통합, 암호화 |
| **API 클라이언트 (OpenAI)** | openai | 1.10.0+ | OpenAI API 호출 | 공식 SDK, async 지원, 타입 힌트 |
| **API 클라이언트 (Google)** | google-api-python-client | 2.111.0+ | Google Docs/Sheets API | 공식 SDK, OAuth2 지원 |
| **HTTP 클라이언트** | httpx | 0.26.0+ | Naver TalkTalk API | async 지원, requests 대비 빠름, 타임아웃 제어 우수 |
| **텔레그램 봇** | python-telegram-bot | 20.7+ | 운영자 알림 | 공식 라이브러리, async 지원, 메시지 포맷팅 |
| **청킹/파싱** | langchain-text-splitters | 0.0.1+ | 문서 청킹 | 한국어 지원, 다양한 분할 전략, PDF 5장 수준에 충분 |
| **PDF 파싱** | PyPDF2 | 3.0.1+ | PDF 텍스트 추출 | 경량, 간단한 PDF에 충분 (복잡한 레이아웃 없음 가정) |
| **테스트 프레임워크** | pytest | 7.4.3+ | 유닛/통합 테스트 | 사실상 표준, 플러그인 생태계, parametrize 지원 |
| **모킹** | pytest-mock | 3.12.0+ | 외부 API 모킹 | pytest 통합, unittest.mock 래퍼 |
| **린터/포매터** | ruff | 0.1.9+ | 코드 품질 | Rust 기반 초고속 (Flake8/Black 대체), 설정 간단 |
| **타입 체크** | mypy | 1.8.0+ | 정적 타입 검증 | 타입 힌트 오류 사전 발견, 코드 품질 향상 |
| **환경 변수** | python-dotenv | 1.0.0+ | 로컬 개발 환경 설정 | .env 파일 로드, Lambda 환경 변수와 일관성 |
| **로깅** | Python logging | 내장 | 구조화된 로그 | 표준 라이브러리, CloudWatch Logs 통합, JSON 포맷 지원 |
| **모니터링** | CloudWatch Logs/Metrics | - | 로그/메트릭 수집 | Lambda 네이티브, 7일 보관 (비용 절감) |

## 메시지 집계 (Message Aggregation)

**도입 시기:** Story 2.5 (30초 타임 윈도우)

### 목적

동일 사용자가 하나의 질문을 여러 메시지로 나눠 보낼 때, 30초 동안 수집하여 하나의 질문으로 조합 후 처리.

### 기술 스택

| 컴포넌트 | 기술 | 버전/설정 | 용도 | 선택 근거 |
|---------|------|---------|------|----------|
| **집계 상태 저장소** | DynamoDB | On-Demand | 30초 타임 윈도우 동안 메시지 수집 상태 관리 | 서버리스 친화적, 낮은 비용, TTL 자동 삭제 |
| **타이머 관리** | SQS Delay Queue | DelaySeconds=30 | 30초 후 집계 완료 트리거 | 구조 단순, Lambda 네이티브 통합, 추가 비용 없음 |

### 아키텍처 패턴

**Before (즉시 처리):**
```
사용자 메시지 → Ingest → SQS → Worker → RAG + LLM → 응답
    (개별)                              (개별 처리)
```

**After (시간 기반 집계):**
```
사용자 메시지들 → Ingest → SQS → Message Aggregator → Worker → RAG + LLM → 응답
  (여러 개)                        (30초 수집/조합)          (통합 처리)
                                         ↓
                                   DynamoDB
                               (집계 상태 관리)
                                         ↓
                              SQS Delay Queue (30s)
                                  (타이머 트리거)
```

### DynamoDB 테이블: AggregationState

**테이블명:** `{StackName}-AggregationState`

**용량 모드:** On-Demand (예상 월간 비용: <$0.50)

**스키마:**
```python
{
  "pk": "{channel_id}#{user_id}",      # Partition Key
  "aggregation_id": "2025-12-24T...",  # Sort Key (ISO 8601 timestamp)
  "messages": [                         # List (최대 10개)
    {
      "timestamp": "2025-12-24T10:30:00.123Z",
      "text": "안녕하세요",
      "webhook_event": {...}  # 원본 이벤트 전체 저장
    }
  ],
  "status": "AGGREGATING",  # AGGREGATING | COMPLETED | CANCELLED
  "started_at": "2025-12-24T10:30:00Z",
  "expires_at": "2025-12-24T10:30:30Z",
  "message_count": 5,
  "ttl": 1735123800  # Unix timestamp (집계 완료 5분 후 자동 삭제)
}
```

**인덱스:**
- Primary Key: `pk` (Partition), `aggregation_id` (Sort)
- GSI (옵션): `status-index` (모니터링용)
- TTL Attribute: `ttl` (5분 후 자동 삭제)

**읽기/쓰기 패턴:**
- **쓰기**: 메시지 수신마다 (30초 동안 평균 3-5회)
- **읽기**: 메시지 수신마다 + 타이머 만료 시 (30초 동안 평균 3-5회 + 1회)
- **삭제**: TTL 자동 삭제 (수동 삭제 불필요)

### SQS 큐: AggregationTriggerQueue

**큐명:** `{StackName}-AggregationTriggerQueue`

**설정:**
```yaml
DelaySeconds: 30               # 기본 30초 지연 (타이머)
VisibilityTimeout: 60          # 처리 시간 충분히 확보
MessageRetentionPeriod: 300    # 5분 (집계 완료 후 불필요)
ReceiveMessageWaitTime: 0      # Long polling 불필요
```

**메시지 포맷:**
```json
{
  "action": "FINALIZE_AGGREGATION",
  "user_key": "channel123#user456",
  "aggregation_id": "2025-12-24T10:30:00Z",
  "started_at": "2025-12-24T10:30:00Z"
}
```

**Lambda 트리거:**
- Worker Lambda가 WorkerQueue와 AggregationTriggerQueue 모두 구독
- 메시지 유형에 따라 처리 로직 분기

### 비용 추정 (월간)

**시나리오:** 일 30건 문의, 평균 메시지 3개로 분할

- **메시지 수**: 30건 × 3메시지 = 90개/일 → 2,700개/월
- **집계 세션**: 30건/일 → 900건/월

**DynamoDB 비용:**
- 쓰기: 2,700 writes (메시지 추가) × $1.25/million = $0.003
- 읽기: 3,600 reads (조회 + 완료) × $0.25/million = $0.0009
- 저장: 1KB × 900건 × 평균 1분 보관 ≈ 무시 가능
- **소계: <$0.01/월**

**SQS 비용:**
- 메시지: 900건 (프리티어 100만건 내)
- **소계: $0/월 (프리티어)**

**총 추가 비용: <$0.01/월** (거의 무료)

### 예상 효과

| 지표 | Before | After | 개선 |
|-----|--------|-------|------|
| LLM 호출 횟수/건 | 3회 | 1회 | -66% |
| 월 LLM 비용 (30건) | $0.60 | $0.20 | -66% |
| 응답 품질 | Baseline | +20% | 문맥 이해 향상 |
| 응답 지연 | 2-5초 | 30-35초 | 허용 범위 |

### Feature Flag

롤백 가능성 확보를 위한 환경 변수:

```python
# Worker Lambda 환경 변수
ENABLE_MESSAGE_AGGREGATION=true  # true | false
AGGREGATION_WINDOW_SECONDS=30     # 타임 윈도우 (조정 가능)
MAX_MESSAGES_PER_AGGREGATION=10   # 최대 메시지 수
```

## 중요 참고사항

### PDF 5장 수준의 극소량 RAG 데이터 최적화

- 벡터 인덱스 전체 크기: 예상 1-3MB (모든 채널 합산)
- Lambda 메모리에 로드 시간: <100ms
- FAISS 대신 단순 코사인 유사도로도 충분하지만, FAISS 사용 시 향후 확장성 확보
- 임베딩 비용: 주 1회 동기화 시 월 $0.05 미만

### 예상 월간 비용

- AWS Lambda: 프리티어 (90-270 invocations/월)
- DynamoDB: <$1 (온디맨드, 극소량 읽기/쓰기)
- SQS: 프리티어 (100만건/월 무료)
- S3: <$0.10 (5MB 미만 저장)
- SSM Parameter Store: Standard는 대부분 무료, Advanced는 비용이 생길 수 있음 (예: Google SA JSON)
- OpenAI API: $1-2 (gpt-4o-mini + embeddings)
- **총 예상 비용: $2-4/월**
