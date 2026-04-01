# argument_value 실패 사례 보고서

작성일: 2026-03-24

## 문서 역할

이 문서는 `argument_value` 실패 분석의 기준 문서다.

- `argument_value` 전체 문제 지도와 우선순위를 정리한다.
- 대표 실패 축과 우선 수정 대상을 정리한다.
- 이전의 `argument_value_failures_with_dialogue.md`가 맡고 있던 상세 사례 역할은 이 문서의 대표 사례 섹션과 원본 평가 산출물 참조로 통합한다.

원본 turn 단위 상세 산출물은 아래 경로를 기준으로 다시 확인할 수 있다.

- `/home/cwj/llm-project/eval_output/qwen-2.5-7b-function-calling_batch2_data_v2`

## 분석 기준

- 기준 실험: `eval_output_500_32batch_10ep_before`
- 기준 문서: `docs/model_comparison_multiway.md`
- 기준 지표: `argument_value_acc = 70.72% (128 / 181)`
- 실패 건수: `53` step
- 분석 범위: `argument_value_acc` 분모에 포함된 step만 대상
  - 즉 relevance / format / function / hallucination / required / type 단계는 통과했지만 마지막 값 비교에서 실패한 케이스만 포함

## 한줄 결론

`argument_value_acc`의 병목은 함수 선택이 아니라 값 보존이다. 특히 검색 필터 재구성, `special_request` 누적 보존, `delivery_note` 비변형 복제가 현재 성능을 가장 많이 깎고 있다.

## 핵심 요약

- 가장 큰 실패 축은 `search_restaurants` 값 복원 오류다.
  - 총 53건 중 23건
  - 주로 `query`, `page_size`, `only_open`, `sort`, `category`가 틀린다.
- 주문/장바구니 계열에서는 `special_request` 보존 실패가 가장 많다.
  - `special_request` 관련 실패 15건
  - 이전 요청을 덮어쓰거나 축약 표현으로 바꾸면서 exact match가 깨진다.
- 결제/주소 단계에서는 `delivery_note`가 취약하다.
  - `delivery_note` 관련 실패 10건
  - 불필요한 메모를 추가하거나, 문장부호/어투를 정규화하면서 exact match가 깨진다.
- 난이도가 높은 케이스는 대부분 두 종류다.
  - 대화 중간에 검색 의도/카테고리/정렬이 자주 바뀌는 경우
  - 장바구니 수정이 누적되어 기존 옵션과 신규 옵션을 함께 보존해야 하는 경우

## 우선 수정 권장 샘플

### 1. sample_0002: 검색 조건 전환 복원 실패가 가장 전형적으로 드러남

- 파일: `eval_data/samples/sample_0002.txt`
- 이유
  - `query`, `sort`, `only_open`, `page_size`가 연속으로 흔들린다.
  - 검색 계열 실패 패턴 대부분이 한 대화 안에 압축돼 있다.
- 우선 활용 방안
  - 멀티턴 검색 전환 보강 데이터의 대표 샘플로 삼기 좋다.

### 2. sample_0015: 실제 오작동 위험이 큰 cart item 식별 실패가 포함됨

- 파일: `eval_data/samples/sample_0015.txt`
- 이유
  - `special_request` 보존 실패뿐 아니라 `remove_cart_items`에서 잘못된 UUID를 선택한다.
  - 단순 exact match 민감도 문제가 아니라 실제 기능 오작동 위험이 있다.
- 우선 활용 방안
  - 장바구니 row 추적 학습 샘플 보강의 우선순위 1순위 후보로 적합하다.

### 3. sample_0028: 생략 가능해 보이는 필드 누락이 한 번에 드러남

- 파일: `eval_data/samples/sample_0028.txt`
- 이유
  - `min_rating`, `page`, `page_size`, `at`, `is_default`, `delivery_note` 마침표까지 폭넓게 실패한다.
  - 현재 모델이 “의미상 같으면 생략 가능”하게 처리하는 습관을 가장 잘 보여준다.
- 우선 활용 방안
  - exact match 규약을 모델에 주입하는 보정 데이터의 대표 사례로 적합하다.

### 4. sample_0029: 불필요한 필드 추가와 빈 문자열 삽입이 동시에 발생함

- 파일: `eval_data/samples/sample_0029.txt`
- 이유
  - `special_request=""`, `delivery_note`, `is_default=false` 같은 불필요 값 생성이 보인다.
  - “아는 필드는 채워 넣고 싶어 하는” 과잉 복원 성향이 드러난다.
- 우선 활용 방안
  - optional field 최소화 규칙을 학습시키는 반례 데이터로 쓰기 좋다.

### 5. sample_0030: 다중 아이템 장바구니 상태 추적이 무너짐

- 파일: `eval_data/samples/sample_0030.txt`
- 이유
  - `menu_item_id`, `cart_item_id`, `quantity`, `delivery_note`가 연쇄적으로 틀린다.
  - 다중 item 상태 추적과 후속 수정의 약점을 가장 명확하게 보여준다.
- 우선 활용 방안
  - 멀티아이템 주문 수정 시나리오의 난도 높은 검증 케이스로 유지할 가치가 크다.

### 6. sample_0038: noisy self-correction에서 최신 의도 추적이 실패함

- 파일: `eval_data/samples/sample_0038.txt`
- 이유
  - `피자 -> 막국수` 수정 발화에서 최신 query를 놓친다.
  - 주소 단계에서는 완전히 다른 주소 엔터티로 덮어쓴다.
- 우선 활용 방안
  - noisy user 샘플을 유지하되, 최종 의도 확정 전략을 강화하는 학습 샘플 보강이 필요하다.

## 파라미터별 실패 빈도

| 파라미터 | 실패 수 | 관찰 |
| --- | ---: | --- |
| `special_request` | 15 | 누적 옵션 일부 소실, 표현 정규화, 다른 항목 요청과 혼동 |
| `delivery_note` | 10 | 문장부호 차이, 불필요한 메모 추가, 일부 요청 누락 |
| `page_size` | 9 | 사용자가 `3개/5개`를 말했는데 기본값 `20`으로 회귀 |
| `query` | 7 | 검색어 누락, 어순 변경, 다른 키워드로 치환 |
| `only_open` | 6 | `false/미지정`이 `true`로 바뀌거나 반대로 희석 |
| `sort` | 6 | `relevance`와 `rating` 혼동 |
| `category` | 6 | 카테고리 누락 또는 query/category 슬롯 뒤바뀜 |

## 함수별 실패 빈도

| 함수 | 실패 수 | 핵심 원인 |
| --- | ---: | --- |
| `search_restaurants` | 23 | 검색 조건 슬롯 누락, 기본값 회귀, 이전 턴 조건 간섭 |
| `add_to_cart` | 9 | `special_request` 축약, 메뉴/수량 매핑 오류 |
| `update_cart_item` | 8 | 누적 요청 보존 실패, 대상 cart item 혼동 |
| `upsert_address` | 6 | 기존 주소 오인, `delivery_note/is_default` 임의 추가 |
| `prepare_checkout` | 5 | 메모 문장 정규화로 exact match 실패 |
| `remove_cart_items` | 1 | 잘못된 `cart_item_id` 선택 |
| `get_restaurant_detail` | 1 | 시간 기준 `at` 누락 |

## 대표 실패 사례

이 섹션은 이전 상세 원장에서 핵심적인 패턴만 추려 남긴다.
전체 turn-by-turn 비교가 다시 필요하면 평가 산출물 원본을 참고한다.

### 1. 검색어가 빠지고 이전 필터가 끼어드는 패턴

- 샘플: `eval_data/samples/sample_0001.txt`
- 대화 흐름: 한식 검색 -> 카페 브런치 검색 -> 중식 2페이지 -> 야식 -> 떡볶이 검색
- 실패 턴
  - turn 1: `query="브런치"` 누락
  - turn 2: `page_size=5`를 `20`으로 되돌리고, `only_open=true`를 불필요하게 추가
- 해석
  - 검색 intent 자체는 맞췄지만, 사용자가 새로 준 검색어와 페이지 조건을 끝까지 붙들지 못했다.
  - 특히 직전 턴의 `only_open` 상태가 다음 턴으로 새어 들어가는 현상이 보인다.

### 2. 카테고리 전환이 잦을 때 `sort/only_open/page_size`가 흔들리는 패턴

- 샘플: `eval_data/samples/sample_0002.txt`
- 대화 흐름: 한식 -> 국밥 재검색 -> 중식 -> 초밥 -> 분식 -> 디저트 카페 -> 치킨 야식 -> 한우
- 실패 턴
  - turn 1: `query="국밥"` 누락
  - turn 2: `sort=relevance`를 `rating`으로 변경
  - turn 3: `only_open=false`를 `true`로 바꾸고 불필요한 `min_rating=null` 생성
  - turn 5: `only_open=false`, `page_size=3`, `sort=relevance`를 모두 놓침
- 해석
  - 검색 도메인은 유지하지만, 세부 필터가 턴마다 재조립되지 않고 모델 내부 default로 재설정된다.
  - "카테고리 전환 + 검색어 + 정렬 + 페이지 제한"이 한 번에 들어오면 마지막 두 슬롯부터 무너지는 경향이 강하다.

### 3. `search_restaurants`에서 `query`와 `category` 슬롯이 뒤바뀌는 패턴

- 샘플: `eval_data/samples/sample_0003.txt`, `sample_0005.txt`, `sample_0006.txt`
- 대표 오류
  - `category="카페"` 누락 + `sort=relevance`를 `rating`으로 변경
  - `category="분식"`를 `null`로 바꾸고 `only_open/min_rating`에 `null`을 명시적으로 삽입
  - `query="초밥"` 대신 `category="초밥"`로 넣고 정작 `query`는 `null`
- 해석
  - 자유형 자연어 키워드를 `query`에 넣어야 할지, 카테고리 슬롯에 넣어야 할지 헷갈리는 현상이다.
  - 특히 음식명 자체가 카테고리처럼 보일 때 슬롯 선택이 흔들린다.

### 4. 장바구니 수정에서 `special_request` 누적 보존에 실패

- 샘플: `eval_data/samples/sample_0011.txt`, `sample_0012.txt`, `sample_0013.txt`, `sample_0015.txt`
- 대표 오류
  - 기존 요청 `고수 빼고, 얼얼함 약하게`를 잃고 `매운맛 2단계`만 남김
  - 기존 요청 `고수 빼고 당면 추가`를 잃고 `매운맛 약하게`만 남김
  - `고수 빼주세요, 소고기 많이 넣어주세요`를 표현만 바꿔 재작성
  - `소면 추가 유지`를 놓치고 `고수 넣고, 버섯 많이`만 남김
- 해석
  - update류 액션을 "변경사항만 덮어쓰기"로 이해해, 누적되어야 할 옵션 전체를 재구성하지 못한다.
  - exact match 관점에서는 의미가 비슷한 paraphrase도 모두 실패로 잡히므로, 현재 모델은 `special_request`를 보존형 슬롯이 아니라 요약형 자연어로 취급하는 경향이 있다.

### 5. 아이템 식별자 선택 실패는 실제 주문 오작동 위험이 큼

- 샘플: `eval_data/samples/sample_0015.txt`, `sample_0030.txt`
- 대표 오류
  - `remove_cart_items`에서 제거해야 할 `cart_item_ids`가 완전히 다른 UUID로 호출됨
  - `update_cart_item`에서 `cart_item_id`, `menu_item_id`, `quantity`가 동시에 어긋남
- 해석
  - 이 패턴은 단순 문구 mismatch보다 위험도가 높다.
  - 사용자가 어떤 항목을 수정/삭제하려는지 추적하지 못하고, 장바구니 내 다른 줄(item row)로 잘못 결합한다.

### 6. 결제 단계에서는 `delivery_note`를 "정리된 문장"으로 다시 쓰는 습관이 문제

- 샘플: `eval_data/samples/sample_0023.txt`, `sample_0024.txt`, `sample_0028.txt`, `sample_0036.txt`, `sample_0037.txt`
- 대표 오류
  - `일회용 수저는 제외해 주세요` -> `일회용 수저 제외`
  - `문 앞에 두고 초인종 누르지 말아주세요.` -> 마침표 제거
  - `문 앞에 두고 벨 눌러주세요` -> 마침표 추가
  - `파란 문 앞에 두고 초인종 누르지 마세요.` -> 마침표 제거
- 해석
  - 의미는 유지되더라도 exact match 기준에서는 전부 실패다.
  - `delivery_note`는 자연어 생성이 아니라 문자열 보존 문제로 봐야 하며, 모델은 현재 이를 "예쁘게 다듬어도 되는 텍스트"로 처리하고 있다.

### 7. 기본값이 있는 필드도 GT에는 명시돼 있으면 그대로 복원해야 한다

- 샘플: `eval_data/samples/sample_0028.txt`, `sample_0029.txt`
- 대표 오류
  - `page`, `page_size`, `min_rating`를 통째로 생략
  - `get_restaurant_detail`의 `at` 누락
  - `is_default=true` 누락
- 해석
  - 스키마 default가 있거나 생략 가능하더라도, 현재 평가에서는 GT와 exact match가 필요하다.
  - 모델은 "의미상 같으면 생략 가능"이라고 판단하지만, 이 지표에서는 오답이다.

### 8. 불필요한 필드를 임의로 추가하는 패턴

- 샘플: `eval_data/samples/sample_0022.txt`, `sample_0029.txt`, `sample_0039.txt`
- 대표 오류
  - 주소 수정 시 사용자가 말하지 않은 `delivery_note`를 추가
  - 주소 등록 시 `is_default=false`를 임의로 추가
  - 저장 주소 선택 턴에서 문 앞 메모를 먼저 넣어버림
- 해석
  - hallucination 단계는 통과했지만, "스키마에 있는 합법적 필드"를 불필요하게 추가하는 값 오류다.
  - 즉 스키마 위반은 아니지만 사용자 의도 위반이다.

### 9. 잡음이 많은 자기 수정 발화에서 최신 의도를 놓친다

- 샘플: `eval_data/samples/sample_0037.txt`, `sample_0038.txt`
- 대표 오류
  - `막국수로 변경` 직후에도 이전 `피자` query를 유지
  - `초장 빼고, 김가루 많이` 대신 `곱빼기`만 반영
  - 어제 배송지를 말하는 문맥에서 완전히 다른 주소 UUID/주소 본문으로 덮어씀
- 해석
  - self-correction이 많아질수록 모델이 마지막 확정 의도를 붙잡지 못하고 중간 초안에 끌린다.
  - 주소/장바구니처럼 상태 추적이 필요한 슬롯에서 특히 취약하다.

## 모델 오류와 평가 민감도를 나눠서 볼 필요가 있는 구간

모든 `argument_value_acc` 실패를 같은 무게로 보면 실제 개선 우선순위가 흐려진다. 이번 53건은 크게 세 층위로 나뉜다.

### 1. 실제 기능 오작동 가능성이 큰 실패

- 예: `sample_0015`, `sample_0030`
- 특징
  - 잘못된 `cart_item_id`, `menu_item_id`, `quantity`, `address_id`
  - 사용자가 의도한 객체 자체를 다른 것으로 잡는다.
- 해석
  - 우선적으로 줄여야 하는 실패다.
  - 실제 서비스 품질에 직접 악영향을 준다.

### 2. 사용자 의도는 맞지만 값 보존이 덜 된 실패

- 예: `sample_0001`, `sample_0002`, `sample_0011`, `sample_0012`
- 특징
  - 검색 intent나 수정 intent는 맞지만 일부 필드가 빠지거나 이전 요청이 유실된다.
- 해석
  - 모델의 상태 추적/슬롯 보존 능력 문제다.
  - 학습 데이터 보강과 decoding 규칙 개선으로 줄일 여지가 크다.

### 3. exact match 기준에 특히 민감한 실패

- 예: `sample_0023`, `sample_0024`, `sample_0036`, `sample_0037`
- 특징
  - 문장부호 추가/삭제
  - 표현 정규화
  - 의미는 비슷하지만 문자열이 완전히 같지 않음
- 해석
  - 이 구간은 평가 기준에 민감하다.
  - 다만 현재 목표가 exact match라면 모델도 그 규칙을 맞춰야 하므로 완전히 무시할 수는 없다.
  - 보고 시에는 “실제 오작동”과 분리해서 보는 편이 합리적이다.

## 개선 포인트

1. `search_restaurants` 전용 데이터에서 `query/category/sort/only_open/page/page_size`를 동시에 바꾸는 멀티턴 전환 사례를 더 늘릴 필요가 있다.
2. `special_request`와 `delivery_note`는 "요약 금지, 문자열 보존" 규칙을 명시적으로 학습시켜야 한다.
3. `update_cart_item`과 `remove_cart_items`는 현재 장바구니 상태에서 대상 row를 고르는 훈련 샘플을 늘려야 한다.
4. `page/page_size/at/is_default`처럼 생략 가능해 보이는 필드도 GT에 명시되면 그대로 복제하도록 평가-학습 간 규약을 맞추는 것이 좋다.
5. 자기 수정 발화가 많은 noisy 대화 샘플에서 "최종 의도만 채택"하는 예시를 추가하는 것이 효과적일 가능성이 높다.

## 바로 실행 가능한 보강 데이터 제안

이 문서는 앞으로도 `argument_value` 전체 문제를 추적하는 기준 문서로 유지한다.
다른 문제 축이 생기면 같은 폴더에 별도 해결 문서를 추가하고, 여기에는 전체 문제 지도와 우선순위만 계속 누적한다.

1. 검색 전환형 샘플 20~30개 추가
   - `query/category/sort/only_open/page/page_size`를 2~4턴 동안 계속 바꾸는 구조
2. `special_request` 누적 수정 샘플 20개 이상 추가
   - 기존 요청 유지 + 일부 수정 + 새 요청 추가를 한 턴에서 동시에 요구
3. 멀티아이템 장바구니 수정 샘플 추가
   - `cart_item_id` 선택, 일부 항목만 수량 변경, 다른 항목 삭제를 섞어서 구성
4. `delivery_note` exact copy 샘플 추가
   - 쉼표, 마침표, 슬래시, 존댓말 차이까지 그대로 복제하는 예시 위주
5. noisy self-correction 샘플 추가
   - `A 아니고 B`, `2개 아니고 3개`, `그 집 말고 저 집` 같은 마지막 의도 확정형 발화 중심

## 전체 실패 목록

- `sample_0001.txt` / turn 1 / `search_restaurants` / `query: 브런치 -> <MISSING>`
- `sample_0001.txt` / turn 2 / `search_restaurants` / `only_open: <MISSING> -> true`, `page_size: 5 -> 20`
- `sample_0002.txt` / turn 1 / `search_restaurants` / `query: 국밥 -> <MISSING>`
- `sample_0002.txt` / turn 2 / `search_restaurants` / `sort: relevance -> rating`
- `sample_0002.txt` / turn 3 / `search_restaurants` / `only_open: false -> true`, `min_rating: <MISSING> -> null`
- `sample_0002.txt` / turn 5 / `search_restaurants` / `only_open: false -> true`, `page_size: 3 -> 20`, `sort: relevance -> rating`
- `sample_0003.txt` / turn 2 / `search_restaurants` / `category: 카페 -> <MISSING>`, `sort: relevance -> rating`
- `sample_0003.txt` / turn 3 / `search_restaurants` / `category: 분식 -> null`, `min_rating: <MISSING> -> null`, `only_open: <MISSING> -> null`
- `sample_0004.txt` / turn 3 / `search_restaurants` / `category: 중식 -> <MISSING>`, `sort: relevance -> rating`
- `sample_0004.txt` / turn 4 / `search_restaurants` / `query: 라멘 -> <MISSING>`, `page_size: 5 -> 20`
- `sample_0004.txt` / turn 6 / `search_restaurants` / `query: 디카페인 -> 디카페인 커피`, `only_open: false -> null`
- `sample_0005.txt` / turn 1 / `search_restaurants` / `category: 분식 -> <MISSING>`
- `sample_0005.txt` / turn 2 / `search_restaurants` / `only_open: <MISSING> -> true`
- `sample_0005.txt` / turn 3 / `search_restaurants` / `sort: rating -> relevance`
- `sample_0006.txt` / turn 1 / `search_restaurants` / `query: 초밥 -> null`, `category: <MISSING> -> 초밥`
- `sample_0008.txt` / turn 0 / `search_restaurants` / `query: 국밥 교대역 -> 교대역 국밥`
- `sample_0009.txt` / turn 0 / `search_restaurants` / `category: 일식 -> <MISSING>`, `page_size: 5 -> 20`
- `sample_0011.txt` / turn 3 / `update_cart_item` / `special_request` 누적 요청 일부 소실
- `sample_0012.txt` / turn 2 / `update_cart_item` / `special_request` 누적 요청 일부 소실
- `sample_0013.txt` / turn 1 / `add_to_cart` / `special_request` 표현 재작성으로 exact match 실패
- `sample_0013.txt` / turn 2 / `update_cart_item` / `special_request` 누적 요청 일부 소실
- `sample_0014.txt` / turn 0 / `search_restaurants` / `sort: <MISSING> -> rating`
- `sample_0015.txt` / turn 0 / `search_restaurants` / `page_size: 5 -> 20`
- `sample_0015.txt` / turn 3 / `update_cart_item` / `special_request` 일부 옵션 누락
- `sample_0015.txt` / turn 4 / `remove_cart_items` / 잘못된 `cart_item_ids`
- `sample_0022.txt` / turn 1 / `upsert_address` / 불필요한 `delivery_note` 추가
- `sample_0022.txt` / turn 2 / `update_cart_item` / `special_request` 표현 축약
- `sample_0023.txt` / turn 2 / `prepare_checkout` / `delivery_note` 문장 정규화
- `sample_0024.txt` / turn 3 / `prepare_checkout` / `delivery_note` 마침표 누락
- `sample_0026.txt` / turn 2 / `add_to_cart` / `special_request` 쉼표 제거
- `sample_0026.txt` / turn 3 / `update_cart_item` / 불필요한 `quantity=2` 추가
- `sample_0028.txt` / turn 0 / `search_restaurants` / `min_rating`, `page`, `page_size` 생략
- `sample_0028.txt` / turn 1 / `get_restaurant_detail` / `at` 누락
- `sample_0028.txt` / turn 6 / `upsert_address` / `is_default=true` 누락
- `sample_0028.txt` / turn 7 / `prepare_checkout` / `delivery_note` 마침표 추가
- `sample_0029.txt` / turn 0 / `search_restaurants` / `page`, `page_size` 생략
- `sample_0029.txt` / turn 2 / `add_to_cart` / `special_request: 떡: 밀떡 -> 밀떡`
- `sample_0029.txt` / turn 2 / `add_to_cart` / 불필요한 빈 문자열 `special_request` 추가
- `sample_0029.txt` / turn 3 / `add_to_cart` / `special_request: 얼음 빼주세요 -> 얼음 없음`
- `sample_0029.txt` / turn 5 / `upsert_address` / 불필요한 `delivery_note`, `is_default=false` 추가
- `sample_0030.txt` / turn 2 / `add_to_cart` / `special_request: 매운맛 2단계로 해주세요 -> 매운맛 2단계`
- `sample_0030.txt` / turn 2 / `add_to_cart` / `menu_item_id`, `quantity` 동시 오류
- `sample_0030.txt` / turn 3 / `update_cart_item` / `cart_item_id`, `quantity` 오류와 `special_request=null` 추가
- `sample_0030.txt` / turn 6 / `prepare_checkout` / `delivery_note` 일부 요청 누락
- `sample_0036.txt` / turn 8 / `prepare_checkout` / `delivery_note` 마침표 제거
- `sample_0037.txt` / turn 1 / `search_restaurants` / `page_size: 5 -> 3`
- `sample_0037.txt` / turn 3 / `add_to_cart` / `special_request` 중 일부만 반영
- `sample_0037.txt` / turn 5 / `upsert_address` / `delivery_note` 마침표 제거
- `sample_0038.txt` / turn 1 / `search_restaurants` / `query: 막국수 -> 피자`, `page_size: 5 -> 3`
- `sample_0038.txt` / turn 3 / `add_to_cart` / `special_request` 표현 정규화
- `sample_0038.txt` / turn 5 / `upsert_address` / 주소 UUID와 주소 본문 전체 오인, `delivery_note` 표현 변경, `is_default=false` 추가
- `sample_0039.txt` / turn 5 / `update_cart_item` / `special_request` 일부 요청 누락
- `sample_0039.txt` / turn 7 / `upsert_address` / 불필요한 `delivery_note` 추가

## 결론

현재 `argument_value_acc` 실패는 단순 JSON 형식 문제보다, "값을 얼마나 충실하게 복사/보존하느냐"의 문제에 가깝다. 검색 쪽은 필터 슬롯 유지, 주문 쪽은 누적 요청 보존, 결제 쪽은 자연어 메모의 비변형 복제가 핵심 병목이다. 따라서 다음 개선은 함수 선택보다 값 보존 중심으로 설계하는 것이 효과적이다.
