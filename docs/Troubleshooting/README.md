## 트러블슈팅 문서 읽기 순서

LoRA 파인튜닝 후 평가 지표 하락을 발견하고, 원인을 분석하고, 규칙과 스키마를 수정한 흐름 순서다.

이 폴더는 아래 세 단계를 따라 읽는 것이 가장 자연스럽다.

1. `1_eval_discovery/`
   - 평가 결과에서 반복 실패를 발견하고 유형별로 분해한다.
2. `2_root_cause/`
   - 각 실패가 실제로 `tool schema`, `datagen 규칙`, `train data 구조` 중 어디에서 비롯됐는지 판정한다.
3. `3_fixes/`
   - 판정된 원인에 대해 어떤 규칙을 바꾸고 어떤 스키마를 단순화할지 결정한다.

특히 `argument_value` 축은 아래 흐름으로 이어진다.

- `1_eval_discovery/05_argument_value_failure_report.md`
  - 값 보존 실패를 검색 필터, 자유서술 슬롯, 상태 추적 문제로 나눠 관찰한다.
- `2_root_cause/01_tool_schema_overdesign_review.md`
  - 이 중 어떤 문제는 실제 스키마 과설계인지, 어떤 문제는 규칙 재정의 또는 학습 보강 문제인지 가른다.
- `3_fixes/01*`
  - `search_restaurants`를 먼저 정리한다.
  - `page/page_size/only_open/sort/min_rating`는 보조 제어 슬롯 단순화로, `query/category`는 역할 경계 재정의로 이어진다.

---

### eval_output 폴더와 트러블슈팅 단계 대응

```
eval_output/
├── before_eval_dataset/            ← 1단계 발견: 수정 전 평가셋으로 문제 확인
│   └── eval_results_comparison.md     base vs gpt4o vs trained 3-way 비교
│
├── beforedata_claude_modified_unchanged_funtion_des/  ← 3단계 검증: Claude 수정 평가셋
├── codex_modified_eval_data/       ← 3단계 검증: Codex 수정 평가셋 (가장 큰 개선)
├── gpt5.4mini/                     ← 3단계 검증: GPT-5.4 mini 평가셋 (최신)
│
└── eval_dataset_before_vs_modified_comparison.md  ← 4개 평가셋 전체 비교 (최종 요약)
```

---

### 1단계 — 평가로 문제 발견 (`1_eval_discovery/`)

근거 데이터: `eval_output/before_eval_dataset/`

| 순서 | 문서 | 내용 | eval_output 연결 |
|------|------|------|-----------------|
| 1 | `01_multiturn_100_vs_500_discovery.md` | LoRA 100 대비 LoRA 500 멀티턴 지표 하락 최초 발견 (2026-03-20) | 현재 삭제된 초기 실험 결과 (LoRA 100/500 비교) |
| 2 | `02_hyperparameter_model_comparison_unmodified_eval.md` | GPT-4o 포함 하이퍼파라미터별 모델 성능 비교 (2026-03-24) | `before_eval_dataset/eval_results_comparison.md` |
| 3 | `03_relevance_detection_failure_report.md` | relevance_detection 실패 56건 케이스 분석 | `before_eval_dataset/qwen-2.5-7b-function-calling_batch2_data_v2_before/tool_failures_with_dialogue.md` |
| 4 | `04_function_matching_failure_report.md` | function_matching 오류 대화 통합 분석 (2개 실험 병합) | `before_eval_dataset/*/predictions.jsonl` |
| 5 | `05_argument_value_failure_report.md` | argument_value 실패 사례 전수 보고 (2026-03-24) | `before_eval_dataset/*/predictions.jsonl` |

**핵심 수치 (수정 전 평가셋, trained 기준):**
- argument_value_acc: **75.30%** (125/166)
- conversation_success_rate: **15.09%** (8/53) ← base(22.64%)보다 낮음
- relevance_detection 초반 실패가 success rate 하락의 직접 원인

---

### 2단계 — 원인 분석 (`2_root_cause/`)

근거 데이터: `before_eval_dataset/` 수치에서 역추적

| 순서 | 문서 | 내용 |
|------|------|------|
| 6 | `01_tool_schema_overdesign_review.md` | argument_value 실패를 스키마 과설계, 규칙 재정의, 자유서술 슬롯 보존 문제로 가르는 기준 문서 (2026-03-28) |
| 7 | `02_relevance_detection_root_cause.md` | relevance_detection 실패 중 규칙 설계 부족으로 설명되는 원인 정리 (2026-04-02) |
| 8 | `03_train_data_dataset_defect_report.md` | 최신 연구 기준으로 다시 본 학습 데이터 구조 분석 보고서 (2026-04-04) |

**핵심 결론:** 실패 원인은 크게 두 축으로 모인다. 하나는 `search_restaurants` 보조 슬롯 과설계와 `query/category` 경계 불안정, 다른 하나는 `get_order_status` 및 text turn 규칙 부족이다. `special_request`, `delivery_note`, 각종 ID 추적 문제는 스키마 축소보다 원문 보존 규약과 상태 추적 규칙 보강 문제로 남는다. 마지막 문서는 이 개별 원인 분석을 넘어, 더 나은 train data 구조 자체를 최신 연구 기준에서 재해석한다.

---

### 3단계 — 파라미터별 수정 결정 (`3_fixes/`)

검증 데이터: `eval_output/codex_modified_eval_data/`, `beforedata_claude_modified_unchanged_funtion_des/`, `gpt5.4mini/`

| 순서 | 문서 | 내용 | 수정 후 효과 |
|------|------|------|-------------|
| 9 | `01_search_restaurants_schema_simplification_decision.md` | search_restaurants 스키마 단순화 결정 기록 (2026-03-28) | — |
| 10 | `01a_query_category_decision_summary.md` | query/category 규칙 정리 및 해결 (2026-03-31) | — |
| 11 | `01b_only_open_sort_decision_summary.md` | only_open/sort 기본값 신호 문제 해결 (2026-04-01) | — |
| 12 | `01c_min_rating_decision_summary.md` | min_rating 문제 정의 및 해결 (2026-04-02) | — |
| 13 | `02_relevance_detection_decision_summary.md` | relevance_detection 문제 정의 및 해결 (2026-04-02) | — |
| 14 | `03_datagen_train_data_generation_fix_plan.md` | datagen 전체 수정 계획 최종 정리 (2026-04-04) | — |

`01*` 문서들은 모두 같은 묶음으로 읽는 것이 좋다.

- `01_search_restaurants_schema_simplification_decision.md`
  - 왜 `search_restaurants`를 우선 수정 대상으로 잡았는지 정리한다.
- `01a_query_category_decision_summary.md`
  - `query/category`를 축소가 아니라 역할 경계 재정의 문제로 다룬다.
- `01b_only_open_sort_decision_summary.md`
  - `only_open/sort`를 기본값 신호 제거와 호출 조건 축소 문제로 다룬다.
- `01c_min_rating_decision_summary.md`
  - `min_rating`를 soft preference와 hard threshold를 분리하는 문제로 다룬다.

**수정 후 주요 지표 변화 (Codex Modified 평가셋, trained 기준):**
- argument_value_acc: 75.30% → **82.00%** (+6.70%p)
- turn_level_accuracy: 64.83% → **72.03%** (+7.20%p)
- conversation_success_rate: 15.09% → **33.96%** (+18.87%p)
- error_cascade_rate: 30.86% → **36.51%** (악화 — eval_data 수정 영향)

> 전체 비교는 `eval_output/eval_dataset_before_vs_modified_comparison.md` 참고
