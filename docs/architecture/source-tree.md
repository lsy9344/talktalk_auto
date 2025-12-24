# Source Tree

이 문서는 `docs/architecture.md`에서 **Source Tree** 부분을 따로 뽑아 만든 파일입니다.

프로젝트 폴더 구조는 AWS SAM 모노레포 구조를 따릅니다.

```
talktalk_auto/
├── .aws-sam/                    # SAM 빌드 아티팩트 (gitignore)
├── .github/
│   └── workflows/
│       └── deploy.yml           # GitHub Actions CI/CD
├── docs/
│   ├── architecture.md          # 아키텍처 문서(전체)
│   ├── architecture/            # 아키텍처 문서(분할)
│   │   ├── coding-standards.md
│   │   ├── tech-stack.md
│   │   └── source-tree.md
│   ├── prd.md                   # PRD 문서(전체, 필요 시)
│   ├── prd/                     # PRD 문서(분할, epic 단위)
│   └── stories/                 # 스토리 문서
├── src/
│   ├── layers/
│   │   └── shared/              # Lambda Layer (공유 라이브러리)
│   │       ├── python/
│   │       │   └── talktalk_shared/
│   │       │       ├── __init__.py
│   │       │       ├── repositories/
│   │       │       │   ├── __init__.py
│   │       │       │   ├── channel_config.py
│   │       │       │   ├── global_mode.py
│   │       │       │   ├── common_doc_ids.py
│   │       │       │   ├── deduplication.py
│   │       │       │   └── vector_index_metadata.py
│   │       │       ├── clients/
│   │       │       │   ├── __init__.py
│   │       │       │   ├── openai_client.py
│   │       │       │   ├── google_docs_client.py
│   │       │       │   ├── google_sheets_client.py
│   │       │       │   ├── talktalk_client.py
│   │       │       │   └── telegram_client.py
│   │       │       ├── models/
│   │       │       │   ├── __init__.py
│   │       │       │   ├── webhook_event.py
│   │       │       │   ├── llm_response.py
│   │       │       │   └── sheets_log_row.py
│   │       │       ├── utils/
│   │       │       │   ├── __init__.py
│   │       │       │   ├── logger.py
│   │       │       │   ├── masking.py
│   │       │       │   ├── text_utils.py
│   │       │       │   └── secrets.py
│   │       │       └── config.py
│   │       └── requirements.txt
│   ├── functions/
│   │   ├── ingest/
│   │   │   ├── app.py               # Ingest Lambda handler
│   │   │   └── requirements.txt
│   │   ├── worker/
│   │   │   ├── app.py               # Worker Lambda handler
│   │   │   ├── rag.py               # RAG 로직
│   │   │   ├── decision.py          # 의사결정 로직
│   │   │   └── requirements.txt
│   │   └── indexer/
│   │       ├── app.py               # Indexer Lambda handler
│   │       ├── chunking.py          # 문서 청킹 로직
│   │       └── requirements.txt
├── tests/
│   ├── unit/
│   │   ├── test_repositories.py
│   │   ├── test_clients.py
│   │   ├── test_rag.py
│   │   └── test_decision.py
│   ├── integration/
│   │   ├── test_ingest_lambda.py
│   │   ├── test_worker_lambda.py
│   │   └── test_indexer_lambda.py
│   └── fixtures/
│       ├── webhook_events.json
│       └── mock_kb_chunks.json
├── infrastructure/
│   ├── template.yaml            # AWS SAM 템플릿
│   └── samconfig.toml           # SAM 배포 설정
├── scripts/
│   ├── setup_google_auth.py     # Google SA 설정 스크립트
│   ├── init_dynamodb.py         # DynamoDB 초기 데이터 로드
│   └── manual_index_trigger.py  # 수동 재색인 트리거
├── .env.example                 # 환경 변수 템플릿
├── .gitignore
├── requirements-dev.txt         # 개발 의존성 (pytest, ruff, mypy)
├── pyproject.toml               # ruff, mypy 설정
└── README.md                    # 프로젝트 README
```

폴더 구조 설명:

- `src/layers/shared`: 모든 Lambda에서 사용하는 공유 코드 (Layer로 배포)
- `src/functions/*`: 각 Lambda 함수별 독립 폴더 (핸들러 + 함수별 의존성)
- `infrastructure/`: SAM 템플릿 및 IaC 관련
- `tests/`: 유닛/통합 테스트, pytest 기반
- `scripts/`: 운영/배포 스크립트
