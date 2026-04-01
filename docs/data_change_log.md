# Data Change Log

## 목적

`eval_data`와 `train_data`에 대한 수정 사항을 간단히 추적하기 위한 로그 문서다.

기록 원칙:

- 실제 데이터 파일이 바뀌었을 때만 남긴다.
- 변경 핵심과 근거 문서를 같이 적는다.
- `eval_data`와 `train_data`를 구분해서 기록한다.
- 상세 규칙은 관련 문서 링크로 연결하고, 여기에는 문제/변경/예시/파일만 짧게 남긴다.

## 로그

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
