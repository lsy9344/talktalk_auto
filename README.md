# TalkTalk Auto - 네이버 톡톡 자동 응답 시스템

**RAG(Google Docs) + OpenAI(gpt-4o-mini) + AWS Serverless Architecture**

## 프로젝트 개요

16개의 네이버 톡톡 채널(wc******)에 대한 고객 문의 응답 자동화 시스템입니다. Google Docs 기반 지식베이스(RAG)와 OpenAI LLM을 활용하여 고객 문의에 자동으로 응답하며, TEST 모드에서 검증 후 PROD 모드로 전환하여 실사용합니다.

## 핵심 목표

1. **16개 톡톡 채널 자동화** (향후 확장 가능)
2. **AWS 기반 서버리스 아키텍처** (비용 효율 우선, 월 예상 비용 $2-4)
3. **Google Docs 기반 RAG** (채널별/공통 문서, 월 1회 수준 업데이트)
4. **TEST 모드 기본** (자동 발송 없음, Sheets 기록만)
5. **검증 후 PROD 전환** (전역/채널/LLM 3단계 플래그 제어)

## 고객 커뮤니케이션 정책 (중요)

본 시스템은 고객에게 불확실한 정보를 제공하지 않는 것을 최우선 원칙으로 합니다:

### 금지된 응답 패턴
- ❌ "모르겠습니다" / "애매합니다" / "추측입니다"
- ❌ "상담원에게 연결할게요" / "상담원 연결" 등

### 불확실한 케이스 처리
- **고객**: 무응답 유지 (silent)
- **운영자**: Telegram 알림 발송 (채널명 + 고객 ID + 질문 요약 + 이유)

## 기술 스택

| 카테고리 | 기술 | 용도 |
|---------|------|------|
| **언어** | Python 3.11 | 주 개발 언어 |
| **런타임** | AWS Lambda | 서버리스 실행 환경 |
| **IaC** | AWS SAM | 인프라 코드화 |
| **벡터 검색** | FAISS (CPU) | 벡터 유사도 검색 |
| **임베딩** | OpenAI text-embedding-3-small | 텍스트 벡터화 |
| **LLM** | OpenAI gpt-4o-mini | 답변 생성 |
| **데이터베이스** | DynamoDB (On-Demand) | 채널 설정/중복 방지 |
| **메시지 큐** | SQS Standard | 이벤트 버퍼링 |
| **스토리지** | S3 Standard | 벡터 인덱스 저장 |
| **스케줄러** | EventBridge Scheduler | 주간 문서 동기화 |
| **비밀 관리** | AWS Secrets Manager | API 키 저장 |
| **테스트** | pytest 7.4.3+ | 유닛/통합 테스트 |
| **린터** | ruff 0.1.9+ | 코드 품질 |

## 시스템 아키텍처

### 데이터 흐름
```
Naver TalkTalk Webhook
  ↓
API Gateway (POST /naver/talktalk/{channel_id}/webhook)
  ↓
Lambda (Ingest) - 스키마 검증 → SQS enqueue → 즉시 200 OK
  ↓
SQS Queue
  ↓
Lambda (Worker) - RAG → LLM → 의사결정 → Sheets 기록 → (조건부) 발송/알림
  ↓
├─ Google Sheets (로그 기록)
├─ Naver TalkTalk Send API (PROD 모드 + 조건 충족 시)
└─ Telegram Bot (불확실 케이스 알림)

EventBridge Scheduler (주 1회)
  ↓
Lambda (Indexer) - Google Docs 동기화 → 청킹 → 벡터화 → S3 저장
```

### AWS 구성 요소
- **API Gateway**: Webhook 엔드포인트 (TLS 필수)
- **Lambda Functions**:
  - Ingest: 웹훅 수신 및 SQS 전송 (타임아웃 3초 대응)
  - Worker: RAG + LLM + 의사결정 + 발송/로깅/알림
  - Indexer: Google Docs 동기화 및 벡터 인덱스 생성
- **DynamoDB Tables**:
  - ChannelConfig: 채널별 설정/문서 매핑/모드
  - GlobalMode: 전역 TEST/PROD 스위치
  - DeduplicationRecord: 중복 방지 (TTL 10분)
  - VectorIndexMetadata: 문서 동기화 상태 추적
- **S3**: 벡터 인덱스(FAISS) 저장
- **SQS**: 이벤트 큐 (유실 방지)
- **EventBridge**: 주간 문서 동기화 스케줄
- **Secrets Manager**: API 키 및 토큰 관리

## TEST/PROD 모드 운영

### TEST 모드 (기본)
- 고객 메시지 수신 → **무조건 무응답**
- Google Sheets에 질문/답변 초안 기록
- 불확실/오류 케이스 → Telegram 알림

### PROD 모드 (실사용)
**3단계 조건 모두 충족 시에만 자동 발송:**
1. ✅ GlobalMode = PROD (DynamoDB)
2. ✅ ChannelConfig.mode = PROD (채널별)
3. ✅ LLM 응답 send_to_user = true (신뢰도 충족)

**조건 미충족 시**: 무응답 + Sheets 기록 + Telegram 알림

## 외부 API 제약사항

### Naver TalkTalk Webhook
- **타임아웃**: Connection 3초 / Read 5초
- **설계 원칙**: 즉시 200 OK 반환 + 비동기 처리 (SQS)
- **보안**: TLS 필수, IP allowlist 권장
- **Echo 이벤트**: 무한 루프 방지 위해 기본 비활성화

### Naver TalkTalk Send API
- **엔드포인트**: `POST https://gw.talk.naver.com/chatbot/v1/event`
- **인증**: Header에 채널별 Authorization 토큰 필요 (Secrets Manager)
- **사용 조건**: PROD 모드 + 3단계 플래그 모두 충족

## 프로젝트 구조

```
talktalk_auto/
├── docs/
│   ├── architecture.md          # 전체 아키텍처 문서
│   ├── architecture/            # 분할된 아키텍처 문서 (코딩 표준, 기술 스택, 소스 트리)
│   ├── prd.md                   # 전체 PRD 문서
│   ├── prd/                     # 분할된 PRD (Epic 단위)
│   └── stories/                 # 개발 스토리
├── src/
│   ├── layers/shared/           # Lambda Layer (공유 라이브러리)
│   └── functions/               # Lambda 함수 (ingest, worker, indexer)
├── tests/
│   ├── unit/                    # 유닛 테스트
│   ├── integration/             # 통합 테스트
│   └── fixtures/                # 테스트 데이터
├── infrastructure/
│   └── template.yaml            # AWS SAM 템플릿
└── scripts/                     # 운영/배포 스크립트
```

## 개발 표준

### 코딩 규칙
- **언어**: Python 3.11
- **스타일**: ruff (line length: 100, isort 호환)
- **타입 힌트**: 모든 공개 함수/메서드 필수
- **로깅**: `print()` 금지 → `logger.info()` 사용
- **예외 처리**: 빈 except 금지, 구체적 예외 타입 명시
- **민감정보**: 로그/에러에 PII 절대 금지 (masking.py 사용)
- **DynamoDB 접근**: Repository 패턴 필수 (직접 boto3 호출 금지)
- **환경 변수**: config.py를 통해서만 접근

### 테스트 전략
- **프레임워크**: pytest 7.4.3+
- **커버리지**: 핵심 로직 80% 이상
- **테스트 피라미드**: 유닛 70% : 통합 25% : E2E 5%
- **AAA 패턴**: Arrange, Act, Assert
- **모킹**: 모든 외부 의존성 모킹 필수 (DynamoDB, OpenAI, Google APIs)

### CI/CD 파이프라인
1. 린팅 (ruff, mypy)
2. 유닛 테스트 (병렬 실행)
3. 통합 테스트
4. 커버리지 리포트 (80% minimum enforced)

## 현재 상태

- ✅ PRD 문서 작성 완료 (docs/prd.md, docs/prd/)
- ✅ 아키텍처 문서 작성 완료 (docs/architecture.md, docs/architecture/)
- ✅ 개발 표준 정의 완료
- ✅ **Story 1.2 완료**: Ingest Lambda, DynamoDB 스키마, SQS 통합, 20개 유닛 테스트 (Ready for Review)

## 구현 완료 (Story 1.2)

### 구조
- ✅ 프로젝트 폴더 구조 (src/, tests/, infrastructure/)
- ✅ AWS SAM 템플릿 (API Gateway, Lambda, DynamoDB, SQS)
- ✅ 개발 환경 설정 (pyproject.toml, requirements-dev.txt)

### 코드
- ✅ Webhook Event Pydantic 모델 (WebhookEvent, TextContent, Options)
- ✅ ChannelConfig Repository (DynamoDB 접근 레이어)
- ✅ Deduplication Repository (중복 방지 로직)
- ✅ Ingest Lambda Handler (src/functions/ingest/app.py)
- ✅ 설정 모듈 (config.py - 환경 변수 관리)
- ✅ 로깅 유틸리티 (logger.py - 구조화된 로깅)

### 테스트
- ✅ 20개 유닛 테스트 (100% 통과)
  - 4개 Webhook 모델 검증 테스트
  - 8개 Repository 테스트
  - 8개 Ingest Lambda 핸들러 테스트
- ✅ 테스트 픽스처 및 설정 (conftest.py, webhook_events.json)
- ✅ Ruff 린팅 통과 (0 errors)

### 검증된 시나리오
- ✅ 정상 send 이벤트 → SQS enqueue → 200 OK
- ✅ 스키마 오류 → 400 Bad Request
- ✅ 채널 없음/비활성 → 404 Not Found
- ✅ echo/open/leave 이벤트 → 200 OK (무시)
- ✅ 중복 이벤트 → 200 OK (enqueue 스킵)
- ✅ SQS 실패 → 500 Internal Server Error

## 다음 단계

1. **Story 1.3 (예정)**: Worker Lambda 및 RAG 파이프라인
2. **Story 1.4 (예정)**: Indexer Lambda 및 Google Docs 동기화
3. **Story 2.x (예정)**: LLM 통합 및 프롬프트 엔지니어링
4. **Story 3.x (예정)**: Google Sheets 로깅
5. **Story 4.x (예정)**: Telegram 알림
6. **Story 5.x (예정)**: 통합 테스트 및 배포

## 로컬 개발

### 설치
```bash
# 개발 의존성 설치
pip install -r requirements-dev.txt
```

### 테스트 실행
```bash
# 모든 유닛 테스트 실행
PYTHONPATH="src/layers/shared/python:src/functions/ingest" pytest tests/unit/ -v

# 특정 테스트 파일 실행
PYTHONPATH="src/layers/shared/python:src/functions/ingest" pytest tests/unit/test_ingest_lambda.py -v

# 커버리지 리포트 생성
PYTHONPATH="src/layers/shared/python:src/functions/ingest" pytest tests/unit/ --cov=src --cov-report=html
```

### 코드 품질
```bash
# 린팅 체크
ruff check src/ tests/

# 자동 수정
ruff check src/ tests/ --fix

# 타입 체크 (추후 추가 예정)
# mypy src/
```

### SAM 로컬 테스트 (추후)
```bash
# 빌드
sam build -t infrastructure/template.yaml

# 로컬 테스트
sam local start-api

# 특정 Lambda 테스트
sam local invoke IngestFunction -e events/webhook-event.json
```

## 문서

### 설계 문서
- **전체 PRD**: [docs/prd.md](docs/prd.md)
- **전체 아키텍처**: [docs/architecture.md](docs/architecture.md)
- **코딩 표준**: [docs/architecture/coding-standards.md](docs/architecture/coding-standards.md)
- **기술 스택**: [docs/architecture/tech-stack.md](docs/architecture/tech-stack.md)
- **소스 트리**: [docs/architecture/source-tree.md](docs/architecture/source-tree.md)
- **구현 실수 방지 메모**: [docs/architecture/implementation-notes.md](docs/architecture/implementation-notes.md)
- **PRD Epic 인덱스**: [docs/prd/index.md](docs/prd/index.md)

### 운영 문서
- **Go-Live 절차 (TEST → PROD 전환)**: [docs/runbooks/go-live.md](docs/runbooks/go-live.md)

## 비용 예상

- **AWS Lambda**: 프리티어 (90-270 invocations/월)
- **DynamoDB**: <$1 (온디맨드, 극소량 읽기/쓰기)
- **SQS**: 프리티어 (100만건/월 무료)
- **S3**: <$0.10 (5MB 미만 저장)
- **Secrets Manager**: $0.40 (시크릿 1개당)
- **OpenAI API**: $1-2 (gpt-4o-mini + embeddings)
- **총 예상**: **$2-4/월**

## 라이선스

Copyright © 2025. All rights reserved.
