# Sprint Change Proposal: AWS Secrets Manager → SSM Parameter Store (SecureString)

입력 문서: `docs/plan_change.md`

작성 방식(초안): YOLO(배치) — 한 번에 초안을 만들고, 이후에 수정/승인 받는 방식

---

## 1) 트리거/이슈 요약

현재 프로젝트는 비밀값(API 키/토큰)을 **AWS Secrets Manager**로 관리하고 있습니다.

이번 변경은 Secrets Manager를 중단하고, **SSM Parameter Store(SecureString)** 로 옮기는 것입니다.

- 목적: 비용 절감 + 운영 단순화
- 핵심 규칙: “비밀값은 SSM에서만 읽는다”

## 2) 이번 변경에서 확정된 것 (입력 문서 기준)

`docs/plan_change.md`에서 이미 확정된 내용입니다.

1. 모든 비밀값은 **SecureString**으로 저장
2. 파라미터 이름(경로) 규칙:
   - 공통 접두어: `/talktalk-auto/`
   - 공통 비밀값: `/talktalk-auto/secrets/...`
   - 채널별 토큰: `/talktalk-auto/channels/{channel_id}/...`
3. 환경 변수에는 “비밀값”이 아니라, **파라미터 이름(경로)** 만 넣기
4. 공통 파라미터(권장):
   - OpenAI: `/talktalk-auto/secrets/openai-api-key`
   - Google SA JSON: `/talktalk-auto/secrets/google-sa-json`
   - Telegram Bot Token: `/talktalk-auto/secrets/telegram-bot-token`
   - TalkTalk 채널 토큰: `/talktalk-auto/channels/{channel_id}/talktalk-auth-token`

추가로, 이번 대화에서 확정된 내용(사용자 결정)입니다.

- **임시 호환 로직 사용(Yes)**: 마이그레이션 기간에는 새 필드 우선, 없으면 기존 필드 사용
- **Google SA JSON 4KB 이슈 있음(Yes)**: `google-sa-json`은 **Advanced Parameter(SecureString)** 로 저장
- **문서 정리 범위 확장(Yes)**: Done(완료) 처리된 스토리/QA 문서도 “현재 방식(SSM)” 기준으로 문구를 바꿈

## 3) 영향 범위(어디가 바뀌나요?)

### 3.1 에픽/스토리 영향

- 기능(MVP)은 그대로이고, **“비밀 저장소만 교체”** 하는 변경입니다.
- 하지만 여러 스토리(토큰/키/권한)가 Secrets Manager 전제로 쓰여 있어서, 문서 정리가 필요합니다.

### 3.2 문서(아티팩트) 영향

- PRD/에픽:
  - `docs/prd.md`
  - `docs/prd/3-시스템-개요architecture.md`
  - `docs/prd/epic-1-core-infrastructure-channel-routing.md`
- 아키텍처 문서:
  - `docs/architecture.md` (다이어그램, AWS Components Summary, 데이터 모델, 비용 표기)
  - `docs/architecture/tech-stack.md` (핵심 서비스/비밀 관리/비용 표기)
  - `docs/architecture/coding-standards.md` (secrets 규칙)
- 스토리 문서(Secrets Manager 언급이 있는 것):
  - `docs/stories/1.1.story.md`
  - `docs/stories/1.3.story.md`
  - `docs/stories/2.3.story.md`
  - `docs/stories/2.4.story.md`
  - `docs/stories/3.2.story.md`
  - `docs/stories/3.4.story.md`
  - `docs/stories/4.1.story.md`
  - `docs/stories/4.2.story.md`
  - `docs/stories/5.1.story.md`
  - `docs/stories/5.3.story.md`
- QA 문서(참고/표현 정리 필요):
  - `docs/qa/assessments/1.1-nfr-20251221.md`
  - `docs/qa/assessments/3.2-nfr-20251224.md`
  - `docs/qa/assessments/3.3-nfr-20251224.md`
  - `docs/qa/assessments/3.4-nfr-20251225.md`
  - `docs/qa/assessments/5.1-nfr-20251225.md`
  - `docs/qa/gates/1.3-system-overview-architecture.yml`
  - `docs/qa/gates/2.4-talktalk-send-api-integration.yml`
  - `docs/qa/gates/3.2-kb-document-sync-change-detection.yml`
  - `docs/qa/gates/3.4-retrieval-strategy-low-cost-sufficiency.yml`
  - `docs/qa/gates/5.1-google-sheets-logging-setup-recommended.yml`

### 3.3 인프라/코드 영향(요약)

- 인프라: `infrastructure/template.yaml`
  - `secretsmanager:GetSecretValue` 권한 제거
  - `ssm:GetParameter` 권한 추가 (가능하면 경로(prefix) 제한)
  - 환경 변수에 “비밀값” 대신 “파라미터 이름”만 주입
- 코드/테스트(대표):
  - `src/layers/shared/python/talktalk_shared/utils/secrets.py` (Secrets Manager → SSM 유틸로 교체)
  - `src/layers/shared/python/talktalk_shared/clients/openai_client.py`
  - `src/layers/shared/python/talktalk_shared/clients/google_docs_client.py`
  - `src/layers/shared/python/talktalk_shared/clients/google_sheets_client.py`
  - `src/functions/worker/send_answer.py`
  - `tests/unit/test_secrets.py`
  - `tests/unit/test_send_answer_if_allowed.py`
  - `tests/unit/test_send_answer_test_mode.py`

## 4) 추천 진행 방법 (Path Forward)

- Option 1 (Direct Adjustment / Integration): [x] 선택
  - MVP 범위는 유지하고, **비밀 저장소만 교체**합니다.
- Option 2 (Rollback): [N/A]
- Option 3 (MVP 재조정): [N/A]

## 5) 구체 수정 내용(초안)

아래는 “어떤 파일을 어떻게 바꿀지”에 대한 수정 초안입니다. (PO/Dev가 실제 반영)

### A) PRD: AWS 구성에서 Secrets Manager → SSM Parameter Store로 변경

대상:

- `docs/prd.md`
- `docs/prd/3-시스템-개요architecture.md`
- `docs/prd/epic-1-core-infrastructure-channel-routing.md`

수정 예시(형태만 보여주는 샘플):

- 수정 전:
  - `* **Secrets Manager**`
  - `  * OpenAI API Key`
  - `  * 채널별 톡톡 Authorization 토큰`
  - `  * Google SA 자격증명(가능하면 최소권한)`
  - `  * Telegram Bot Token`
- 수정 후(제안):
  - `* **SSM Parameter Store (SecureString)**`
  - `  * /talktalk-auto/secrets/openai-api-key`
  - `  * /talktalk-auto/secrets/google-sa-json`
  - `  * /talktalk-auto/secrets/telegram-bot-token`
  - `  * /talktalk-auto/channels/{channel_id}/talktalk-auth-token`

### B) 아키텍처: 다이어그램/요약/데이터 모델에서 Secrets Manager → SSM으로 교체

대상:

- `docs/architecture.md`

핵심 수정(우선순위 높은 것부터):

1) High Level Project Diagram (Mermaid)

- 수정 전: `SM[Secrets Manager<br/>API Keys]`, 그리고 `Read Secrets`
- 수정 후(제안): `SSM[SSM Parameter Store<br/>SecureString]`, 그리고 `Read Parameters`

2) AWS Components Summary

- 수정 전: `7. **Secrets Manager:** ...`
- 수정 후(제안): `7. **SSM Parameter Store (SecureString):** Stores sensitive config/secrets (see below)`

3) Secrets 목록 섹션

- 섹션 제목:
  - 수정 전: `Secrets Manager Contents`
  - 수정 후: `SSM Parameter Store Parameters (SecureString)`
- 본문:
  - “AWS Secrets Manager에 저장한다” 문장을 “SSM Parameter Store에 SecureString으로 저장한다”로 변경
  - 아래 표를 그대로 넣는 것을 권장 (입력 문서 기준)

| 용도 | 타입 | 추천 파라미터 이름 |
|---|---|---|
| OpenAI API Key | SecureString | `/talktalk-auto/secrets/openai-api-key` |
| Google Service Account JSON | SecureString (Advanced) | `/talktalk-auto/secrets/google-sa-json` |
| Telegram Bot Token | SecureString | `/talktalk-auto/secrets/telegram-bot-token` |
| TalkTalk 채널 토큰(채널별) | SecureString | `/talktalk-auto/channels/{channel_id}/talktalk-auth-token` |

4) Data Model 변경(ChannelConfig)

- 수정 전: `talktalk_auth_secret_arn`: String - Secrets Manager ARN (채널별 Authorization 토큰)
- 수정 후(제안): `talktalk_auth_parameter_name`: String - SSM Parameter 이름/경로 (채널별 Authorization 토큰)

5) 비용 표기

- 수정 전: `- Secrets Manager: $0.40 (시크릿 1개당)`
- 수정 후(제안):
  - Secrets Manager 비용 라인을 제거
  - (주의 문구) “Google SA JSON은 4KB를 넘어서 Advanced Parameter(비용) 필요” 1줄 추가

### C) Tech Stack: 비밀 관리 항목 변경

대상:

- `docs/architecture/tech-stack.md`

수정 방향:

- `핵심 서비스` 목록에서 `Secrets Manager` → `SSM Parameter Store`
- 기술 스택 테이블:
  - 수정 전: `| **비밀 관리** | AWS Secrets Manager | ... |`
  - 수정 후: `| **비밀 관리** | AWS SSM Parameter Store (SecureString) | ... |`
- 비용 표기:
  - Secrets Manager 비용 라인 제거(또는 SSM 기준으로 재작성)

### D) Coding Standards: secrets 규칙 변경

대상:

- `docs/architecture/coding-standards.md`

수정 방향:

- 수정 전: `- **secrets:** 하드코딩 절대 금지, Secrets Manager 사용 필수`
- 수정 후: `- **secrets:** 하드코딩 절대 금지, SSM Parameter Store(SecureString) 사용`

### E) 스토리 문서: Secrets Manager 전제 문구 정리

대상(대표):

- `docs/stories/2.4.story.md`
  - `talktalk_auth_secret_arn` → `talktalk_auth_parameter_name`으로 문구 변경
  - “Secrets Manager에서 토큰 읽기” → “SSM Parameter Store에서 토큰 읽기”
  - 배포/권한 메모: `secretsmanager:GetSecretValue` → `ssm:GetParameter`
- `docs/stories/3.2.story.md`
  - Dependencies에서 “Secrets Manager에 준비” 문구를 “SSM Parameter Store에 SecureString으로 준비”로 변경
- `docs/stories/4.2.story.md`, `docs/stories/5.1.story.md` 등
  - “OpenAI API 키가 Secrets Manager에 있어야…” 같은 문구를 SSM 기준으로 변경

정리 방법(빠른 점검):

- `rg -n "Secrets Manager|secretsmanager" docs/stories -S`

### F) QA 문서: 게이트/평가 문구 정리

대상:

- `rg -l "Secrets Manager|secretsmanager" docs/qa -S`로 나온 파일들

수정 방향:

- “Secrets Manager에서만 읽는다” → “SSM Parameter Store(SecureString)에서만 읽는다”
- “시크릿 노출 금지/마스킹” 같은 보안 원칙은 그대로 유지

## 6) 결정된 것(사용자 확정)

사용자가 아래 3가지를 모두 **Yes**로 확정했습니다.

1. **임시 호환 로직 사용**
   - 새 필드(`talktalk_auth_parameter_name`)가 있으면 그걸 먼저 사용
   - 새 필드가 없으면 기존(`talktalk_auth_secret_arn`) 사용
   - (주의) 이 호환 로직은 “마이그레이션 기간”에만 유지하고, 마이그레이션이 끝나면 제거합니다.
2. **Google SA JSON은 Advanced Parameter 사용**
   - `/talktalk-auto/secrets/google-sa-json`은 **Advanced SecureString** 으로 저장합니다.
3. **문서 정리 범위는 전체**
   - Done(완료) 처리된 스토리/QA 문서도 “현재 방식(SSM)” 기준으로 문구를 바꿉니다.

## 7) 다음 단계(역할별)

1. PO: 위 문서들(PRD/아키텍처/테크스택/코딩표준/스토리/QA) 문구 정리
2. SM: “Secrets Manager → SSM Parameter Store 이관”을 1개 스토리로 묶어 AC/체크리스트 재정의
3. Dev: 인프라 + 코드 + 테스트 실제 구현 (plan_change의 Step 2~6)
4. QA: 변경된 방식 기준으로 NFR/게이트 재확인(특히 시크릿 노출/로그 마스킹)

## 8) 체크리스트 기록(요약)

- 1. Trigger/Context: [x] 운영 정책/비용 이유로 “Secrets → SSM” 변경 (입력: `docs/plan_change.md`)
- 2. Epic 영향: [x] 기능 범위는 유지, 문서/인프라/코드에 파급
- 3. 아티팩트 영향: [x] PRD/Architecture/Stories/QA + infra + code/test 영향
- 4. Path Forward: [x] Option 1 (Direct Adjustment)

## 9) 승인

- (최종 확인) 이 제안서 방향대로 진행할까요? (예/아니오)
