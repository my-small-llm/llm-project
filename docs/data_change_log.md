# Data Change Log

## 목적

`eval_data`와 `train_data`에 대한 수정 사항을 간단히 추적하기 위한 로그 문서다.

기록 원칙:

- 실제 데이터 파일이 바뀌었을 때만 남긴다.
- 변경 핵심과 근거 문서를 같이 적는다.
- `eval_data`와 `train_data`를 구분해서 기록한다.
- 상세 규칙은 관련 문서 링크로 연결하고, 여기에는 문제/변경/예시/파일만 짧게 남긴다.

## 로그

### 2026-04-02

- `eval_data`
  - 문제: `eval_data/dataset.jsonl`과 sample 원문들 안의 `search_restaurants.min_rating` tool 설명이 예전 규칙으로 남아 있었다. 설명은 `평점 높은 곳`만 생략 대상으로 적고 있어서, `평점 높은 순/별점순은 sort=rating`이라는 새 기준이 gold dataset 내부 문맥에 충분히 반영되지 않았다.
  - 변경: [min_rating_decision_summary.md](/home/cwj/llm-project/docs/Troubleshooting/arg_val_fail/min_rating_decision_summary.md) 기준으로 `eval_data/dataset.jsonl`과 `eval_data/samples/*.txt`의 `min_rating` 설명 문구를 datagen과 동일한 새 규칙으로 통일했다. 실제 GT 대화의 `search_restaurants` 호출도 재점검했고, 이번 기준에서 `평점 높은 곳 -> min_rating` 같은 남은 케이스는 확인되지 않았다.
  - 예시: `고객이 '4.5 이상', '최소 4.3'처럼 숫자 기준을 명시한 경우에만 ... '평점 높은 곳'처럼 ... 생략` -> `... '평점 높은 곳', '추천해줘'처럼 ... 생략. '평점 높은 순', '별점순'은 sort로 처리 ...`
  - 상세 기준: [min_rating_decision_summary.md](/home/cwj/llm-project/docs/Troubleshooting/arg_val_fail/min_rating_decision_summary.md)
  - 변경 파일: `eval_data/dataset.jsonl`, `eval_data/samples/sample_*.txt` (`search_restaurants.min_rating` 설명 문구 정렬)

- `train_data`
  - 문제: `search_restaurants`에서 `평점 높은 곳`, `추천해줘`, `인기 많은 곳`, `평점 좋은 곳` 같은 soft preference를 숫자 threshold로 과해석해 `min_rating=4.3~4.6`을 붙인 GT가 넓게 남아 있었다. 또한 dataset 내부 tool schema 설명도 예전 규칙(`평점 높은 곳`만 생략) 기준이라 `sort`와 `min_rating`의 경계가 약했다.
  - 변경: [min_rating_decision_summary.md](/home/cwj/llm-project/docs/Troubleshooting/arg_val_fail/min_rating_decision_summary.md) 기준으로 `train_data/dataset_500.jsonl`을 재검토했다. 직전 사용자 발화에 `4.5 이상`, `최소 4.3`, `별점 4점` 같은 숫자 기준이 없으면 `search_restaurants` 호출의 `min_rating`을 제거했고, dataset 내부 tool schema 설명도 `평점 높은 순/별점순은 sort=rating` 규칙을 포함한 새 문구로 통일했다.
  - 예시: `{"category":"한식","min_rating":4.5,"only_open":true,"sort":"rating"}` -> `{"category":"한식","only_open":true,"sort":"rating"}`
  - 상세 기준: [min_rating_decision_summary.md](/home/cwj/llm-project/docs/Troubleshooting/arg_val_fail/min_rating_decision_summary.md)
  - 변경 파일: `train_data/dataset_500.jsonl` (`search_restaurants` 호출 70건 relabel, `min_rating` 포함 호출 89→19, soft-to-hard 케이스 60→0)

### 2026-04-01

- `eval_data`
  - 문제: `search_restaurants` 멀티턴 GT에서 `only_open`과 `sort`가 턴 사이에 일관되지 않았다. 어떤 턴은 사용자가 명시적으로 바꾸지 않았는데도 기존 `only_open=true` 또는 `sort`가 빠졌고, 반대로 일부 턴은 정렬 기준을 직접 말하지 않았는데 `sort="rating"`이 과하게 남아 있었다.
  - 변경: [only_open_sort_decision_summary.md](/home/cwj/llm-project/docs/Troubleshooting/arg_val_fail/only_open_sort_decision_summary.md) 기준으로 `eval_data/dataset.jsonl`의 `search_restaurants` 호출을 재검토했다. 정렬 기준을 직접 말하지 않은 `sort`는 제거하고, 멀티턴에서 사용자가 `only_open`/`sort`를 명시적으로 바꾸지 않은 경우에는 자연스러운 carry-over를 반영해 GT를 정리했다.
  - 예시: `{"category":"한식","min_rating":4.5,"sort":"rating"}` -> `{"category":"한식","min_rating":4.5,"sort":"rating","only_open":true}`
  - 상세 기준: [only_open_sort_decision_summary.md](/home/cwj/llm-project/docs/Troubleshooting/arg_val_fail/only_open_sort_decision_summary.md)
  - 변경 파일: `eval_data/dataset.jsonl` (`search_restaurants` 호출 25건 relabel)

- `train_data`
  - 문제: `train_data/dataset_500.jsonl`에도 같은 축의 문제가 남아 있었다. 첫 검색에서 영업 여부를 직접 말하지 않았는데 `only_open=true`가 붙은 케이스와, 정렬 기준을 말하지 않았는데 `sort="rating"` 또는 `sort="relevance"`가 기본값처럼 붙은 케이스가 넓게 섞여 있었다. 멀티턴 후속 검색 14건은 반대로 carry-over 유지 여부를 row별로 다시 판단할 필요가 있었다.
  - 변경: [only_open_sort_decision_summary.md](/home/cwj/llm-project/docs/Troubleshooting/arg_val_fail/only_open_sort_decision_summary.md)와 [dataset_500_only_open_sort_relabel_plan.md](/home/cwj/llm-project/docs/Troubleshooting/arg_val_fail/dataset_500_only_open_sort_relabel_plan.md) 기준으로 `train_data/dataset_500.jsonl` 500개 row를 전수 검토하고 relabel했다. first-search의 과한 `only_open`/`sort`는 제거하고, 멀티턴 14건은 대화 흐름을 보고 유지 또는 reset을 수동 확정했다.
  - 예시: `{"query":"bbq 판교점","only_open":true,"sort":"relevance"}` -> `{"query":"bbq 판교점"}`
  - 상세 기준: [dataset_500_only_open_sort_relabel_plan.md](/home/cwj/llm-project/docs/Troubleshooting/arg_val_fail/dataset_500_only_open_sort_relabel_plan.md)
  - 변경 파일: `train_data/dataset_500.jsonl` (`search_restaurants` 호출 193건 relabel, `only_open=true` 283→161, `sort="rating"` 268→136)


### 2026-03-31

- `eval_data`
  - 문제: `search_restaurants`에서 `query`와 `category` 기준이 섞여 있었다.
  - 변경: `query/category` 내용을 정리해 taxonomy는 `category`, 자유 검색어는 `query`로 맞췄다.
  - 예시: `query="한식"` -> `category="한식"`
  - 상세 기준: [query_category_decision_summary.md](/home/cwj/llm-project/docs/Troubleshooting/arg_val_fail/query_category_decision_summary.md)
  - 변경 파일: `dataset.jsonl`, `sample_0002.txt`(turn 0, 1, 2), `sample_0008.txt`(turn 3), `sample_0033.txt`(turn 0), `sample_0035.txt`(turn 0), `sample_0036.txt`(turn 0), `sample_0037.txt`(turn 0)

- `train_data`
  - 문제: `search_restaurants`에서 메뉴/브랜드성 `query`에 category를 자동추론해 붙이거나, 고정 taxonomy 밖 값(`치킨`, `디저트`, `이탈리안`)을 `category`에 넣은 샘플, category-only 검색에 빈 `query=""`를 남긴 샘플이 있었다.
  - 변경: `query/category` 역할 분리 규칙에 맞춰 자동추론 category를 제거하고, taxonomy 밖 category는 `query`로 옮기거나 제거했으며, category-only 케이스의 빈 query를 제거했다.
  - 예시: `{"category":"치킨","min_rating":4.5}` -> `{"query":"치킨","min_rating":4.5}`
  - 상세 기준: [query_category_decision_summary.md](/home/cwj/llm-project/docs/Troubleshooting/arg_val_fail/query_category_decision_summary.md)
  - 변경 파일: `train_data/dataset_500_redownload_stripped.jsonl` (line 7, 9, 11, 24, 35, 42, 52, 69, 70, 71, 81, 119, 128, 152, 161, 169, 180, 188, 198, 203, 204, 213, 233, 244, 260, 272, 274, 280, 298, 301, 308, 315, 321, 346, 349, 350, 368, 370, 403, 410, 411, 422, 428, 435, 443, 457, 488, 493)

## 다음 기록 템플릿

### YYYY-MM-DD

- `eval_data`
  - 문제:
  - 변경:
  - 예시:
  - 상세 기준:
  - 변경 파일:

- `train_data`
  - 문제:
  - 변경:
  - 예시:
  - 상세 기준:
  - 변경 파일:
