# evaluations — Function Calling 모델 평가 패키지

LLM의 Function Calling(도구 호출) 성능을 정량적으로 평가하기 위한 패키지입니다.  
**BFCL 3대 메트릭 + Unitxt 6종 분해 메트릭 + HammerBench 멀티턴 평가**를 한 번에 계산합니다.

---

## 📁 파일 구조

```
evaluations/
├── __init__.py              # 패키지 초기화
├── metrics.py               # BFCL + Unitxt 통합 메트릭 (핵심)
├── multi_turn_metrics.py    # HammerBench 스타일 멀티턴 평가
├── preprocessing.py         # 데이터 전처리 유틸리티
├── runner.py                # vLLM 기반 전체 평가 파이프라인 CLI
└── README.md                # 이 문서
```

---

## 🚀 빠른 시작

### 1. 싱글턴 평가 (GPU 불필요)

모델 출력이 있다면 `evaluate_function_calls`만 호출하면 됩니다.

```python
from evaluations.metrics import evaluate_function_calls

labels = [
    '<tool_call>\n{"name": "view_user_profile", "arguments": {"user_id": "U002"}}\n</tool_call>',
    '<tool_call>\n{"name": "search_product", "arguments": {"keyword": "노트북"}}\n</tool_call>',
    '안녕하세요! 무엇을 도와드릴까요?',
]

predictions = [
    '<tool_call>\n{"name": "view_user_profile", "arguments": {"user_id": "U002"}}\n</tool_call>',
    '<tool_call>\n{"name": "search_product", "arguments": {"keyword": "마우스"}}\n</tool_call>',
    '안녕하세요! 무엇을 도와드릴까요?',
]

results = evaluate_function_calls(labels, predictions)
print(results.summary())
```

출력:
```
=== Function Calling 평가 결과 ===

[BFCL 메트릭]
  exact_match (ASTAcc)     : 50.00%
  relevance_detection (F1) : 100.00%

[Unitxt 분해 메트릭]
  tool_selection           : 100.00%
  param_name_recall        : 100.00%
  param_name_precision     : 100.00%
  params_value_accuracy    : 50.00%
  schema_valid_rate        : N/A (스키마 미제공)
```

### 2. 멀티턴 평가 (HammerBench 스타일)

대화 단위로 턴별 정확도와 오류 연쇄를 분석합니다.

```python
from evaluations.multi_turn_metrics import evaluate_multi_turn

# 대화별 턴 리스트의 리스트
conv_labels = [
    [  # 대화 1: 검색 → 주문
        '<tool_call>\n{"name": "search", "arguments": {"q": "치킨"}}\n</tool_call>',
        '<tool_call>\n{"name": "order", "arguments": {"id": "1"}}\n</tool_call>',
    ],
]

conv_preds = [
    [  # 대화 1: 검색 맞음, 주문 틀림
        '<tool_call>\n{"name": "search", "arguments": {"q": "치킨"}}\n</tool_call>',
        '<tool_call>\n{"name": "wrong_fn", "arguments": {"id": "1"}}\n</tool_call>',
    ],
]

results = evaluate_multi_turn(conv_labels, conv_preds)
print(results.summary())
```

출력:
```
=== 멀티턴 평가 결과 (HammerBench) ===

[멀티턴 메트릭]
  turn_level_accuracy      : 50.00%
  conversation_success_rate: 0.00%
  first_failure_turn_avg   : 1.0
  error_cascade_rate       : 0.00%
```

### 3. 전체 파이프라인 실행 (GPU 필요)

데이터셋만 지정하면 **스키마 자동 추출 → vLLM 추론 → 메트릭 계산 → 결과 출력**을 한 번에 수행합니다.

```bash
# 기본 평가 (BFCL + Unitxt + 스키마 검증)
python -m evaluations.runner \
    --model Qwen/Qwen2.5-7B-Instruct \
    --dataset jjun123/delivery-app-function-calling-datasets-korean

# 멀티턴(HammerBench) 평가도 포함
python -m evaluations.runner \
    --model Qwen/Qwen2.5-7B-Instruct \
    --dataset jjun123/delivery-app-function-calling-datasets-korean \
    --multi-turn
```

데이터셋에 `tools` 필드가 있으면 자동으로 스키마를 추출하여 `schema_valid_rate`도 함께 측정합니다.

#### 조건별 실행 예시

```bash
# 1) 베이스 모델 평가
python -m evaluations.runner \
    --model Qwen/Qwen2.5-7B-Instruct \
    --dataset jjun123/delivery-app-function-calling-datasets-korean

# 2) 멀티턴(HammerBench) 평가 포함
python -m evaluations.runner \
    --model Qwen/Qwen2.5-7B-Instruct \
    --dataset jjun123/delivery-app-function-calling-datasets-korean \
    --multi-turn

# 3) 테스트 비율 변경 (50%를 테스트로)
python -m evaluations.runner \
    --model Qwen/Qwen2.5-7B-Instruct \
    --dataset jjun123/delivery-app-function-calling-datasets-korean \
    --test-ratio 0.5

# 4) 결과를 특정 경로에 저장
python -m evaluations.runner \
    --model Qwen/Qwen2.5-7B-Instruct \
    --dataset jjun123/delivery-app-function-calling-datasets-korean \
    --output results/base_model_eval.csv

```

> ⚠️ **`runner.py`는 vLLM + GPU 환경에서만 실행됩니다.** 메트릭 계산만 필요하면 `metrics.py`를 직접 import하세요.

---

## 📊 메트릭 체계 설명

### 메트릭이 3종류인 이유

| 프레임워크      | 역할                                     | 비유         |
| --------------- | ---------------------------------------- | ------------ |
| **BFCL**        | "전체적으로 몇 점인지" 한눈에 파악       | 시험 총점    |
| **Unitxt**      | "왜 틀렸는지" 원인 분해                  | 오답 분석표  |
| **HammerBench** | "멀티턴에서 어디서 망가지는지" 턴별 진단 | 대화 CT 검사 |

---

### BFCL 2대 핵심 메트릭

| 메트릭                                  | 보는 것                                   | 쉽게 말하면                   |
| --------------------------------------- | ----------------------------------------- | ----------------------------- |
| **exact_match** (≈ ASTAcc)              | 함수명 + 인자 이름/값이 정답과 완전 일치? | "정답 JSON이랑 똑같이 뱉었나" |
| **relevance_detection_f1** (≈ IrrelAcc) | 호출하면 안 되는 상황에서 거부했나?       | "툴 남발 안 하나"             |

---

### Unitxt 5종 분해 메트릭

| 메트릭                    | 질문                                   |
| ------------------------- | -------------------------------------- |
| **tool_selection**        | 함수 선택이 맞았나?                    |
| **param_name_recall**     | 필수 인자를 빠짐없이 넣었나?           |
| **param_name_precision**  | 쓸데없는 인자를 넣지 않았나?           |
| **params_value_accuracy** | 값이 맞나?                             |
| **schema_valid_rate**     | 타입이 스키마에 맞나? (스키마 제공 시) |

**원인 진단 활용:**

| 증상                             | Unitxt 진단             | 처방                               |
| -------------------------------- | ----------------------- | ---------------------------------- |
| Tool Selection ↑ / Exact Match ↓ | 파라미터 쪽 문제        | 파라미터 다양성 강화               |
| Param Name Recall ↓              | 필수 인자를 자주 빠뜨림 | required 파라미터 학습 데이터 보강 |
| Param Name Precision ↓           | 불필요한 인자 추가      | 불필요 파라미터 없는 예시 보강     |
| Value Precision ↓                | 값 추출 오류            | 맥락→값 추출 패턴 학습 데이터 추가 |

---

### HammerBench 4종 멀티턴 메트릭

| 메트릭                        | 보는 것                             |
| ----------------------------- | ----------------------------------- |
| **turn_level_accuracy**       | 개별 턴 정확도 평균                 |
| **conversation_success_rate** | 대화 전체가 모든 턴 정답인 비율     |
| **first_failure_turn_avg**    | 첫 실패가 발생하는 턴의 평균 위치   |
| **error_cascade_rate**        | 한 턴 틀린 후 다음 턴도 틀리는 비율 |

> **error_cascade_rate**가 높으면 "자기 조건화(self-conditioning)" 문제입니다.  
> 초기 턴의 오류가 후속 턴에 연쇄적으로 전파되고 있다는 뜻입니다.

---

## 🔍 종합 예시: 에러 케이스 분석

| #   | 정답                                                    | 예측                                    | 차이점              |
| --- | ------------------------------------------------------- | --------------------------------------- | ------------------- |
| 1   | `view_user_profile(user_id="U002")`                     | `view_profile(user_id="U002")`          | 함수명 틀림         |
| 2   | `search_product(keyword="노트북", category="전자기기")` | `search_product(keyword="노트북")`      | category 누락       |
| 3   | `check_stock(product_id="P001")`                        | `"재고 확인은 제품 번호가 필요합니다."` | tool_call 자체 실패 |

**BFCL 결과:**
- exact_match: **0.00%** (완전 일치 없음)

**Unitxt 분해 결과:**
- tool_selection: **33.33%** (3개 중 search_product만 맞음)
- param_name_recall: **50.00%** (정답 파라미터 4개 중 2개만 예측에 포함)
- param_name_precision: **100.00%** (예측한 파라미터 2개 모두 정답에 존재)
- params_value_accuracy: **66.67%** (공통 파라미터 값 3개 중 2개 일치)

→ **진단**: 함수 선택이 주요 문제. Recall은 낮지만 Precision은 높음 → 필수 인자 누락이 주 원인.

---

## 🧩 함수 사용법

### `evaluate_function_calls(labels, predictions, tool_schemas=None) → EvalResults`

| 파라미터       | 타입                      | 설명                          |
| -------------- | ------------------------- | ----------------------------- |
| `labels`       | `list[str]`               | 정답 레이블 리스트            |
| `predictions`  | `list[str]`               | 모델 예측 리스트              |
| `tool_schemas` | `dict[str, dict] \| None` | 함수별 파라미터 스키마 (선택) |

**`EvalResults` 속성:**

| 속성                      | 타입    | 설명                          |
| ------------------------- | ------- | ----------------------------- |
| `.exact_match`            | `float` | BFCL ASTAcc (0~1)             |
| `.relevance_detection_f1` | `float` | BFCL IrrelAcc F1 (0~1)        |
| `.tool_selection`         | `float` | Unitxt Tool Choice (0~1)      |
| `.param_name_recall`      | `float` | Unitxt 필수 인자 커버율 (0~1) |
| `.param_name_precision`   | `float` | Unitxt 불필요 인자 비율 (0~1) |
| `.params_value_accuracy`  | `float` | Unitxt 값 정확도 (0~1)        |
| `.schema_valid_rate`      | `float` | 스키마 준수율 (0~1, -1=N/A)   |
| `.to_dict()`              | `dict`  | 딕셔너리 변환                 |
| `.summary()`              | `str`   | 사람이 읽기 좋은 요약         |

### `evaluate_multi_turn(conv_labels, conv_preds, tool_schemas=None) → MultiTurnResults`

| 파라미터                   | 타입                      | 설명                          |
| -------------------------- | ------------------------- | ----------------------------- |
| `conversation_labels`      | `list[list[str]]`         | 대화별 정답 턴 리스트         |
| `conversation_predictions` | `list[list[str]]`         | 대화별 예측 턴 리스트         |
| `tool_schemas`             | `dict[str, dict] \| None` | 함수별 파라미터 스키마 (선택) |

**`MultiTurnResults` 속성:**

| 속성                         | 타입                | 설명                            |
| ---------------------------- | ------------------- | ------------------------------- |
| `.turn_level_accuracy`       | `float`             | 턴별 정확도 평균                |
| `.conversation_success_rate` | `float`             | 대화 전체 성공률                |
| `.first_failure_turn_avg`    | `float`             | 첫 실패 턴 평균 위치            |
| `.error_cascade_rate`        | `float`             | 오류 연쇄율                     |
| `.aggregated`                | `EvalResults`       | 전체 턴 합산 BFCL+Unitxt 메트릭 |
| `.per_turn_results`          | `list[EvalResults]` | 턴별 상세 결과                  |
| `.to_dict()`                 | `dict`              | 딕셔너리 변환                   |
| `.summary()`                 | `str`               | 사람이 읽기 좋은 요약           |

### `prepare_eval_data(dataset, test_ratio) → (prompts, labels)`

HuggingFace Dataset을 평가용 (프롬프트, 정답) 쌍으로 변환합니다.

```python
from datasets import load_dataset
from evaluations.preprocessing import prepare_eval_data

dataset = load_dataset("iamjoon/ecommerce-function-calling-datasets-korean", split="train")
prompts, labels = prepare_eval_data(dataset, test_ratio=0.2)
```

---

## ⚙️ runner.py CLI 옵션

```bash
python -m evaluations.runner --help
```

| 옵션            | 기본값                     | 설명                                 |
| --------------- | -------------------------- | ------------------------------------ |
| `--model`       | (필수)                     | HuggingFace 모델 경로                |
| `--dataset`     | `jjun123/delivery-app-...` | HuggingFace 데이터셋 경로            |
| `--test-ratio`  | `0.2`                      | 테스트 데이터 비율                   |
| `--output`      | `evaluation_results.csv`   | 결과 CSV 저장 경로                   |
| `--temperature` | `0`                        | 샘플링 온도 (0 = greedy)             |
| `--max-tokens`  | `2048`                     | 최대 생성 토큰 수                    |
| `--multi-turn`  | (플래그)                   | 멀티턴(HammerBench) 평가도 함께 실행 |

**결과물:**
- `evaluation_results.csv` — 프롬프트, 정답, 예측 상세 기록
- `evaluation_results.metrics.json` — 전체 메트릭 JSON (멀티턴 포함)

---

## 🧪 테스트

```bash
python -m pytest tests/test_evaluations.py -v
```

35개 테스트: 파싱, BFCL 메트릭, Unitxt 분해(Recall/Precision 분리, 스키마 검증), HammerBench 멀티턴(대화 성공률, 오류 연쇄율), 전처리(스키마 추출) 등을 검증합니다.
