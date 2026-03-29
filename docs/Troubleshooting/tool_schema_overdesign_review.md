# 함수 스키마 과설계 검토 통합 문서

작성일: 2026-03-28

## 목적

이 문서는 기존의 `schema_overdesign_parameter_review.md`와 `tool_schema_parameter_analysis.md`를 통합한 문서다.

정리 관점은 `argument_value_failure_case_report.md`를 기준으로, 함수 스키마를 처음 정의할 때 넣은 파라미터 중 아래 성질을 가진 항목을 식별하는 것이다.

- 실제 기능 수행에 꼭 필요하지 않을 수 있음
- 사용 용도가 모호하거나 사용자 발화에서 직접 드러나지 않음
- 모델이 반복적으로 틀리거나 기본값으로 회귀함
- 실서비스 가치보다 평가 오류를 더 많이 유발함

즉 이 문서는 "모델이 왜 틀렸는가"보다 "스키마 자체가 과했는가"를 보는 문서다.

## 기준

- 기준 실험: `eval_output_500_32batch_10ep_before`
- 기준 보고서: [argument_value_failure_case_report.md](/home/cwj/llm-project/docs/Troubleshooting/argument_value_failure_case_report.md)
- 참고 스키마: [config.py](/home/cwj/llm-project/datagen/config.py)

## 한줄 결론

가장 먼저 재검토해야 할 파라미터는 `search_restaurants.page`, `search_restaurants.page_size`, `get_restaurant_detail.at`, `upsert_address.is_default` 이다.

이들은 현재 구조에서 "핵심 의도 슬롯"이라기보다 "기본값성 제어 슬롯"에 가깝고, 실제 가치 대비 오류를 많이 만든다.

반면 `query`, `category`, `special_request`, `delivery_note`, 각종 ID와 `quantity`는 실패가 있더라도 제거 대상이 아니다. 이들은 기능의 본질을 이루는 핵심 슬롯이다.

## 분석 관점

파라미터는 아래 네 부류로 나눠서 보는 것이 유용하다.

- 핵심 업무 슬롯
  - 이 값이 없으면 함수의 본래 목적이 성립하지 않음
- 보조 제어 슬롯
  - 있으면 세밀한 제어가 가능하지만 없어도 주 기능은 유지됨
- 상태 전달 슬롯
  - 이전 함수 결과를 후속 함수에 정확히 연결하기 위한 값
- 자유서술 슬롯
  - 사용자의 자연어 요청을 문자열 그대로 보존해야 하는 값

실제 문제는 주로 두 곳에서 발생했다.

- 보조 제어 슬롯이 많고 기본값까지 노출되면 모델이 불필요하게 채워 넣는다.
- 자유서술 슬롯을 모델이 "보존"이 아니라 "요약/정리" 대상으로 처리한다.

## 보고서 기준 핵심 근거

[argument_value_failure_case_report.md](/home/cwj/llm-project/docs/Troubleshooting/argument_value_failure_case_report.md) 에서 관찰된 주요 실패는 다음과 같다.

- `special_request`: 15건
- `delivery_note`: 10건
- `page_size`: 9건
- `query`: 7건
- `only_open`: 6건
- `sort`: 6건
- `category`: 6건

하지만 이 숫자를 그대로 "제거 우선순위"로 읽으면 안 된다.

- `special_request`, `delivery_note`, `query`, `category`는 실패가 많아도 실서비스 핵심 슬롯이다.
- 반대로 `page_size`, `page`, `at`, `is_default`는 실패 수가 다소 적더라도 "실제 가치 대비 과한 슬롯"일 가능성이 높다.

## 핵심 판단 기준

파라미터를 세 종류로 나눠서 보는 것이 좋다.

### 1. 제거 또는 축소 검토 대상

- 없어도 대부분의 핵심 기능은 성립함
- 사용자가 직접 말하지 않는 경우가 많음
- 모델이 기본값이나 생략으로 자주 흔들림

### 2. 유지하되 사용 조건을 엄격히 해야 하는 대상

- 의미는 있지만 항상 필요한 것은 아님
- 사용자 요청이 있을 때만 등장해야 함

### 3. 절대 제거하면 안 되는 핵심 대상

- 실제 기능의 본질을 이루는 슬롯
- 오류가 많아도 제거 대신 학습 보강이 필요함

## 함수별 정리

### 1. `search_restaurants`

원래 목적:

- 배달앱 검색 화면처럼 식당 목록을 조회하기 위한 함수
- 검색어, 카테고리, 평점, 영업 여부, 정렬, 페이지네이션을 조합해 다양한 탐색 시나리오를 만들기 위한 설계

파라미터별 역할:

- `query`
  - 식당명, 메뉴명, 키워드 탐색용 핵심 슬롯
- `category`
  - 카테고리 필터용 핵심 슬롯
- `min_rating`
  - "별점 4.5 이상" 같은 명시적 기준 대응용 필터
- `only_open`
  - "지금 영업 중인 곳만" 대응용 필터
- `sort`
  - 관련도순, 평점순, 배달비순 같은 UI 제어값
- `page`
  - 결과 페이지 이동용 제어값
- `page_size`
  - 한 번에 몇 개 보여줄지 정하는 제어값

현재 평가에서의 관찰:

- `query`, `category`, `min_rating`은 검색 의도 자체를 이루는 핵심 슬롯이다.
- `only_open`, `sort`, `page`, `page_size`는 보조 제어 슬롯인데 멀티턴에서 자주 흔들린다.
- 특히 `page_size`는 사용자가 "3개만", "5개만"이라고 말할 때는 의미가 있지만, 그 외에는 기본값 `20`으로 회귀하는 경향이 강했다.
- `page`도 검색 기능상 있으면 좋지만, 실제 데이터셋에서 사용 빈도와 중요도 대비 오류 유발 비중이 컸다.
- `sort`와 `only_open`은 의미는 분명하지만, 현재 데이터셋에서는 이전 턴 상태가 섞여 들어오거나 기본값처럼 취급되는 문제가 있었다.
- `min_rating`는 유지 가치가 있지만, 모호한 "평점 높은 곳" 요청이 임의의 숫자 기준으로 번역되는 현상은 제한할 필요가 있다.

정리:

- 유지 필요: `query`, `category`
- 유지하되 사용 조건 강화 필요: `min_rating`, `only_open`, `sort`
- 축소 또는 사용 조건 제한 검토: `page`, `page_size`

실무적 해석:

- 이 함수는 원래 "실제 검색 UI를 최대한 닮게" 만들려다 보니 파라미터가 많아졌다.
- 하지만 현재 목적이 멀티턴 function calling 평가라면, `page/page_size`는 검색 이해력보다 exact match 실패만 키우는 경향이 강하다.
- `only_open`, `sort`, `min_rating`는 완전 제거보다는 "사용자 발화에 근거가 있을 때만 등장"하도록 제한하는 것이 맞다.

### 2. `get_restaurant_detail`

원래 목적:

- 특정 식당 상세 화면을 열고 메뉴 목록과 영업 여부를 확인하기 위한 함수

파라미터별 역할:

- `restaurant_id`
  - 상세 조회의 핵심 키
- `at`
  - 특정 시점 기준 영업 여부 확인용 보조 슬롯

현재 평가에서의 관찰:

- `restaurant_id`는 당연히 필수이며 의미가 분명하다.
- `at`는 기능적으로는 이해 가능하지만 실제 데이터에서는 거의 쓰이지 않는다.
- 보고서에서도 `at` 누락은 1건뿐이지만, 설계 의도 대비 활용도가 매우 낮다.

정리:

- 유지 필요: `restaurant_id`
- 축소 후보: `at`

실무적 해석:

- `at`는 "현재 시각이 아닌 특정 시각 기준 확인"이라는 시뮬레이션 목적에는 쓸 수 있지만, 일반적인 주문 흐름 데이터셋에서는 거의 등장하지 않는다.

### 3. `upsert_address`

원래 목적:

- 배송지 신규 등록과 기존 주소 수정을 하나의 함수로 처리

파라미터별 역할:

- `user_id`
  - 주소 소유자 식별용 핵심 슬롯
- `address_id`
  - 수정 대상 주소 식별용 상태 슬롯
- `recipient_name`, `phone`, `line1`
  - 실제 배송 가능한 주소 생성을 위한 핵심 슬롯
- `line2`
  - 상세 위치 정보
- `is_default`
  - 기본 배송지 지정 여부
- `gate_password`
  - 공동현관 접근 정보
- `delivery_note`
  - 주소 저장 시 함께 메모를 보관하려는 부가 슬롯

현재 평가에서의 관찰:

- `recipient_name`, `phone`, `line1`, `line2`는 주소 엔터티 자체를 만드는 데 의미가 크다.
- `address_id`도 수정 흐름에는 분명히 필요하다.
- 하지만 `is_default`는 사용자가 명시하지 않아도 시스템 내부 기본값으로 처리 가능한 경우가 많아, 예측이 `false`를 임의 삽입하는 원인이 된다.
- `delivery_note`는 주소 등록 단계에 둘 수도 있지만, 실제 주문마다 달라질 수 있는 메모라서 `prepare_checkout`와 역할이 겹친다.
- `gate_password`는 현실적인 값이지만 등장 빈도는 낮고, 없다고 주문 흐름이 깨지지는 않는다.

정리:

- 유지 필요: `user_id`, `address_id`, `recipient_name`, `phone`, `line1`, `line2`
- 유지하되 명시적 요청 때만 쓰도록 제한 권장: `is_default`
- 단계 재배치 검토: `delivery_note`
- 유지 가능하지만 데이터셋 비중 축소 가능: `gate_password`

실무적 해석:

- `upsert_address`는 "주소록 관리"와 "주문 메모 관리"를 한 함수에 일부 섞어 둔 면이 있다.
- 지금 오류 패턴은 이 혼합 설계가 모델에게 불필요한 생성 자유도를 준 결과로 볼 수 있다.

### 4. `list_addresses`

원래 목적:

- 저장된 주소 목록을 보여주고, 이후 `address_id`를 선택하게 하는 함수

현재 평가에서의 관찰:

- 단순하고 과설계 요소가 거의 없다.

정리:

- 현재 구조 유지가 적절하다.

### 5. `add_to_cart`

원래 목적:

- 메뉴를 장바구니에 담기 위한 핵심 액션

파라미터별 역할:

- `user_id`, `restaurant_id`, `menu_item_id`, `quantity`
  - 장바구니 생성과 추가의 핵심 슬롯
- `special_request`
  - 메뉴별 요청사항 보존 슬롯

현재 평가에서의 관찰:

- 핵심 구조는 매우 타당하다.
- 문제는 `special_request`가 제거 대상이 아니라 문자열 보존 실패의 중심이라는 점이다.
- 빈 문자열 `""`을 불필요하게 넣는 경우는 설계보다는 optional handling 문제에 가깝다.

정리:

- 전체 유지 권장
- 다만 `special_request`는 "요약 금지, 원문 보존" 규칙이 필요하다.

### 6. `update_cart_item`

원래 목적:

- 이미 담긴 항목의 수량이나 요청사항을 수정

파라미터별 역할:

- `user_id`, `cart_item_id`
  - 수정 대상 식별용 핵심 슬롯
- `quantity`
  - 수량 수정값
- `special_request`
  - 누적 보존되어야 하는 요청사항 슬롯

현재 평가에서의 관찰:

- 구조 자체는 맞다.
- 다만 모델이 `special_request`를 전체 교체가 아니라 부분 수정처럼 다뤄 누적 보존에 실패한다.

정리:

- 전체 유지 권장
- 문제는 스키마보다 데이터 생성과 학습 규약이다.

### 7. `remove_cart_items`

원래 목적:

- 장바구니에서 특정 row를 삭제

현재 평가에서의 관찰:

- 스키마는 간결하고 적절하다.
- 실패가 나면 주로 row 선택 오류이지, 파라미터 설계 과잉 때문은 아니다.

정리:

- 현재 구조 유지가 적절하다.

### 8. `prepare_checkout`

원래 목적:

- 결제 직전 스냅샷 생성
- 카트와 배송지를 결합해 최종 주문 데이터를 확정하기 위한 함수

파라미터별 역할:

- `user_id`, `address_id`
  - 주문 준비의 핵심 연결 슬롯
- `delivery_note`
  - 주문 단위 배달 요청 메모

현재 평가에서의 관찰:

- 함수 구조는 자연스럽다.
- `delivery_note`는 주문 시점 메모로서 위치가 적절하다.
- 다만 exact match 평가에서는 문장부호, 어투, 축약 때문에 실패가 많이 난다.

정리:

- 전체 유지 권장
- 제거 대상이 아니라 원문 보존 강화 대상이다.

### 9. `place_order`

원래 목적:

- `prepare_checkout`에서 만든 스냅샷을 바탕으로 주문을 최종 확정

현재 평가에서의 관찰:

- `snapshot`, `payment_method` 모두 기능적으로 핵심이다.
- 설계 과잉보다 상태 전달의 정확성이 더 중요하다.

정리:

- 현재 구조 유지가 적절하다.

### 10. `get_order_status`

원래 목적:

- 주문 상태와 결제 상태를 조회

파라미터별 역할:

- `user_id`
  - 주문 소유자 식별용 핵심 슬롯
- `order_id`
  - 조회 대상 주문 식별용 핵심 슬롯

현재 평가에서의 관찰:

- 구조가 단순하고 과설계 요소가 거의 없다.
- 실패가 나면 주로 잘못된 주문을 집는 문제이지, 파라미터 설계 자체의 과잉 때문은 아니다.

정리:

- 현재 구조 유지가 적절하다.

## 이번 관점에서 본 우선순위

### A. 가장 먼저 재설계 검토할 것

1. `search_restaurants.page`
2. `search_restaurants.page_size`
3. `get_restaurant_detail.at`
4. `upsert_address.is_default`

### B. 유지하되 노출 조건을 줄일 것

1. `search_restaurants.sort`
2. `search_restaurants.only_open`
3. `search_restaurants.min_rating`

### C. 유지하고 학습을 보강할 것

1. `query`
2. `category`
3. `special_request`
4. `delivery_note`
5. 각종 ID와 `quantity`

## 최종 판단

이번 목적이 "초기 스키마 정의가 과했는지"를 찾는 것이라면, 핵심 자연어 슬롯보다 기본값성 제어 슬롯을 먼저 의심하는 것이 맞다.

특히 다음 파라미터들은 현재 구조에서 아래 문제를 동시에 가진다.

- 없어도 대부분의 대화는 성립한다.
- 모델이 자주 생략하거나 기본값으로 회귀한다.
- exact match 평가에서는 오답을 크게 늘린다.

해당 파라미터:

- `page`
- `page_size`
- `at`
- `is_default`

반대로 `special_request`와 `delivery_note`는 오류가 많더라도 "쓸모없는 파라미터"가 아니라, 제거하면 안 되는 핵심 슬롯이다. 이 둘은 스키마 축소 대상이 아니라 보존 규칙 강화 대상이다.

## 요약

현재 함수 스키마의 문제는 모든 파라미터가 많은 데 있지 않다. 핵심 의도 슬롯과 기본값성 제어 슬롯이 같은 수준으로 열려 있다는 점이 더 큰 문제다.

요약하면 다음처럼 보는 것이 적절하다.

- 바로 줄이거나 제거를 검토할 것
  - `search_restaurants.page`
  - `search_restaurants.page_size`
  - `get_restaurant_detail.at`
  - `upsert_address.is_default`
- 유지하되 "명시적 요청 시에만 사용"으로 좁힐 것
  - `search_restaurants.sort`
  - `search_restaurants.only_open`
  - `search_restaurants.min_rating`
- 유지하고 학습/평가 규약을 보강할 것
  - `query`
  - `category`
  - `special_request`
  - `delivery_note`
  - 각종 ID와 `quantity`
