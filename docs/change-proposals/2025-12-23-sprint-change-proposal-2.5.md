# Sprint Change Proposal: Story 2.5 (검토 반영)

## 1) 이슈 요약

Story 2.5는 방향은 좋지만, 바로 개발하기에는 “막히는 부분(블로커)”이 있습니다.

1. **Worker Lambda 뼈대가 없음**
   - 지금 SAM 템플릿에는 Ingest만 있고, Worker Function 자체가 없습니다.
   - 그런데 Story 2.5는 “Worker가 SQS 메시지를 받아 처리”하는 걸 전제로 합니다.
2. **`aggregation_id`를 쓰는데 Repository API가 맞지 않음**
   - 트리거 메시지에는 `aggregation_id`가 들어가는데,
   - Repository 메서드는 `user_key`만 받아서 “늦게 온 트리거가 새 집계를 완료”시키는 위험이 있습니다.
3. **문서 Source 링크가 깨짐**
   - 보안 관련 Source 링크가 실제 문서에 없는 섹션을 가리킵니다.
4. **신규 조건: 문의내용은 항상 500자 이하**
   - 메시지를 합친 “최종 문의 텍스트”가 500자를 넘지 않게 해야 합니다.

추가로, PO의 `validate-story-draft` 검증에서 “바로 구현할 때 헷갈릴 수 있는 부분(Should-Fix)”이 더 발견됐습니다.

5. **Task 1.2에 `MessageRetentionPeriod: 300`이 빠져 있음**
   - AC에는 있는데, Task에는 없어서 놓치기 쉽습니다.
6. **Worker Function 리소스 기본값이 더 명확히 필요**
   - `CodeUri/Handler/Timeout/Memory/Layers(SharedLayer)` 같은 “기본 뼈대” 정보가 Task에 더 있으면 좋습니다.
7. **“기존 RAG + LLM 호출”의 연결 지점이 애매함**
   - 집계/비집계가 같은 “단일 메시지 처리 함수”를 재사용하도록 Story에서 더 분명히 안내가 필요합니다.
8. **집계 관련 env + `config.py` getter 목록이 누락**
   - Worker에서 `os.getenv()` 직접 사용 금지라서, 어떤 getter를 추가할지 Story에 적어야 합니다.
   - `.env.example` 예시도 같이 업데이트하는 게 좋습니다.
9. **`models/__init__.py`, `repositories/__init__.py` 수정이 Tasks에 빠져 있음**
   - File List에는 있는데, Tasks에 없어서 빠질 수 있습니다.

## 2) 영향 범위

- Epic 영향: Epic 2 범위 안에서 해결 가능 (계획 유지)
- 바뀌는 아티팩트:
  - [x] `docs/stories/2.5.story.md` (Status/AC/Tasks/Source 보완)
  - [x] `docs/prd/epic-2-message-processing-pipeline.md` (500자 제한 요구사항 추가 - 기존 반영)
  - [x] `docs/change-proposals/2025-12-24-message-aggregation-proposal.md` (500자 제한 반영 - 기존 반영)

## 3) 추천 진행 방법

- Option 1 (Direct Adjustment / Integration): [x] 선택
- Option 2 (Rollback): [N/A]
- Option 3 (MVP 재조정): [N/A]

## 4) 구체 수정 내용

### A. Worker Lambda 뼈대 포함(사용자 선택 반영)

- SAM 템플릿에 Worker Function 리소스를 추가하는 Task를 Story 2.5에 넣습니다.
- `src/functions/worker/app.py`(핸들러 파일)를 “신규 생성”으로 명확히 합니다.

### B. Repository API를 `aggregation_id` 기준으로 안전하게 수정

- `get(user_key, aggregation_id)`를 추가합니다.
- `complete/cancel/add_message`는 `aggregation_id`를 같이 받도록 바꿉니다.
- 최종 처리(트리거)에서는 `aggregation_id`가 일치하지 않으면 **그냥 무시**하도록 설계합니다.

### C. 문의내용 500자 이하 규칙 반영

- `combine_messages()` 결과는 **500자 이하**가 되도록 자릅니다.
- (권장) 뒤에서 500자만 유지해서 “마지막에 온 중요한 내용”을 살립니다.

### D. 깨진 Source 링크 교체

- 보안 관련 Source를 `docs/architecture.md#security` 등 실제 존재하는 섹션으로 바꿉니다.

### E. 테스트/파일명 가이드 보완

- 통합 테스트 파일명은 가이드에 맞게 `tests/integration/test_worker_lambda.py`로 제안합니다.

### F. Task 1.0/1.2/1.3 보강 (Should-Fix)

- Task 1.0에 Worker Function “기본 설정”을 더 명확히 적습니다:
  - `CodeUri`, `Handler`, `Timeout`, `MemorySize`, `Layers(SharedLayer)`
  - `AggregationTriggerQueue`로 SendMessage 권한도 포함
- Task 1.2에 `MessageRetentionPeriod: 300`을 추가합니다.
- Task 1.3에 아래 내용을 추가합니다:
  - `talktalk_shared/config.py`에 집계 관련 getter 목록 명시
  - `.env.example`에 집계 관련 환경 변수 예시 추가 안내

### G. Task 2.1/2.2 보강 (Tasks 누락 채우기)

- `models/__init__.py`, `repositories/__init__.py` 수정이 Tasks에도 보이도록, Task 2.1/2.2에 subtask로 추가합니다.

### H. Dev Notes 보강 (Nice-to-have)

- WorkerQueue / AggregationTriggerQueue의 SQS MessageBody 예시를 Story에 넣습니다.
- “집계 완료도 단일 메시지 처리 흐름 재사용”을 Dev Notes에 한 번 더 적습니다.

## 5) 체크리스트 기록(요약)

- 1. Trigger/Context: [x] Story 2.5 검토 결과 반영
- 2. Epic 영향: [x] Epic 2 안에서 해결
- 3. 아티팩트 영향: [x] Story/PRD/Change Proposal 수정
- 4. Path Forward: [x] Direct Adjustment

## 6) 다음 단계

1. Story 2.5를 `Draft`로 두고(문서 보완 중), 수정된 AC/Tasks 기준으로 다시 검증합니다.
2. 검증이 끝나면 `Approved`로 올린 뒤, 개발(dev)이 구현을 시작합니다.

## 7) 승인

- 사용자 승인: 완료 (PO 검증 결과 반영 지시)
- 500자 제한: “30초 동안 합친 최종 문의 텍스트” 기준, **뒤에서 500자만 사용**
