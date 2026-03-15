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

### 시나리오 3: OpenAI API 모델 평가

.env 파일에 OPENAI_API_KEY가 필요하다.

```bash
# 추론 + 스코어링
python -m evaluations.api_runner \
    --model gpt-4o \
    --dataset eval_data/dataset.jsonl \
    --output eval_output_api

# 추론만
python -m evaluations.api_runner \
    --model gpt-4o \
    --dataset eval_data/dataset.jsonl \
    --output eval_output_api \
    --inference-only
```

### 시나리오 4: 기존 predictions로 스코어링만

```bash
python -m evaluations.scorer \
    --predictions eval_output/predictions.jsonl \
    --dataset eval_data/dataset.jsonl \
    --output eval_output
```

### 시나리오 5: 외부 predictions 스코어링

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

### 시나리오 6: predictions.jsonl을 가독성 좋은 텍스트로 변환

```bash
python -m evaluations.convert_readable \
    --predictions eval_output_api/predictions.jsonl
```

`--output`을 생략하면 같은 디렉토리에 `predictions_readable.md`로 생성된다.

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

### Tool Call Level

의존 체인 방식으로 평가한다. 앞 단계가 실패하면 뒷 단계의 분모에서 제외된다.
각 단계의 분모는 이전 단계를 통과한 수이다.

1. relevance_detection_acc
   tool call이 필요한 상황에서 모델이 tool call을 시도했는지,
   필요 없는 상황에서 시도하지 않았는지 판단하는 정확도.
   분모는 전체 샘플 수.

2. format_compliance_acc
   모델이 출력한 tool call의 JSON 형식이 유효한지.
   <tool_call> 태그 안에 유효한 JSON이 있고 name, arguments 필드가 존재하는지 확인.
   분모는 1단계를 통과한 tool call 시도 수.

3. function_matching_acc
   모델이 호출한 함수 이름이 정답과 일치하는지.
   분모는 2단계를 통과한 수.

4. param_hallucination_acc
   모델이 스키마에 정의되지 않은 파라미터를 만들어내지 않았는지.
   분모는 3단계를 통과한 수 중 스키마가 있는 경우. 스키마가 없으면 N/A.

5. required_params_acc
   스키마에서 required로 지정된 필수 파라미터를 모두 포함했는지.
   분모는 4단계를 통과한 수.

6. argument_type_acc
   파라미터 값의 타입이 스키마 명세와 일치하는지.
   예: 스키마가 integer인데 문자열 "2"를 넣으면 실패.
   분모는 5단계를 통과한 수 중 스키마가 있는 경우. 스키마가 없으면 N/A.

7. argument_value_acc
   파라미터 값이 정답과 정확히 일치하는지 (exact match).
   함수 구조는 맞지만 값이 다르면 실패. 최종 정확도를 나타낸다.
   분모는 6단계를 통과한 수.

### Turn / Conversation Level

턴(turn)은 사용자의 실제 발화 1회에 대한 응답 단위이다.
한 턴 안에 tool call이 여러 개일 수 있다 (sequential call).
턴의 pass 판정: tool call이 있는 턴은 모든 tool call step이 정답이면 pass,
tool call이 없는 턴은 모델이 불필요한 tool call을 시도하지 않으면 pass.

- turn_level_accuracy
  전체 턴 중 pass인 턴의 비율.

- conversation_success_rate
  모든 턴이 pass인 대화의 비율. 대화 내 턴이 하나라도 fail이면 그 대화는 실패.
  가장 엄격한 지표.

- conversation_progress_rate
  각 대화에서 pass한 턴의 비율을 구하고, 그 비율들의 평균.
  부분 성공도 반영하므로 success_rate보다 관대한 지표.

- first_failure_turn_avg
  각 대화에서 처음으로 실패한 턴의 인덱스(0부터)를 모아 평균낸 값.
  값이 낮을수록 대화 초반에 실패한다는 의미. -1.0이면 실패한 대화 없음.

- error_cascade_rate
  한 턴이 실패한 직후 다음 턴도 실패할 비율.
  GT History 방식에서 이 값이 높으면 에러 전파가 아니라
  모델이 특정 대화 패턴 자체에 약하다는 의미.

---

## 패키지 구조

```
evaluations/
├── preprocessing.py        # 데이터 전처리 유틸리티
├── metrics.py              # Tool Call Level 단계별 acc 계산
├── multi_turn_metrics.py   # Turn / Conversation Level 집계
├── turn_splitter.py        # GT 히스토리 기반 싱글턴 분할
├── scorer.py               # predictions.jsonl 기반 독립 스코어링
├── runner.py               # vLLM 추론 + 평가 실행기
├── api_runner.py           # OpenAI API 추론 + 평가 실행기
└── convert_readable.py     # predictions.jsonl → 가독성 텍스트 변환
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
