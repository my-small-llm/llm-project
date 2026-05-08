# 대표 벤치마크 조사와 평가 축 학습

## 목적

이 문서는 툴콜링 방향으로 파인튜닝한 LLM을 어떻게 평가할지 학습하고 정리해 온 흐름을 요약한다.

출발점은 단순했다. 우리는 툴콜링 방향으로 LLM을 파인튜닝하려 했고, 따라서 이 모델의 성능을 어떻게 측정할 것인지 먼저 정의해야 했다. 당시에는 툴콜링 모델을 어떤 기준으로 평가해야 하는지조차 명확히 알지 못했다. 그래서 대표 벤치마크와 평가 방법론을 조사하며, 무엇을 측정해야 하는지부터 학습했다.

이 문서는 그 조사 과정에서 무엇을 배웠는지, 그리고 그 결과가 현재 프로젝트의 평가 설계에 어떻게 반영되었는지를 정리한다.

## 1. 처음 던진 질문

초기 질문은 `우리 평가 코드를 어떻게 짤까`가 아니었다. 먼저 확인하려던 것은 아래 질문이었다.

- 툴콜링 파인튜닝 모델은 보통 무엇으로 평가하는가
- 툴콜링 성능은 어떤 항목으로 분해해서 볼 수 있는가
- 멀티턴 에이전트 성능은 어떤 철학으로 측정하는가

이 질문에 답하기 위해 먼저 BFCL을 보고, 이후 HammerBench까지 확장해 읽었다.

## 2. BFCL에서 먼저 배운 것

대표 벤치마크를 조사하는 과정에서 가장 먼저 접한 것은 BFCL이었다. BFCL을 통해 툴콜링 평가는 자연어 응답 품질 평가가 아니라, 함수 호출의 구조 정확성을 평가하는 문제라는 점을 먼저 이해하게 되었다.

기존 조사 문서에서 정리했듯, BFCL의 singleton 평가는 함수명 정확성, required 파라미터 존재 여부, 파라미터 이름 정확성, 타입 정확성, 스키마 외 파라미터 생성 여부, 값 제약 조건 만족 여부처럼 함수 호출의 구조적 정확성을 엄격하게 본다.

이 과정에서 우리는 아래 항목들이 툴콜링 성능을 읽는 기본 축이라는 점을 배웠다.

- 함수 호출이 필요한 상황을 올바르게 판단하는가
- 함수 이름을 정확하게 선택하는가
- 필수 파라미터를 빠뜨리지 않는가
- 스키마에 없는 파라미터를 만들어내지 않는가
- 타입과 값이 정답과 일치하는가

또한 BFCL을 보며 single-turn과 multi-turn 평가를 구분해서 봐야 한다는 점도 배웠다. single-turn에서는 구조 정확성이 핵심이고, multi-turn에서는 한 턴의 구조 정확성 위에 상태 유지와 절차적 완주가 추가된다.

## 3. BFCL만으로는 충분하지 않았던 이유

BFCL을 통해 구조 정확성과 멀티턴 성공 평가의 틀을 배웠지만, 우리 실험 목적에는 그것만으로 충분하지 않았다.

이유는 두 가지였다.

- 우리 프로젝트는 실제 backend state와 database를 재현하는 평가 환경을 만들지 않았다
- 같은 베이스 모델에 대해 데이터 구성과 학습 조건이 바뀔 때 어떤 하위 능력이 어떻게 변하는지를 읽어내는 것이 더 중요했다

BFCL 멀티턴 평가는 state-based evaluation과 response-based evaluation을 통해 대화 전체 성공 여부를 강하게 판단하는 데 적합하다. 하지만 현재 프로젝트는 그 전제를 그대로 재현하지 않았다. 따라서 BFCL의 멀티턴 철학을 그대로 복제하기보다, 현재 실험 조건에 맞는 방식으로 번역할 필요가 있었다.

또한 우리는 단순히 모델 간 순위를 매기려는 것이 아니라, 같은 사전학습 모델에 대해 데이터와 학습 방식이 바뀌었을 때 에이전트 성능이 어떤 항목에서 어떻게 변하는지 추적하고 싶었다. 이 목적에서는 총점이나 대화 전체 성공률만으로는 부족했고, 실패 원인을 더 잘 분해해서 볼 수 있는 지표가 필요했다.

## 4. HammerBench까지 확장해 본 이유

이 문제의식 때문에 HammerBench까지 확장해 읽게 되었다.

HammerBench는 실제 사용자 대화에서 발생하는 incomplete instruction, slot filling, argument shift, pronoun/external info, intent shift 같은 문제를 더 세밀하게 다룬다. 또한 대화를 function-calling snapshot으로 분해해, 전체 성공 여부뿐 아니라 어느 순간 어떤 유형의 오류가 발생했는지를 세분화해서 보게 한다.

이 문서화 과정에서 HammerBench를 통해 특히 중요하게 받아들인 점은 아래와 같다.

- 전체 성공 여부만으로는 실패 원인을 충분히 설명할 수 없다
- 파라미터 누락, 환각, 값 오류 같은 실패 유형을 분해해서 봐야 한다
- 멀티턴 평가는 대화 완주 여부뿐 아니라 어디까지 진행했는지도 함께 봐야 한다

정리하면 BFCL이 `표준 시험지`에 가깝다면, HammerBench는 `실패 원인을 더 잘 보여주는 진단 도구`에 가까웠다.

## 5. 현재 프로젝트에 실제로 가져온 것

현재 `evaluations` 구현은 BFCL이나 HammerBench를 그대로 복제한 것이 아니다. 두 벤치마크에서 배운 평가 철학을 현재 데이터 구조와 실험 목적에 맞게 번역한 결과다.

### 5.1 BFCL에서 가져온 것

- 툴 호출 필요 여부를 평가하는 관점
- 함수 호출의 구조 정확성을 엄격하게 보는 관점
- 함수명, required 파라미터, 타입, 값 비교 중심의 평가
- 멀티턴에서 turn / conversation 단위의 성공 여부를 집계하는 관점

### 5.2 HammerBench에서 가져온 것

- 실패 원인을 세부 항목으로 분해해서 보는 관점
- parameter hallucination, missing, value error 같은 항목별 진단
- 전체 성공률 외에 진행률과 실패 위치를 함께 보는 관점

### 5.3 그대로 가져오지 않은 것

- BFCL의 backend state 기반 평가 환경
- BFCL의 minimal trajectory 직접 비교
- HammerBench의 원형 snapshot 데이터셋 구조
- LLM judge 기반 평가

## 6. 현재 평가 코드와의 대응

현재 평가 설계는 아래 코드에 반영되어 있다.

- [metrics.py](/home/wonjun/llm-project/evaluations/metrics.py:1)
  - `relevance_detection_acc`
  - `format_compliance_acc`
  - `function_matching_acc`
  - `param_hallucination_acc`
  - `required_params_acc`
  - `argument_type_acc`
  - `argument_value_acc`
- [multi_turn_metrics.py](/home/wonjun/llm-project/evaluations/multi_turn_metrics.py:1)
  - `turn_level_accuracy`
  - `conversation_success_rate`
  - `conversation_progress_rate`
  - `first_failure_turn_avg`
  - `error_cascade_rate`
- [turn_splitter.py](/home/wonjun/llm-project/evaluations/turn_splitter.py:1)
  - GT history 기반 step 분할
  - sequential call을 포함한 turn 단위 평가 입력 생성

이 구조는 BFCL의 구조 정확성 평가를 바탕으로, HammerBench식 분해와 진행률 관점을 결합한 프로젝트용 평가 계측기라고 볼 수 있다.

## 7. 이 문서의 위치

이 문서는 `무엇을 참고해 현재 평가 체계를 설계했는가`를 설명하는 문서다. 실제 프로젝트용 평가 기준과 구현 상세는 아래 문서에서 이어진다.

1. [01_eval_problem_definition.md](/home/wonjun/llm-project/docs/eval/01_eval_problem_definition.md:1)
2. [02_eval_metric_report.md](/home/wonjun/llm-project/docs/eval/02_eval_metric_report.md:1)
3. [03_eval_plan.md](/home/wonjun/llm-project/docs/eval/03_eval_plan.md:1)
4. [04_metric_issue_resolution_workflow.md](/home/wonjun/llm-project/docs/eval/04_metric_issue_resolution_workflow.md:1)

## 참고 조사 문서

- [01_bfcl_overview.md](/home/wonjun/llm-project/docs/eval_docs/01_bfcl_overview.md:1)
- [02_bfcl_single_turn.md](/home/wonjun/llm-project/docs/eval_docs/02_bfcl_single_turn.md:1)
- [03_bfcl_multi_turn.md](/home/wonjun/llm-project/docs/eval_docs/03_bfcl_multi_turn.md:1)
- [04_hammerbench_overview.md](/home/wonjun/llm-project/docs/eval_docs/04_hammerbench_overview.md:1)
- [05_bfcl_vs_hammerbench.md](/home/wonjun/llm-project/docs/eval_docs/05_bfcl_vs_hammerbench.md:1)
