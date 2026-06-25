# `LoRA 100` vs `LoRA 500` 멀티턴 하락 가설 메모

작성일: 2026-03-20

## 문서 역할

`01_multiturn_100_vs_500_discovery.md`에서 분리한 가설 보관용 메모다.

이 문서는 최종 원인 분석 문서가 아니다. 나중에 `2_root_cause/`의 문서들과 함께 가설을 다시 정리하기 위한 재료로 둔다.

## 가설 후보

### 1. `500셋`은 더 좋은 멀티턴 분포가 아니라 짧고 반복적인 흐름을 많이 추가했을 수 있다

기존 분석에서 관찰한 차이:

- 허브 100셋 평균 tool call: `5.82회`
- 로컬 500셋 평균 tool call: `3.84회`
- 허브 100셋 평균 user 발화: `8.16회`
- 로컬 500셋 평균 user 발화: `4.95회`

또 로컬 500셋은 500개 대화에 대해 tool sequence가 179종뿐이었고, 321개가 이미 본 sequence의 반복이었다.

따라서 데이터 수는 늘었지만 멀티턴 정책 분기 수는 충분히 늘지 않았을 가능성이 있다.

### 2. `LoRA 500`은 tool-call 경로 진입 안정성이 이미 약했을 수 있다

Tool Call Level 비교에서 `LoRA 500`은 `LoRA 100`보다 일부 선행 지표가 낮았다.

- `relevance_detection_acc`: `86.51% -> 84.47%`
- `required_params_acc`: `99.38% -> 98.67%`
- `argument_type_acc`: `96.89% -> 94.59%`

멀티턴 지표는 턴 pass/fail 집계이므로, 초반 tool/no-tool 판단이나 필수 인자 처리 약화가 턴 실패 증가로 이어졌을 가능성이 있다.

### 3. `500셋`은 end-to-end 주문 완료보다 중간 단계 흐름 비중이 높았을 수 있다

허브 100셋은 `place_order`, `prepare_checkout`, `list_addresses`, `add_to_cart` 같은 후반 주문 완료 흐름 비중이 더 높았다.

반대로 로컬 500셋은 `search_restaurants`, `get_restaurant_detail`, 장바구니 진입, 중간 종료 흐름 비중이 높았을 수 있다.

이 경우 모델은 한 단계씩 호출하는 패턴은 배워도, 대화 전체를 끝까지 안정적으로 이어가는 능력은 충분히 강화하지 못했을 수 있다.

### 4. no-call과 순수 unsupported 학습 신호가 부족했을 수 있다

두 데이터셋 모두 순수 no-call 대화는 거의 없었다.

로컬 500셋에는 unsupported 응답이 등장하지만, 대부분 tool 흐름 중간에 삽입된 형태였다. 이 경우 모델은 unsupported를 독립적인 비호출 패턴이 아니라 잠깐의 일반 응답 후 tool flow로 돌아가는 패턴으로 배웠을 수 있다.

### 5. `search_restaurants`의 인자 분포가 단조로웠을 수 있다

로컬 500셋에서 `search_restaurants`는 자주 등장했지만, 일부 인자 분포가 단조로웠을 가능성이 있다.

- `only_open`은 사실상 `true` 중심
- `sort`는 거의 `rating`
- `page`는 대부분 `1`
- `page_size`도 대부분 `20`

이 경우 모델은 전형적인 호출 형식은 익혀도, 애매한 검색 의도, 여러 후보 중 다시 좁히기, 이전 턴 제약을 반영한 재검색 같은 멀티턴 분기는 충분히 배우지 못했을 수 있다.

## 나중에 확인할 것

- 고정된 동일 eval 세트에서 `100 vs 500`을 다시 비교했는가?
- 데이터 양 효과와 데이터 분포 효과를 분리했는가?
- end-to-end 주문 완료, 분기 후 복귀, 필수 슬롯 재회수, 순수 no-call, 순수 unsupported 샘플 비중을 확인했는가?
- `search_restaurants`의 `sort`, `only_open`, `page`, `page_size`, `min_rating` 분포를 실제 데이터에서 다시 집계했는가?
