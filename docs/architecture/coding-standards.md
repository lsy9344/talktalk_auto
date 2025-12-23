# Coding Standards

이 문서는 `docs/architecture.md`에서 **Coding Standards**와 **Test Strategy** 부분을 따로 뽑아 만든 파일입니다.

## Coding Standards

**이 섹션은 AI 개발 에이전트가 반드시 준수해야 하는 규칙입니다.** 프로젝트별 핵심 규칙만 명시하며, 일반적인 Python 모범 사례는 가정합니다.

### 핵심 표준

- **언어 및 런타임:** Python 3.11
- **스타일 및 린팅:** ruff (설정: pyproject.toml)
  - Line length: 100
  - Import sorting: isort 호환
  - 사용하지 않는 import/변수 금지
- **타입 힌트:** 모든 공개 함수/메서드에 타입 힌트 필수
- **테스트 파일 규칙:**
  - 유닛 테스트: `tests/unit/test_{module_name}.py`
  - 통합 테스트: `tests/integration/test_{lambda_name}_lambda.py`

### 필수 규칙 (AI 에이전트 준수 필수)

- **로깅:** `print()` 사용 금지 → `logger.info()` 사용
  - 예: `logger.info("Message received", extra={"channel_id": ch_id})`
- **민감정보:** 로그, 에러 메시지, Telegram 알림에 PII 절대 금지
  - 전화번호, 이메일, 결제정보 → `masking.py` 사용
- **예외 처리:** 빈 except 금지, 구체적 예외 타입 명시
  - 나쁜 예: `except:`
  - 좋은 예: `except OpenAIAPIException as e:`
- **DynamoDB 접근:** Repository 패턴 필수, 직접 boto3 호출 금지
  - 나쁜 예: `ddb_client.get_item(...)`
  - 좋은 예: `channel_config_repo.get(channel_id)`
- **외부 API 호출:** 반드시 타임아웃 + 재시도 + Circuit Breaker 적용
  - 모든 API 클라이언트는 `clients/` 모듈 사용
- **환경 변수:** `config.py`를 통해서만 접근, 직접 os.getenv() 금지
  - 나쁜 예: `os.getenv("OPENAI_API_KEY")`
  - 좋은 예: `config.get_openai_api_key()`
- **secrets:** 하드코딩 절대 금지, Secrets Manager 사용 필수
- **PRD 프롬프트 준수:** LLM 호출 시 PRD Section 7의 프롬프트 그대로 사용
  - 프롬프트 수정 시 아키텍트와 협의 필요

### 네이밍 규칙

| 요소 | 규칙 | 예시 |
|------|------|------|
| 파일 | snake_case | `channel_config.py` |
| 클래스 | PascalCase | `ChannelConfigRepository` |
| 함수/메서드 | snake_case | `get_channel_config()` |
| 상수 | UPPER_SNAKE_CASE | `MAX_RETRIES = 3` |
| 프라이빗 메서드 | _snake_case | `_validate_schema()` |
| Lambda 핸들러 | lambda_handler | `def lambda_handler(event, context):` |

### Python 특정 가이드라인

- **타입 힌트 예시:**
  ```python
  from typing import Optional, List, Dict, Any

  def get_channel_config(channel_id: str) -> Optional[Dict[str, Any]]:
      pass
  ```
- **Pydantic 모델 사용:** 모든 외부 데이터 검증 (웹훅, LLM 응답, API 응답)
  ```python
  class WebhookEvent(BaseModel):
      event: str
      user: str
      textContent: Optional[Dict[str, str]]
  ```
- **async/await:** httpx 사용 시 비동기 패턴 활용 (Worker Lambda에서 병렬 API 호출)

---

## Test Strategy and Standards

### 테스팅 철학

- **접근 방식:** 테스트 후 개발 (Test-After Development)
  - 핵심 비즈니스 로직 (RAG, 의사결정)은 반드시 테스트 작성
  - 단순 CRUD 래퍼는 선택적
- **커버리지 목표:**
  - 유닛 테스트: 80% 이상 (핵심 로직)
  - 통합 테스트: 주요 워크플로 커버
- **테스트 피라미드:** 유닛 70% : 통합 25% : E2E 5%

### 테스트 유형 및 조직

#### 유닛 테스트

- **프레임워크:** pytest 7.4.3+
- **파일 규칙:** `tests/unit/test_{module}.py`
- **위치:** `tests/unit/`
- **모킹 라이브러리:** pytest-mock 3.12.0+
- **커버리지 요구사항:** 핵심 로직 80% 이상

AI 에이전트 요구사항:

- 모든 공개 메서드에 대해 테스트 작성
- AAA 패턴 준수 (Arrange, Act, Assert)
- 외부 의존성은 모두 모킹 (DynamoDB, OpenAI, Google APIs 등)
- Edge case 커버: 빈 값, None, 빈 리스트, 예외 상황

예시:

```python
def test_decision_logic_test_mode_always_no_send(mock_config):
    # Arrange
    config = mock_config(global_mode="TEST", channel_mode="TEST")
    llm_response = {"confidence": 0.95, "risk_level": "LOW"}

    # Act
    decision = make_send_decision(config, llm_response)

    # Assert
    assert decision["send_to_user"] is False
    assert decision["reason"] == "TEST_MODE"
```

#### 통합 테스트

- **범위:** Lambda 함수 전체 흐름 (모킹된 외부 API와 함께)
- **위치:** `tests/integration/`
- **테스트 인프라:**
  - DynamoDB: moto 라이브러리 (로컬 모킹)
  - S3: moto 라이브러리
  - 외부 API: WireMock 또는 pytest-httpx

예시 시나리오:

- `test_ingest_lambda_valid_webhook`: 유효한 웹훅 수신 → SQS 전송 → 200 OK
- `test_worker_lambda_test_mode_flow`: SQS → RAG → LLM → Sheets 기록 (발송 없음)
- `test_indexer_lambda_unchanged_doc`: 변경 없는 문서 → 재색인 스킵

#### End-to-End 테스트

- **프레임워크:** pytest + httpx
- **범위:** 실제 dev 환경에서 웹훅 전송 → Sheets 확인
- **환경:** dev 환경 (GlobalMode=TEST 고정)
- **테스트 데이터:** 전용 테스트 채널 (`wc_test_channel`)

### 테스트 데이터 관리

- **전략:** Fixture 기반 (pytest fixtures)
- **Fixtures 위치:** `tests/fixtures/`
  - `webhook_events.json`: 다양한 웹훅 이벤트 샘플
  - `mock_kb_chunks.json`: RAG 테스트용 KB 청크
  - `llm_responses.json`: OpenAI 응답 샘플
- **Factories:** 없음 (간단한 프로젝트, fixtures로 충분)
- **Cleanup:** pytest의 autouse fixture로 테스트 후 자동 정리

### CI 테스트 통합

- CI 단계:
  1. 린팅 (ruff, mypy)
  2. 유닛 테스트 (병렬 실행)
  3. 통합 테스트
  4. 커버리지 리포트 (80% minimum enforced)
