# Sprint Change Proposal: Story 3.1 (문서 구조)

## 1) 이슈 요약

Story 3.1은 “공통 KB 문서 목록”을 **DynamoDB `GlobalMode` 테이블**에 저장하자고 되어 있습니다.

- `config_key="COMMON_DOC_IDS"` 아이템을 만들고, `doc_ids: List[String]`로 저장 (Story 3.1 기준)

그런데 아키텍처 문서의 `GlobalMode` 설명은 `config_key="GLOBAL_MODE"` **단일 레코드(1개만)**처럼 적혀 있습니다.

그래서 지금 상태로는 “공통 KB 문서 목록을 어디에 어떻게 저장하는지”가 문서끼리 달라서, 개발자가 헷갈리고 스토리가 막힙니다. (3.1 NO-GO)

## 2) 영향 범위

- Epic 영향: Epic 3 안에서 해결 가능 (계획 유지)
- 바뀌는 아티팩트(문서):
  - [x] `docs/architecture.md` (GlobalMode 데이터 모델/설명 보완)
  - [x] `docs/architecture/source-tree.md` (Repository 목록에 파일 추가)
  - [ ] `docs/stories/3.1.story.md` (선택: Dev Notes에 GlobalMode 저장 형태 1~2줄 보강)
  - [ ] `docs/prd/epic-3-rag-knowledge-base-management.md` / `docs/prd/61-문서-구조.md` (선택: “저장 위치” 1줄 보강)

## 3) 추천 진행 방법 (Path Forward)

- Option 1 (Direct Adjustment / Integration): [x] 선택
  - **GlobalMode 테이블을 “전역 설정 테이블”처럼 사용**합니다.
  - `config_key` 값에 따라 여러 설정 아이템을 저장할 수 있게 문서를 맞춥니다.
- Option 2 (GLOBAL_MODE 아이템에 필드로 넣기): [ ] 미선택
  - 장점: “단일 레코드” 문구 유지
  - 단점: `GLOBAL_MODE` 아이템이 너무 많은 역할을 하게 됨(복잡)
- Option 3 (새 DynamoDB 테이블 추가): [ ] 미선택
  - 장점: 역할 분리
  - 단점: 인프라/코드/테스트 범위가 커짐

## 4) 구체 수정 내용(초안)

### A. `docs/architecture.md` - GlobalMode 설명을 “여러 config_key 허용”으로 수정

**수정 전(현재 요약):**

- `config_key`: String (PK) - 고정값 `"GLOBAL_MODE"`
- DynamoDB 스키마: 단일 레코드

**수정 후(제안):**

- `config_key`: String (PK) - 전역 설정 키 (예: `"GLOBAL_MODE"`, `"COMMON_DOC_IDS"`)
- `config_key="GLOBAL_MODE"` 아이템은 기존처럼 전역 모드(TEST/PROD)만 담당
- `config_key="COMMON_DOC_IDS"` 아이템은 공통 KB 문서 ID 목록을 담당
  - Attributes: `doc_ids: List[String]`
  - 아이템이 없으면 `[]`로 취급 (안전 기본값)

**예시(문서에 추가 제안):**

```yaml
# 전역 모드(기존)
{ config_key: "GLOBAL_MODE", mode: "TEST" }

# 공통 KB 문서 목록(신규)
{ config_key: "COMMON_DOC_IDS", doc_ids: ["doc_id_1", "doc_id_2"] }
```

> 참고: `GlobalModeTable`은 원래부터 PK가 `config_key`라서(여러 아이템 저장 가능), 인프라 변경은 필요 없습니다. (`infrastructure/template.yaml` 기준)

### B. `docs/architecture.md` - Shared Libraries Repository 목록 보강

`GlobalModeRepository` 옆에 아래 1줄을 추가합니다.

- `CommonDocIdsRepository`: GlobalMode에서 공통 KB 문서 목록 조회/저장 (`config_key="COMMON_DOC_IDS"`)

### C. `docs/architecture/source-tree.md` - repositories 목록에 파일 추가

`src/layers/shared/python/talktalk_shared/repositories/` 목록에 아래 파일을 추가합니다.

- `common_doc_ids.py`

### D. `docs/stories/3.1.story.md` - (선택) Dev Notes에 GlobalMode 저장 형태 보강

Dev Notes > Data Models에 아래 내용을 1~2줄로 추가하면 개발자가 더 안 헷갈립니다.

- GlobalMode: `config_key="COMMON_DOC_IDS"`, `doc_ids: List[String]` (없으면 `[]`)

## 5) 체크리스트 기록(요약)

- 1. Trigger/Context: [x] Story 3.1 검토 결과 반영
- 2. Epic 영향: [x] Epic 3 안에서 해결
- 3. 아티팩트 영향: [x] Architecture/Source Tree(필수), Story/PRD(선택)
- 4. Path Forward: [x] Option 1 (Direct Adjustment)

## 6) 다음 단계

1. (문서) `docs/architecture.md`에 GlobalMode 설명을 수정합니다.
2. (문서) `docs/architecture/source-tree.md`에 `common_doc_ids.py`를 추가합니다.
3. (선택) `docs/stories/3.1.story.md` Dev Notes를 1~2줄 보강합니다.
4. PO가 다시 `validate-story-draft`로 3.1을 재검증합니다.

## 7) 승인

- 사용자 선택: Option 1 (GlobalMode에 `COMMON_DOC_IDS` 아이템 추가) - 2025-12-24
*** End Patch
