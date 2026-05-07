# `search_restaurants` only_open / sort 기본값 신호 문제 정의 및 해결

작성일: 2026-04-01

## 목적

이 문서는 `search_restaurants`의 `only_open` 문제를 중심으로, 함께 얽혀 있는 `sort` 기본값 신호 문제까지 한 문서에서 다루기 위해 만든 통합 문서다.

아래 내용을 함께 담는다.

- 현재 `argument_value` 실패에서 `only_open`이 어떻게 드러나는가
- 왜 이번 정리에서 `sort`도 함께 수정 대상으로 묶였는가
- datagen 함수 명세를 지금처럼 고친 것만으로 충분한가
- 코드상으로 어디를 더 수정해야 하는가
- eval data / train data는 어떤 기준으로 손봐야 하는가

## 문제 요약

`query/category`를 제외하면 현재 `argument_value`에서 가장 많이 반복되는 실패는 `only_open`이다. 이번 문서는 이 `only_open` 문제를 중심으로 보되, 같은 "불필요한 기본값 신호" 축에 있는 `sort`도 함께 정리한다.

- 분석 대상: [tool_failures_with_dialogue.md](/home/cwj/llm-project/eval_output/qwen-2.5-7b-function-calling_batch2_data_v2/tool_failures_with_dialogue.md)
- `query/category` 제외 후 파라미터 mismatch 집계
  - `only_open`: 21건
  - `min_rating`: 5건
  - `special_request`: 2건
  - `delivery_note`: 2건

실패 패턴은 거의 한 가지로 수렴한다.

- `GT=false 또는 미지정`인데 `PRED=true`
- 사용자가 이번 턴에서 영업 여부를 직접 말하지 않았는데도 모델이 `only_open=true`를 붙임
- 이전 턴의 `영업 중` 조건을 다음 턴까지 과하게 끌고 감

대표 사례:

- [tool_failures_with_dialogue.md:103](/home/cwj/llm-project/eval_output/qwen-2.5-7b-function-calling_batch2_data_v2/tool_failures_with_dialogue.md:103)
- [tool_failures_with_dialogue.md:171](/home/cwj/llm-project/eval_output/qwen-2.5-7b-function-calling_batch2_data_v2/tool_failures_with_dialogue.md:171)
- [tool_failures_with_dialogue.md:3910](/home/cwj/llm-project/eval_output/qwen-2.5-7b-function-calling_batch2_data_v2/tool_failures_with_dialogue.md:3910)

이 문제를 볼 때 먼저 분리해야 할 개념이 있다.

- `is_open`
  - 각 식당이 실제로 현재 영업 중인지 아닌지를 나타내는 상태값
  - DB나 응답 객체에서는 당연히 `true/false` boolean이다
- `only_open`
  - 검색에서 `is_open=true`인 식당만 제한적으로 보겠다는 필터 옵션
  - 즉 "가게 상태값"이 아니라 "검색 조건"이다

이 문서에서 다루는 문제는 `is_open`의 boolean 정의가 아니라, `only_open`을 tool call에서 언제 명시해야 하느냐는 문제다.

예를 들면 아래처럼 구분한다.

- `치킨집 찾아줘`
  - 결과에 열려 있는 가게와 닫힌 가게가 함께 있을 수 있다
  - 각 가게의 `is_open` 값은 여전히 분명하다
  - 하지만 사용자는 "영업 중인 곳만"이라고 제한하지 않았으므로 `only_open`은 생략한다
- `지금 영업 중인 치킨집만 찾아줘`
  - 검색 자체를 open 상태 가게로 제한해야 하므로 `only_open=true`

즉 데이터베이스와 백엔드에서는 boolean이 맞고, LLM 호출 규약에서는 `only_open`을 optional filter로 다루는 것이 핵심이다.

## 현재 datagen 수정만으로 충분한가

결론부터 말하면, 아직 충분하지 않다.

좋아진 점은 있다.

- [datagen/tool_specs.py](/home/cwj/llm-project/datagen/tool_specs.py:398)
  - `only_open` 설명이 `명시적으로 요청한 경우에만 true, 아니면 생략`으로 이미 바뀌어 있다.
- [datagen/tool_specs.py](/home/cwj/llm-project/datagen/tool_specs.py:403)
  - `sort`도 `명시한 경우에만 사용`으로 바뀌어 있다.

하지만 아직 예전 규약이 코드와 예시에 남아 있다.

### 1. 함수 시그니처와 schema default가 여전히 `false` 중심이다

- [datagen/tool_specs.py](/home/cwj/llm-project/datagen/tool_specs.py:117)
  - `search_restaurants(... only_open: bool = False, sort: str = "rating")`
- [datagen/tool_specs.py](/home/cwj/llm-project/datagen/tool_specs.py:398)
  - schema에 `only_open.default = False`
- [datagen/tool_specs.py](/home/cwj/llm-project/datagen/tool_specs.py:403)
  - schema에 `sort.default = "rating"`

즉 설명 문구는 `true 또는 생략`으로 바뀌었지만, 함수 계약의 구조 자체는 여전히:

- `only_open=false`가 자연스러운 기본값처럼 보이고
- `sort="rating"`이 호출 인자 기본값처럼 보인다

모델은 보통 설명뿐 아니라 default, 예시, 반환 포맷도 함께 학습 신호로 받기 때문에, 이 상태는 `only_open=true/false/생략` 경계를 계속 흐릴 가능성이 높다.

특히 여기서 중요한 점은, 백엔드 내부 표현이 boolean이라는 사실과 LLM 호출 규약은 같은 층위의 문제가 아니라는 것이다.

- 백엔드 / DB
  - 각 식당은 `is_open=true/false`
- 검색 tool input
  - `only_open=true`면 `is_open=true`만 필터링
  - `only_open` 생략이면 open 필터 없이 다른 조건만 적용

그런데 현재 함수 시그니처는 `only_open=False`를 기본값으로 노출하고 있어서, 모델 입장에서는 "필터 없음"과 "`false`를 명시적으로 넣는 것"의 경계를 굳이 구분하지 않아도 되는 구조가 된다. 지금 exact match 평가에서는 이 점이 계속 잡음이 된다.

### 2. 프롬프트 본문은 `query/category` 규칙만 강하고 `only_open` 규칙은 약하다

- [datagen/prompts.py](/home/cwj/llm-project/datagen/prompts.py:34)
- [datagen/prompts.py](/home/cwj/llm-project/datagen/prompts.py:149)
- [datagen/prompts.py](/home/cwj/llm-project/datagen/prompts.py:195)

현재 프롬프트는 `query/category`에 대한 강한 규칙은 있지만, `only_open`에 대해서는 아래가 빠져 있다.

- 사용자가 `영업 중`, `지금 열려 있는`, `문 연 곳만`처럼 직접 말할 때만 `only_open=true`
- 영업 여부 언급이 없으면 `only_open` 생략
- 이전 턴의 open 조건은 사용자가 유지하라고 말한 경우에만 carry-over
- `only_open=false`는 생성하지 않음

즉 설명 문구는 tool schema에 일부 들어갔지만, 실제 생성 지시문에는 `only_open` 행동 규칙이 충분히 강하게 박혀 있지 않다.

### 3. 고정 예시가 오히려 예전 규약을 다시 가르친다

- [datagen/prompts.py](/home/cwj/llm-project/datagen/prompts.py:55)
  - 예시 호출은 `{"query": "피자"}`로 잘 되어 있다.
- [datagen/prompts.py](/home/cwj/llm-project/datagen/prompts.py:57)
  - 바로 뒤 function response의 `applied_filters`에는 `"only_open": false`, `"sort": "relevance"`가 들어 있다.

이 예시는 모델에게 아래 메시지를 준다.

- 영업 여부를 말하지 않아도 `only_open=false`가 자연스럽다
- 검색에서 `sort`와 `only_open`은 항상 채워진다는 인상을 준다

즉 호출 인자는 생략 규약인데, 응답 예시와 schema default는 여전히 채워진 상태를 보여주고 있다.

### 4. 반환 포맷도 호출 규약과 다르게 보일 수 있다

- [datagen/tool_specs.py](/home/cwj/llm-project/datagen/tool_specs.py:576)
  - `applied_filters.only_open: boolean`

백엔드 응답에서 `applied_filters.only_open`이 boolean인 것 자체는 자연스럽다. 다만 현재 의도는 "호출 인자에서는 true 또는 생략"이므로, 생성 모델 입장에서는 호출 규약과 응답 표현 규약이 다르게 보일 수 있다. 즉 이 항목은 단독 원인이라기보다, default와 예시가 함께 있을 때 혼선을 키우는 보조 신호에 가깝다.

## 실제 데이터에서 무엇이 보이는가

현재 로컬 생성 데이터는 아직 예전 관성이 강하다.

- `datagen/output/dataset.jsonl`
  - `search_restaurants` 총 90건
  - `only_open=true`: 77건
  - `only_open=false`: 3건
  - `only_open` 생략: 10건

즉 설명 문구를 일부 고쳤더라도, 실제 학습 데이터 분포는 여전히 `only_open=true` 편향이 크다.

반면 eval data는 상대적으로 새 규약에 더 가깝다.

- `eval_data/dataset.jsonl`
  - `search_restaurants` 총 59건
  - `only_open=true`: 19건
  - `only_open=false`: 0건
  - `only_open` 생략: 40건

이 상태는 train과 eval의 규약이 완전히 같지 않다는 뜻이다.

- eval은 거의 `true 또는 생략`
- train은 여전히 `true` 편향 + 일부 `false`

이 불일치는 현재 모델이 `only_open=true`를 과추론하는 이유 중 하나로 볼 수 있다.

## 결론

앞으로 `search_restaurants`의 `only_open`은 아래 규칙으로 고정한다.

- 사용자가 `영업 중`, `지금 열려 있는`, `문 연 곳만`처럼 명시하면 `only_open=true`
- 영업 여부를 말하지 않으면 `only_open` 생략
- `only_open=false`는 호출 인자에서 사용하지 않는다
- 이전 턴의 `only_open=true`는 사용자가 유지 의도를 보인 경우에만 carry-over 한다
- 사용자가 검색어/카테고리를 새로 바꾸면서 open 조건을 다시 말하지 않았다면, 기본적으로 open 조건은 reset 검토 대상이다

이 규칙은 `only_open`의 boolean 타입을 부정하는 것이 아니다. 식당의 실제 상태값 `is_open`은 계속 boolean이고, `only_open`도 타입상으로는 boolean 필터다. 다만 LLM이 만드는 호출 표기에서는 `true`가 필요할 때만 명시하고, 필터 미적용은 생략으로 통일하자는 뜻이다.

실행 의미는 아래처럼 정리한다.

- `only_open=true`
  - `is_open=true`인 식당만 검색
- `only_open` 생략
  - open 조건으로는 제한하지 않음
  - 다른 검색 조건을 만족하는 `is_open=true/false` 식당이 모두 결과에 포함될 수 있음

한 줄로 요약하면:

- DB의 `is_open`은 boolean으로 유지하고, LLM의 `only_open` 호출 규약은 `true 또는 생략`으로 단순화한다

## 코드 수정 계획

### 1. datagen 함수 명세

우선 수정 대상은 [datagen/tool_specs.py](/home/cwj/llm-project/datagen/tool_specs.py) 다.

권장 수정:

- `search_restaurants` 시그니처
  - `only_open: Optional[bool] = None`
  - `sort: Optional[str] = None`
- schema properties
  - `only_open`에서 `default: False` 제거
  - `sort`에서 `default: "rating"` 제거
- `SearchFilters`
  - `only_open: Optional[bool]`
  - `sort: Optional[str]`

이유:

- 생성 모델이 default 값을 "호출 시 항상 채워도 되는 값"으로 오해하지 않게 해야 한다.
- 지금 문제는 값이 틀리는 것보다, 불필요한 기본값을 자꾸 생성하는 데 있다.
- 백엔드 내부 boolean 표현은 유지하되, LLM 호출 표기는 필터 미적용을 생략으로 통일하는 편이 더 안정적이다.

추가로 이번 수정에서 `sort`도 함께 정리한 이유는, `only_open`과 같은 종류의 문제를 공유하기 때문이다.

- 기존 `sort="rating"` default는 사용자가 정렬 기준을 말하지 않아도 호출 인자에 기본값이 들어가도 된다는 신호를 줬다.
- 이는 `only_open=false` 기본값 노출과 마찬가지로, "필터/정렬 미지정"과 "기본값을 명시적으로 채운 호출"의 경계를 흐렸다.
- 특히 고정 예시와 schema default가 함께 있을 때, 모델은 `search_restaurants`에서 보조 슬롯을 과도하게 채우는 방향으로 학습될 수 있다.

즉 `sort` 수정은 `only_open`과 별개 주제를 새로 연 것이 아니라, 같은 "불필요한 기본값 신호 제거" 작업의 일부로 보는 편이 맞다.

### 2. datagen 프롬프트

수정 대상:

- [datagen/prompts.py](/home/cwj/llm-project/datagen/prompts.py:34)
- [datagen/prompts.py](/home/cwj/llm-project/datagen/prompts.py:149)
- [datagen/prompts.py](/home/cwj/llm-project/datagen/prompts.py:195)
- [datagen/config.py](/home/cwj/llm-project/datagen/config.py:179)
- [datagen/config.py](/home/cwj/llm-project/datagen/config.py:207)

추가할 규칙:

- `only_open`은 고객이 영업 중 조건을 직접 말한 경우에만 `true`
- 영업 여부 언급이 없으면 `only_open`을 쓰지 말 것
- `only_open=false`는 생성하지 말 것
- 검색 조건 변경 시 이전 `only_open`을 자동 유지하지 말 것
- 이전 open 조건을 유지하려면 고객이 명시적으로 유지 의도를 보여야 함

### 3. datagen 예시

수정 대상:

- [datagen/prompts.py](/home/cwj/llm-project/datagen/prompts.py:55)

권장 수정:

- 예시의 `search_restaurants` function response에서 `applied_filters.only_open`을 `false`로 고정 노출하지 않기
- 같은 이유로 `applied_filters.sort`도 기본값처럼 고정 노출하지 않기
- 가능하면 예시를 아래 둘로 바꾸는 것이 좋다
  - 영업 여부 미지정 검색: 호출 인자에 `only_open` 없음
  - 영업 중 명시 검색: 호출 인자에 `only_open=true`

핵심은 예시가 규약을 다시 흐리지 않도록 하는 것이다.

## 이번에 실제 반영한 내용

이번 datagen 수정에서는 문서 권장안을 아래처럼 실제 코드에 반영했다.

### 1. `search_restaurants` 시그니처와 타입 정의 수정

- [datagen/tool_specs.py](/home/cwj/llm-project/datagen/tool_specs.py:117)
  - `only_open: Optional[bool] = None`
  - `sort: Optional[str] = None`
- [datagen/tool_specs.py](/home/cwj/llm-project/datagen/tool_specs.py:31)
  - `SearchFilters.only_open: Optional[bool]`
  - `SearchFilters.sort: Optional[str]`

의도:

- `only_open=false`, `sort="rating"`이 함수 기본값처럼 보이지 않게 함
- 호출 인자에서 "명시된 조건만 넣는다"는 규약을 더 직접적으로 드러냄

### 2. tool schema description 수정

- [datagen/tool_specs.py](/home/cwj/llm-project/datagen/tool_specs.py:398)
  - `only_open` 설명에 "필터 미적용은 false 대신 생략" 규칙 반영
- [datagen/tool_specs.py](/home/cwj/llm-project/datagen/tool_specs.py:402)
  - `sort`는 사용자가 정렬 기준을 명시한 경우에만 사용하도록 유지

의도:

- `only_open`과 `sort` 모두 "보조 슬롯은 필요할 때만 명시"라는 방향으로 통일

### 3. schema default 제거

- [datagen/tool_specs.py](/home/cwj/llm-project/datagen/tool_specs.py:398)
  - `only_open.default = False` 제거
- [datagen/tool_specs.py](/home/cwj/llm-project/datagen/tool_specs.py:402)
  - `sort.default = "rating"` 제거

의도:

- default 값 자체가 LLM에게 "항상 채워도 되는 값"처럼 보이는 학습 신호를 줄이기 위함

### 4. 프롬프트 규칙 보강

- [datagen/prompts.py](/home/cwj/llm-project/datagen/prompts.py:34)
- [datagen/prompts.py](/home/cwj/llm-project/datagen/prompts.py:154)
- [datagen/prompts.py](/home/cwj/llm-project/datagen/prompts.py:203)
- [datagen/config.py](/home/cwj/llm-project/datagen/config.py:179)
- [datagen/config.py](/home/cwj/llm-project/datagen/config.py:207)

반영한 규칙:

- `only_open`은 영업 중 조건을 직접 말할 때만 `true`
- 영업 여부를 말하지 않으면 `only_open` 생략
- `only_open=false`는 생성하지 않음
- 이전 턴의 `only_open=true`는 유지 의도를 다시 말한 경우에만 carry-over

### 5. 고정 예시 수정

- [datagen/prompts.py](/home/cwj/llm-project/datagen/prompts.py:57)

기존:

- `applied_filters.only_open = false`
- `applied_filters.sort = "relevance"`
- 결과 식당도 모두 영업 중으로만 보이게 구성

수정 후:

- `applied_filters.only_open = null`
- `applied_filters.sort = null`
- 검색 결과에 영업 중인 식당과 영업 종료 식당이 함께 보이도록 변경

의도:

- 사용자가 영업 여부를 제한하지 않았을 때 결과에는 `is_open=true/false`가 함께 나올 수 있다는 점을 예시 차원에서 드러냄
- 동시에 `only_open`과 `sort`가 기본적으로 채워지는 슬롯이 아니라는 신호를 강화함

## eval 코드 / 평가 규약 계획

현재 평가 로직은 생략된 optional 파라미터를 schema default로 채운다.

- [evaluations/metrics.py](/home/cwj/llm-project/evaluations/metrics.py:57)

따라서 `only_open.default=False`가 schema에 남아 있으면:

- GT에서 `only_open` 생략
- 정규화 후 `only_open=false`

가 된다.

현재 평가셋이 `true 또는 생략` 규약으로 정리된다면, 이 동작 자체가 꼭 틀린 것은 아니다. 다만 아래를 같이 맞춰야 한다.

- eval data의 tool schema에서도 `only_open.default=False`를 유지할지
- 아니면 default를 제거하고 `생략 = None`으로 볼지

현재 우선순위는 metric 코드 변경보다 eval GT 정리다.

이유:

- 지금 실패의 핵심은 `생략 vs false`보다 `pred=true` 과추론이다
- `default`를 제거해도 `true` 오예측은 여전히 실패한다
- 먼저 GT 규약과 schema 규약을 문서 기준으로 통일하는 편이 낫다

다만 장기적으로는 문서와 코드에서 `is_open`과 `only_open`의 역할을 더 분명히 분리해 둘 필요가 있다. 그래야 "boolean인데 왜 생략하느냐"는 혼선을 줄일 수 있다.

권장 순서:

1. eval data를 `true 또는 생략` 규약으로 재검토
2. 그 규약을 기준으로 schema default 유지 여부를 결정
3. 필요하면 그 다음에 metric normalization 정책을 조정

## eval data 수정 계획

수정 원칙:

- 사용자가 현재 턴에서 `영업 중`을 직접 말한 경우만 `only_open=true`
- 사용자가 새 검색으로 넘어가며 open 조건을 다시 말하지 않았다면 `only_open` 제거 검토
- 과거 턴의 open 조건을 자동 상속한 GT가 있으면 제거 검토
- `only_open=false`가 명시된 GT가 있으면 생략으로 바꾸는 것을 우선 검토

특히 우선 재검토할 케이스:

- 검색어/카테고리 변경 턴
- `평점 높은 곳`, `추천해줘`처럼 soft preference만 있는 턴
- 이전 턴에는 `영업 중`이 있었지만 현재 턴에는 없는 케이스

## train data 수정 계획

수정 원칙은 eval과 동일하게 맞춘다.

- `only_open=false` 호출은 제거
- 영업 여부 비명시 검색에서는 `only_open` 생략
- 새 검색 조건으로 넘어갈 때 open 조건 자동 유지 샘플 제거 또는 수정
- `only_open=true` 편향이 과도한 샘플 분포를 완화

현재 로컬 생성 데이터에서는 `search_restaurants` 90건 중:

- `only_open=true`: 77건
- `only_open` 생략: 10건
- `only_open=false`: 3건

즉 단순 relabel만이 아니라 분포 자체를 다시 맞출 필요가 있다.

권장 작업:

- 기존 train dataset relabel
- datagen regenerate
- regenerate 후 `only_open=true / 생략` 비율 재점검

## 실제 적용 항목

### Datagen code

- `datagen/tool_specs.py`
  - `only_open` default 제거
  - 필요하면 `sort` default도 함께 제거
  - 타입 정의를 optional 중심으로 정리
- `datagen/prompts.py`
  - `only_open` 규칙 명시 추가
  - 예시 수정
- `datagen/config.py`
  - 골드 카테고리 instruction에 `only_open` reset / carry-over 규칙 추가

### Dataset relabel

- train data의 `search_restaurants` 중 `only_open=false` 제거
- 영업 여부 비명시 케이스의 `only_open=true` 제거
- 검색 조건 변경 턴에서 carry-over 된 `only_open=true` 제거 검토

### Eval

- eval data의 `search_restaurants` GT를 같은 규약으로 재검토
- 이후 필요하면 schema default / normalization 정책 재정렬

## 최종 정리

이번 `only_open` 문제의 핵심은 모델이 boolean 하나를 못 맞춘다기보다, 생성 단계에서부터 아래 신호가 서로 충돌한다는 데 있다.

- 설명 문구는 `true 또는 생략`
- 함수 시그니처와 schema default는 `false 기본값`
- 예시 응답은 `only_open=false`를 반복 노출
- train data 분포는 `only_open=true` 편향이 강함

그리고 이 문제는 "가게의 영업 상태는 분명한데 왜 false를 안 쓰느냐"의 문제가 아니다. 가게의 실제 상태는 `is_open=true/false`로 분명하고, 우리가 정리하려는 것은 `only_open`이라는 검색 필터를 tool call에 어떤 표기로 넣을지다. 이 프로젝트에서는 필터 미적용을 `false` 대신 생략으로 통일하는 편이 학습과 평가 모두에서 더 안정적이다.

그래서 현재 datagen 함수 명세를 일부 고친 것만으로는 충분하지 않다.

앞으로는 아래 순서로 정리한다.

1. datagen tool spec의 default 신호 제거
2. 프롬프트와 예시에 `only_open` 규칙을 명시
3. train data를 `true 또는 생략` 규약으로 relabel 또는 재생성
4. eval data도 같은 규약으로 재검토

이렇게 맞추면 현재 `argument_value`에서 `query/category` 다음으로 큰 축인 `only_open` 실패를 가장 직접적으로 줄일 수 있다.
