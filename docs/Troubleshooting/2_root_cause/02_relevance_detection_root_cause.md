# `relevance_detection` 루트코즈 정리

작성일: 2026-04-02

## 문서 역할

`2_root_cause`의 두 번째 문서다.

`1_eval_discovery/03_relevance_detection_failure_report.md`는 tool 호출이 필요한 턴과 text 응답이 필요한 턴의 경계가 흔들린다는 사실을 보여줬다. 이 문서는 그 실패 전체를 다시 다루기보다, `datagen` 규칙과 함수 설명 부족으로 설명 가능한 원인만 추려서 정리한다.

## 기준 질문

- `relevance_detection` 실패 중 실제로 규칙 설계 문제로 볼 수 있는 것은 무엇인가?
- 단순 모델 실수와 `datagen / tool spec` 결함은 어디서 갈리는가?
- 이후 수정 단계에서 어떤 text turn 규칙을 명시해야 하는가?

## 핵심 결론

이번 축의 핵심 원인은 새 함수를 추가하지 않아서가 아니라, 기존 함수 중 `get_order_status`의 호출 경계와 `text turn` 규칙이 충분히 고정되지 않았다는 데 있다.

특히 아래 세 가지가 루트코즈로 남는다.

- `get_order_status` 호출 조건이 좁게 정의되지 않음
- `clarification text turn` 규칙이 약함
- `policy / unsupported text turn` 규칙이 약함

반대로 아래는 이 문서의 중심 원인으로 보지 않는다.

- 단순 missed tool call
- 단순 spurious tool call
- 멀티스텝 전이 실패 다수

이들은 대체로 GT 규칙은 충분히 타당하고, 모델이 실행 단계에서 순수하게 실수한 케이스에 가깝다.

## 원인 1. `get_order_status` 호출 경계가 불명확했다

`get_order_status`는 아래 조건을 더 강하게 설명해야 했다.

- 실제 상태 조회일 때만 호출
- 조회 가능한 `order_id`가 있을 때만 호출
- 환불, 보상, 버그 신고는 이 함수로 처리하지 않음

이 경계가 약하면 모델은 아래처럼 오해하기 쉽다.

- 주문 관련 키워드가 나오면 `get_order_status`
- 주문번호 비슷한 값이 나오면 `get_order_status`
- 주문번호가 있으면 일단 `get_order_status`

하지만 `1_eval_discovery`에서 본 실패는 이런 단순 규칙보다 더 좁은 gold 기준을 갖고 있었다. 즉 문제는 "함수를 아느냐 모르느냐"보다 "언제 호출하면 안 되는가"가 충분히 명시되지 않은 데 있었다.

## 원인 2. `clarification text turn`이 별도 턴 유형으로 고정되지 않았다

다음과 같은 경우는 tool보다 clarification text가 먼저 와야 한다.

- 주문번호가 없음
- 주문번호 형식이 조회 가능한 값이 아님
- 사용자가 정정 중이라 마지막 의도가 확정되지 않음
- 선택 기준이 아직 상충하거나 미정임

현재 데이터와 설명은 `tool vs text` 정도는 가르치지만, `clarification text`를 독립된 턴 유형으로 충분히 강하게 고정하지 못했다. 그 결과 모델이 성급하게 tool call로 뛰는 패턴이 반복됐다.

## 원인 3. `policy / unsupported text turn` 규칙이 약했다

다음 요청은 주문번호가 등장하더라도 상태 조회보다 정책/안내 text가 우선이다.

- 환불 요청
- 보상 요청
- 버그 신고
- 타사 비교
- 레시피 요청

그런데 현재 데이터와 함수 설명은 이 경계를 충분히 강하게 고정하지 못했다. 그래서 주문번호가 보이면 모델이 `get_order_status`로 빨려 들어가는 경향이 생겼다.

핵심은 `주문번호가 있느냐`보다 `요청의 핵심이 상태 조회인가, 정책 처리인가`를 먼저 판단해야 한다는 점이다.

## `1_eval_discovery`와의 연결

이 문서는 `03_relevance_detection_failure_report.md`의 다음 질문들에 답한다.

- 주문번호 부족 상태에서 왜 `get_order_status`를 성급하게 호출했는가?
- 정책 안내가 필요한 턴에서 왜 tool call로 기울었는가?
- clarification이 먼저 필요한 턴을 왜 안정적으로 분리하지 못했는가?

이 질문들에 대한 루트코즈는 모델이 전혀 모르는 함수가 있어서가 아니라, `get_order_status` 비호출 조건과 text turn 분기 규칙이 데이터 생성 규칙에 충분히 박혀 있지 않았다는 데 있다.

## 다음 단계로 넘길 결정

수정 단계에서는 아래를 실제 규칙으로 내릴 필요가 있다.

- `get_order_status`를 상태 조회 전용 함수로 더 좁게 고정
- `clarification text turn`을 별도 규칙으로 명시
- `policy / unsupported text turn`을 별도 규칙으로 명시

이후 결정 문서는 `../3_fixes/02_relevance_detection_decision_summary.md`에서 이어진다.
