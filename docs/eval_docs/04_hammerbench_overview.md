> 이 문서는 HammerBench 조사 과정의 핵심 근거 문서다.
> 현재 프로젝트용 정리 문서는 [docs/eval/02_eval_metric_report.md](/home/wonjun/llm-project/docs/eval/02_eval_metric_report.md:1) 이다.

# HammerBench 개요

## 1. HammerBench란 무엇인가

HammerBench는 멀티턴 function calling 대화에서 모델이 어디서, 어떤 종류의 오류를 내는지 정량적으로 분석하는 평가 체계로 이해했다.

BFCL이 `이 대화는 성공했는가`를 강하게 묻는다면, HammerBench는 `이 대화의 어느 턴에서 어떤 실패가 일어났는가`를 더 세밀하게 묻는다.

## 2. 핵심 개념

### 2.1 데이터 규모

60개 기능 카테고리, 1,063개 도구, 6,531개 쿼리로 구성되어 있다.

### 2.2 Instruction 유형 4가지

HammerBench는 instruction을 단순히 "완벽한 지시"로 가정하지 않고 아래 네 가지로 나눈다.

| 유형 | 설명 |
| --- | --- |
| Perfect | 필요한 정보가 모두 포함된 완전한 지시 |
| Imperfect | 필수 파라미터가 누락되어 추가 질문이 필요한 지시 |
| External pronoun | "그 사람/그 회사" 같이 외부 정보에 대한 대명사 포함 |
| Irrelevant | 호출할 수 있는 함수가 없는 무관한 지시 |

### 2.3 Snapshot 기반 평가

멀티턴 대화를 turn 단위의 snapshot으로 나누고, 각 snapshot에서 모델이 호출해야 하는 함수와 인자를 비교한다. "Learning to Ask"(정보 부족 시 질문하도록 유도) 방식과 비교했을 때, snapshot 방식이 OOD 대화 100개 기준 성공률 68% → 84%로 높았다고 논문에서 보고한다.

### 2.4 턴 단위 비교

각 snapshot에서 아래 항목을 본다.

- 함수명 정확도
- 파라미터 정확도
- 누락 여부
- 환각 여부

## 3. 주요 지표

| 지표 | 설명 | 방향 |
| --- | --- | --- |
| Function Name Accuracy (Func Acc) | 함수명이 정답과 일치한 snapshot 비율 | 높을수록 좋음 |
| Parameter Hallucination Rate (PHR) | tool 정의에 없는 파라미터를 생성한 비율 | 낮을수록 좋음 |
| Parameter Missing Rate (PMR) | 필수 파라미터를 누락한 비율 | 낮을수록 좋음 |
| Progress Rate (PR) | 첫 오류 전까지 연속으로 맞은 턴 비율 (`k/n`, k=첫 오류 전 맞은 턴 수, n=전체 턴 수) | 높을수록 좋음 |
| Success Rate (SR) | 전체 snapshot 중 정답인 비율 (`correct_turns / total_turns`) | 높을수록 좋음 |

이 조합은 `성공/실패`만이 아니라 `실패 유형`과 `어디까지 갔는가`를 함께 보여준다.

PR은 대화 초반부터 어느 시점에 무너지는지를, SR은 전체적으로 얼마나 맞췄는지를 잡는다. 같은 대화를 BFCL로 평가하면 한 턴 실패 시 전체 0점이 되지만, HammerBench는 "2/3 턴은 맞았다"는 정보를 유지한다.

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
