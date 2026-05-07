# 1. Eval Discovery

이 폴더는 LoRA 파인튜닝 후 평가 결과에서 처음 관측된 실패를 정리하는 단계다.

여기서는 원인을 확정하거나 수정안을 결정하지 않는다. 먼저 지표 하락을 확인하고, 하이퍼파라미터를 바꿔도 문제가 남는지 본 뒤, 마지막에는 전체 실패 원장을 열어 실제 실패 패턴을 분리해 이후 `2_root_cause/`와 `3_fixes/`에서 다룰 문제를 좁힌다.

## 읽기 순서

| 순서 | 문서 | 답하는 질문 |
| --- | --- | --- |
| 1 | `01_multiturn_100_vs_500_discovery.md` | 학습 데이터를 100개에서 500개로 늘렸는데 왜 멀티턴 지표가 좋아지지 않았는가? |
| 2 | `02_hyperparameter_model_comparison_unmodified_eval.md` | 하이퍼파라미터별 실험에서 어떤 지표가 좋아지고 나빠지는가? |
| 3 | `03_relevance_detection_failure_report.md` | 전체 실패 원장에서 모델이 tool 호출과 text 응답의 경계를 어디서 틀리는가? |
| 4 | `04_function_matching_failure_report.md` | 전체 실패 원장에서 함수 선택 실패는 어떤 단계 순서 혼동과 데이터셋 문제로 나뉘는가? |
| 5 | `05_argument_value_failure_report.md` | 전체 실패 원장에서 함수는 맞췄지만 인자값이 틀린 실패는 어떤 파라미터와 패턴에 집중되는가? |

## 단계 경계

- 이 폴더의 산출물: 관측된 실패 목록, 실패 유형 분류, 우선 검토 샘플
- 다음 단계의 산출물: 실패가 `eval`, `train_data`, `datagen`, `tool schema`, `model` 중 어디서 왔는지에 대한 원인 판단
- 수정 결정 위치: `../3_fixes/`

## 분석 흐름

이 단계의 실제 흐름은 아래와 같다.

1. `01`에서 LoRA 100 대비 LoRA 500의 멀티턴 완주 성능이 기대만큼 좋아지지 않는다는 문제를 먼저 발견했다.
2. `02`에서 하이퍼파라미터를 바꿔도 모든 지표가 한 방향으로 안정적으로 개선되지 않는다는 점을 확인했다.
3. 그래서 `eval_output/before_eval_dataset/qwen-2.5-7b-function-calling_batch2_data_v2_before/tool_failures_with_dialogue.md`에 전체 tool-level 실패 step을 모은 원장을 만들었다.
4. `03`~`05`는 이 실패 원장에서 각각 `relevance_detection`, `function_matching`, `argument_value` step만 다시 추려 정리한 문서다.

## 핵심 발견

- LoRA 500은 데이터 수가 늘었지만 멀티턴 완주 능력이 안정적으로 좋아지지 않았다.
- 전체 실패 원장을 열어보니 `relevance_detection`, `function_matching`, `argument_value` 실패가 반복적으로 같은 패턴으로 나타났다.
- `relevance_detection`에서는 `get_order_status` 과호출과 text turn 규칙 혼동이 두드러졌다.
- `function_matching`에서는 검색, 장바구니, 배송지, 결제 준비 사이의 단계 순서 혼동이 반복됐다.
- `argument_value`에서는 `search_restaurants` 필터 복원, `special_request` 보존, `delivery_note` 문자열 보존 실패가 가장 많이 관찰됐다.
