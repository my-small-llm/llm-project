> 이 문서는 HammerBench 조사 과정의 핵심 근거 문서다.
> 현재 프로젝트용 정리 문서는 [docs/eval/02_eval_metric_report.md](/home/wonjun/llm-project/docs/eval/02_eval_metric_report.md:1) 이다.

# HammerBench 개요

## 1. HammerBench란 무엇인가

HammerBench는 멀티턴 function calling 대화에서 모델이 어디서, 어떤 종류의 오류를 내는지 정량적으로 분석하는 평가 체계로 이해했다.

BFCL이 `이 대화는 성공했는가`를 강하게 묻는다면, HammerBench는 `이 대화의 어느 턴에서 어떤 실패가 일어났는가`를 더 세밀하게 묻는다.

## 2. 핵심 개념

### 2.1 Snapshot 기반 평가

멀티턴 대화를 turn 단위의 snapshot으로 나누고, 각 snapshot에서 모델이 호출해야 하는 함수와 인자를 비교한다.

### 2.2 턴 단위 비교

각 snapshot에서 아래 항목을 본다.

- 함수명 정확도
- 파라미터 정확도
- 누락 여부
- 환각 여부

## 3. 주요 지표

조사 과정에서 중요하게 본 지표는 아래와 같았다.

- Function Name Accuracy
- Parameter Hallucination Rate
- Parameter Missing Rate
- Progress Rate
- Success Rate

이 조합은 `성공/실패`만이 아니라 `실패 유형`과 `어디까지 갔는가`를 함께 보여준다.

## 4. BFCL과 다른 점

HammerBench가 특히 중요했던 이유는 아래 세 가지였다.

- imperfect instruction을 더 현실적으로 다룬다
- slot value 수정, intent shift, pronoun/external info 같은 실제 대화 흐름을 다룬다
- 실패 위치와 오류 유형을 더 잘 분해한다

## 5. 프로젝트에 준 영향

현재 프로젝트의 평가 설계는 HammerBench를 그대로 따르지는 않았지만, 아래 관점을 강하게 가져왔다.

- 전체 성공률만으로는 부족하다
- parameter missing / hallucination / value error 같은 실패 유형을 분해해야 한다
- 대화 전체 완주 여부 외에 progress도 함께 봐야 한다

이 문서는 `왜 BFCL만으로는 실험 해석이 부족하다고 느꼈는가`를 설명하는 핵심 근거 문서다.
