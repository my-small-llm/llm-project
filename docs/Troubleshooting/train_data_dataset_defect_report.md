# train_data 데이터셋 구조 분석 및 개선 보고서

작성일: 2026-04-04

## 1. 목적

본 문서는 `train_data`를 "문제가 많은 잡담 데이터"로 단정하기보다, **최신 tool-calling / PEFT 연구를 기준으로 현재 데이터셋이 어떤 학습 신호를 충분히 담고 있고 어떤 의사결정 신호가 부족한지**를 재해석하기 위해 작성되었다.

평가 초점은 모델 성능 자체가 아니라, **LoRA/QLoRA 기반 tool-calling 학습에서 데이터 구조가 올바른 decision boundary를 형성하는 데 얼마나 적합한가**이다.

## 2. 해석 기준

최근 연구들은 공통적으로 "tool-call 데이터 비율"이나 "잡담 비율" 자체보다 아래 요소를 더 중요하게 본다.

- **Decision quality**
  - 언제 tool을 호출해야 하는지
  - 언제 직접 답해야 하는지
  - 언제 추가 정보를 물어야 하는지
  - 언제 현재 도구셋으로는 처리할 수 없다고 말해야 하는지
- **Schema faithfulness**
  - 실제 존재하는 함수와 파라미터를 기준으로 답변과 실행이 연결되는지
- **Conversation realism**
  - synthetic noise를 늘리는 대신, 실제 사용자 흐름처럼 multi-turn과 clarification이 자연스럽게 이어지는지
- **Data informativeness**
  - LoRA/QLoRA에서 특히 중요한 정보량, 라벨 일관성, supervision의 명확성이 확보되는지

즉, 본 문서의 관점은 다음과 같다.

> 문제는 "non-tool 데이터가 많다" 그 자체가 아니라,  
> **non-tool 데이터가 tool decision 학습에 유효한 형태로 구조화되어 있는가**이다.

## 3. 데이터셋 현황 요약

총 사용자 발화: **2478턴**

### 3.1 영역별 분포

| 영역 | 건수 | 비율 | 의미 |
| --- | ---: | ---: | --- |
| 퓨어 툴 | 1069 | 43.14% | 현재 보유 함수로 처리 가능한 의도만 있는 턴 |
| 툴 + 스키마밖 혼합 | 278 | 11.22% | tool 처리 가능 요청과 unsupported 요청이 함께 있는 턴 |
| 스키마밖 only | 229 | 9.24% | 현재 함수셋으로 직접 처리할 수 없는 요청 |
| 기타/단답/미분류 | 902 | 36.40% | 짧은 응답, 애매한 대화, 약한 supervision 턴 |

### 3.2 상위 구조

- **Tool 관련 전체**: 1347턴 (54.36%)
- **Schema 밖 요청 포함 전체**: 507턴 (20.46%)
- **의도 불명확 / 약한 supervision 턴**: 902턴 (36.40%)

이 수치만 보면 현재 데이터는 완전히 잘못된 데이터셋이라기보다, **tool-use 데이터 위에 unsupported 요청과 저정보량 non-tool 데이터가 함께 섞여 있는 상태**에 가깝다.

## 4. 연구 기준에서 본 핵심 해석

## 4.1 non-tool 비율 자체보다, non-tool의 역할 분해가 부족하다

최근 연구는 고정된 "잡담 비율의 정답"을 제시하지 않는다. 대신 non-tool 데이터를 아래처럼 **명시적 역할이 있는 decision supervision 데이터**로 설계하는 방향을 제안한다.

- **direct-answer / autonomy**
  - tool 없이 직접 답할 수 있는 일반 질의
- **clarification**
  - 정보가 부족해 바로 tool call 하면 안 되는 질의
- **cannot-answer / unsupported**
  - 현재 도구셋으로 처리 불가능한 요청
- **irrelevant-function negative**
  - 비슷한 이름의 함수를 잘못 고르지 않도록 만드는 negative 데이터
- **follow-up / stateful**
  - 이전 맥락을 이어받는 짧은 후속 요청

현재 `기타/단답/미분류 902턴(36.40%)`은 이 역할 기준으로 충분히 세분화되어 있지 않다. 따라서 해석의 초점은 "잡담이 많다"가 아니라 아래에 있다.

- direct-answer형 autonomy 데이터가 얼마나 있는지 불명확하다.
- clarification 데이터가 상대적으로 약하다.
- follow-up / stateful supervision이 별도 의사결정 라벨로 드러나지 않는다.
- trivial acknowledgment와 decision-relevant non-tool이 같은 바구니에 섞여 있다.

즉, **현재 non-tool 영역의 핵심 문제는 양이 아니라 정보 구조의 불투명성**이다.

## 4.2 스키마밖 요청은 잡담이 아니라 핵심 negative / boundary 데이터다

현재 데이터에서 스키마밖 요청은 총 **507턴(20.46%)**이며, 이는 단순한 노이즈로만 볼 수 없다. 최신 연구 기준에서는 이런 요청을 오히려 반드시 포함해야 하는 데이터로 본다.

이유는 다음과 같다.

- 모델은 "언제 tool을 써야 하는가"뿐 아니라 "언제 tool을 쓰지 말아야 하는가"도 배워야 한다.
- unsupported 요청이 없으면 억지 tool call, 유사 함수 오선택, 허위 파라미터 생성이 늘어나기 쉽다.
- irrelevant / unsupported 상황은 tool decision 품질을 가장 직접적으로 시험하는 구간이다.

따라서 현재 구조의 문제는 **스키마밖 요청이 들어 있다는 사실 자체가 아니라, 이 요청들이 별도 라벨과 응답 정책으로 관리되지 않고 있다는 점**이다.

권장 해석:

- `schema 밖 요청`은 "잡담"으로 묶지 않는다.
- 아래와 같은 명시 라벨로 분리한다.
  - `unsupported_request`
  - `cannot_answer_with_available_tools`
  - `out_of_schema_request`
  - `needs_handoff` 또는 `policy_response`

## 4.3 현재 fallback 응답은 boundary 학습에는 유용하지만, faithfulness 측면 보완이 필요하다

스키마밖 only 229턴 중 **207턴이 assistant 텍스트 응답**으로 처리되며, 그중 상당수는 아래와 같은 반복 패턴을 가진다.

- `담당자에게 전달하겠습니다`
- `처리해드릴 수 없습니다`
- `답변할 수 없는 내용입니다`

이 구조는 장점과 한계를 동시에 가진다.

### 장점

- unsupported 요청에 대해 tool call을 억제하는 negative supervision으로는 의미가 있다.
- 모델이 모든 요청에 무조건 tool을 부르지 않도록 만드는 최소한의 경계 학습에는 도움이 된다.

### 한계

- 실제 스키마에 없는 action을 수행한 것처럼 보이는 문구는 **tool faithfulness**를 해친다.
- "전달했다", "처리 요청했다" 같은 완료형 문장은 검증 불가능한 실행 서술이 된다.
- limitation 설명, 가능한 대안, 추가 경로 안내가 분리되지 않아 **cannot-answer 품질이 낮아진다.**

따라서 개선 방향은 fallback 제거 자체가 아니라, **fallback를 더 정직하고 근거 있는 응답 정책으로 재작성하는 것**이다.

예시:

- 나쁜 형태: `담당자에게 전달했습니다`
- 권장 형태: `현재 제공된 도구로는 회원 탈퇴를 직접 처리할 수 없습니다. 앱 고객센터 또는 계정 설정 메뉴에서 진행해 주세요.`

## 4.4 혼합 의도 자체보다, "어떻게 혼합되었는가"가 중요하다

한 발화 안에 의도 범주가 3개 이상 섞인 샘플은 **136턴(5.49%)**이다.

- 49개: tool 관련 요청만 여러 개 겹침
- 70개: tool 요청 + 스키마밖 요청 혼합
- 11개: tool 요청 + 잡담/상담 혼합
- 6개: tool 요청 + 스키마밖 요청 + 잡담 동시 혼합

최근 연구 흐름은 multi-intent 자체를 금지하지 않는다. 오히려 실제 사용자는 복합적이고 모호한 요청을 자주 한다고 본다. 다만, 아래와 같은 샘플은 품질이 떨어질 가능성이 높다.

- 서로 관련 없는 요청을 한 턴에 과하게 욱여넣은 경우
- priority가 불분명한 경우
- clarification 없이 바로 실행하도록 유도하는 경우
- multi-turn으로 나누면 자연스러운 흐름을 단일 턴에 압축한 경우

따라서 현재 mixed-intent 데이터는 전부 제거 대상이 아니라, 아래 기준으로 재정비하는 것이 맞다.

- **관련 있는 복합 요청**은 유지
- **서로 무관한 요청의 과적재**는 축소
- 필요한 경우 **clarification -> 단계적 실행 -> 후속 응답** 형태의 multi-turn으로 분해

## 5. 현재 데이터셋의 구조적 보완 포인트

## 5.1 "기타/단답/미분류" 36.40%는 재라벨링 우선순위가 가장 높다

이 영역은 단순히 삭제할 대상이 아니라, **decision supervision으로 전환 가능한 후보 집합**으로 보는 것이 맞다.

우선 아래처럼 재분류하는 것을 권장한다.

1. **direct-answer / autonomy**
   - tool 없이 답해야 하는 일반 설명, 추천, 상식, 짧은 조언
2. **clarification**
   - missing parameter, ambiguous request, slot 부족
3. **follow-up / stateful**
   - `그걸로 해줘`, `아까 거 다시 보여줘` 같은 후속 요청
4. **unsupported / cannot-answer**
   - 현재 함수셋 밖 요청
5. **trivial ack**
   - `네`, `아니요`, `고마워` 같은 저정보량 턴

이렇게 바꾸면 기존의 큰 "기타" 덩어리가 **tool decision 학습에 실제로 쓰이는 supervision 데이터**로 바뀔 수 있다.

## 5.2 스키마밖 데이터는 유지하되, 응답 품질과 라벨 체계를 올려야 한다

현재 스키마밖 비율 자체는 과도하게 높다고 단정하기 어렵다. 오히려 툴 중심 어시스턴트라면 어느 정도의 unsupported 데이터는 필수다.

실무 출발점으로는 다음 구조를 권장한다.

- **direct-answer / autonomy형**: 10~20%
- **unsupported / irrelevance / cannot-answer형**: 5~15%
- **나머지 주력**: tool-use

이 수치는 특정 논문이 고정 정답으로 제시한 값은 아니며, 최신 연구가 공통적으로 강조하는 데이터 종류를 반영한 **초기 실험용 기준선**이다.

중요한 점은 비율보다 아래 조건이다.

- unsupported 데이터가 별도 라벨로 관리될 것
- irrelevant function negative가 포함될 것
- cannot-answer 응답이 정직하고 일관될 것
- policy/handoff 문구가 허구의 실행처럼 보이지 않을 것

## 5.3 현재 데이터에 추가되어야 할 샘플 유형

최신 벤치마크와 논문 흐름을 기준으로 보면, 아래 유형은 반드시 보강하는 것이 좋다.

### 1. ambiguous query

- 예: `피자 시켜줘`
- 어떤 매장인지, 어떤 메뉴인지, 어떤 주소인지 부족한 상태
- 바로 tool call 하지 않고 clarification을 해야 한다

### 2. missing parameter

- 예: `지난번처럼 주문해줘`
- 맥락 추적 또는 추가 질문이 필요한 상황

### 3. wrong-tool 유도 / irrelevant function negative

- 함수 이름이 비슷하거나 일부만 관련 있는 상황
- 올바른 non-call 또는 대안 제시를 학습해야 한다

### 4. partial execution

- 요청 일부만 tool로 처리 가능하고 나머지는 unsupported인 상황
- 무엇을 실행하고 무엇을 거절할지 분리해야 한다

### 5. multi-turn follow-up / stateful

- 앞선 응답을 이어받는 후속 지시
- 실제 주문/조회 플로우에 더 가깝다

### 6. policy / refusal / harmful tool response

- 안전상 호출하면 안 되는 요청
- 도구 사용 가능성과 정책 허용 여부를 함께 판단해야 한다

## 6. 권장 라벨 체계

현재 4개 분류를 유지하더라도, 연구 기준에 맞추려면 최소한 아래 7개 역할 라벨로 재설계하는 편이 좋다.

1. **pure_tool_use**
2. **tool_use_with_clarification_needed**
3. **direct_answer_autonomy**
4. **out_of_schema_unsupported**
5. **irrelevant_function_negative**
6. **multi_turn_followup_stateful**
7. **policy_refusal_or_safe_fallback**

이 구조의 장점은 다음과 같다.

- tool-call 성공 여부만이 아니라 decision quality를 직접 학습할 수 있다.
- unsupported 요청을 잡담과 분리할 수 있다.
- clarification과 follow-up을 별도 supervision으로 관리할 수 있다.
- LoRA/QLoRA에서 중요한 라벨 일관성과 정보량을 높일 수 있다.

## 7. 실무용 개선 가이드

## 7.1 바로 수정할 것

- `기타/단답/미분류`를 유지하지 말고 역할 기반으로 재라벨링한다.
- `담당자에게 전달했습니다` 같은 허구의 완료형 문구를 제거한다.
- unsupported 요청을 `잡담`이 아니라 `boundary/negative data`로 승격한다.
- 복합 요청 중 무관한 intent 과적재 샘플은 multi-turn으로 분해한다.

## 7.2 유지하되 정제할 것

- schema 밖 요청 자체는 유지한다.
- tool + unsupported 혼합 샘플도 유지 가능하다.
- 다만 `일부는 tool 처리`, `일부는 추가 질문`, `일부는 불가 안내`가 구분되도록 supervision을 다시 써야 한다.

## 7.3 추가할 것

- clarification 중심 샘플
- missing parameter 샘플
- irrelevant function negative 샘플
- multi-turn state tracking 샘플
- partial execution 샘플

## 8. 결론

현재 데이터셋의 핵심 이슈는 "잡담이 많다"가 아니다.  
연구 기준에서 더 정확한 진단은 아래와 같다.

- **decision supervision이 충분히 역할 분해되어 있지 않다**
- **unsupported 요청이 핵심 negative data임에도 별도 라벨과 응답 정책이 약하다**
- **fallback 텍스트 일부가 tool faithfulness를 해칠 수 있다**
- **혼합 의도 샘플 중 일부는 multi-turn / clarification 구조로 바꾸는 편이 더 현실적이다**

따라서 이 데이터셋은 전면 폐기 대상이라기보다, **tool-use 중심 데이터 위에 decision-quality supervision을 보강하고 라벨 체계를 재구성해야 하는 데이터셋**으로 보는 것이 적절하다.

## 9. 참고 문헌

1. A Deep Dive into the Trade-Offs of Parameter-Efficient Preference Alignment Techniques  
   https://arxiv.org/abs/2406.04879
2. When2Call: When (not) to Call Tools  
   https://arxiv.org/abs/2504.18851
3. Hammer: Robust Function-Calling for On-Device Language Models via Function Masking  
   https://arxiv.org/abs/2410.04587
4. BFCL V3: Multi-Turn & Multi-Step Function Calling  
   https://gorilla.cs.berkeley.edu/blogs/13_bfcl_v3_multi_turn.html
5. ToolFlow: Boosting LLM Tool-Calling Through Natural and Coherent Dialogue Synthesis  
   https://arxiv.org/abs/2410.18447
6. ToolPlanner: A Tool Augmented LLM for Multi Granularity Instructions with Path Planning and Feedback  
   https://aclanthology.org/2024.emnlp-main.1018/
7. ToolACE: Winning the Points of LLM Function Calling  
   https://arxiv.org/abs/2409.00920
