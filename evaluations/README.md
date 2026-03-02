# evaluations

GT 히스토리 기반 Function Calling 평가 파이프라인.
eval/eval_plan.md 기준 단계별 Tool Call / Turn / Conversation 메트릭으로
파인튜닝 모델의 tool calling 능력을 측정한다.

---

## 실행

### 시나리오 1: 인퍼런스 + 스코어링 (기본)

```bash
python -m evaluations.runner \
    --model Qwen/Qwen2.5-7B-Instruct \
    --dataset eval_data/dataset.jsonl \
    --output eval_output
```

### 시나리오 2: 인퍼런스만 (predictions.jsonl 생성)

```bash
python -m evaluations.runner \
    --model Qwen/Qwen2.5-7B-Instruct \
    --dataset eval_data/dataset.jsonl \
    --output eval_output \
    --inference-only
```

### 시나리오 3: 기존 predictions로 스코어링만

```bash
python -m evaluations.scorer \
    --predictions eval_output/predictions.jsonl \
    --dataset eval_data/dataset.jsonl \
    --output eval_output
```

### 시나리오 4: API 모델 결과 스코어링

사용자가 predictions.jsonl 포맷에 맞춰 생성한 파일을 스코어링한다.

predictions.jsonl 레코드 포맷:
```json
{"conversation_id": 0, "turn_index": 0, "step_index": 0, "is_tool_call": true, "gt_response": "...", "prediction": "..."}
```

```bash
python -m evaluations.scorer \
    --predictions api_output/predictions.jsonl \
    --dataset eval_data/dataset.jsonl \
    --output api_output \
    --model gpt-4o
```

결과 파일:
- `eval_output/predictions.jsonl` — 턴별 예측 전체
- `eval_output/eval_results.json` — 메트릭 전체
- `eval_output/eval_results.csv` — 메트릭 요약

---

## 평가 방식

### GT 히스토리 기반 싱글턴 분할

각 턴에 정답(GT) 이전 대화를 context로 넣어 턴별 순수 tool calling 능력을 독립 평가한다.
모델의 이전 예측 오류가 다음 턴 평가에 영향을 주지 않는다.

```
[싱글턴 1]  input: [system, user(T1)]
            label: search_restaurants({"category": "한식"})

[싱글턴 2]  input: [system, GT_T1, user(T2)]
            label: get_restaurant_detail({"restaurant_id": "r1"})

[싱글턴 3]  input: [system, GT_T1, GT_T2, user(T3)]
            label: "결과입니다."  (비호출 → relevance detection 평가)
```

### Sequential Call 처리

한 턴에 tool call이 2개 이상인 경우(sequential call) step 단위로 분할한다.

```
user: "버거킹 메뉴 알려줘"

Step 0  input: [system, user]                         label: search_restaurants(...)
Step 1  input: [system, user, GT_tc0, GT_tr0]         label: get_restaurant_detail(...)
Step 2  input: [system, user, GT_tc0, GT_tr0, GT_tc1, GT_tr1]  label: "메뉴는 ..."
```

---

## 메트릭

### Tool Call Level (분모: 전체 step 수)

의존 체인 방식으로 평가한다. 앞 단계가 실패하면 뒷 단계의 분모에서 제외된다.

```
1. Relevance Detection   — tool call 호출 여부 판단
2. Format Compliance     — JSON 파싱 + name/arguments 필드 존재
3. Function Matching     — 함수 이름 일치
4. Param Hallucination   — 스키마에 없는 파라미터 탐지
5. Required Params       — 필수 파라미터 존재
6. Argument Type         — 타입 명세 일치
7. Argument Value        — 값 exact match
```

| 메트릭 | 설명 |
|--------|------|
| `relevance_detection_acc` | tool call 호출 여부 판단 정확도 |
| `format_compliance_acc` | `<tool_call>` JSON 구조 유효 비율 |
| `function_matching_acc` | 함수 이름 일치율 |
| `param_hallucination_acc` | 스키마에 없는 파라미터를 만들지 않은 비율 |
| `required_params_acc` | 필수 파라미터를 모두 포함한 비율 |
| `argument_type_acc` | 타입 명세를 만족한 비율 |
| `argument_value_acc` | 정답 arguments exact match 비율 |

### Turn / Conversation Level (분모: 턴 수 / 대화 수)

| 메트릭 | 설명 |
|--------|------|
| `turn_level_accuracy` | 전체 턴 중 pass 비율 |
| `conversation_success_rate` | 모든 턴이 pass인 대화 비율 (SR) |
| `conversation_progress_rate` | 대화별 pass 턴 비율의 평균 (PR) |
| `first_failure_turn_avg` | 첫 실패 턴 인덱스 평균 (-1.0 = 실패 없음) |
| `error_cascade_rate` | 이전 턴 실패 후 연속 실패 비율 |

---

## 패키지 구조

```
evaluations/
├── preprocessing.py        # 데이터 전처리 유틸리티
├── metrics.py              # Tool Call Level 단계별 acc 계산
├── multi_turn_metrics.py   # Turn / Conversation Level 집계
├── turn_splitter.py        # GT 히스토리 기반 싱글턴 분할
├── scorer.py               # predictions.jsonl 기반 독립 스코어링
└── runner.py               # vLLM 추론 + 평가 실행기
```

### `preprocessing.py`

데이터셋을 평가 입력 형식으로 변환하는 유틸리티 함수.

| 함수 | 설명 |
|------|------|
| `to_chatml(data)` | messages 리스트를 ChatML 문자열로 변환 |
| `extract_examples(chatml)` | ChatML에서 `(input, label)` 쌍 추출 |
| `format_conversations(sample)` | `system_prompt`를 messages 앞에 삽입 |
| `extract_tool_schemas(tools)` | tools 리스트에서 `{함수명: {properties, required}}` 추출, None 필터링 |

### `metrics.py`

Tool Call Level 메트릭 계산 모듈.

```python
from evaluations.metrics import evaluate_function_calls, EvalResults

results = evaluate_function_calls(labels, predictions, tool_schemas=schemas)
print(results.summary())
```

- `_parse_tool_call(text) -> dict | None` — `<tool_call>` 블록 파싱
- `evaluate_function_calls(labels, predictions, tool_schemas=None) -> EvalResults`
- `evaluate_function_call_step(label, prediction, tool_schemas=None)` — step 단위 판정
- `EvalResults` — `to_dict()`, `summary()` 메서드 제공

### `multi_turn_metrics.py`

Turn / Conversation Level 메트릭 계산 모듈.

```python
from evaluations.multi_turn_metrics import evaluate_multi_turn, MultiTurnResults

# conv_turn_passes[i][j] = i번째 대화 j번째 턴의 pass 여부
results = evaluate_multi_turn(conv_turn_passes)
print(results.summary())
```

- `MultiTurnResults.aggregated` — 전체 step에 대한 Tool Call Level 집계 결과

### `turn_splitter.py`

GT 히스토리 기반 싱글턴 분할 핵심 로직.

```python
from evaluations.turn_splitter import split_conversations, InferenceInput

inputs = split_conversations(conversations)
# inputs[i].messages  : vLLM에 넘길 메시지 리스트
# inputs[i].gt_response : 정답 assistant 응답
# inputs[i].is_tool_call : tool_call 여부
```

`InferenceInput` 필드:

| 필드 | 타입 | 설명 |
|------|------|------|
| `conversation_id` | int | 대화 인덱스 |
| `turn_index` | int | 대화 내 턴 인덱스 |
| `step_index` | int | 턴 내 step (sequential call용) |
| `messages` | list[dict] | system + GT history + 현재 user |
| `gt_response` | str | 정답 assistant 응답 |
| `is_tool_call` | bool | tool_call 여부 |
| `tools` | list[dict] | 함수 스키마 |

### `scorer.py`

predictions.jsonl 기반 독립 스코어링 실행기.

```python
from evaluations.scorer import score_predictions
from pathlib import Path

score_predictions(
    records=records,           # predictions.jsonl 레코드 리스트
    tool_schemas=tool_schemas, # 선택적 스키마 (없으면 None)
    output_dir=Path("eval_output"),
    model_name="my-model",
    dataset_name="eval_data/dataset.jsonl",
)
```

| 함수 | 설명 |
|------|------|
| `score_predictions(records, tool_schemas, output_dir, model_name, dataset_name)` | 레코드 리스트로 메트릭 계산 + 결과 저장 |

### `runner.py`

vLLM 추론 + 메트릭 계산 + 결과 저장 실행기.

```
데이터 로드
  └─ split_conversations()
       └─ ChatML 프롬프트 생성 + vLLM 추론
            └─ predictions.jsonl 저장
                 └─ score_predictions()  (--inference-only이면 생략)
                      ├─ evaluate_function_calls()  → tool_call_level 메트릭
                      └─ turn pass 집계
                           └─ evaluate_multi_turn() → multi_turn 메트릭
                           └─ eval_results.json / eval_results.csv 저장
```

---

## 참고

- `eval/eval_plan.md` — 평가 프레임워크 설계 및 GT 히스토리 방식 채택 근거
- `docs/eval_metric_report.md` — BFCL·Unitxt·HammerBench 메트릭 레퍼런스
- `eval_data/dataset.jsonl` — 평가 기준 데이터 (40개 대화)
