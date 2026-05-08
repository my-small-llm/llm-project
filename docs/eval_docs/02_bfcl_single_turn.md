> 이 문서는 BFCL singleton 평가를 정리한 핵심 근거 문서다.
> 현재 프로젝트용 정리 문서는 [docs/eval/02_eval_metric_report.md](/home/wonjun/llm-project/docs/eval/02_eval_metric_report.md:1) 이다.

# BFCL Single-Turn

## 1. BFCL Singleton의 본질

BFCL singleton은 단 한 번의 턴에서 모델이 정확한 함수 호출 구조를 생성했는가를 평가한다.

멀티턴처럼 상태 비교나 trajectory 완주 여부를 보지 않고, 출력된 함수 호출의 구조적 정확성만 본다.

## 2. Singleton의 핵심 평가 기준

BFCL Singleton은 사실상 JSON Schema Validation 문제로 이해할 수 있다. 조사 과정에서 정리한 핵심 기준은 아래 여섯 가지였다.

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

조사 문서에서는 singleton 안에서도 다음처럼 난이도를 나눠 이해했다.

- Simple: 단일 호출
- Parallel: 동일 함수 다회 호출

현재 프로젝트는 parallel call보다 sequential call과 turn 분해가 더 중요했기 때문에, singleton 철학은 유지하되 데이터 구조에는 그대로 복제하지 않았다.

## 5. 이 문서에서 얻은 결론

이 문서를 통해 가장 먼저 배운 것은 `툴콜링 평가는 자연어 답변 품질이 아니라 함수 호출 구조 정확성 평가`라는 점이었다. 이후 평가 코드 설계에서 구조 정확성을 먼저 분해해서 보게 된 출발점이 이 문서다.
