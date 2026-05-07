# `relevance_detection` 실패 사례 분석

## 문서 역할

`1_eval_discovery`의 세 번째 문서다.

2번 문서에서 하이퍼파라미터를 바꿔도 모든 지표가 한 방향으로 개선되지 않는다는 점을 확인했다. 그래서 이 단계에서는 전체 실패 원장인 `tool_failures_with_dialogue.md`를 열어보고, 모델이 현재 턴에서 tool을 호출해야 하는지 text로 응답해야 하는지를 어디서 틀리는지 확인한다.

- 기준 질문: 모델은 어떤 턴에서 tool/no-tool 경계 판단을 틀리는가?
- 이 문서의 범위: `relevance_detection` 실패 유형과 대표 케이스 정리
- 이 문서에서 하지 않는 것: 최종 원인 확정, 수정안 결정
- 다음 문서: `04_function_matching_failure_report.md`

## 기준 자료

- 원장: `eval_output/before_eval_dataset/qwen-2.5-7b-function-calling_batch2_data_v2_before/tool_failures_with_dialogue.md`
- 전체 tool-level 실패: `98`건
- 이 중 `relevance_detection` 실패: `42`건
- 이 문서의 범위: 위 원장에서 `relevance_detection` step만 다시 분류한 결과

## 핵심 발견

`relevance_detection` 실패는 단순 포맷 문제가 아니라, 현재 턴을 `tool`로 처리할지 `text`로 처리할지에 대한 상태 판단 실패였다.

실패는 크게 두 방향으로 나뉘지만, 전체 원장에서 반복적으로 드러난 핵심은 한쪽에 더 쏠려 있었다.

- `missed_tool_call`: tool 호출이 필요한데 text로 응답함
- `spurious_tool_call`: text 응답이 필요한데 tool을 호출함

특히 이 문서에서 우선 남길 문제는 나중에 실제 수정 결정으로 이어진 세 가지다.

- 주문번호가 없는 상태 조회 턴에서 `get_order_status`를 성급하게 호출함
- 조회 가능한 형식이 아닌 주문번호에도 `get_order_status`를 호출함
- 환불, 보상, 버그 신고 같은 policy / unsupported text turn에서도 `get_order_status`를 호출함

반대로 noisy 주문 요청이나 상태 변경 누락 같은 relevance 실패는 문서에 남기되, 이후 fix의 중심축으로 두지는 않는다.

## 실패 유형 분포

| 유형 | 건수 | 의미 |
| --- | ---: | --- |
| `missed_tool_call` | 13 | tool 호출이 필요한 턴에서 text로 멈춤 |
| `spurious_tool_call` | 29 | text 응답이 필요한 턴에서 tool을 호출 |

## 주요 패턴

### 1. 지원 가능한 주문 요청을 불가/민원으로 오판

이 패턴도 relevance 실패에 포함되지만, 이번 문서에서 fix와 직접 연결해 우선 남길 핵심은 아니다. 다만 전체 실패 맥락을 이해하기 위해 보조 패턴으로 남긴다.

대표 예시:

- `sample_0036`: `"치긴 벅고십다 아무거나 빨리"`에서 gold는 `search_restaurants`였지만, 모델은 지원 불가 text로 응답했다.
- `sample_0037`: `"치긴 벅고십다 ㅠㅠ … 짲장묜 배달?"`에서 gold는 `search_restaurants`였지만, 모델은 고객센터 안내 text로 멈췄다.
- `sample_0039`: `"그냥 제일 싼 거 아무거나... 막구수!"`에서 gold는 `search_restaurants`였지만, 모델은 불가/추가 질문 text로 응답했다.

이 패턴은 실제 음식 주문 가능 요청과 noisy unsupported 요청의 경계가 데이터 안에서 충분히 선명하지 않을 수 있다는 가설로 이어진다.

### 2. tool이 필요한 상태 변경을 text로 선행 처리

이 역시 relevance 실패의 한 축이지만, 이번 문서에서 이후 수정안의 중심으로 삼는 케이스는 아니다. 모델이 tool response 없이도 내부 상태를 알고 있는 것처럼 말한다는 점을 보여주는 보조 패턴으로 남긴다.

대표 예시:

- `sample_0036`: 주소 층수 변경 이후 gold는 `add_to_cart`였지만, 모델은 이미 주소가 변경된 것처럼 text로 응답했다.
- `sample_0040`: 주소 선택과 주문 준비가 필요한 턴에서 gold는 `prepare_checkout`였지만, 모델은 장바구니 합계와 주소 설정을 text로 선행 처리했다.
- `sample_0022`: 결제 전 금액 확인에서 gold는 `prepare_checkout`였지만, 모델은 금액 확인을 text로 처리했다.

이 패턴은 모델이 tool response 없이도 내부 상태를 알고 있는 것처럼 말하는 문제와 연결된다.

### 3. text / clarification / policy 턴에서 성급하게 tool 호출

전체 실패 원장에서 가장 반복적으로 드러난 relevance 문제는 이 패턴이었다. 주문번호가 없거나, 주문 상태 조회가 아니라 버그 신고/환불/정책 안내가 핵심인 턴에서 모델이 `get_order_status` 같은 tool을 호출했다.

대표 예시:

- `conv=15 turn=0`: 주문번호 없이 배달 출발 여부를 물었는데, gold는 주문번호 요청 text였고 모델은 `get_order_status`를 호출했다.
- `conv=16 turn=0`: 사용자가 `12345` 같은 짧은 번호를 말했는데, gold는 UUID 형식 주문번호 재요청 text였고 모델은 그대로 `get_order_status(order_id="12345")`를 호출했다.
- `conv=20 turn=0`: 주문번호를 아직 주지 않았는데 모델이 자연어 문장을 `order_id` 자리에 넣어 `get_order_status`를 호출했다.
- `conv=40 turn=0`: 주문번호가 있어도 핵심 요청이 파손, 배상, 환불, 버그 신고, 가격 비교인 턴에서 gold는 정책/안내 text였지만 모델은 `get_order_status`를 호출했다.
- `conv=43 turn=1`: 주문번호가 있어도 라이더 사고 보상 문의가 핵심인데, 모델은 상태 조회 tool로 진입했다.

이 패턴은 `get_order_status` 호출 조건과 policy/clarification text turn 규칙을 더 명확히 해야 한다는 다음 단계 질문으로 이어진다.

## 우선 확인할 대표 케이스

| 케이스 | 핵심 패턴 | 왜 중요한가 |
| --- | --- | --- |
| `conv=15 turn=0` | 주문번호 없는 상태 조회에서 `get_order_status` 과호출 | clarification text turn이 먼저여야 한다는 점을 가장 직접적으로 보여줌 |
| `conv=16 turn=0` | 비-UUID 주문번호 `12345`로 `get_order_status` 호출 | `order_id`는 "있기만 하면 되는 값"이 아니라 조회 가능한 형식이어야 함을 보여줌 |
| `conv=20 turn=0` | 자연어 문장을 `order_id`에 넣어 호출 | 주문번호 요청 turn을 별도 규칙으로 고정해야 함을 보여줌 |
| `conv=40 turn=0` | 정책/민원성 문의인데 `get_order_status` 호출 | policy / unsupported text turn 규칙이 약하다는 점을 보여줌 |
| `conv=43 turn=1` | 보상 문의인데 상태 조회 tool로 진입 | 주문번호가 있어도 핵심 요청이 정책 처리면 text가 먼저여야 함을 보여줌 |

## 이 단계의 판단

이 문서만으로 최종 원인을 확정하지는 않는다. 다만 하이퍼파라미터 튜닝만으로 설명하기 어려운 실제 실패 패턴은 확인됐다.

특히 다음 세 가지는 이후 원인 분석에서 다시 봐야 한다.

- `get_order_status` 호출 조건과 policy/clarification text turn 규칙
- 주문번호 요청 turn을 별도 clarification text turn으로 고정할 필요
- 주문번호가 있어도 정책/민원 요청이면 text를 우선해야 하는 규칙

## 다음 문서로 넘길 질문

`relevance_detection`은 tool 호출 여부 자체의 문제다. 다음 문서에서는 tool 호출까지는 했지만 어떤 함수를 호출해야 하는지를 틀린 `function_matching` 실패를 본다.

다음 질문:

- 함수 선택 실패 중 실제 모델 오류와 데이터 라벨 문제는 어떻게 나뉘는가?
- 대화 안에 필요한 ID가 아직 없는데 GT가 내부 엔터티 매핑을 가정한 케이스가 있는가?
- 함수 경계가 애매해서 모델이 잘못 배웠을 가능성이 있는가?

## Appendix. 전체 케이스 목록

| Case | 샘플 | conversation_id | 실패 수 | missed | spurious | 핵심 메모 |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| 01 | `conv=2 turn=3 step=0` | 2 | 1 | 1 | 0 | 밤 영업 분식 검색이 필요한데 text로 응답 |
| 02 | `conv=5 turn=3 step=0` | 5 | 1 | 1 | 0 | 주문 가능한 noisy 요청을 지원 불가 text로 처리 |
| 03 | `conv=7 turn=4 step=0` | 7 | 1 | 1 | 0 | 막국수 검색이 필요한데 불가/추가질문 text로 멈춤 |
| 04 | `conv=15` | 15 | 1 | 0 | 1 | 주문번호 없는 상태 조회에서 `get_order_status` 과호출 |
| 05 | `conv=16` | 16 | 1 | 0 | 1 | 비-UUID 주문번호 `12345`를 그대로 조회 |
| 06 | `conv=17` | 17 | 1 | 0 | 1 | 주문번호 없이 상태 조회 tool 호출 |
| 07 | `conv=18` | 18 | 1 | 0 | 1 | 짧은 주문번호로 상태 조회 tool 호출 |
| 08 | `conv=19` | 19 | 1 | 0 | 1 | 비정상 주문번호 형식에도 상태 조회 시도 |
| 09 | `conv=20` | 20 | 1 | 0 | 1 | 자연어 문장을 `order_id`에 넣어 호출 |
| 10 | `conv=22` | 22 | 1 | 0 | 1 | `12345` 재확인 없이 상태 조회 시도 |
| 11 | `conv=23` | 23 | 1 | 0 | 1 | UUID 재요청 대신 상태 조회 시도 |
| 12 | `conv=24 turn=0 step=1` | 24 | 1 | 0 | 1 | 배송지 확인 질문이 필요한 text turn에서 `get_cart` 호출 |
| 13 | `conv=26 turn=0 step=1` | 26 | 1 | 0 | 1 | 배송지 선택 질문이 필요한 turn에서 `list_addresses` 호출 |
| 14 | `conv=29 turn=3 step=1` | 29 | 1 | 1 | 0 | `place_order`가 필요한 마무리 단계에서 tool 호출 누락 |
| 15 | `conv=32 turn=4 step=1` | 32 | 1 | 1 | 0 | 주소 등록 단계에서 `upsert_address` 호출 누락 |
| 16 | `conv=32 turn=4 step=2` | 32 | 1 | 1 | 0 | 주소 등록 후 `prepare_checkout` 호출 누락 |
| 17 | `conv=32 turn=4 step=3` | 32 | 1 | 1 | 0 | 결제 완료를 위한 `place_order` 호출 누락 |
| 18 | `conv=33 turn=4 step=1` | 33 | 1 | 1 | 0 | 결제 준비가 필요한 turn을 text로 선행 처리 |
| 19 | `conv=37 turn=5 step=1` | 37 | 1 | 0 | 1 | `place_order` 대신 tool 과호출로 마무리 text turn을 침범 |
| 20 | `conv=40` | 40 | 1 | 0 | 1 | 정책/민원성 문의에서 `get_order_status` 호출 |
| 21 | `conv=41 turn=1` | 41 | 1 | 0 | 1 | 정책 안내가 필요한 흐름에서 상태 조회 tool 호출 |
| 22 | `conv=41 turn=3` | 41 | 1 | 0 | 1 | 보상/민원성 맥락에서 상태 조회 tool 호출 |
| 23 | `conv=42 turn=0 step=0` | 42 | 1 | 0 | 1 | 복합 민원/레시피 문의를 음식 검색으로 오판 |
| 24 | `conv=42 turn=1 step=0` | 42 | 1 | 0 | 1 | 환불/보상 정책 text turn에서 `list_addresses` 호출 |
| 25 | `conv=43 turn=1` | 43 | 1 | 0 | 1 | 보상 문의를 상태 조회로 오판 |
| 26 | `conv=43 turn=2` | 43 | 1 | 0 | 1 | policy turn을 다시 상태 조회로 처리 |
| 27 | `conv=44 turn=0` | 44 | 1 | 0 | 1 | 환불/보상 문의에서 `get_order_status` 호출 |
| 28 | `conv=44 turn=1` | 44 | 1 | 0 | 1 | policy turn 반복 과호출 |
| 29 | `conv=46 turn=0` | 46 | 1 | 0 | 1 | 민원성 문의에서 상태 조회 tool 호출 |
| 30 | `conv=46 turn=1` | 46 | 1 | 0 | 1 | 후속 policy turn에서도 상태 조회 유지 |
| 31 | `conv=47 turn=2` | 47 | 1 | 0 | 1 | 정책/안내 text가 필요한 turn에서 과호출 |
| 32 | `conv=48 turn=0 step=0` | 48 | 1 | 0 | 1 | 민원/사과가 필요한 turn을 음식 검색으로 오판 |
| 33 | `conv=49 turn=0 step=1` | 49 | 1 | 0 | 1 | 상세 조회 text turn 대신 추가 검색 tool 호출 |
| 34 | `conv=49 turn=2 step=2` | 49 | 1 | 0 | 1 | 첫 아이템 추가 후 text 확인 turn에서 `add_to_cart` 재호출 |
| 35 | `conv=49 turn=3 step=1` | 49 | 1 | 1 | 0 | 결제 준비가 필요한 단계에서 tool 호출 누락 |
| 36 | `conv=50 turn=1 step=0` | 50 | 1 | 1 | 0 | 새 검색이 필요한데 `<tool_call>` 미생성 |
| 37 | `conv=50 turn=1 step=1` | 50 | 1 | 1 | 0 | 상세 조회가 필요한데 `<tool_call>` 미생성 |
| 38 | `conv=50 turn=1 step=2` | 50 | 1 | 1 | 0 | 장바구니 추가가 필요한데 `<tool_call>` 미생성 |
| 39 | `conv=51 turn=0 step=1` | 51 | 1 | 0 | 1 | 상세 조회 전 text 안내 turn에서 `get_restaurant_detail` 호출 |
| 40 | `conv=51 turn=2 step=1` | 51 | 1 | 0 | 1 | 장바구니 확인 text turn에서 `add_to_cart` 과호출 |
| 41 | `conv=52 turn=0 step=0` | 52 | 1 | 0 | 1 | 가격/브랜드 비교 문의를 음식 검색으로 오판 |
| 42 | `conv=52 turn=2 step=3` | 52 | 1 | 1 | 0 | 주문 직전 배송지 선택 단계에서 `list_addresses` 호출 누락 |
