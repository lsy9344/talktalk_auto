# Go-Live Runbook: TEST → PROD 전환 절차

## 목차

- [개요](#개요)
- [핵심 용어](#핵심-용어)
- [Go-Live 6단계 절차](#go-live-6단계-절차)
- [설정 변경 방법](#설정-변경-방법)
- [모니터링 및 튜닝](#모니터링-및-튜닝)
- [긴급 롤백 절차](#긴급-롤백-절차)

---

## 개요

이 문서는 TalkTalk 자동 응답 시스템을 **TEST 모드에서 PROD 모드로 안전하게 전환**하는 운영 절차(Runbook)입니다.

### 목적

- 16개 채널을 단계적으로 PROD로 전환
- 운영 실수와 사고 최소화
- 긴급 상황 시 빠른 롤백 가능

### 전제 조건

- ✅ Story 7.1: TEST 모드 필수 조건이 테스트로 고정됨
- ✅ Story 7.2: PROD 전환 전 안전장치가 테스트로 고정됨
- ✅ 전체 테스트 통과: `python3 -m pytest -q`

---

## 핵심 용어

### 3-Gate System

PROD 모드에서 자동 발송이 실행되려면 **3가지 게이트가 모두 통과**해야 합니다:

| Gate | 조건 | 설명 |
|------|------|------|
| **Gate 1** | `GlobalMode = PROD` | 전역 스위치 (전체 시스템) |
| **Gate 2** | `ChannelConfig.channel_mode = PROD` | 채널별 스위치 |
| **Gate 3** | LLM 승인 + 안전 조건 | `send_to_user=true` + 신뢰도 threshold 통과 + `risk_level != HIGH` |

### GlobalMode (전역 모드)

- **위치**: DynamoDB `GlobalMode` 테이블
- **Key**: `config_key="GLOBAL_MODE"`
- **값**: `mode="TEST" | "PROD"`
- **영향**: 모든 채널에 영향 (킬 스위치 역할)
- **기본값**: `TEST` (안전)

### ChannelConfig (채널별 설정)

- **위치**: DynamoDB `ChannelConfig` 테이블
- **Key**: `channel_id` (예: `wc123456`)
- **주요 필드**:
  - `channel_mode`: `"TEST" | "PROD" | "DISABLED"`
  - `confidence_threshold`: 자동 발송 최소 신뢰도 (예: `0.85`)
- **영향**: 해당 채널만 영향

### 모드별 동작

| Mode | 자동 발송 | Sheets 로그 | Telegram 알림 | 용도 |
|------|----------|------------|-------------|------|
| **TEST** | ❌ 절대 안 함 | ✅ 100% 기록 | ✅ 모든 케이스 알림 | 검증, 품질 확인 |
| **PROD** | ✅ 3-Gate 통과 시 | ✅ 100% 기록 | ⚠️ 차단/실패 시만 알림 | 실제 운영 |
| **DISABLED** | ❌ 처리 안 함 | ❌ | ❌ | 채널 비활성화 |

---

## Go-Live 6단계 절차

### Phase 1: 초기 설정 (모든 채널 TEST)

**목표**: 전체 시스템을 TEST 모드로 시작

- [ ] **1.1** GlobalMode를 `TEST`로 설정 (기본값 확인)
  ```bash
  # DynamoDB 확인
  aws dynamodb get-item \
    --table-name {StackName}-GlobalMode \
    --key '{"config_key": {"S": "GLOBAL_MODE"}}'
  # mode="TEST" 확인
  ```

- [ ] **1.2** 모든 16개 채널의 `channel_mode`를 `TEST`로 설정
  ```bash
  # DynamoDB 확인 (예시: wc123456)
  aws dynamodb get-item \
    --table-name {StackName}-ChannelConfig \
    --key '{"channel_id": {"S": "wc123456"}}'
  # channel_mode="TEST" 확인
  ```

- [ ] **1.3** 전체 테스트 통과 확인
  ```bash
  python3 -m pytest -q
  # 384 passed 확인
  ```

- [ ] **1.4** (선택) 1~2개 샘플 채널로 TEST 모드 문의 테스트
  - 웹훅 전송 → Sheets 로그 기록 확인
  - Telegram 알림 수신 확인

**완료 조건**: 모든 채널 TEST 모드 + 테스트 통과

---

### Phase 2: TEST 모드 검증 (1~2주)

**목표**: Sheets 로그와 Telegram 알림으로 답변 품질 검증

- [ ] **2.1** Sheets 로그 확인 (매일 또는 2~3일마다)
  - **확인 항목**:
    - 답변 초안 품질 (정확성, 친절함)
    - 근거(retrieved chunks) 적절성
    - `send_to_user=false` 비율 관찰 (너무 높으면 threshold/KB 조정 필요)

- [ ] **2.2** Telegram 알림 빈도 확인
  - **확인 항목**:
    - 알림이 너무 많은가? (짧은 질문, 이미지 케이스 등)
    - HIGH 리스크 케이스 빈도
    - RAG 근거 부족(insufficient evidence) 빈도

- [ ] **2.3** 품질 이슈 발견 시 조치
  - KB 문서 보강 (Google Docs 업데이트 → 재색인)
  - 프롬프트 튜닝 (아키텍트 협의 필요)
  - 채널별 threshold 조정 고려

**완료 조건**: 1~2주간 안정적 운영 + 답변 품질 수용 가능

---

### Phase 3: 채널별 문서 보강

**목표**: 채널별 KB 문서를 최신 상태로 유지

- [ ] **3.1** 채널별 Google Docs 문서 업데이트
  - 자주 묻는 질문(FAQ) 추가
  - 정책 변경사항 반영

- [ ] **3.2** 재색인 실행 (주 1회 또는 문서 업데이트 시)
  ```bash
  # Indexer Lambda 수동 트리거
  python3 scripts/manual_index_trigger.py
  ```

- [ ] **3.3** 재색인 후 TEST 모드로 재검증
  - 업데이트된 문서 기반으로 답변 품질 확인

**완료 조건**: 채널별 KB 문서 최신화 + 재색인 완료

---

### Phase 4: 부분 PROD 전환 (일부 채널만)

**목표**: 일부 채널만 PROD로 올려서 "부분 준비"

⚠️ **중요**: GlobalMode는 아직 TEST로 유지! (자동 발송은 아직 안 됨)

- [ ] **4.1** 시범 채널 선정 (예: 1~3개 채널)
  - 기준: 문서 품질 높음, 문의 빈도 낮음, 리스크 낮음

- [ ] **4.2** 시범 채널의 `channel_mode`를 `PROD`로 변경
  ```bash
  # DynamoDB 업데이트 (예시: wc123456)
  aws dynamodb update-item \
    --table-name {StackName}-ChannelConfig \
    --key '{"channel_id": {"S": "wc123456"}}' \
    --update-expression "SET channel_mode = :mode" \
    --expression-attribute-values '{":mode": {"S": "PROD"}}'
  ```

- [ ] **4.3** 시범 채널의 초기 `confidence_threshold` 설정
  - **권장 시작값**: `0.85` (보수적)
  - 이미 설정되어 있으면 확인만

- [ ] **4.4** 부분 PROD 상태 확인
  - GlobalMode: `TEST` (아직 자동 발송 안 됨)
  - 시범 채널: `channel_mode=PROD` (준비 완료)
  - 나머지 채널: `channel_mode=TEST`

**완료 조건**: 1~3개 시범 채널만 PROD 준비 완료

---

### Phase 5: 전체 PROD 전환 (GlobalMode 전환)

**목표**: 마지막 게이트 열기 - 자동 발송 시작

⚠️ **매우 중요**: 이 단계부터 실제 고객에게 자동 발송이 시작됩니다!

- [ ] **5.1** 최종 점검
  - [ ] 시범 채널 `channel_mode=PROD` 확인
  - [ ] 시범 채널 `confidence_threshold=0.85` 확인
  - [ ] 나머지 채널 `channel_mode=TEST` 확인 (아직 발송 안 함)
  - [ ] Telegram 봇 정상 작동 확인
  - [ ] Sheets 로그 정상 기록 확인

- [ ] **5.2** GlobalMode를 `PROD`로 전환
  ```bash
  # DynamoDB 업데이트
  aws dynamodb update-item \
    --table-name {StackName}-GlobalMode \
    --key '{"config_key": {"S": "GLOBAL_MODE"}}' \
    --update-expression "SET #mode = :mode" \
    --expression-attribute-names '{"#mode": "mode"}' \
    --expression-attribute-values '{":mode": {"S": "PROD"}}'
  ```

- [ ] **5.3** 자동 발송 시작 확인
  - 시범 채널만 자동 발송 시작 (3-Gate 모두 통과)
  - 나머지 채널은 여전히 TEST (Gate 2 차단)

- [ ] **5.4** 긴급 연락망 대기
  - Telegram 알림 실시간 모니터링 (초기 1~3시간)
  - 문제 발생 시 즉시 롤백 준비

**완료 조건**: GlobalMode=PROD + 시범 채널 자동 발송 시작 + 긴급 대응 준비

---

### Phase 6: 모니터링 및 점진적 확대

**목표**: 초기 1~3일 집중 모니터링 + threshold 튜닝 + 나머지 채널 단계적 전환

#### 6.1 초기 모니터링 (Day 1~3)

- [ ] **Telegram 알림 집중 모니터링**
  - 차단 이유 (`SEND_BLOCKED_*`) 빈도 확인
  - HIGH 리스크 케이스 검토
  - 고객 피드백 확인 (클레임, 만족도)

- [ ] **Sheets 로그 확인**
  - `send_to_user=true/false` 비율
  - 자동 발송된 답변 품질 재확인
  - 잘못된 답변 발견 시 즉시 조치

- [ ] **긴급 상황 대응**
  - 문제 발생 시 → [긴급 롤백 절차](#긴급-롤백-절차) 실행
  - 원인 파악 후 재시도

#### 6.2 Threshold 튜닝 (Day 2~7)

- [ ] **`send_to_user=false` 비율 관찰**
  - **너무 높음** (예: >50%): threshold 너무 높음 → 0.80으로 낮춤
  - **너무 낮음** (예: <10%): 거의 모든 답변 자동 발송 → 품질 재확인 필요

- [ ] **채널별 threshold 조정**
  ```bash
  # DynamoDB 업데이트 (예: 0.85 → 0.80)
  aws dynamodb update-item \
    --table-name {StackName}-ChannelConfig \
    --key '{"channel_id": {"S": "wc123456"}}' \
    --update-expression "SET confidence_threshold = :threshold" \
    --expression-attribute-values '{":threshold": {"N": "0.80"}}'
  ```

- [ ] **튜닝 후 재모니터링** (1~2일)
  - 발송 비율 변화 확인
  - 품질 유지 확인

#### 6.3 나머지 채널 단계적 전환 (Week 2~4)

- [ ] **채널별 전환 우선순위 결정**
  - 기준: KB 품질, 문의 복잡도, 리스크, 문의 빈도

- [ ] **채널별 순차 전환**
  - 1~2개 채널씩 `channel_mode=PROD`로 전환
  - 각 전환 후 1~2일 모니터링
  - 문제 없으면 다음 채널 전환

- [ ] **전체 채널 PROD 완료**
  - 16개 채널 모두 `channel_mode=PROD`
  - GlobalMode: `PROD`
  - 일상 운영 체제 전환

**완료 조건**: 전체 채널 PROD 전환 완료 + 안정적 운영 + 모니터링 체계 확립

---

## 설정 변경 방법

### GlobalMode 변경

**위치**: DynamoDB `{StackName}-GlobalMode` 테이블

**조회**:
```bash
aws dynamodb get-item \
  --table-name {StackName}-GlobalMode \
  --key '{"config_key": {"S": "GLOBAL_MODE"}}'
```

**TEST로 변경** (긴급 중단):
```bash
aws dynamodb update-item \
  --table-name {StackName}-GlobalMode \
  --key '{"config_key": {"S": "GLOBAL_MODE"}}' \
  --update-expression "SET #mode = :mode" \
  --expression-attribute-names '{"#mode": "mode"}' \
  --expression-attribute-values '{":mode": {"S": "TEST"}}'
```

**PROD로 변경**:
```bash
aws dynamodb update-item \
  --table-name {StackName}-GlobalMode \
  --key '{"config_key": {"S": "GLOBAL_MODE"}}' \
  --update-expression "SET #mode = :mode" \
  --expression-attribute-names '{"#mode": "mode"}' \
  --expression-attribute-values '{":mode": {"S": "PROD"}}'
```

⚠️ **주의**: GlobalMode 변경은 **모든 채널에 즉시 영향**

---

### ChannelConfig 변경

**위치**: DynamoDB `{StackName}-ChannelConfig` 테이블

**조회** (예: wc123456):
```bash
aws dynamodb get-item \
  --table-name {StackName}-ChannelConfig \
  --key '{"channel_id": {"S": "wc123456"}}'
```

**channel_mode 변경** (TEST/PROD/DISABLED):
```bash
# PROD로 전환
aws dynamodb update-item \
  --table-name {StackName}-ChannelConfig \
  --key '{"channel_id": {"S": "wc123456"}}' \
  --update-expression "SET channel_mode = :mode" \
  --expression-attribute-values '{":mode": {"S": "PROD"}}'

# TEST로 복구
aws dynamodb update-item \
  --table-name {StackName}-ChannelConfig \
  --key '{"channel_id": {"S": "wc123456"}}' \
  --update-expression "SET channel_mode = :mode" \
  --expression-attribute-values '{":mode": {"S": "TEST"}}'
```

**confidence_threshold 변경**:
```bash
# 0.85로 설정 (보수적)
aws dynamodb update-item \
  --table-name {StackName}-ChannelConfig \
  --key '{"channel_id": {"S": "wc123456"}}' \
  --update-expression "SET confidence_threshold = :threshold" \
  --expression-attribute-values '{":threshold": {"N": "0.85"}}'

# 0.80으로 낮춤 (더 많이 발송)
aws dynamodb update-item \
  --table-name {StackName}-ChannelConfig \
  --key '{"channel_id": {"S": "wc123456"}}' \
  --update-expression "SET confidence_threshold = :threshold" \
  --expression-attribute-values '{":threshold": {"N": "0.80"}}'
```

---

## 모니터링 및 튜닝

### 관찰 대상

| 항목 | 위치 | 확인 내용 | 빈도 |
|------|------|----------|------|
| **Sheets 로그** | Google Sheets | 답변 초안, 근거, send_to_user | 매일 (초기 1~3일) |
| **Telegram 알림** | Telegram | 차단 이유, HIGH 리스크, 에러 | 실시간 (초기 1~3일) |
| **발송 비율** | Sheets `send_to_user` 컬럼 | true/false 비율 | 매일 |
| **고객 피드백** | 톡톡 대화 이력 | 클레임, 만족도 | 수시 |

### Threshold 튜닝 가이드

**목표**: `send_to_user=false` 비율을 적절히 유지

| 현상 | 원인 | 조치 |
|------|------|------|
| **발송 비율 너무 낮음** (<20%) | threshold 너무 높음 | `0.85 → 0.80` 또는 `0.80 → 0.75` |
| **발송 비율 너무 높음** (>80%) | threshold 너무 낮음 | `0.75 → 0.80` 또는 `0.80 → 0.85` |
| **답변 품질 나쁨** | KB 부족 또는 프롬프트 이슈 | KB 보강 또는 아키텍트 협의 |
| **HIGH 리스크 빈번** | 민감한 질문 많음 | 정상 (알림으로 운영자 개입) |

**권장 시작값**: `0.85` (보수적)
**일반 운영**: `0.75 ~ 0.85` 범위에서 채널별 조정

---

## 긴급 롤백 절차

### 롤백 시나리오

다음 상황 발생 시 즉시 롤백:

- ❌ 잘못된 답변이 고객에게 자동 발송됨
- ❌ 시스템 에러로 응답 불가
- ❌ Telegram 알림 폭주 (threshold 너무 낮음)
- ❌ 무한 루프 또는 예상치 못한 동작

### 롤백 레벨

#### Level 1: 전체 시스템 긴급 중단 (Kill Switch)

**상황**: 치명적 문제 발생 - 즉시 모든 자동 발송 중단 필요

**절차**:

1. **GlobalMode를 TEST로 변경**
   ```bash
   aws dynamodb update-item \
     --table-name {StackName}-GlobalMode \
     --key '{"config_key": {"S": "GLOBAL_MODE"}}' \
     --update-expression "SET #mode = :mode" \
     --expression-attribute-names '{"#mode": "mode"}' \
     --expression-attribute-values '{":mode": {"S": "TEST"}}'
   ```

2. **즉시 효과**:
   - 모든 채널 자동 발송 즉시 중단 (Gate 1 차단)
   - Sheets 로그 기록은 계속됨
   - Telegram 알림은 계속됨 (TEST 모드)

3. **확인**:
   - 새 문의 받아서 발송 안 되는지 확인
   - Telegram 알림 "TEST_MODE" 이유 확인

4. **원인 파악 및 조치**:
   - Sheets/Telegram/로그 확인
   - 필요시 KB 업데이트, 프롬프트 수정, threshold 조정
   - 재배포 필요시 코드 수정 후 배포

5. **재시작**:
   - 문제 해결 후 [Phase 5](#phase-5-전체-prod-전환-globalmode-전환)부터 재시작

**복구 시간**: ~1분 (GlobalMode 변경 즉시 반영)

---

#### Level 2: 특정 채널만 중단

**상황**: 특정 채널에서만 문제 발생 - 해당 채널만 격리

**절차**:

1. **문제 채널의 channel_mode를 TEST로 변경**
   ```bash
   # 예: wc123456 채널 중단
   aws dynamodb update-item \
     --table-name {StackName}-ChannelConfig \
     --key '{"channel_id": {"S": "wc123456"}}' \
     --update-expression "SET channel_mode = :mode" \
     --expression-attribute-values '{":mode": {"S": "TEST"}}'
   ```

2. **즉시 효과**:
   - 해당 채널만 자동 발송 중단 (Gate 2 차단)
   - 나머지 채널은 정상 운영 계속
   - 해당 채널은 TEST 모드로 전환 (Sheets 기록 + 알림)

3. **확인**:
   - 해당 채널 새 문의 받아서 발송 안 되는지 확인
   - 나머지 채널 정상 동작 확인

4. **원인 파악 및 조치**:
   - 채널별 KB 확인
   - threshold 재조정
   - 필요시 문서 업데이트

5. **재시작**:
   - 문제 해결 후 해당 채널만 `channel_mode=PROD`로 복구

**복구 시간**: ~1분 (ChannelConfig 변경 즉시 반영)

---

### 롤백 후 체크리스트

- [ ] 롤백 원인 문서화 (Sheets 또는 별도 로그)
- [ ] 영향받은 고객 수 파악
- [ ] 필요시 고객 개별 대응
- [ ] 근본 원인 분석 및 조치
- [ ] 재발 방지 대책 수립
- [ ] 팀 공유 및 회고

---

## 참고 문서

- **Architecture**: `docs/architecture.md` - TEST/PROD 모드 프레임워크
- **Story 7.1**: `docs/stories/7.1.story.md` - TEST 모드 필수 조건
- **Story 7.2**: `docs/stories/7.2.story.md` - PROD 전환 전 안전장치
- **Coding Standards**: `docs/architecture/coding-standards.md` - 테스트 전략

---

## 운영 전 최소 검증

Go-Live 시작 전에 아래 항목을 **반드시** 확인하세요:

### 코드 품질 검증

- [ ] **전체 테스트 통과**
  ```bash
  python3 -m pytest -q
  # 384 passed 확인
  ```

- [ ] **린팅 통과** (선택)
  ```bash
  ruff check .
  # No errors
  ```

### 인프라 확인

- [ ] DynamoDB 테이블 존재 확인:
  - `{StackName}-GlobalMode`
  - `{StackName}-ChannelConfig`

- [ ] Telegram 봇 정상 작동 확인
  - 테스트 메시지 전송 → 알림 수신

- [ ] Google Sheets 접근 확인
  - TEST 문의 → Sheets 기록 확인

### 설정 확인

- [ ] GlobalMode = `TEST` (초기 안전 상태)
- [ ] 모든 ChannelConfig.channel_mode = `TEST`
- [ ] 모든 ChannelConfig.confidence_threshold 존재 (기본 0.85)

---

## 문의 및 지원

- **긴급 문제**: Telegram 알림 채널 확인
- **기술 지원**: 아키텍트/개발팀
- **문서 피드백**: `docs/runbooks/go-live.md` 이슈 제기
