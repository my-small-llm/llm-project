> 이 문서는 BFCL multi-turn 평가를 정리한 핵심 근거 문서다.
> 현재 프로젝트용 정리 문서는 [docs/eval/02_eval_metric_report.md](/home/wonjun/llm-project/docs/eval/02_eval_metric_report.md:1) 이다.

# BFCL Multi-Turn

## 1. BFCL Multi-Turn의 본질

BFCL multi-turn은 단순히 함수 호출이 맞았는가를 평가하는 벤치마크가 아니다.

대화 단위에서 다음 세 가지를 함께 검증하는 문제로 이해했다.

1. 최종 상태(state)가 정확한가
2. 필수 도구 사용 경로(trajectory)를 거쳤는가
3. 루프 없이 정상 종료되었는가

또한 한 턴이라도 실패하면 대화 전체가 실패하는 all-or-nothing 성격이 강하다.

## 2. 멀티턴 평가 구조

조사 과정에서 멀티턴은 아래 두 층으로 나눠 이해했다.

- 평가 엔진
- 문제 유형

평가 엔진은 모든 문제에 공통으로 적용되고, 문제 유형은 난이도와 상황 구성을 바꾼다.

## 3. 평가 엔진의 핵심 2축

### 3.1 State-Based Evaluation

턴 종료 시점의 시스템 상태를 Ground Truth 상태와 비교한다. write, delete, update 류 작업에서 특히 중요하다.

### 3.2 Response-Based Evaluation

read 성격의 작업처럼 상태 변화만으로 판정하기 어려운 경우, 정답 데이터의 minimal path를 포함했는지 본다.

이 두 축 때문에 BFCL 멀티턴은 `대화가 전체적으로 성공했는가`를 강하게 평가하는 틀로 이해되었다.

## 4. 프로젝트에 바로 복제하지 않은 이유

현재 프로젝트는 실제 backend state와 database를 재현하지 않았기 때문에, BFCL의 state-based evaluation을 그대로 구현하지 않았다.

대신 아래 방향으로 번역했다.

- GT history 기반으로 turn과 step을 분할
- turn pass / fail 집계
- conversation success와 progress를 함께 계산

즉 멀티턴 철학은 가져오되, 현재 실험 조건에 맞게 평가 구조를 바꾼 셈이다.

## 5. 이 문서에서 얻은 결론

이 문서를 통해 `한 턴의 구조 정확성`과 `대화 전체 완주`는 다른 문제라는 점을 분명히 이해하게 되었다. 이후 우리 평가 설계에서도 tool-call level과 conversation level을 분리하게 된 이유가 여기 있다.
