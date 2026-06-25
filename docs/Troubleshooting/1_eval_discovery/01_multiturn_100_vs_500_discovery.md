# `LoRA 100` 대비 `LoRA 500` 멀티턴 지표 하락 발견

작성일: 2026-03-20

## 문서 역할

`1_eval_discovery`의 첫 번째 문서다. 학습 데이터가 `100 -> 500`으로 늘었는데도 멀티턴 지표가 개선되지 않은 최초 이상 신호를 기록한다.

- 기준 질문: 데이터 수를 늘렸는데 멀티턴 지표가 왜 좋아지지 않았는가?
- 이 문서의 범위: 지표 하락 현상과 평가 방식상 해석 주의점
- 이 문서에서 하지 않는 것: 원인 확정, 수정안 결정
- 다음 문서: `02_hyperparameter_model_comparison_unmodified_eval.md`

## 핵심 발견

`LoRA 500`은 `LoRA 100`보다 학습 데이터 수가 많지만, 멀티턴 주요 지표 일부에서 더 낮았다.

특히 완주 대화 수는 늘지 않았고, 성공 턴 수와 대화별 평균 진행률은 소폭 하락했으며, 실패한 대화에서는 첫 실패가 더 이른 턴에 나타났다.

## 비교 지표

| 모델 | turn_level_accuracy | conversation_success_rate | conversation_progress_rate | first_failure_turn_avg | error_cascade_rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| LoRA 100 | 55.44% | 15.00% | 56.81% | 0.65 | 51.91% |
| LoRA 500 | 53.74% | 15.00% | 55.33% | 0.50 | 53.68% |

실제 집계값:

- `turn_level_accuracy`: `163/294 -> 158/294`
- `conversation_success_rate`: `6/40 -> 6/40`
- `conversation_progress_rate`: `56.81% -> 55.33%`
- `first_failure_turn_avg`: `0.65 -> 0.50`
- `error_cascade_rate`: 약 `68/131 -> 73/136`

## 지표 해석

- `turn_level_accuracy` 하락은 전체 294턴 중 성공 턴이 5개 줄었다는 뜻이다.
- `conversation_success_rate`가 그대로라는 것은 완주한 대화 수가 늘지 않았다는 뜻이다.
- `conversation_progress_rate` 하락은 대화별 평균 성공 턴 비율이 낮아졌다는 뜻이다.
- `first_failure_turn_avg` 하락은 실패한 대화에서 첫 실패가 더 앞 턴에 나타났다는 뜻이다.
- `error_cascade_rate` 상승은 한 번 실패한 뒤 다음 턴도 실패하는 비율이 조금 높아졌다는 뜻이다.

## 평가 방식상 주의점

이번 멀티턴 평가는 GT history 기반이다. 따라서 이 결과는 이전 턴의 실제 오답이 다음 턴 문맥을 오염시켜서 무너졌다는 의미와는 다르다.

더 정확히는, 각 턴이 정답 히스토리를 받은 상태에서도 모델이 특정 턴 패턴, 분기, 슬롯 회수, tool/no-tool 경계 판단을 반복적으로 어려워했다는 신호에 가깝다.

## 이 단계의 결론

이 문서에서 확정할 수 있는 것은 `LoRA 500`이 데이터 수 증가에도 불구하고 멀티턴 안정성을 뚜렷하게 개선하지 못했다는 점이다.

원인은 아직 확정하지 않는다. 가능한 가설은 별도 메모에 보관하고, 이후 `2_root_cause/`에서 데이터 분포, 평가셋 라벨, datagen 규칙, tool schema 관점으로 다시 검토한다.

관련 가설 메모:

- `hypothesis_notes_from_multiturn_100_vs_500.md`
