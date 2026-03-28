# Function Matching Error Conversations: Merged Summary

- Source 1: `eval_output_500_2batch_3ep/function_matching_error_conversations.md`
- Source 2: `eval_output_500_32batch_10ep_before/function_matching_error_conversations.md`
- Source 1 error rows: 10
- Source 2 error rows: 19
- 목적: 두 어댑터의 function matching 오류를 통합 정리하되, 샘플 원문과 툴 스키마를 다시 확인해 **모델 오류**와 **데이터셋 라벨 문제**를 분리해서 본다.

## 핵심 결론

초기에는 `get_restaurant_detail`와 `search_restaurants`의 혼동으로 보였던 일부 사례를 모델 오류로 분류했지만, 샘플 원문과 툴 정의를 다시 보면 일부는 **데이터셋이 대화 밖의 숨은 엔터티 매핑을 가정한 라벨**에 가깝다.

특히 아래 두 케이스는 평가에서 일반적인 모델 오류와 분리해서 보는 편이 맞다.

- `Conv 8 / sample_0009`
- `Conv 12 / sample_0013`

이유는 공통적이다.

- `get_restaurant_detail`는 `restaurant_id`가 필수다.
- 사용자 발화에는 보통 식당명만 있고 `restaurant_id`는 없다.
- 대화 안에 해당 식당의 `restaurant_id`가 아직 등장하지 않았다면, 자연스러운 툴 흐름은 보통 `search_restaurants -> get_restaurant_detail`이다.

즉, 식당명이 구체적이라는 이유만으로 바로 `get_restaurant_detail`를 정답 처리한 라벨은, 실제 툴 사용보다는 내부 엔터티 링크가 이미 되어 있다는 가정을 깔고 있다.

## 분류 요약

| 유형 | 설명 | 판정 | 대표 사례 |
|---|---|---|---|
| 숨은 엔터티 매핑 가정 | 식당명이 처음 등장했는데 검색 없이 바로 `get_restaurant_detail`를 GT로 둠 | 데이터셋 이슈 | Conv 8, Conv 12 |
| 검색/상세 조회 실제 혼동 | 새 지점을 물었는데 기존 식당 상세 조회로 점프함 | 실제 모델 오류 | Conv 7 |
| 담기 대신 재조회 | 이미 메뉴가 식별됐는데 `add_to_cart` 대신 `get_restaurant_detail`로 후퇴 | 실제 모델 오류 | Conv 13, Conv 39 |
| 조회 대신 성급한 담기 | 메뉴 ID 확보 전인데 `add_to_cart`로 점프 | 실제 모델 오류 | Conv 10, Conv 14 |
| 장바구니/배송지/결제 단계 혼동 | `get_cart`, `list_addresses`, `upsert_address`, `prepare_checkout` 순서를 섞음 | 대체로 실제 모델 오류 | Conv 23, Conv 24, Conv 37, Conv 39 |
| 요청사항 해석 애매 | 기존 요청을 일부 유지할지 전체 교체할지 발화만으로 애매 | 라벨 애매 | Conv 22 |

## 1. 명확한 데이터셋 이슈

### Conv 8 / sample_0009

사용자 발화:

```text
그럼 버거킹 판교역점 메뉴도 보여줘.
```

데이터셋 GT:

```json
{"name": "get_restaurant_detail", "arguments": {"restaurant_id": "f1a2b3c4-d5e6-7f89-8a7b-6c5d4e3f2a1b"}}
```

왜 라벨이 문제인가:

- 직전 대화에서 `버거킹 판교역점`은 검색 결과로 등장한 적이 없다.
- 따라서 대화 안에는 그 식당의 `restaurant_id`가 없다.
- 툴 스키마상 자연스러운 흐름은 먼저 `search_restaurants`로 `버거킹 판교역점`을 찾고, 그 다음 `get_restaurant_detail`를 호출하는 것이다.

판정:

- **명확한 데이터셋 라벨 이슈**
- 이 케이스에서 `search_restaurants`를 택한 모델을 단순 오답으로 처리하는 것은 과도하다.

### Conv 12 / sample_0013

사용자 발화:

```text
마라당 강남점 메뉴 뭐 있어요? 마라탕 담고 싶어요.
```

데이터셋 GT:

```json
{"name": "get_restaurant_detail", "arguments": {"restaurant_id": "e1a4b6f2-9c3d-4e8a-8d2b-3f6c5b7a9d21"}}
```

왜 라벨이 문제인가:

- 대화 첫 턴이므로 이전 문맥에서 `restaurant_id`를 얻을 경로가 전혀 없다.
- 따라서 스키마 기준으로는 `search_restaurants(query="마라당 강남점")`가 먼저 와야 한다.

판정:

- **명확한 데이터셋 라벨 이슈**
- 이 경우도 `search_restaurants`를 오답으로 보는 평가는 실제 툴 사용 흐름과 어긋난다.

## 2. 실제 모델 오류로 보는 것이 타당한 사례

### 2-1. 검색과 상세 조회의 실제 혼동

#### Conv 7 / sample_0008

사용자 발화:

```text
장터국밥 서초본점 메뉴도 볼 수 있어요?
```

GT:

```json
{"name": "search_restaurants", "arguments": {"query": "장터국밥 서초본점", "only_open": true}}
```

예측 오류:

```json
{"name": "get_restaurant_detail", "arguments": {"restaurant_id": "2a9b8b3c-1f43-4c71-89cd-7e18a5e09a77"}}
```

해석:

- 직전까지 본 것은 `장터국밥 서초점`이고, 사용자는 새 지점 `서초본점`을 물었다.
- 따라서 먼저 검색으로 새 엔터티를 재확정하는 GT가 자연스럽다.
- 이건 실제 모델 오류로 보는 것이 맞다.

### 2-2. 메뉴 조회와 장바구니 추가 혼동

#### Conv 13 / sample_0012

사용자 발화:

```text
볶음밥도 하나 추가해줘.
```

GT:

```json
{"name": "add_to_cart", "arguments": {"user_id": "47d67a36-584a-4154-8a7c-e9eb74ee1326", "restaurant_id": "5c1e7dc9-3a34-4b4d-8f87-2b0b2e9bc2ef", "menu_item_id": "2b7d1aa3-92dc-4b29-9e33-0f75e142e70c", "quantity": 1}}
```

예측 오류:

```json
{"name": "get_restaurant_detail", "arguments": {"restaurant_id": "5c1e7dc9-3a34-4b4d-8f87-2b0b2e9bc2ef"}}
```

해석:

- 직전 문맥에서 메뉴 목록과 식당 정보가 이미 확보돼 있다.
- 따라서 다시 상세 조회할 이유가 없고, 바로 `add_to_cart`가 맞다.
- 전형적인 상태 추적 실패다.

#### Conv 10 / sample_0011

사용자 발화 맥락:

```text
홍리마라 판교점에서 마라탕 중자 하나 장바구니에 담아줘.
```

GT 흐름:

1. `search_restaurants`
2. `get_restaurant_detail`
3. `add_to_cart`

해석:

- 메뉴 ID를 알아야 담을 수 있으므로, 상세 조회를 먼저 거친 뒤 담는 흐름이 스키마와 잘 맞는다.
- 따라서 이 단계에서 바로 `add_to_cart`로 점프한 모델은 실제로 너무 성급한 선택을 한 것이다.

## 3. 장바구니, 배송지, 결제 단계에서의 문제

이 구간은 대부분 GT가 타당했다. 다만 일부는 라벨 해석의 여지가 있었다.

### 3-1. GT가 대체로 타당한 사례

#### Conv 23 / sample_0024

사용자 발화:

```text
장바구니 결제 진행하려고 해요. 장바구니랑 배송지 확인해 주실 수 있나요?
```

GT:

```json
{"name": "get_cart", "arguments": {"user_id": "dd1fbd52-cd42-4a6e-b943-44a36e4e7f2d"}}
```

해석:

- 장바구니를 먼저 확인하고, 이어서 배송지를 보여주는 흐름은 자연스럽다.
- `list_addresses`를 먼저 호출해도 아주 이상하다고 보긴 어렵지만, GT 쪽이 더 보수적이고 설계 의도에 맞다.

#### Conv 24 / sample_0023, Conv 37 / sample_0037, Conv 39 / sample_0039

공통 패턴:

- 사용자가 공동현관 비밀번호, 상세주소, 연락처 같은 배송지 메타데이터를 바꾼다.
- GT는 먼저 `upsert_address`를 호출한다.
- 모델은 `prepare_checkout`로 성급하게 넘어가는 경향이 있다.

해석:

- 배송지 객체 자체가 바뀌므로 `upsert_address` 선행이 맞다.
- 이 범주는 대부분 실제 모델 오류로 보는 것이 타당하다.

### 3-2. 라벨이 애매한 사례

#### Conv 22 / sample_0023

사용자 발화:

```text
아, 요청사항을 경비실에 맡겨주세요로 바꿔주세요. 그리고 바로 결제할게요.
```

GT:

```json
{"name": "prepare_checkout", "arguments": {"user_id": "83e6d570-ad10-40f0-8aca-0f1cdc63a14f", "address_id": "6f1b3785-4c2a-4b5e-8de0-3edfa3e3e0a1", "delivery_note": "경비실에 맡겨주세요. 일회용 수저는 제외해 주세요."}}
```

왜 애매한가:

- 발화만 보면 `경비실에 맡겨주세요`로 전체 메모를 교체하는 해석도 가능하다.
- GT는 이전 메모의 일부인 `일회용 수저는 제외`를 유지하는 해석을 택했다.

판정:

- **명백한 데이터셋 오류라고 보긴 어렵지만 라벨이 애매한 사례**
- 모델을 강하게 페널티 주기에는 사용자 발화가 완전히 단정적이지 않다.

## 샘플 원문 재검토 결과

`eval_data/samples`의 관련 샘플들을 26줄 이후 대화 원문 기준으로 다시 읽은 결과는 아래와 같다.

### 명확한 데이터셋 이슈

- `sample_0009 / Conv 8`
  - `버거킹 판교역점`이 사전 검색 결과에 없는데 GT가 즉시 `get_restaurant_detail`
- `sample_0013 / Conv 12`
  - 첫 턴부터 `마라당 강남점`에 대해 GT가 즉시 `get_restaurant_detail`

### 라벨이 애매한 사례

- `sample_0023 / Conv 22`
  - 요청사항 수정 시 이전 메모 일부를 유지할지 완전히 교체할지 발화만으로는 완전히 고정되지 않음

### 대부분 GT가 타당했던 사례

- `sample_0008 / Conv 7`
- `sample_0011 / Conv 10`
- `sample_0012 / Conv 13`
- `sample_0024 / Conv 23`
- `sample_0036 / Conv 36`
- `sample_0037 / Conv 37`
- `sample_0039 / Conv 39`

이 케이스들은 대체로 데이터셋보다 모델의 멀티턴 상태 추적과 우선순위 결정 실패가 더 크게 보였다.

## 데이터셋 설계상 추가로 보인 주의점

### 1. 함수는 맞지만 인자 기본값 선택이 임의적인 경우

`sample_0037`에서는 사용자가 다음처럼 말한다.

```text
카카오…? 아니 카드… 에잇 아무거나 빨리.
```

GT는 `payment_method: "card"`를 택한다. 하지만 발화만 보면 `card`와 `kakao` 중 어느 쪽을 정답으로 고정할지 완전히 분명하지 않다. 즉, 이런 샘플은 함수명 평가에는 도움이 되지만, 인자 평가에는 임의성이 섞일 수 있다.

### 2. 식당명만으로 내부 ID를 안다고 가정하는 경우

이 문제는 `search_restaurants` / `get_restaurant_detail` 구간에서 가장 크게 드러난다.

- 스키마는 `restaurant_id` 기반이다.
- 그런데 일부 샘플은 대화 안의 검색 단계 없이 바로 상세 조회를 정답 처리한다.

이런 라벨은 실제 툴 사용 시나리오보다 이상화된 엔터티 링크를 가정한다.

## 최종 정리

이번 재검토 기준으로 보면, 초기 문서에서 하나의 오류 유형으로 묶였던 사례들 중 일부는 실제 모델 오류가 아니라 데이터셋 라벨 문제였다.

분리해서 보는 것이 맞는 항목은 다음과 같다.

1. **명확한 데이터셋 이슈**
   - `Conv 8 / sample_0009`
   - `Conv 12 / sample_0013`
2. **라벨이 애매한 사례**
   - `Conv 22 / sample_0023`
3. **실제 모델 오류가 중심인 사례**
   - 나머지 다수의 장바구니 수정, 주소 업데이트, 결제 준비, 멀티턴 상태 추적 관련 오류

실무적으로는 앞으로 이 평가 문서를 볼 때 오류를 최소 다음 세 부류로 나눠 보는 것이 좋다.

- 명확한 모델 오류
- 데이터셋 라벨이 애매한 사례
- 데이터셋이 숨은 엔터티 매핑이나 임의 기본값 선택을 가정한 사례
