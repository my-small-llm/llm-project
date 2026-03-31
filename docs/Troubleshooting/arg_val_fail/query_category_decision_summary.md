# `search_restaurants` query/category 규칙 결정 요약

작성일: 2026-03-31

## 목적

이 문서는 [query_category_rule_recommendation.md](/home/cwj/llm-project/eval_output/qwen-2.5-7b-function-calling_batch2_data_v2/query_category_rule_recommendation.md) 의 결론을 실제 운영 관점으로 짧게 정리한 결정 문서다.

정리하려는 내용은 세 가지다.

- datagen에서 왜 `query/category` 문제가 만들어졌는가
- 실제 데이터와 실패 사례에서 어떤 식으로 드러났는가
- 그래서 앞으로 어떤 규칙으로 고칠 것인가

## 결론

앞으로 `search_restaurants`는 아래 규칙으로 고정한다.

- `category`
  - 고정 taxonomy만 사용
  - `한식`, `중식`, `일식`, `분식`, `카페`, `야식`
- `query`
  - 자유 검색어만 사용
  - 메뉴명, 요리명, 브랜드명, 식당명, 세부 키워드
  - 예: `치킨`, `피자`, `초밥`, `라멘`, `짜장면`, `떡볶이`, `불고기 비빔밥`, `미스터피자`

한 줄로 요약하면:

- `category = 고정 분류`
- `query = 자유 검색어`

## 1. Datagen에서 왜 문제가 생겼는가

현재 datagen의 `search_restaurants` 설명은 슬롯 경계를 애매하게 만든다.

- [config.py](/home/cwj/llm-project/datagen/config.py#L181)
  - `query`: `식당명 또는 메뉴명 검색 키워드 (예: '피자', '치킨')`
- [config.py](/home/cwj/llm-project/datagen/config.py#L185)
  - `category`: `음식 카테고리 필터 (예: '한식', '중식', '피자')`

여기서 `피자`가 양쪽 예시에 동시에 들어간다. 즉 생성 단계에서부터 아래가 모두 가능해져 버렸다.

- `피자 -> query`
- `피자 -> category`
- `한식 -> query`
- `한식 -> category`

또한 datagen 프롬프트에는 `query/category` 선택 규칙이 명시적으로 박혀 있지 않다. 그래서 생성 모델은 같은 의미를 샘플마다 다르게 슬롯에 배치할 수 있다.

결과적으로 datagen은 아래 문제를 만들었다.

- 같은 의미가 `query`와 `category`에 혼용됨
- 어떤 샘플은 cuisine을 `query`에 넣고, 어떤 샘플은 `category`에 넣음
- 어떤 샘플은 같은 의미를 `query`와 `category`에 중복으로 넣음

## 2. 실제 데이터에서 어떤 문제가 있었는가

실제 `search_restaurants` GT 분포를 보면 이미 혼합이 보인다.

- `query`만 사용: 25건
- `category`만 사용: 24건
- 둘 다 사용: 10건

같은 토큰이 양쪽 슬롯에 모두 등장한 사례도 있다.

- `한식`: `query`와 `category` 양쪽에 존재
- `중식`: `query`와 `category` 양쪽에 존재

실패 사례에서도 이 혼선이 직접 드러난다.

- `한식`이 어떤 케이스에서는 `query`, 어떤 케이스에서는 `category`
- `중식`이 어떤 케이스에서는 `query`, 어떤 케이스에서는 `category`
- `라멘`, `초밥` 같은 메뉴 키워드에 대해 `category`를 자동추론한 예측이 나옴
- `query=중식, category=중식`처럼 중복을 요구하거나 허용한 GT가 있음

즉 지금의 `argument_value` 실패 중 일부는 모델이 완전히 틀렸다기보다, 데이터 생성과 GT 자체가 같은 개념을 일관되게 표현하지 못해서 생긴 문제다.

## 3. 그래서 어떻게 해결할 것인가

해결 방향은 단순하다. `query/category`를 역할 기반으로 강하게 분리한다.

### 규칙 1. 고정 cuisine / 도메인은 `category`

- `한식`, `중식`, `일식`, `분식`, `카페`, `야식`

예:

- `한식 맛집 추천해줘` -> `{"category": "한식"}`
- `중식으로 바꿔줘` -> `{"category": "중식"}`

### 규칙 2. 메뉴명 / 요리명 / 브랜드명 / 식당명은 `query`

예:

- `치킨 먹고 싶어` -> `{"query": "치킨"}`
- `라멘 맛집` -> `{"query": "라멘"}`
- `초밥 잘하는 곳` -> `{"query": "초밥"}`
- `미스터피자` -> `{"query": "미스터피자"}`

### 규칙 3. 둘 다 필요할 때만 함께 쓴다

예:

- `일식집에서 초밥` -> `{"category": "일식", "query": "초밥"}`
- `중식집 중 짜장면 위주` -> `{"category": "중식", "query": "짜장면"}`
- `야식으로 치킨` -> `{"category": "야식", "query": "치킨"}`

### 규칙 4. 같은 의미를 중복해서 넣지 않는다

금지 예:

- `{"query": "한식", "category": "한식"}`
- `{"query": "중식", "category": "중식"}`

### 규칙 5. 사용자가 말하지 않은 category를 자동추론하지 않는다

예:

- `라멘 맛집` -> `{"query": "라멘"}`
- `초밥 잘하는 데` -> `{"query": "초밥"}`

즉 `라멘 -> 일식`, `치킨 -> 야식` 같은 자동 보강은 하지 않는다.

## 4. 실제 적용 항목

### Datagen

- `search_restaurants` tool description 수정
- datagen 프롬프트에 아래 문구 추가
  - `category는 고정 taxonomy 값에만 사용하세요.`
  - `query는 메뉴명/브랜드명/식당명/자유 검색어에 사용하세요.`
  - `같은 의미를 query와 category에 동시에 넣지 마세요.`
  - `사용자가 메뉴만 말하면 category를 추론하지 마세요.`

### Dataset relabel

- `query in {한식, 중식, 일식, 분식, 카페, 야식}` 이고 `category`가 비어 있으면 `category`로 이동 검토
- `query == category`이면 중복 제거
- 메뉴/브랜드 query에 붙은 자동추론 category는 제거 검토

### Eval

- 이 규칙을 기준으로 GT를 재정비
- `query/category` 불일치 케이스를 우선 재검토

## 최종 정리

이번 문제의 본질은 모델이 `query`와 `category`를 못 배웠다기보다, 생성 단계에서부터 두 슬롯의 역할이 충분히 고정되지 않았다는 데 있다.

그래서 앞으로는 아래 기준으로 정리한다.

- `category`: 고정 taxonomy
- `query`: 자유 검색어

이 규칙으로 datagen, dataset, eval GT를 같이 맞추면 현재 `argument_value` 실패의 큰 축인 `query/category` 혼선을 가장 먼저 줄일 수 있다.
