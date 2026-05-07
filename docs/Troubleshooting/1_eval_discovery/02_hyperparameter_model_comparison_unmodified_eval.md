# 수정 전 평가셋 기준 하이퍼파라미터별 모델 성능 비교

> 작성일: 2026-03-24
>
> 비교 대상: GPT-4o, Original Qwen2.5-7B, LoRA 100, LoRA 500 (배치2, 3ep), LoRA 500 (배치2, 3ep, highLR), LoRA 500 (배치32, 10ep)
>
> 평가 데이터: `eval_data/dataset.jsonl`

## 문서 역할

`1_eval_discovery`의 두 번째 문서다.

1번 문서에서 `LoRA 500`이 `LoRA 100`보다 멀티턴 지표를 안정적으로 개선하지 못하는 현상을 발견했다. 이 단계에서는 그 원인을 데이터 결함으로 바로 확정하지 않고, 먼저 하이퍼파라미터 튜닝 문제일 가능성을 확인하기 위해 여러 LoRA 실험 조건을 비교한다.

- 기준 질문: 멀티턴 하락이 특정 학습 조건, batch size, epoch, learning rate 설정의 문제인가?
- 이 문서의 범위: 수정 전 평가셋 기준 하이퍼파라미터별 tool call / multi-turn 지표 비교
- 다음 판단: 지표별 병목을 보고 `relevance_detection`, `function_matching`, `argument_value` 중 어떤 실패 축을 세부 분석할지 결정한다.
- 다음 문서: `03_relevance_detection_failure_report.md`

## Tool Call Level 비교

| 모델 | relevance_detection_acc | format_compliance_acc | function_matching_acc | param_hallucination_acc | required_params_acc | argument_type_acc | argument_value_acc |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| GPT-4o | 83.92% | 96.30% | 94.87% | 100.00% | 100.00% | 100.00% | 70.27% |
| Original Qwen2.5-7B | 86.88% | 91.62% | 92.57% | 100.00% | 99.38% | 90.06% | 44.83% |
| LoRA 100 | 86.51% | 94.02% | 93.64% | 100.00% | 99.38% | 96.89% | 61.54% |
| LoRA 500 (배치2, 3ep) | 84.47% | 94.12% | 93.75% | 100.00% | 98.67% | 100.00% | 68.24% |
| LoRA 500 (배치2, 3ep, highLR) | 88.54% | 94.90% | 91.40% | 100.00% | 98.82% | 100.00% | 62.50% |
| LoRA 500 (배치32, 10ep, before) | 89.65% | 95.28% | 90.59% | 100.00% | 98.91% | 100.00% | 70.72% |
| LoRA 500 (배치32, 10ep) | 89.50% | 95.31% | 92.12% | 100.00% | 98.93% | 100.00% | 70.27% |

## Multi-Turn 비교

| 모델 | turn_level_accuracy | conversation_success_rate | conversation_progress_rate | first_failure_turn_avg | error_cascade_rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| GPT-4o | 59.86% | 12.50% | 61.70% | 0.26 | 39.83% |
| Original Qwen2.5-7B | 47.62% | 10.00% | 49.81% | 0.50 | 60.78% |
| LoRA 100 | 55.44% | 15.00% | 56.81% | 0.65 | 51.91% |
| LoRA 500 (배치2, 3ep) | 57.48% | 15.00% | 58.88% | 0.79 | 52.00% |
| LoRA 500 (배치2, 3ep, highLR) | 57.82% | 12.50% | 59.17% | 0.57 | 51.61% |
| LoRA 500 (배치32, 10ep, before) | 60.88% | 7.50% | 62.26% | 1.24 | 51.30% |
| LoRA 500 (배치32, 10ep) | 60.88% | 7.50% | 62.45% | 1.24 | 52.17% |

## 비교 배경

1번 문서의 최초 발견만으로는 `LoRA 500`의 멀티턴 하락이 데이터 분포 문제인지, 학습 설정 문제인지 구분할 수 없었다.

그래서 이 문서에서는 batch size, epoch, learning rate가 다른 LoRA 실험들을 같은 수정 전 평가셋에서 비교한다. 목표는 하나의 튜닝 조건이 모든 지표를 동시에 개선하는지, 아니면 지표별로 서로 다른 실패 축이 드러나는지 확인하는 것이다.

## 변경 메모

- `LoRA 500 (배치2, 3ep, highLR)` 결과를 비교표에 새로 추가했다.
- `LoRA 500 (배치2, 3ep)`와 `LoRA 500 (배치32, 10ep)`의 수치를 최신 `eval_results.json` 기준으로 수정했다.
- `LoRA 500 (배치16, 8ep)` 행은 현재 비교 대상 결과 파일이 열려 있지 않아 제거했다.
- `LoRA 500 (배치32, 10ep, before)`를 별도 행으로 추가해 메트릭 코드 변경 전후 비교 맥락을 남겼다.

## 핵심 관측

- `LoRA 500 (배치32, 10ep, before)`는 현재 비교표에서 `argument_value_acc`가 70.72%로 가장 높고, `turn_level_accuracy`도 60.88%로 가장 높다.
- `LoRA 500 (배치32, 10ep)`는 `function_matching_acc`가 92.12%로 더 높지만, `argument_value_acc`는 70.27%로 `before`보다 소폭 낮다.
- `LoRA 500 (배치2, 3ep, highLR)`는 relevance와 format은 개선됐지만, 최종 `argument_value_acc`가 62.50%로 기본 `배치2, 3ep`보다 낮다. highLR이 호출 의도 판단에는 도움이 되었지만 값 정확도에는 불리했을 가능성이 있다.
- `conversation_success_rate`는 `배치2, 3ep`가 15.00%로 가장 높고, `배치32, 10ep` 계열은 7.50%에 머문다. 반면 `first_failure_turn_avg`는 `배치32, 10ep` 계열이 1.24로 더 높아, 완전 성공은 적지만 더 뒤에서 처음 실패하는 경향이 보인다.

## 다음 분석으로 넘길 실패 축

하이퍼파라미터를 바꿔도 모든 지표가 한 방향으로 개선되지는 않았다.

- highLR은 `relevance_detection` 쪽에는 도움이 되었지만 `argument_value`는 악화됐다.
- batch32/10ep 계열은 `turn_level_accuracy`와 `argument_value_acc`는 상대적으로 높았지만 `conversation_success_rate`는 낮았다.
- `function_matching`, `argument_value`, `relevance_detection`이 서로 다른 방향으로 움직여, 단일 튜닝 문제라기보다 실패 축별 세부 분석이 필요해졌다.

따라서 다음 단계에서는 먼저 tool/no-tool 경계 판단인 `relevance_detection` 실패를 살펴보고, 이어서 `function_matching`, `argument_value` 실패를 각각 분리해 분석한다.

## 비교 시 주의점

- `eval_output_batch32-10ep`는 총 샘플 수가 543개이고, 다른 세 LoRA 500 결과는 541개다.
- 따라서 `LoRA 500 (배치32, 10ep)`와 나머지 결과를 완전히 동일 표본 기준의 apples-to-apples 비교로 해석하면 안 된다.
- 동일 prediction으로 메트릭 코드 효과만 보려면 `eval_output_500_32batch_10ep_before`처럼 같은 `predictions.jsonl`에 대해 scorer만 재실행한 결과를 우선 기준으로 보는 것이 적절하다.
