# `function_matching` 실패 사례 분석

## 문서 역할

`1_eval_discovery`의 네 번째 문서다.

3번 문서에서 tool 호출 여부 자체가 흔들리는 `relevance_detection` 실패를 확인했다. 이 문서에서는 전체 실패 원장 중 tool 호출까지는 들어갔지만 어떤 함수를 호출해야 하는지를 틀린 `function_matching` 실패를 다시 모아 본다.

- 기준 질문: 함수 선택 실패는 모두 모델 오류인가, 아니면 GT 라벨 문제가 섞여 있는가?
- 이 문서의 범위: `function_matching` 실패 대화의 유형 분류와 라벨 타당성 재검토
- 이 문서에서 하지 않는 것: 최종 수정안 결정
- 다음 문서: `05_argument_value_failure_report.md`

## 기준 자료

- 원장: `eval_output/before_eval_dataset/qwen-2.5-7b-function-calling_batch2_data_v2_before/tool_failures_with_dialogue.md`
- 전체 tool-level 실패: `98`건
- 이 중 `function_matching` 실패: `7`건

이 문서는 위 원장에서 `function_matching` step만 다시 추려 보고, 어떤 함수 선택 오류가 반복되는지와 그중 무엇이 데이터셋 해석 이슈인지 분리해 정리한다.

## 핵심 발견

전체 실패 원장에서 가장 반복적으로 보인 `function_matching` 문제는 검색/상세조회보다도 장바구니, 배송지, 결제 준비 사이의 단계 순서 혼동이었다.

특히 아래 두 축이 중심이었다.

- 배송지 선택, 장바구니 확인, 결제 준비 사이의 선후관계 혼동
- 복합 주문 수정 턴에서 현재 상태 확인보다 곧바로 수정 함수나 후속 단계 함수로 점프

한편 소수 사례에서는 `search_restaurants`와 `get_restaurant_detail`의 경계가 흔들리는 경우도 남아 있었다.

## 분류 요약

| 유형 | 판정 | 대표 사례 | 핵심 의미 |
| --- | --- | --- | --- |
| 배송지/장바구니/결제 준비 단계 순서 혼동 | 모델 오류 | `conv=24`, `conv=29`, `conv=32` | `list_addresses`, `get_cart`, `prepare_checkout` 순서를 섞음 |
| 상태 확인 없이 수정 함수로 점프 | 모델 오류 | `conv=27`, `conv=29`, `conv=32` | 현재 cart 확인보다 `add_to_cart` / `update_cart_item`로 너무 빨리 감 |
| 검색/상세 조회 경계 혼동 | 모델 오류 | `conv=12`, `conv=52` | 새 검색이 필요한데 상세 조회로 점프하거나, 반대로 상세 조회를 검색으로 후퇴 |
| 데이터셋 해석 이슈 가능성 | 제한적 검토 필요 | 일부 상세 조회 케이스 | 식당명만으로 상세 조회를 바로 요구하는 라벨은 별도 재검토 여지가 있음 |

## 대표 패턴

### 1. 배송지, 장바구니, 결제 준비 단계 순서 혼동

대표 사례:

- `conv=24 turn=0 step=0`: 배송지를 바꾸고 요청사항을 반영한 뒤 결제 준비를 원했는데, GT는 `list_addresses`를 먼저 요구했고 모델은 `get_cart`를 호출했다.
- `conv=28 turn=2 step=0`: 이미 주소 수정이 끝난 상태에서 GT는 `prepare_checkout`였지만 모델은 다시 `get_cart`로 후퇴했다.
- `conv=29 turn=3 step=0`: 결제 준비 후 추가 요청을 합쳐 처리해야 하는 턴에서 GT는 `prepare_checkout`였지만 모델은 `update_cart_item`으로 점프했다.

판단:

- 이 축은 현재 상태를 먼저 확인할지, 배송지를 먼저 고를지, 결제 준비로 넘어갈지를 안정적으로 정하지 못한 문제다.
- 대부분은 GT가 요구하는 단계 순서가 자연스럽고, 모델이 선후관계를 섞은 경우로 보는 편이 적절하다.

### 2. 상태 확인 없이 수정 함수로 너무 빨리 점프

대표 사례:

- `conv=27 turn=0 step=1`: GT는 `get_cart`로 현재 장바구니를 확인해야 했지만 모델은 `add_to_cart`로 바로 진입했다.
- `conv=32 turn=3 step=0`: GT는 `get_cart`로 현재 장바구니를 다시 읽어야 했지만 모델은 `update_cart_item`으로 바로 수량 수정을 시도했다.
- `conv=29 turn=3 step=0`: 결제 준비와 추가 요청을 함께 처리해야 하는 턴에서 장바구니 수정 함수 하나로 축약했다.

판단:

- 이 범주는 복합 턴에서 "무엇을 먼저 확인해야 하는가"보다 "바로 수정해도 된다"는 쪽으로 과감하게 점프하는 문제다.
- 멀티턴 상태 추적과 단계 우선순위 결정 실패로 보는 것이 타당하다.

### 3. 검색과 상세 조회 경계 혼동

대표 사례:

- `conv=12 turn=2 step=0`: GT는 `get_restaurant_detail`로 라페스타 피자 메뉴를 보여줘야 했지만 모델은 `search_restaurants`로 후퇴했다.
- `conv=52 turn=2 step=0`: 사용자가 `피자`에서 `막국수`로 의도를 바꿨는데 GT는 `search_restaurants(query="막국수")`였고 모델은 `get_restaurant_detail`로 점프했다.

판단:

- 일부는 새 검색이 필요한지, 이미 후보가 특정됐는지에 대한 경계가 흔들린 케이스다.
- 현재 failure ledger 기준으로는 이 축보다 단계 순서 혼동이 더 자주 반복됐다.

### 4. 데이터셋 해석 이슈는 보조적으로만 남긴다

이전 개별 샘플 검토에서는 식당명만으로 곧바로 상세 조회를 요구하는 라벨이 과한 것 아니냐는 의문도 있었다. 다만 현재 문서에서는 전체 실패 원장에서 반복적으로 보이는 패턴을 우선 남긴다. 따라서 데이터셋 해석 이슈는 보조 메모 수준으로만 유지하고, 이 문서의 중심축은 모델의 단계 순서 혼동으로 둔다.

## 이 단계의 판단

`function_matching` 실패는 모두 같은 성격이 아니었다.

이 문서에서 중요한 발견은, 전체 실패 원장을 기준으로 보면 `function_matching` 실패가 무작위가 아니라 특정 단계 순서 혼동에 몰려 있었다는 점이다. 따라서 이후 문서에서는 단순히 실패 수만 보는 것이 아니라, 실패를 아래처럼 나눠야 한다.

- 명확한 단계 순서 혼동
- 현재 상태 확인 없이 수정 함수로 점프한 사례
- 검색/상세 조회 경계 혼동
- 보조적으로만 남는 데이터셋 해석 이슈

## 다음 문서로 넘길 질문

다음 문서에서는 함수 선택은 맞았지만 인자값이 틀린 `argument_value` 실패를 본다.

다음 질문:

- 함수는 맞았는데 어떤 파라미터 값이 자주 틀리는가?
- 단순 exact match 민감도와 실제 기능 오작동 위험을 어떻게 분리할 것인가?
- search filter, 장바구니 요청사항, 배송 메모처럼 보존이 필요한 값이 어디서 깨지는가?

## Appendix. 케이스 판정 요약

| 사례 | 판정 | 메모 |
| --- | --- | --- |
| `conv=12 turn=2` | 모델 오류 | 상세 조회가 필요한데 `search_restaurants`로 후퇴 |
| `conv=24 turn=0 step=0` | 모델 오류 | `list_addresses` 대신 `get_cart` 호출 |
| `conv=27 turn=0 step=1` | 모델 오류 | `get_cart` 대신 `add_to_cart`로 점프 |
| `conv=28 turn=2 step=0` | 모델 오류 | `prepare_checkout` 대신 `get_cart` 호출 |
| `conv=29 turn=3 step=0` | 모델 오류 | `prepare_checkout` 대신 `update_cart_item` 호출 |
| `conv=32 turn=3 step=0` | 모델 오류 | 현재 장바구니 재확인 없이 `update_cart_item` 호출 |
| `conv=52 turn=2 step=0` | 모델 오류 | 새 검색이 필요한데 `get_restaurant_detail`로 점프 |
