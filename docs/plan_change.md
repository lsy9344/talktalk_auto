# 설계 변경 계획: AWS Secrets Manager → SSM Parameter Store(SecureString)

## 1) 목표(왜 바꾸나요?)

- **목표:** 지금 쓰는 “AWS Secrets Manager”를 그만 쓰고, **SSM Parameter Store(SecureString)** 로 비밀값(API 키/토큰)을 관리합니다.
- **이유(장점):**
  - 비용 절감: Secrets Manager는 시크릿 1개당 비용이 나는데, Parameter Store(Standard)는 보통 더 저렴/단순합니다.
  - 운영 단순화: “비밀값은 SSM에서만 읽는다” 규칙으로 정리합니다.

## 2) 이번 변경에서 확정한 3가지(사용자 결정)

1. **SecureString 사용:** Yes (모든 비밀값은 SecureString)
2. **파라미터 이름(경로) 규칙:** 아래 “추천 규칙”을 사용
3. **초보자가 보기 쉬운 방식(선택):**
   - Lambda 환경 변수에는 **비밀값 자체를 넣지 않고**, “파라미터 이름(경로)”만 넣습니다.
   - 코드는 실행 중에 SSM에서 값을 읽습니다. (한 곳에서만 읽도록 유틸을 둡니다)

## 3) 추천 파라미터 이름(경로) 규칙

### 3.1 기본 규칙

- 공통 접두어(prefix): `/talktalk-auto/`
- 의미가 보이게 폴더처럼 나누기
- 비밀값은 `/secrets/` 아래에 모으기
- 채널별 토큰은 `/channels/{channel_id}/` 아래에 두기

### 3.2 파라미터 목록(권장)

| 용도 | 타입 | 추천 파라미터 이름 |
|---|---|---|
| OpenAI API Key | SecureString | `/talktalk-auto/secrets/openai-api-key` |
| Google Service Account JSON | SecureString | `/talktalk-auto/secrets/google-sa-json` |
| Telegram Bot Token | SecureString | `/talktalk-auto/secrets/telegram-bot-token` |
| TalkTalk 채널 토큰(채널별) | SecureString | `/talktalk-auto/channels/{channel_id}/talktalk-auth-token` |

> 참고: `{channel_id}`는 실제 채널 ID(예: `wc123...`)로 바꿉니다.

## 4) 영향 범위(어디가 바뀌나요?)

### 4.1 문서(에픽/스토리/아키텍처)

- PRD/에픽:
  - `docs/prd.md`
  - `docs/prd/epic-1-core-infrastructure-channel-routing.md`
  - `docs/prd/3-시스템-개요architecture.md`
- 아키텍처 문서:
  - `docs/architecture.md` (AWS Components Summary / “Secrets Manager Contents” 부분)
  - `docs/architecture/tech-stack.md` (비밀 관리 항목)
  - `docs/architecture/coding-standards.md` (“secrets: Secrets Manager 사용 필수” 문구)
- 스토리(Secrets Manager 가정이 들어간 것들):
  - `docs/stories/2.4.story.md` (채널 토큰 읽기)
  - `docs/stories/3.2.story.md` (OpenAI/Google SA 비밀값)
  - `docs/stories/4.1.story.md`, `docs/stories/4.2.story.md` (OpenAI 키)
  - `docs/stories/5.1.story.md` (Google SA JSON)
  - 그 외 “Secrets Manager”라고 적힌 스토리들 전반

### 4.2 인프라(IAM/환경 변수)

- `infrastructure/template.yaml`
  - `secretsmanager:GetSecretValue` 권한 제거
  - `ssm:GetParameter` 권한 추가(필요한 경로만)
  - (선택) “파라미터 이름(경로)”를 환경 변수로 주입

### 4.3 코드(실제 구현 변경 — 이번 문서는 계획만)

현재 코드에서 Secrets Manager를 직접 쓰는 곳:

- `src/layers/shared/python/talktalk_shared/utils/secrets.py`
- `src/layers/shared/python/talktalk_shared/clients/openai_client.py` (OPENAI_API_KEY)
- `src/layers/shared/python/talktalk_shared/clients/google_docs_client.py` (GOOGLE_SA_JSON)
- `src/layers/shared/python/talktalk_shared/clients/google_sheets_client.py` (GOOGLE_SA_JSON)
- `src/functions/worker/send_answer.py` (ChannelConfig의 `talktalk_auth_secret_arn`)
- 관련 테스트:
  - `tests/unit/test_secrets.py`
  - `tests/unit/test_send_answer_if_allowed.py`
  - `tests/unit/test_send_answer_test_mode.py`

## 5) 설계 변경 내용(무엇을 어떻게 바꾸나요?)

### 5.1 “데이터 모델” 변경: ChannelConfig 필드 이름

- 기존: `talktalk_auth_secret_arn` (Secrets Manager ARN)
- 변경: `talktalk_auth_parameter_name` (SSM Parameter 이름/경로)

이 필드는 **“비밀값”이 아니라 “비밀값이 들어있는 위치(이름)”** 만 저장합니다.

### 5.2 “비밀값 읽기” 공통 유틸(한 곳에서만)

- 목표: 코드 여기저기서 boto3를 부르지 않고, **한 파일에서만** Parameter Store를 읽습니다.
- 유틸이 해야 하는 일(요구사항):
  - `get_parameter_value(name, with_decryption=True)` 형태
  - 실패하면 짧고 명확한 예외 타입으로 올리기
  - 로그에 비밀값이 찍히지 않게 “마스킹” 처리
  - 간단 캐시(같은 값을 여러 번 읽지 않도록)

### 5.3 환경 변수 설계(초보자가 보기 쉬운 방식)

**원칙:** 환경 변수에는 “비밀값”이 아니라 “파라미터 이름(경로)”만 넣습니다.

예시(권장):

- `OPENAI_API_KEY_PARAM_NAME=/talktalk-auto/secrets/openai-api-key`
- `GOOGLE_SA_JSON_PARAM_NAME=/talktalk-auto/secrets/google-sa-json`
- `TELEGRAM_BOT_TOKEN_PARAM_NAME=/talktalk-auto/secrets/telegram-bot-token`

채널별 토큰은 DynamoDB(ChannelConfig)에 아래처럼 저장:

- `talktalk_auth_parameter_name=/talktalk-auto/channels/wc123.../talktalk-auth-token`

## 6) 작업 순서(실행 계획)

### Step 1. SSM Parameter Store에 값 넣기(운영 준비)

1) AWS Console(쉬움)에서 Parameter Store로 들어가서 SecureString 파라미터를 만들고 값을 넣습니다.  
2) 특히 `google-sa-json`은 JSON이라 값이 길 수 있습니다.

주의:

- SecureString(Standard)는 값 크기 제한이 있습니다(대략 4KB).  
  만약 Google SA JSON이 너무 크면 “Advanced parameter”를 써야 합니다(비용이 생길 수 있음).

### Step 2. 인프라 권한/환경 변수 반영

- `infrastructure/template.yaml`에서:
  - Secrets Manager 권한 제거
  - SSM `GetParameter` 권한 추가
  - 위에서 정한 `*_PARAM_NAME` 환경 변수 추가

### Step 3. 코드 변경(Secrets Manager → Parameter Store)

- `talktalk_shared/utils/secrets.py`를 대체(또는 이름 변경)해서 SSM 기반 유틸로 변경
- OpenAI/Google 클라이언트가 SSM에서 키/JSON을 읽게 변경
- Worker의 send 로직이 `talktalk_auth_parameter_name`을 읽어서 SSM에서 토큰을 가져오게 변경

### Step 4. 데이터 마이그레이션(ChannelConfig 값 변경)

- DynamoDB `ChannelConfig` 아이템에서:
  - `talktalk_auth_secret_arn` → `talktalk_auth_parameter_name`으로 값 채우기
  - (안전하게) 배포 초반에는 “둘 다 있으면 새 필드 우선” 같은 호환 로직을 잠깐 둘지 결정

### Step 5. 문서 업데이트(설계 문서/스토리 정리)

- 모든 문서에서 “Secrets Manager”를 “SSM Parameter Store(SecureString)”로 바꿉니다.
- 특히 `docs/architecture.md`의 “Secrets Manager Contents”는 “Parameter Store Parameters”로 바꾸고,
  위 3.2 표를 그대로 넣는 것을 권장합니다.

### Step 6. 검증(테스트/린트/검색)

아래 3가지를 통과해야 “변경 완료”로 봅니다.

- `python3 -m pytest -q`
- `python3 -m ruff check .`
- `python3 -m mypy src`

그리고 “Secrets Manager 흔적”이 남아있는지 검색:

- `rg -n "secretsmanager|Secrets Manager" -S src infrastructure tests`

## 7) 완료 기준(Definition of Done)

- 프로덕션에서 Secrets Manager 권한이 없어도(또는 사용하지 않아도) 정상 동작
- OpenAI/Google/Telegram/TalkTalk 토큰이 **SSM Parameter Store에서만** 로드됨
- DynamoDB(ChannelConfig)에는 비밀값이 없고, “파라미터 이름(경로)”만 저장됨
- 테스트/린트/타입체크가 모두 통과
- 문서(PRD/Architecture/Stories) 내용이 현재 구현 방식과 일치

## 8) 롤백(되돌리기) 계획

- 문제가 생기면:
  1) 이전 배포 버전으로 롤백
  2) `infrastructure/template.yaml`의 IAM/환경 변수를 원복
  3) ChannelConfig 마이그레이션 전이라면, 기존 `talktalk_auth_secret_arn` 값으로 계속 동작

## 9) 다음 작업(권장: BMAD 흐름)

- PO(문서 담당): PRD/아키텍처/스토리 문구 수정
- SM(일감 담당): “Secrets → Parameter Store 이관” 스토리 1개로 묶어, 체크리스트/AC를 다시 세팅
- Dev/QA: 위 Step 2~6을 실제로 구현/검증

