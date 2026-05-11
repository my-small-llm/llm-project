# Experiment Documentation Convention

이 문서는 `docs/` 아래 실험 문서를 어떤 순서와 규격으로 작성할지 정리합니다. 목표는 두 가지입니다.

- 연구를 진행하는 사람이 같은 흐름으로 기록할 수 있게 한다.
- 처음 보는 사람도 같은 흐름으로 읽을 수 있게 한다.

이 규약은 특히 `docs/Troubleshooting/`에 강하게 적용하지만, 원칙 자체는 `docs/` 전체 실험 문서에 공통으로 사용합니다.

## 기본 원칙

- 문서는 질문 중심으로 쓴다.
- 한 문서는 한 단계의 한 질문에 집중한다.
- 관측, 원인, 결정, 결과를 한 문서에 섞지 않는다.
- 파일명만 보고도 읽기 순서와 주제가 드러나야 한다.
- 문서 본문은 현재 작업 언어를 따른다.
- 실제 문서 생성이나 수정 전에는 관련 문서를 먼저 읽고, 기존 문서를 재사용할지 판단한다.

## 표준 실험 흐름

실험 문서는 가능한 한 아래 순서를 기준으로 구성합니다.

1. `00_experiment_charter`
2. `01_eval_discovery`
3. `02_root_cause`
4. `03_fix_plan`
5. `04_execution_log`
6. `05_result_report`

모든 실험이 모든 단계를 반드시 가지는 것은 아닙니다. 다만 문서를 새로 만들 때는 항상 현재 작업이 이 중 어느 단계인지 먼저 판별해야 합니다.

## 단계별 역할

| 단계 | 답하는 질문 | 문서 역할 |
|------|-------------|-----------|
| `00_experiment_charter` | 무엇을 검증하려는가? | 실험 목표, 범위, 성공 기준 정의 |
| `01_eval_discovery` | 무엇이 이상한가? | 실패/현상 관측과 분류 |
| `02_root_cause` | 왜 이런 현상이 생겼는가? | 원인 판정과 책임 위치 구분 |
| `03_fix_plan` | 무엇을 바꿀 것인가? | 수정 결정과 적용 계획 |
| `04_execution_log` | 실제로 어떻게 적용했는가? | 실행 순서와 적용 메모 |
| `05_result_report` | 무엇이 얼마나 바뀌었는가? | 전후 비교와 결과 해석 |

## 파일명 규칙

메인 문서는 아래 형식을 기본으로 사용합니다.

```text
<순서>_<주제>_<문서유형>.md
```

예시:

```text
00_train_data_v3_experiment_charter.md
01_relevance_detection_failure_report.md
02_relevance_detection_root_cause.md
03_datagen_fix_plan.md
05_train_data_v3_result_report.md
```

규칙:

- 읽기 순서가 필요한 메인 문서는 번호 접두어를 붙입니다.
- 파일명은 주제가 먼저 드러나야 합니다.
- 날짜나 실험 ID는 파일명보다 메타데이터에서 관리합니다.
- 메모성 문서는 `notes_`, `hypothesis_` 접두어를 사용할 수 있습니다.
- `README.md`는 해당 폴더의 읽기 순서와 단계 경계를 설명하는 인덱스 문서로 유지합니다.

권장 문서 유형 어휘:

- `experiment_charter`
- `failure_report`
- `root_cause`
- `decision_summary`
- `fix_plan`
- `execution_log`
- `result_report`
- `notes`
- `README`

## 상단 메타데이터 규칙

실험 문서는 상단에 아래 메타데이터 블록을 두는 것을 기본으로 합니다.

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

필드 설명:

- `experiment_slug`: 같은 실험 흐름을 묶는 식별자
- `stage`: 현재 문서 단계
- `question`: 이 문서가 답하려는 질문
- `status`: 진행 상태
- `owner`: 주 작성자
- `related_eval_output`: 관련 평가 산출물
- `related_code_paths`: 관련 코드 경로
- `related_docs`: 선행 또는 연결 문서
- `last_updated`: 마지막 갱신일

규칙:

- 메타데이터 키는 영문 유지
- 본문은 사용자 언어 사용
- 같은 실험 흐름에서는 `experiment_slug`를 일관되게 사용

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

## 기존 문서 업데이트 vs 새 문서 생성

기존 문서를 업데이트하는 경우:

- 같은 실험
- 같은 단계
- 같은 핵심 질문
- 새 표, 새 수치, 새 사례를 추가하는 경우

새 문서를 만드는 경우:

- 단계가 바뀌는 경우
- 핵심 질문이 바뀌는 경우
- 의사결정 단위가 분기되는 경우
- 기존 문서가 너무 커져 읽기 흐름이 깨지는 경우

## 언어 규칙

- 문서 본문은 사용자의 현재 요청 언어를 따릅니다.
- 기존 문서 묶음이 이미 한 언어로 통일돼 있으면 그 언어를 우선합니다.
- 같은 실험 흐름 안에서는 언어를 섞지 않습니다.
- 메타데이터 키, 코드 경로, 파일 경로는 영문 표기를 유지합니다.

## `Troubleshooting/`에 적용하는 방법

`docs/Troubleshooting/`은 이 규약을 가장 엄격하게 따르는 대표 폴더입니다.

- `1_eval_discovery/`에서는 현상 관측과 실패 분류만 다룹니다.
- `2_root_cause/`에서는 원인 판정과 책임 위치를 다룹니다.
- `3_fixes/`에서는 실제 수정 결정과 적용 계획을 다룹니다.
- 폴더별 `README.md`는 읽기 순서와 단계 경계를 설명하는 문서로 유지합니다.

즉, `Troubleshooting/`은 이 규약의 축약형이 아니라, 가장 선명한 대표 구현입니다.

## AI 사용 규칙

AI가 실험 문서를 만들거나 고칠 때는 아래 순서를 따릅니다.

1. 관련 `docs/` 문서와 해당 폴더의 `README.md`를 읽습니다.
2. 현재 작업이 어느 단계인지 판별합니다.
3. 기존 문서를 업데이트할지 새 문서를 만들지 결정합니다.
4. 필요한 문서 목록과 파일명을 먼저 제안합니다.
5. 사용자 승인 후에만 실제 파일을 생성하거나 수정합니다.

## 금지 사항

- 관측 단계 문서에서 원인을 확정하지 않기
- 원인 분석 문서에서 수정 결정을 끝내지 않기
- 결과 보고서에서 근거 없이 성공만 선언하지 않기
- 실제 대화 원문, 프롬프트 전문, 모델 응답 전문을 문서에 넣지 않기
- 같은 실험 흐름 안에서 파일명 규칙과 언어 규칙을 흔들지 않기
