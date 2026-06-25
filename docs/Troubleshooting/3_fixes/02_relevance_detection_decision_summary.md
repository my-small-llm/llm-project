# `relevance_detection` 문제 정의 및 해결

작성일: 2026-04-02

## 목적

이 문서는 `relevance_detection` 실패 전체를 다 설명하려는 문서가 아니다.

이 문서의 목적은 아래에 한정된다.

- 실패 사례 중에서 `함수 정의의 모호함`이나 `datagen 규칙 부족`으로 설명 가능한 부분만 정리한다
- 단순한 모델 실수처럼 보이는 케이스는 과하게 원인 확대 해석하지 않는다
- 그래서 실제로 함수 설명과 datagen 규칙을 어디까지 고쳐야 하는지 결정한다

즉 이 문서는 `relevance_detection`의 모든 실패 원인을 다루는 문서가 아니라, `datagen / 함수 정의 관점에서 실제로 고칠 수 있는 원인`만 추린 문서다.

## 문제 요약

이번 `relevance_detection` 실패를 다시 좁혀서 보면, 현재 함수 집합을 유지하는 전제에서 datagen 관점으로 실제로 고칠 수 있는 핵심은 제한적이었다.

이번 문서에서 남기는 핵심은 아래 두 가지다.

- `get_order_status` 호출 조건이 충분히 명시되지 않음
- `policy / unsupported text turn`과 `clarification text turn` 규칙이 충분히 명시되지 않음

즉 이번 문서에서 가장 중요하게 보는 문제는:

- 첫 대화에서 주문번호가 없는 상태 조회 문의를 어떻게 처리할지
- 주문번호가 있더라도 핵심 요청이 환불/보상/버그 신고 같은 정책 처리인 경우를 어떻게 처리할지

가 함수 설명과 datagen 규칙에 충분히 고정되지 않았다는 점이다.

반대로 아래는 이 문서의 중심 원인으로 보지 않는다.

- 단순 missed tool call
- 단순 spurious tool call
- 멀티스텝 전이 실패 중 다수

이들은 많은 경우 GT는 충분히 맞고, `pred` 모델이 순수하게 실수한 케이스로 보는 편이 더 적절했다.

한 줄로 요약하면:

- 이번 문서에서 남길 핵심은 `get_order_status`와 `text turn 규칙`의 정의 부족이다

## 분석 범위

이번 문서에서는 아래 같은 케이스는 핵심 분석 대상에서 제외한다.

- `search_restaurants`를 호출하면 되는 단순 검색 요청인데 모델이 그냥 놓친 경우
- `place_order`나 `prepare_checkout`에서 상태를 제대로 못 따라간 순수 실행 실수
- 사용자가 비교적 분명하게 말했는데 모델이 임의로 잘못 호출한 단순 과호출

이런 경우는 직접적으로는 모델 성능 문제로 보는 편이 더 자연스럽다.

반면 아래 경우는 함수 정의나 규칙 부족과 직접 연결된다고 판단했다.

- `get_order_status`에서 `order_id` 전제조건과 정책 처리 경계가 약한 경우
- 주문번호 요청, 정책 안내, clarification text를 먼저 내야 하는 턴의 기준이 약한 경우
- 주문번호가 있어도 핵심 요청이 상태 조회가 아니라 정책 처리인 경우를 text로 우선 처리해야 한다는 규칙이 약한 경우

## 케이스 분류

이 문서에서 실제로 남기는 핵심 분류는 아래와 같다.

### A. `get_order_status` 호출 경계 불명확

`get_order_status`는 아래 조건을 강하게 설명하지 못했다.

- 실제 상태 조회일 때만 호출
- `order_id`가 있어야 호출
- 환불/보상/버그 신고는 이 함수로 처리하지 않음

그 결과 아래 같은 혼선이 반복됐다.

- 주문번호가 없는데도 호출
- `12345` 같은 비-UUID를 주문 ID로 호출
- 주문번호가 있어도 핵심 요청이 환불/보상인데 상태 조회로 진입

### B. clarification text turn 규칙 부족

모델이 성급하게 tool을 호출한 모든 케이스를 함수 정의 문제로 보기는 어렵다.

하지만 아래처럼 `먼저 물어봐야 하는 턴`에 대한 규칙이 약한 부분은 datagen 문제로 볼 수 있다.

- 주문번호가 없어서 먼저 주문번호를 요청해야 하는 턴
- 사용자가 요구를 뒤섞거나 정정해서 마지막 의도가 아직 확정되지 않은 턴
- 어떤 기준으로 고를지 아직 정해지지 않아 clarification이 먼저 필요한 턴

즉 여기서의 핵심은:

- `tool vs text`만이 아니라
- `clarification text`라는 별도 턴 유형을 datagen에서 더 강하게 고정해야 한다는 점이다

### C. policy / unsupported text turn 규칙 부족

아래 요청은 tool 호출이 아니라 정책/안내 text가 먼저 와야 한다.

- 환불 요청
- 보상 요청
- 버그 신고
- 타사 비교
- 레시피 요청

그런데 현재 데이터와 함수 설명은 이 경계를 충분히 강하게 고정하지 못했다.

특히 주문번호가 등장하면 모델이 `get_order_status`로 빨려 들어가는 경향이 보였다.

즉 이 항목의 본질은:

- `주문번호가 있다`보다
- `요청의 핵심이 상태 조회인가, 정책 처리인가`

를 먼저 판단해야 한다는 점이다.

## 규칙 결정에 직접 영향을 준 사례

이번 문서에서 실제로 남길 대표 사례는 아래다.

- `conv=15 turn=0`
  - 주문번호 없이 배달 상태를 물었다.
  - GT는 주문번호 요청 text였고, 이는 함수 호출 이전의 clarification turn으로 보는 것이 맞다.
  - [tool_failures_with_dialogue.md:1404](/home/cwj/llm-project/eval_output/qwen-2.5-7b-function-calling_batch2_data_v2/tool_failures_with_dialogue.md:1404)
- `conv=16 turn=0`
  - 사용자가 `12345` 같은 짧은 번호를 말했지만, GT는 UUID 형식 주문번호를 다시 요청했다.
  - 단순 `required=order_id`만으로는 부족하고, 조회 가능한 ID 형식 조건까지 설명해야 함을 보여준다.
  - [tool_failures_with_dialogue.md:1432](/home/cwj/llm-project/eval_output/qwen-2.5-7b-function-calling_batch2_data_v2/tool_failures_with_dialogue.md:1432)
- `conv=20 turn=0`
  - 모델이 아예 자연어 문장을 `order_id` 자리에 넣어 호출했다.
  - 주문번호 요청 turn을 별도 규칙으로 강하게 잡아야 함을 보여준다.
  - [tool_failures_with_dialogue.md:1544](/home/cwj/llm-project/eval_output/qwen-2.5-7b-function-calling_batch2_data_v2/tool_failures_with_dialogue.md:1544)
- `conv=40 turn=0`
  - 주문번호가 있어도 핵심은 파손, 배상, 환불, 버그 신고, 가격 비교였다.
  - GT는 정책/안내 text였고, 이는 `get_order_status`의 비호출 조건을 함수 정의에 더 분명히 적어야 함을 보여준다.
  - [tool_failures_with_dialogue.md:3561](/home/cwj/llm-project/eval_output/qwen-2.5-7b-function-calling_batch2_data_v2/tool_failures_with_dialogue.md:3561)
- `conv=43 turn=1`
  - 주문번호가 있어도 라이더 사고 보상 문의는 상태 조회가 아니라 담당자 전달이 먼저였다.
  - [tool_failures_with_dialogue.md:3677](/home/cwj/llm-project/eval_output/qwen-2.5-7b-function-calling_batch2_data_v2/tool_failures_with_dialogue.md:3677)
이 중 핵심 우선순위는 `get_order_status`와 정책/안내 text turn 경계다. 자기정정이나 모호 발화 문제는 문서에 남기되, 이번 해결안의 중심축으로 두지는 않는다.

## 추천안

검토 결과 datagen과 함수 정의에 실제로 반영할 만한 추천안은 아래였다.

### 규칙 1. `get_order_status`를 상태 조회 전용 함수로 더 강하게 고정

- 첫 대화에서 `order_id`가 없으면 호출하지 않음
- 그 경우는 `주문번호 요청 clarification text turn`으로 처리함
- `order_id`가 있더라도 시스템에서 조회 가능한 형식이어야 함
- 사용자의 핵심 요청이 실제 상태 조회일 때만 호출
- 환불/보상/버그 신고는 이 함수로 처리하지 않음

### 규칙 2. clarification text turn을 별도 규칙으로 명시

아래 경우는 tool보다 clarification text가 우선이다.

- 주문번호가 없음
- 주문번호 형식이 조회 가능한 값이 아님
- 사용자 의도가 정정 중임
- 선택 기준이 아직 상충하거나 미정임

### 규칙 3. policy / unsupported text turn을 별도 규칙으로 명시

아래 경우는 tool call보다 정책/안내 text가 우선이다.

- 환불 요청
- 보상 요청
- 버그 신고
- 타사 비교
- 레시피 요청

주문번호가 같이 등장하더라도 핵심 요청이 위 항목이면 우선은 text turn으로 처리한다.

## 결론

이번 문서 기준으로 `relevance_detection`에서 실제로 함수 정의와 규칙 문제로 강하게 볼 수 있는 핵심은 아래다.

- `get_order_status` 호출 경계가 충분히 정의되지 않았다
- `clarification text turn` 규칙이 약했다
- `policy / unsupported text turn` 규칙이 약했다

반면 아래는 이 문서의 핵심 원인으로 보지 않는다.

- 단순 검색 missed tool call
- 단순 과호출
- 멀티스텝 전이 실패 다수

한 줄로 정리하면:

- `relevance_detection`에서 datagen 관점의 진짜 핵심은 새 함수를 추가하는 것이 아니라, 기존 함수 중 `get_order_status`의 호출 조건과 `text turn 규칙`을 명확히 정의하는 것이다

## 1. Datagen에서 왜 문제가 생겼는가

현재 함수 설명과 프롬프트는 `argument_value` 수준의 슬롯 규칙은 비교적 잘 설명하지만, `relevance_detection` 수준의 text turn 분기를 강하게 설명하지 않는다.

특히 아래가 약하다.

- 주문번호 요청 turn
- 정책 안내 turn
- clarification turn

대표적으로:

- [tool_specs.py:557](/home/cwj/llm-project/datagen/tool_specs.py:557)
  - `get_order_status`는 주문 상태 조회라고만 되어 있고, 비호출 조건과 선행 조건이 충분히 설명되지 않는다.

즉 함수 설명만 보면 모델은 아래처럼 오해하기 쉽다.

- 주문 관련 키워드가 나오면 `get_order_status`
- 주문번호 비슷한 값이 나오면 `get_order_status`
- 주문번호가 있으면 일단 `get_order_status`

하지만 실제 gold 기준은 더 좁다.

## 2. 실제 데이터에서 어떤 문제가 있었는가

실패 사례를 좁혀 보면, datagen 규칙 부족으로 볼 수 있는 패턴은 아래로 수렴한다.

- 주문번호가 없는데 상태 조회 tool을 호출
- 조회 가능한 주문 ID가 아닌데도 상태 조회 tool을 호출
- 주문번호가 있어도 핵심 요청이 환불/보상/버그 신고인데 상태 조회 tool을 호출
- 사용자가 정정 중이거나 선택 기준이 불명확한데 clarification 없이 tool을 호출

즉 이 문서에서 다루는 본질은:

- `tool을 아느냐 모르느냐` 문제가 아니라
- `먼저 text로 받아야 하는 턴을 분리하지 못한 문제`다

## 3. 그래서 어떻게 해결할 것인가

해결 방향은 단순하다. 새로운 함수를 추가하지 않고, 현재 함수 집합 안에서 호출 조건과 text turn 규칙을 더 명확히 고정한다.

### 규칙 1. 함수 설명에 비호출 조건을 명시한다

예:

- `get_order_status`
  - 환불/보상/버그 신고는 처리하지 않음
  - 주문번호가 없으면 호출하지 않음
  - 조회 가능한 형식의 주문 ID가 아니면 호출하지 않음

### 규칙 2. text turn 유형을 datagen에 명시한다

최소한 아래는 분리한다.

- `clarification text turn`
- `policy / unsupported text turn`
- `tool execution turn`

### 규칙 3. 복합 발화에서 핵심 요청 우선순위를 정한다

예:

- 주문번호가 있어도 환불/보상 요청이 핵심이면 text
- 검색 의도가 아직 정정 중이면 clarification text

## 4. 실제 적용 항목

### Datagen

- `get_order_status` description 수정
- 프롬프트에 아래 문구 추가
  - `첫 대화에서 주문번호가 없으면 먼저 clarification text를 생성하세요.`
  - `조회 가능한 주문 ID 형식이 아니면 상태 조회 tool을 호출하지 마세요.`
  - `환불/보상/버그 신고는 policy text turn으로 처리하세요.`
  - `주문번호가 같이 등장하더라도 핵심 요청이 환불/보상/버그 신고이면 text turn으로 처리하세요.`
  - `사용자가 정정 중이면 마지막 의도가 확정되기 전까지 clarification text를 우선하세요.`

### Dataset relabel

- `get_order_status` relevance 실패 케이스 우선 재검토
- 주문번호가 있어도 핵심 요청이 상태 조회가 아닌 케이스는 non-tool로 재확인
- clarification이 먼저여야 하는 케이스의 gold를 일관되게 점검

### Eval

- relevance GT 작성 시 아래를 분리해 관리
  - 상태 조회 tool turn
  - clarification text turn
  - policy / unsupported text turn

## 최종 정리

이번 문서에서 남긴 결론은 크지 않다.

정말로 함수 정의와 규칙 부족으로 설명 가능한 핵심은 아래뿐이다.

- `get_order_status` 호출 경계
- clarification text turn 규칙
- policy / unsupported text turn 규칙

현재 함수 집합을 유지하는 전제라면, 이 세 가지를 고정하는 것이 이번 문서 범위에서 가장 현실적인 해결안이다.

이 세 가지를 고정하면, `relevance_detection` 실패 중 datagen 관점에서 줄일 수 있는 부분을 가장 먼저 줄일 수 있다.
