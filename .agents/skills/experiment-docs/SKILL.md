---
name: experiment-docs
description: Use when the user wants AI to create, extend, or reorganize experiment and troubleshooting documents under docs/. This skill standardizes experiment documentation flow, file naming, stage transitions, metadata blocks, and language choice so both researchers and first-time readers can follow the same sequence.
---

# Experiment Docs

이 skill은 `docs/` 아래 실험 문서를 같은 흐름으로 만들고 유지하기 위한 규약이다.

언제 사용하나:
- 사용자가 실험 문서를 새로 만들고 싶어 할 때
- 사용자가 트러블슈팅 문서 흐름을 정리하고 싶어 할 때
- 사용자가 결과 보고서, 실패 보고서, 원인 분석, 수정 계획 문서를 구조화하고 싶어 할 때
- AI가 실험 기록 순서나 파일명을 제안해야 할 때

## 목표

- 사람과 AI가 같은 실험 문서 흐름을 따른다.
- 처음 보는 사람도 문서를 읽는 순서를 예측할 수 있어야 한다.
- 한 문서가 다루는 질문과 단계가 분명해야 한다.
- 문서는 파일명, 메타데이터, 본문 템플릿에서 일관성을 유지해야 한다.

## 먼저 할 일

1. `docs/CLAUDE.md`와 관련 폴더의 README를 읽는다.
2. 현재 실험이 어떤 단계에 있는지 판별한다.
3. 이미 같은 질문을 다루는 문서가 있는지 찾는다.
4. 새 문서가 필요한지, 기존 문서 업데이트가 맞는지 결정한다.
5. 실제 파일 수정 전에는 반드시 사용자 승인을 받는다.

## 최상위 문서 흐름

기본 실험 흐름은 아래 순서를 따른다.

1. `00_experiment_charter`
2. `01_eval_discovery`
3. `02_root_cause`
4. `03_fix_plan`
5. `04_execution_log`
6. `05_result_report`

모든 실험이 모든 단계를 다 가져야 하는 것은 아니다. 다만 AI는 항상 이 상위 프레임으로 현재 위치를 먼저 판단해야 한다.

- `Troubleshooting/`은 `01 → 02 → 03` 흐름을 가장 엄격하게 따른다.
- `result_report` 계열 문서는 보통 `05_result_report` 역할을 맡는다.
- `eval/`이나 `data/` 문서는 실험 전반을 직접 기록하지 않아도 되지만, 가능하면 어느 단계 산출물인지 문서 안에서 드러내야 한다.

## 단계별 역할

### `00_experiment_charter`

실험 시작 전 문서다.

- 답하는 질문: 무엇을 검증하려는가?
- 포함할 것: 문제, 가설, 범위, 제외 범위, 성공 기준, 산출물

### `01_eval_discovery`

실패나 현상을 관측하고 분류하는 단계다.

- 답하는 질문: 무엇이 이상한가?
- 여기서는 원인을 확정하지 않는다.
- 포함할 것: 관측값, 대표 사례, 패턴 분류, 다음 질문

### `02_root_cause`

관측된 현상의 원인을 판정하는 단계다.

- 답하는 질문: 왜 이런 현상이 생겼는가?
- 포함할 것: 증거, 배제한 가설, 원인 판정, 책임 위치

### `03_fix_plan`

수정 방향과 의사결정을 남기는 단계다.

- 답하는 질문: 무엇을 바꿀 것인가?
- 포함할 것: 결정 사항, 대안 비교, 적용 범위, 검증 방법, 롤백 조건

### `04_execution_log`

실행 과정과 적용 내역을 남기는 단계다.

- 답하는 질문: 실제로 어떻게 적용했는가?
- 포함할 것: 변경 순서, 실행 로그 요약, 관찰 메모, 후속 확인 항목

### `05_result_report`

실험 결과를 전후 비교로 정리하는 단계다.

- 답하는 질문: 무엇이 얼마나 좋아지거나 나빠졌는가?
- 포함할 것: 변경 요약, 전후 비교, 남은 리스크, 다음 단계

## 파일명 규칙

파일명은 아래 형식을 기본으로 한다.

```text
<순서>_<주제>_<문서유형>.md
```

예시:
- `00_train_data_v3_experiment_charter.md`
- `01_relevance_detection_failure_report.md`
- `02_relevance_detection_root_cause.md`
- `03_datagen_fix_plan.md`
- `05_train_data_v3_result_report.md`

규칙:
- 읽기 순서가 필요한 메인 문서는 `00_`, `01_`, `02_`처럼 번호를 붙인다.
- 파일명은 소문자와 `_` 중심으로 쓴다.
- 파일명은 질문이나 주제가 먼저 드러나야 한다.
- 날짜나 실험 ID는 파일명보다 문서 상단 메타데이터에 둔다.
- 메모성 문서는 `notes_` 또는 `hypothesis_` 접두어를 사용할 수 있다.
- `README.md`는 폴더 읽기 순서와 단계 경계를 설명하는 인덱스 문서로만 사용한다.

문서 유형 어휘는 아래 중에서 우선 선택한다.

- `experiment_charter`
- `failure_report`
- `root_cause`
- `decision_summary`
- `fix_plan`
- `execution_log`
- `result_report`
- `notes`
- `README`

## 메타데이터 규칙

실험 문서 상단에는 공통 메타데이터 블록을 둔다.

```md
---
experiment_slug: train-data-v3
stage: root_cause
question: Why does the current train data structure fail to preserve tool-use state?
status: in_progress
owner: codex
related_eval_output:
  - eval_output/before_eval_dataset/eval_results_comparison.md
related_code_paths:
  - datagen/
  - train/
related_docs:
  - docs/Troubleshooting/1_eval_discovery/05_argument_value_failure_report.md
last_updated: 2026-05-08
---
```

필드 규칙:
- 메타데이터 키는 영문 유지
- 본문은 사용자 언어 사용
- `stage`는 `experiment_charter`, `eval_discovery`, `root_cause`, `fix_plan`, `execution_log`, `result_report` 중 하나를 쓴다
- `question`은 이 문서가 답하려는 질문 한 줄이어야 한다
- `status`는 `planned`, `in_progress`, `done`, `superseded` 중 하나를 우선 사용한다

## 언어 규칙

- 문서 본문은 사용자의 현재 요청 언어를 따른다.
- 기존 문서 묶음이 이미 한 언어로 통일돼 있으면 그 언어를 우선한다.
- 같은 실험 흐름 안에서는 언어를 섞지 않는다.
- 메타데이터 키와 코드 경로는 영문 표기를 유지한다.

## 새 문서 vs 기존 문서 업데이트

아래 기준으로 판단한다.

기존 문서 업데이트:
- 같은 `experiment_slug`
- 같은 `stage`
- 같은 핵심 질문
- 새 증거, 새 표, 새 사례, 새 반례를 보강하는 경우

새 문서 생성:
- 단계가 바뀐 경우
- 핵심 질문이 바뀐 경우
- 결정 단위가 분기된 경우
- 한 문서가 너무 커져 읽기 흐름이 깨지는 경우

예시:
- `01_relevance_detection_failure_report.md`에 사례가 더 생기면 기존 문서 업데이트
- 원인 판정으로 넘어가면 `02_relevance_detection_root_cause.md` 새 문서 생성
- `search_restaurants` 아래 결정이 `query_category`와 `min_rating`으로 갈라지면 각각 새 문서 생성

## 문서 생성 절차

사용자가 실험 문서 작성을 요청하면 아래 순서를 따른다.

1. 현재 문서 흐름과 관련 폴더를 읽는다.
2. 현재 단계와 핵심 질문을 판별한다.
3. 필요한 문서 목록과 파일명을 제안한다.
4. 실제 생성 또는 수정 전 사용자 승인을 받는다.
5. 승인 후 초안을 작성한다.
6. 필요하면 관련 `README.md`에 읽기 순서 반영 여부를 점검한다.

## 문서 유형별 필수 섹션

### `experiment_charter`

- 문제
- 가설
- 실험 범위
- 제외 범위
- 성공 기준
- 산출물

### `failure_report`

- 관측값
- 대표 사례
- 패턴 분류
- 아직 해석하지 않은 점
- 다음 질문

### `root_cause`

- 문제 재정의
- 증거
- 배제한 가설
- 원인 판정
- 책임 위치
- 다음 단계 연결

### `decision_summary` / `fix_plan`

- 문제 정의
- 결정 사항
- 고려한 대안
- 적용 범위
- 검증 방법
- 롤백 조건

### `execution_log`

- 변경 순서
- 실행 내역
- 중간 관찰
- 남은 확인 항목

### `result_report`

- 변경 요약
- 전후 비교
- 해석
- 남은 리스크
- 다음 단계

## 출력 스타일

- 처음 보는 사람도 읽을 수 있게 질문 중심으로 쓴다.
- 원인과 결정을 섞지 않는다.
- 결과 문서에서는 수치 비교를 먼저 보여준다.
- 실제 대화 원문, 프롬프트 전문, 모델 응답 전문은 저장소 규칙에 맞게 포함하지 않는다.
- 코드 경로는 `datagen/tool_specs.py` 같은 모듈 경로 형식으로 적는다.

## 이 저장소에서 특히 맞춰야 할 점

- `docs/Troubleshooting`은 `발견 → 원인 → 수정` 경계를 흐리지 않는다.
- `1_eval_discovery`에서는 원인 확정이나 수정 결정을 하지 않는다.
- `2_root_cause`에서는 책임 위치와 원인 판정을 분리해서 쓴다.
- `3_fixes`에서는 실제 결정과 적용 계획을 문서화한다.
- 이미 해결된 트러블슈팅 문서도 의사결정 근거이므로 삭제보다 유지가 기본이다.
