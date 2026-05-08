# 현재 프로젝트 평가 설계

## 목적

이 문서는 현재 프로젝트에서 사용하는 LLM function calling 평가 체계의 설계 기준을 정리한 문서다.

[01_eval_problem_definition.md](/home/wonjun/llm-project/docs/eval/01_eval_problem_definition.md:1) 에서 왜 평가 설계가 별도로 필요했는지를 설명했고, [02_eval_metric_report.md](/home/wonjun/llm-project/docs/eval/02_eval_metric_report.md:1) 에서 BFCL과 HammerBench를 조사하며 무엇을 배웠는지 정리했다. 이 문서는 그 다음 단계로, 현재 프로젝트에서 실제로 어떤 평가 구조를 채택했는지를 정의한다.

현재 설계의 핵심은 아래와 같다.

- single-turn에서는 tool call의 구조 정확성을 단계별로 분해해 본다
- multi-turn에서는 turn / conversation 단위의 성공 여부와 진행률을 함께 본다
- 실제 backend state를 재현하지 않으므로, GT history 기반 분할로 순수 tool calling 능력을 측정한다
- 평가는 모델 간 단순 순위화보다, 같은 베이스 모델에서 데이터와 학습 조건 변화가 어떤 하위 능력에 영향을 주는지 읽는 계측 체계에 가깝다

## 1. 싱글턴 정의

user 입력 1회에 대해 assistant가 수행하는 모든 출력(tool_call, tool_response, 최종 응답)을 하나로 묶은 단위.

```
1) 정상적인 경우
   user → assistant(tool_call) → tool_response → assistant(최종 응답)

2) 여러번 툴콜링을 하는 경우 (Sequential)
   user → assistant(tool_call A) → tool_response A
        → assistant(tool_call B) → tool_response B
        → assistant(최종 응답)
```

1, 2번 모두 싱글턴으로 취급한다.

## 2. 전제 조건

- Parallel function call은 챗봇 기능상 필요하지 않으므로 배제한다.
- Sequential function call은 학습 데이터에 포함하되, 평가 데이터셋에서 제한을 두고 생성한다.
- Metric의 기본 판정은 Pass/Fail로 구성한다.
  어느 지점에서 오류가 났는지를 파악하고 모델 성능 향상 루프를 진행한다.
  이후 Precision, Recall 등 세부 수치를 추가한다.

## 3. 평가 항목 (Tool Call Level)

하나의 tool call에 대해 아래 순서로 평가한다.
각 단계는 다음 단계의 전제 조건이다.

```
1. Function Relevance Detection
   툴 호출 필요성 판단 정확도.

2. Function Call Correctness
   함수 호출 정확도.

   2.1 Format Compliance
       <tool_call> 태그 안의 JSON이 유효한 구조인가.
       - JSON 파싱 성공 여부
       - name, arguments 필드 존재 여부
       fail 시 이후 모든 단계를 평가할 수 없으므로 자동 fail 처리한다.

   2.2 Function Matching
       함수 이름이 정확히 일치하는가.

   2.3 Parameter & Argument Matching
       함수 호출에 들어간 파라미터와 아규먼트가 명세와 일치하는가.

       2.3.1 Parameter Hallucination Detection
             모델이 예측한 파라미터 이름이 스키마에 실제로 존재하는가.

       2.3.2 Required Parameters Matching
             필수 파라미터에 대응하는 아규먼트가 모두 존재하는가.

       2.3.3 Argument Type Matching
             아규먼트의 타입이 파라미터의 타입 명세와 일치하는가.

       2.3.4 Argument Value Matching
             아규먼트의 값이 정답과 일치하는가. (exact match)
```

## 4. 평가 레벨

하나의 conversation을 유저 입력 기준으로 싱글턴 N개로 분할하고,
싱글턴 N개에서 tool call M개를 추출한다.
eval 데이터셋은 T개의 conversation으로 구성된다.

### 4.1 Tool Call Level (분모: M)

개별 tool call을 독립 평가한다.
전체 micro acc와 함께 항목별 micro acc를 산출한다.

```
micro acc ~= Σ(pass) / Σ(M_i),  i = 1..T
```

항목별 개별 성능:
- Relevance Detection
- Format Compliance
- Function Matching
- Parameter Hallucination Detection
- Required Parameters Matching
- Argument Type Matching
- Argument Value Matching

> 의존 체인에 따라, 앞 단계가 fail인 경우 뒷 단계의 분모에서 제외한다.

### 4.2 Turn Level (분모: N)

해당 턴의 모든 tool call이 pass여야 턴 pass.
sequential call이 2개이면 둘 다 pass여야 한다.

```
micro acc ~= Σ(pass) / Σ(N_i),  i = 1..T
```

### 4.3 Conversation Level (분모: T)

- **SR (Success Rate)**: conversation 내 모든 턴이 pass여야 해당 conversation pass. All or nothing.
- **PR (Progress Rate)**: conversation 내 pass 턴 비율의 평균.
- **First Failure Turn Avg**: 실패가 처음 발생하는 턴 위치의 평균.
- **Error Cascade Rate**: 한 턴 실패 후 다음 턴도 연속 실패하는 비율.

## 5. 멀티턴 평가를 위한 싱글턴 분할

### 5.1 파이프라인

```
[추론] eval 데이터셋 → 모델 → pred_conversation 저장
[평가] gt_conversation + pred_conversation → 평가 스크립트 → 점수
```

추론과 평가를 분리한다. 재현성 확보, 디버깅 용이성, 모델 간 비교가 가능하다.

### 5.2 싱글턴 분할 방식

gt 히스토리 기반으로 분할한다.
각 턴의 히스토리에 정답(gt) 대화를 넣어
턴별 순수 툴콜링 능력을 독립적으로 측정한다.

```
(예시) 3턴 conversation

[싱글턴 1] — 히스토리 없음
  input:  user: "서울 날씨 알려줘"
  label:  get_weather(city="서울")

[싱글턴 2] — turn 1의 gt를 히스토리로 포함
  input:  [turn 1 정답 대화] + user: "거기 맛집 찾아줘"
  label:  search_restaurant(city="서울")

[싱글턴 3] — turn 1~2의 gt를 히스토리로 포함
  input:  [turn 1~2 정답 대화] + user: "첫번째로 2명 예약해줘"
  label:  book_restaurant(name="○○식당", people=2)
```

### 5.3 히스토리 방식 변경 이력

초기 설계에서는 pred 히스토리(모델 실제 출력을 히스토리에 누적)를 계획했으나,
gt 히스토리(정답 대화를 히스토리에 누적)로 변경했다. 근거는 다음과 같다.

1. **tool_response 생성 문제**: pred 히스토리 방식에서는 모델이 tool_call을 예측한 뒤
   그에 대한 tool_response를 생성해야 다음 턴으로 넘어갈 수 있다.
   현재 mock 함수(`datagen/tool_specs.py`)가 입력 파라미터와 무관하게
   하드코딩된 동일한 값을 반환하므로, 모델이 올바른 호출을 해도
   비현실적인 tool_response가 히스토리에 쌓인다.
   이는 현재 평가 설계가 의도한 "자연스러운 오류 전파"가 아닌
   mock의 한계에 의한 인위적 분기를 유발한다.

2. **진단 용이성**: gt 히스토리에서 턴별 독립 평가를 하면,
   "어떤 유형의 함수 호출에서 모델이 약한지"를 정확히 파악할 수 있다.
   pred 히스토리에서는 Turn N이 틀렸을 때
   Turn N 자체의 문제인지, 이전 턴 오류의 전파인지 구분이 어렵다.

3. **단계적 확장**: gt 히스토리로 기본 성능을 먼저 확인한 뒤,
   mock 함수를 파라미터 반응형으로 고도화하거나 DB를 연동한 후
   pred 히스토리 방식을 추가하는 것이 현실적인 경로이다.

## 6. 점수 산출 예시

3턴, tool call 4개인 상황:

```
turn 1: tool_call A (pass)                     → 턴 pass
turn 2: tool_call B (pass) → tool_call C (fail) → 턴 fail
turn 3: tool_call D (pass)                     → 턴 pass
```

| 레벨 | 계산 | 결과 |
|------|------|------|
| Tool Call Level | 3/4 | 75.0% |
| Turn Level | 2/3 | 66.7% |
| Conversation SR | 전체 턴 pass 아님 | 0 |
| Conversation PR | 2/3 | 66.7% |

T=3 conversation으로 확장:

| conversation | 턴 결과 | SR | PR |
|-------------|---------|----|----|
| conv 1 | pass, fail, pass | 0 | 66.7% |
| conv 2 | pass, pass, pass | 1 | 100% |
| conv 3 | fail, fail, pass | 0 | 33.3% |

| 레벨 | 결과 |
|------|------|
| 전체 SR | 1/3 = 33.3% |
| 전체 PR | (66.7 + 100 + 33.3) / 3 = 66.7% |

## 7. 기존 벤치마크와의 차이

### 7.1 HammerBench와의 차이

**히스토리 방식:**
HammerBench와 동일하게 gt 히스토리 기반 스냅샷으로 각 턴의 순수 툴콜링 능력을 측정한다.
향후 mock 함수 고도화 시 pred 히스토리 방식을 추가하여 오류 전파 측정도 가능하다.
(변경 근거는 5.3 참조)

**평가 항목 세분화:**
HammerBench는 아규먼트의 타입과 값을 Args Acc 하나로 뭉뚱그려 측정한다.
현재 프레임워크는 Argument Type Matching과 Argument Value Matching을 분리하여
실패 원인을 구체적으로 진단한다.

### 7.2 BFCL과의 차이

**싱글턴 판정 방식:**
BFCL은 AST 비교로 파라미터와 아규먼트를 구분 없이 하나의 pass/fail로 평가한다.
현재 프레임워크는 Hallucination → Required → Type → Value 의존 체인으로
실패 지점을 단계별로 특정한다.

**멀티턴 판정 방식:**
BFCL V3 멀티턴은 state-based evaluation과 response-based evaluation을 함께 사용한다.
state-based는 각 턴 종료 시 백엔드 시스템 상태가 정답과 일치하는지를 보고,
response-based는 모델의 실행 경로가 정답의 최소 실행 경로를 부분 집합으로 포함하는지를 본다.
모델이 탐색을 위해 추가 호출을 해도 최소 경로를 포함하면 허용한다.
현재 프레임워크는 각 tool call을 gt label과 exact match로 비교한다.
우회 경로나 탐색적 호출을 허용하지 않으며, 정답 경로와 정확히 일치해야 한다.

**평가 대상 범위:**
parallel call을 포함하는 BFCL과는 다르게 sequential call에 집중한다.

## 8. 구현 대응

이 설계는 아래 코드에 반영되어 있다.

- [metrics.py](/home/wonjun/llm-project/evaluations/metrics.py:1)
- [multi_turn_metrics.py](/home/wonjun/llm-project/evaluations/multi_turn_metrics.py:1)
- [turn_splitter.py](/home/wonjun/llm-project/evaluations/turn_splitter.py:1)
- [scorer.py](/home/wonjun/llm-project/evaluations/scorer.py:1)

이 문서를 수정할 때는 위 구현과의 불일치를 함께 확인해야 한다.
