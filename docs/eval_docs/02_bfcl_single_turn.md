> 이 문서는 BFCL singleton 평가를 정리한 핵심 근거 문서다.
> 현재 프로젝트용 정리 문서는 [docs/eval/02_eval_metric_report.md](/home/wonjun/llm-project/docs/eval/02_eval_metric_report.md:1) 이다.

# BFCL Single-Turn

## 1. BFCL Singleton의 본질

BFCL singleton은 단 한 번의 턴에서 모델이 정확한 함수 호출 구조를 생성했는가를 평가한다.

멀티턴처럼 상태 비교나 trajectory 완주 여부를 보지 않고, 출력된 함수 호출의 구조적 정확성만 본다.

## 2. 평가 방식 3가지

BFCL singleton은 세 가지 방식으로 평가한다.

**AST evaluation**: 모델 출력의 함수 호출을 AST로 파싱하여 함수명, required parameter, hallucination 여부, 타입/값을 엄격하게 비교한다. 사실상 JSON Schema Validation 문제다.

**Executable evaluation**: 생성한 호출을 실제로 실행해서 기대 결과와 맞는지 확인한다. AST가 구조적 정확성을 보는 반면, executable은 실행 가능성과 결과까지 본다.

**Relevance detection**: 호출해야 할 함수가 제공된 tool list에 없는 상황에서 아무 함수도 호출하지 않는지를 본다. tool hallucination 억제를 직접 측정한다.

AST evaluation의 핵심 기준 6가지:

1. 함수명 정확성
2. 필수(required) 파라미터 존재 여부
3. 파라미터 이름 정확성
4. 타입 정확성
5. 스키마 외 파라미터 없음
6. 값 제약 조건 만족

이 기준은 현재 프로젝트에서 `function_matching`, `required_params`, `argument_type`, `argument_value`, `param_hallucination`으로 번역되는 출발점이 되었다.

## 3. Singleton 평가 절차

평가 흐름은 아래와 같이 이해했다.

```text
User 요청
  ↓
Model 함수 호출 생성
  ↓
JSON/AST 파싱
  ↓
Schema Validation 수행
  ↓
모든 조건 통과 → Correct
하나라도 실패 → Wrong
```

Singleton은 기본적으로 all-or-nothing 성격이 강하다.

## 4. Task 유형 메모

조사 문서에서는 singleton 안에서도 다음처럼 난이도를 나눴다.

- **Simple**: 단일 함수 1회 호출
- **Parallel**: 동일 함수를 여러 인자로 다회 호출 (예: 서울/도쿄 날씨를 동시에 조회)
- **Multiple**: 서로 다른 함수를 여러 개 호출 (예: 거리 계산 후 배송비 계산)
- **Parallel + Multiple**: 동일 함수 다회 + 다른 함수 다회를 동시에 요구하는 최고 난이도

현재 프로젝트는 parallel call보다 sequential call과 turn 분해가 더 중요했기 때문에, singleton 철학은 유지하되 데이터 구조에는 그대로 복제하지 않았다.

## 5. 이 문서에서 얻은 결론

이 문서를 통해 가장 먼저 배운 것은 `툴콜링 평가는 자연어 답변 품질이 아니라 함수 호출 구조 정확성 평가`라는 점이었다. 이후 평가 코드 설계에서 구조 정확성을 먼저 분해해서 보게 된 출발점이 이 문서다.
