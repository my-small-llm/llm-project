# `search_restaurants` min_rating 문제 정의 및 해결

작성일: 2026-04-02

## 목적

이 문서는 `search_restaurants`의 `min_rating` 문제를 한 문서에서 끝까지 다루기 위해 만든 통합 문서다.

아래 내용을 함께 담는다.

- 문제가 무엇이었는가
- 어떤 실패 케이스가 근거였는가
- 어떤 규칙을 추천했는가
- 최종적으로 무엇으로 결정했는가

정리하려는 내용은 세 가지다.

- datagen에서 왜 `min_rating` 문제가 만들어졌는가
- 실제 데이터와 실패 사례에서 어떤 식으로 드러났는가
- 그래서 앞으로 어떤 규칙으로 고칠 것인가

## 문제 요약

현재 `argument_value` 실패 중 `search_restaurants`는 크게 아래 네 문제로 수렴한다.

- `query`와 `category`의 경계가 불명확함
- `only_open=true`를 기본값처럼 과추론함
- `평점 높은 곳`을 `min_rating=4.5`로 과해석함
- 정정 발화가 나와도 이전 의도를 완전히 지우지 못함

그중 `min_rating` 문제의 핵심은 soft preference를 hard filter로 바꾸는 데 있다.

즉 사용자가:

- `평점 높은 곳`
- `평점 높은 순으로`
- `추천해줘`
- `인기 많은 곳`

처럼 상대적 선호나 정렬 의도만 말했는데, 모델이 이를:

- `min_rating=4.5`

같은 절대 숫자 필터로 바꾸는 패턴이 반복된다.

이 문제는 단순히 숫자 하나를 잘못 고른 문제가 아니다.

- 사용자가 말하지 않은 threshold를 임의로 발명하고
- 검색 결과 집합 자체를 더 좁게 만들 수 있으며
- `sort`와 `min_rating`의 역할 경계를 흐리고
- 데이터셋과 프롬프트 규칙이 조금만 흔들려도 반복적으로 재발한다

즉 이 문제는 모델의 "평점 관련 선호 해석" 문제이면서, 동시에 annotation policy와 generation policy를 더 강하게 고정해야 하는 문제다.

## 케이스 분류

이 이슈를 검토할 때 사용한 핵심 분류는 아래와 같았다.

### A. soft preference의 hard threshold화

- `평점 높은 곳`
- `평점 높은 순`
- `추천해줘`

같은 표현에서 사용자가 숫자를 말하지 않았는데 `min_rating=4.5`가 생성되는 경우

### B. sort와 min_rating의 역할 혼동

- `평점 높은 순으로`
- `별점 순으로`

는 정렬 기준인데, 모델이 정렬과 별개로 `min_rating=4.5`까지 함께 넣는 경우

### C. 이전 숫자 조건의 과도한 carry-over

- 이전 턴에서 `4.5 이상`을 사용했더라도
- 새 검색으로 전환하거나 검색 의도가 바뀌었는데
- 이전 threshold가 남아 다음 턴까지 이어지는 경우

### D. eval / train / datagen 규칙 불일치

- 설명 문구는 `숫자 기준을 명시한 경우에만 min_rating 사용`이라고 되어 있어도
- 프롬프트 본문, 예시, 실제 데이터 분포가 이 규칙을 충분히 강하게 밀지 못하면
- 모델은 여전히 `평점 높은 곳 -> 4.5 이상`을 자연스럽게 추론하게 된다

## 규칙 결정에 직접 영향을 준 사례

- `conv=0 turn=2`
  - 사용자는 `평점 높은 곳으로 추천` 정도만 말했는데 `min_rating=4.5`가 추가됐다.
  - [tool_failures_with_dialogue.md:171](/home/cwj/llm-project/eval_output/qwen-2.5-7b-function-calling_batch2_data_v2/tool_failures_with_dialogue.md:171)
- `conv=7 turn=0`
  - `category=한식`, `sort=rating`이면 충분한데 `min_rating=4.5`가 추가됐다.
  - [tool_failures_with_dialogue.md:1023](/home/cwj/llm-project/eval_output/qwen-2.5-7b-function-calling_batch2_data_v2/tool_failures_with_dialogue.md:1023)
- `conv=32 turn=0`
  - 사용자가 숫자 threshold를 직접 말하지 않았는데도 `min_rating=4.5`가 생성됐다.
  - [tool_failures_with_dialogue.md:2525](/home/cwj/llm-project/eval_output/qwen-2.5-7b-function-calling_batch2_data_v2/tool_failures_with_dialogue.md:2525)
- `conv=34 turn=0`
  - `query/category` 혼선과 함께 `min_rating=4.5`가 같이 과생성됐다.
  - [tool_failures_with_dialogue.md:2935](/home/cwj/llm-project/eval_output/qwen-2.5-7b-function-calling_batch2_data_v2/tool_failures_with_dialogue.md:2935)
- `conv=37 turn=0`
  - `불고기 비빔밥` 검색에서 사용자가 threshold를 말하지 않았는데 `min_rating=4.5`가 붙었다.
  - [tool_failures_with_dialogue.md:3332](/home/cwj/llm-project/eval_output/qwen-2.5-7b-function-calling_batch2_data_v2/tool_failures_with_dialogue.md:3332)

즉 이 문제는 몇몇 예외 사례가 아니라, "평점 관련 soft phrase를 보면 숫자 cutoff를 채우려는" 반복 패턴으로 보는 편이 맞다.

## 추천안

검토 결과 가장 안정적인 추천안은 아래였다.

- `min_rating`
  - 사용자가 숫자 기준을 직접 명시했을 때만 사용
  - 예: `4.5 이상`, `최소 4.3`, `별점 4점 넘는 곳`, `평점 4.7 이상`
- `sort`
  - 사용자가 정렬 기준을 직접 말했을 때 사용
  - 예: `평점 높은 순`, `별점순`, `관련도순`, `배달비 낮은 순`
- soft preference
  - `평점 높은 곳`, `추천`, `인기 많은 곳`처럼 숫자가 없는 표현은 기본적으로 `min_rating`으로 바꾸지 않음

권장 원칙은 아래와 같았다.

- explicit numeric threshold -> `min_rating`
- ranking / ordering request -> `sort`
- vague preference without number -> `min_rating` 생략
- 사용자가 숫자를 말하지 않았으면 임의의 cutoff를 만들지 않음

## 결론

앞으로 `search_restaurants`는 아래 규칙으로 고정한다.

- 사용자가 `4.5 이상`, `최소 4.3`, `별점 4점 넘는 곳`처럼 숫자 기준을 직접 말할 때만 `min_rating` 사용
- `평점 높은 곳`, `추천해줘`, `인기 많은 곳`처럼 모호한 선호만 말하면 `min_rating`은 생략
- `평점 높은 순`, `별점순`은 `sort=rating` 문제이지 `min_rating` 문제가 아님
- 이전 턴의 `min_rating`은 사용자가 유지 의도를 보인 경우에만 carry-over
- 새 검색으로 전환했거나 검색 의도가 바뀌었는데 숫자 조건을 다시 말하지 않으면 `min_rating`은 reset 검토 대상이다

한 줄로 요약하면:

- `min_rating = 숫자 기준이 직접 말해졌을 때만 사용`

## 1. Datagen에서 왜 문제가 생겼는가

현재 `min_rating`의 설명 문구 자체는 비교적 올바른 편이다.

- [tool_specs.py](/home/cwj/llm-project/datagen/tool_specs.py:394)
  - `고객이 '4.5 이상', '최소 4.3'처럼 숫자 기준을 명시한 경우에만 사용하는 최소 평점 필터입니다. '평점 높은 곳'처럼 모호한 표현만 있으면 이 파라미터는 생략합니다.`

하지만 이것만으로는 충분하지 않다.

### 1. 프롬프트 본문에서 min_rating 규칙이 충분히 강하지 않다

- [prompts.py](/home/cwj/llm-project/datagen/prompts.py:18)
- [prompts.py](/home/cwj/llm-project/datagen/prompts.py:149)
- [prompts.py](/home/cwj/llm-project/datagen/prompts.py:230)

현재 프롬프트는 `query/category`, `only_open`, `sort` 규칙은 비교적 자세히 적고 있지만 `min_rating`에 대해서는 아래가 빠져 있다.

- 숫자 기준이 있을 때만 `min_rating`
- `평점 높은 곳`, `추천`, `인기 많은 곳`은 `min_rating`으로 바꾸지 않음
- `평점 높은 순`은 `sort=rating`으로 처리
- 이전 턴의 `min_rating`을 언제 유지하고 언제 버릴지

즉 tool schema에는 규칙이 들어가 있지만, 실제 데이터 생성 지시문에는 행동 규칙이 약하다.

### 2. sort와 min_rating의 경계를 따로 고정하지 않으면 오해가 남는다

현재 프롬프트는 정렬 규칙은 있지만, 아래 대비가 충분히 강조되어 있지 않다.

- `평점 높은 순` -> `sort=rating`
- `평점 4.5 이상` -> `min_rating=4.5`

이 구분이 약하면 모델은 "평점과 관련된 표현"을 보면 두 슬롯을 함께 채우거나, 정렬 요청을 threshold로 과해석할 수 있다.

### 3. 실제 학습 데이터에 남아 있는 관성이 있을 수 있다

설명 문구를 고친 뒤에도 기존 train 샘플에 아래 같은 패턴이 남아 있으면 문제가 계속된다.

- soft phrase인데 `min_rating=4.5`
- 정렬 요청인데 `sort`와 `min_rating`을 동시에 생성
- 새 검색으로 바뀌었는데 이전 `min_rating`이 남아 있음

즉 이 문제는 schema 문구만으로 해결되기보다, datagen prompt와 실제 dataset 분포까지 같이 맞춰야 줄어든다.

## 2. 실제 데이터에서 어떤 문제가 있었는가

실패 사례를 보면 `min_rating` mismatch는 거의 한 방향으로 반복된다.

- GT=`null 또는 미지정`
- PRED=`4.5`

대표 사례:

- [tool_failures_with_dialogue.md:171](/home/cwj/llm-project/eval_output/qwen-2.5-7b-function-calling_batch2_data_v2/tool_failures_with_dialogue.md:171)
- [tool_failures_with_dialogue.md:1023](/home/cwj/llm-project/eval_output/qwen-2.5-7b-function-calling_batch2_data_v2/tool_failures_with_dialogue.md:1023)
- [tool_failures_with_dialogue.md:2525](/home/cwj/llm-project/eval_output/qwen-2.5-7b-function-calling_batch2_data_v2/tool_failures_with_dialogue.md:2525)
- [tool_failures_with_dialogue.md:2935](/home/cwj/llm-project/eval_output/qwen-2.5-7b-function-calling_batch2_data_v2/tool_failures_with_dialogue.md:2935)
- [tool_failures_with_dialogue.md:3332](/home/cwj/llm-project/eval_output/qwen-2.5-7b-function-calling_batch2_data_v2/tool_failures_with_dialogue.md:3332)

즉 현재 `min_rating` 실패의 본질은:

- 숫자를 틀리게 고르는 문제라기보다
- 사용자가 말하지 않은 숫자 기준을 생성하는 문제다

또한 이 문제는 단독으로만 나타나지 않는다.

- `query/category` 혼선
- `only_open=true` 과추론
- `sort` 과생성 또는 carry-over

와 함께 묶여 나타나는 경우가 많다.

즉 `min_rating`은 별도 문제이지만, 검색 보조 슬롯을 과도하게 채우는 더 큰 성향의 일부로 보는 편이 맞다.

## 3. 그래서 어떻게 해결할 것인가

해결 방향은 단순하다. `min_rating`을 "숫자 threshold 슬롯"으로 강하게 고정한다.

### 규칙 1. 숫자 기준이 직접 있을 때만 `min_rating`

예:

- `평점 4.5 이상만 보여줘` -> `{"min_rating": 4.5}`
- `최소 4.3 이상` -> `{"min_rating": 4.3}`
- `별점 4점 넘는 곳` -> `{"min_rating": 4.0}`

### 규칙 2. 정렬 요청은 `sort`로만 처리

예:

- `평점 높은 순으로` -> `{"sort": "rating"}`
- `별점순으로 보여줘` -> `{"sort": "rating"}`

즉 숫자가 없으면 `min_rating`까지 자동으로 만들지 않는다.

### 규칙 3. soft preference는 기본적으로 threshold로 바꾸지 않는다

예:

- `평점 높은 곳 추천해줘` -> `{"sort": "rating"}` 또는 다른 슬롯만 사용
- `인기 많은 곳` -> popularity 관련 별도 규칙이 없다면 `min_rating`으로 바꾸지 않음
- `추천해줘` -> `min_rating` 생성 금지

### 규칙 4. 이전 threshold는 명시적 유지 의도가 있을 때만 carry-over

예:

- 직전 턴: `4.5 이상만`
- 다음 턴: `거기서 중식으로 바꿔줘`
  - 같은 검색 축 유지로 해석되면 `min_rating=4.5` 유지 가능
- 다음 턴: `이번엔 중식으로 추천해줘`
  - 새 검색 전환이고 threshold를 다시 말하지 않았다면 reset 검토

### 규칙 5. 사용자가 숫자를 해제하거나 느슨하게 바꾸면 `min_rating` 제거 검토

예:

- `4.5 이상만` 다음에 `그냥 평점 높은 곳으로만 볼게`
  - `min_rating` 유지가 아니라 `sort=rating` 쪽으로 전환 검토

## 4. 실제 적용 항목

### Datagen

- `search_restaurants` 프롬프트 규칙에 아래 문구 추가
  - `min_rating은 사용자가 4.5 이상, 최소 4.3처럼 숫자 기준을 직접 말할 때만 사용하세요.`
  - `평점 높은 곳, 추천해줘, 인기 많은 곳 같은 모호한 표현만 있으면 min_rating을 만들지 마세요.`
  - `평점 높은 순, 별점순은 sort=rating으로 처리하고 min_rating은 추가하지 마세요.`
  - `새 검색으로 전환했는데 숫자 기준을 다시 말하지 않으면 이전 min_rating을 자동 유지하지 마세요.`

### Dataset relabel

- soft phrase인데 `min_rating=4.5`가 붙은 train 샘플 재검토
- `평점 높은 순`류를 `sort=rating` 중심으로 재정비
- 새 검색 전환인데 이전 `min_rating`이 남은 샘플 재검토

### Eval

- GT가 정말 `숫자 기준 명시 시에만 min_rating`을 따르는지 재확인
- `평점 높은 곳`류 문장을 `min_rating` 없이도 충분히 표현하도록 기준을 고정

## 최종 정리

이번 문제의 본질은 모델이 `min_rating` 숫자 자체를 못 외웠다는 데 있지 않다.

핵심은 아래에 있다.

- 모델이 평점 관련 soft phrase를 보면 threshold를 임의로 보강하려는 경향
- `sort`와 `min_rating`의 역할 구분이 데이터와 프롬프트에서 충분히 강하지 않았던 점

그래서 앞으로는 아래 기준으로 정리한다.

- `min_rating`: 숫자 threshold
- `sort`: 정렬 기준
- `평점 높은 곳`: 기본적으로 threshold가 아니라 선호/정렬 신호

이 규칙으로 datagen, dataset, eval GT를 같이 맞추면 현재 `argument_value` 실패 중 `min_rating` 축을 비교적 깔끔하게 줄일 수 있다.
