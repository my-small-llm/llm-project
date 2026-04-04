# datagen 훈련데이터 생성 로직 문제 분석 및 수정 계획

작성일: 2026-04-04

## 1. 문서 목적

이 문서는 [train_data_dataset_defect_report.md](/home/cwj/llm-project/docs/Troubleshooting/train_data_dataset_defect_report.md)에서 정리한 연구 기반 문제의식을, 실제 `datagen` 생성 로직과 연결해 **어떤 구조가 현재 데이터 분포를 왜곡하고 있으며 이를 어떤 순서로 수정해야 하는지** 기록하기 위한 설계 문서다.

이번 문서의 목적은 구현이 아니라 **다음 실행 턴에서 바로 작업할 수 있는 수정 계획을 저장해두는 것**이다.

## 2. 배경 요약

현재 `train_data` 분석 결과의 핵심은 "잡담이 많다"가 아니라 아래에 있었다.

- non-tool 데이터가 decision supervision 기준으로 충분히 역할 분해되어 있지 않다.
- schema 밖 요청이 잡담처럼 섞여 있어 핵심 negative data로 관리되지 않는다.
- fallback 문구 일부가 tool faithfulness를 해친다.
- multi-intent 샘플 중 일부가 자연스러운 multi-turn보다 synthetic overload에 가깝다.

`datagen` 코드를 확인한 결과, 이 문제들 중 상당수는 모델 산출물의 우연한 특성이 아니라 **생성 파이프라인이 애초에 그렇게 나오도록 강제하는 구조**에서 비롯된다.

## 3. 코드 레벨 문제 분석

## 3.1 `generate_batch.py`가 unsupported 요청을 사실상 모든 샘플에 강제 주입한다

핵심 근거:

- [generate_batch.py](/home/cwj/llm-project/datagen/generate_batch.py#L77)
- [generate_batch.py](/home/cwj/llm-project/datagen/generate_batch.py#L78)
- [generate_batch.py](/home/cwj/llm-project/datagen/generate_batch.py#L83)
- [generate_batch.py](/home/cwj/llm-project/datagen/generate_batch.py#L93)

현재 로직은 요청 1건마다 아래를 수행한다.

- `QUESTION_TOPICS` 2개를 뽑음
- `UNSUPPORTED_SCENARIOS` 1개를 뽑음
- 외부 잡담 데이터 `question` 1개를 추가함
- 이를 `combined_unsupported`로 합쳐 프롬프트에 넣음

즉, 샘플 하나가 생성될 때마다 **tool 관련 주제 + unsupported 요청 + 외부 잡담**이 함께 섞이도록 구조적으로 유도한다.

이 구조의 결과:

- pure tool-use 샘플 비율이 낮아진다.
- unsupported가 독립 negative data가 아니라 중간 삽입물처럼 학습된다.
- off-domain 잡담이 in-domain unsupported와 같은 역할처럼 섞인다.
- 혼합 의도가 자연스럽게 발생한 것이 아니라 생성기에서 강제로 들어간다.

## 3.2 외부 `ChatbotData.csv` 의존성이 데이터 분포를 더 왜곡한다

핵심 근거:

- [generate_batch.py](/home/cwj/llm-project/datagen/generate_batch.py#L51)
- [generate_batch.py](/home/cwj/llm-project/datagen/generate_batch.py#L149)
- [generate_batch.py](/home/cwj/llm-project/datagen/generate_batch.py#L151)
- [generate_batch.py](/home/cwj/llm-project/datagen/generate_batch.py#L153)
- [config.py](/home/cwj/llm-project/datagen/config.py#L148)

현재 파이프라인은 외부 `ChatbotData.csv`를 읽어 count와 샘플 내용을 결정하는 구조를 가진다.

문제는 다음과 같다.

- 학습셋 분포가 tool-calling 목적이 아니라 외부 잡담 데이터셋 특성에 끌린다.
- CSV 로드 실패 시에는 `UNSUPPORTED_SCENARIOS` 반복으로 샘플을 채워, 오히려 unsupported 비율이 더 커진다.
- 재현성과 품질 통제가 약해진다.

즉, 현재 count와 내용이 **명시적 generation policy**가 아니라 외부 잡담 소스의 가용성에 영향을 받는다.

## 3.3 `prompts.py`가 unsupported와 "담당자 전달" 템플릿을 직접 강제한다

핵심 근거:

- [prompts.py](/home/cwj/llm-project/datagen/prompts.py#L21)
- [prompts.py](/home/cwj/llm-project/datagen/prompts.py#L25)
- [prompts.py](/home/cwj/llm-project/datagen/prompts.py#L187)
- [prompts.py](/home/cwj/llm-project/datagen/prompts.py#L190)
- [prompts.py](/home/cwj/llm-project/datagen/prompts.py#L193)

현재 프롬프트는 아래 두 가지를 동시에 강제한다.

1. unsupported 요청을 대화 중간에 포함하라고 지시함
2. 함수로 처리할 수 없는 요청은 `담당자에게 전달하겠다`고 말하라고 지시함

이 구조의 문제:

- unsupported 샘플이 별도 라벨로 관리되지 않고 거의 항상 tool 흐름에 섞인다.
- unsupported 응답이 "정확한 limitation 설명"보다 "고정 안내 문구"로 수렴한다.
- `담당자에게 전달`, `신속히 처리` 같은 검증 불가능한 완료형 문구가 반복된다.
- unsupported의 목적이 decision boundary 학습이 아니라 fallback template 학습으로 바뀐다.

## 3.4 예시 대화 자체가 mid-flow unsupported 혼입을 정상 패턴으로 가르친다

핵심 근거:

- [prompts.py](/home/cwj/llm-project/datagen/prompts.py#L72)
- [prompts.py](/home/cwj/llm-project/datagen/prompts.py#L86)
- [prompts.py](/home/cwj/llm-project/datagen/prompts.py#L87)
- [prompts.py](/home/cwj/llm-project/datagen/prompts.py#L88)

현재 예시 1은 정상 주문 흐름 한가운데에 배달비 불만을 삽입하고, 이를 `담당자 전달` 텍스트로 처리한 뒤 다시 주문 플로우로 돌아간다.

이 예시는 모델에게 아래를 암묵적으로 가르친다.

- unsupported 요청은 독립 시나리오가 아니라 언제든 중간에 끼워 넣어도 된다.
- unsupported 응답은 정형화된 민원 텍스트면 충분하다.
- tool-use 샘플과 unsupported 샘플을 명확히 구분할 필요가 없다.

즉, 예시 자체가 현재 데이터셋 왜곡을 정상 패턴처럼 reinforce한다.

## 3.5 `config.py`가 in-domain unsupported와 off-domain 잡담을 같은 버킷으로 관리한다

핵심 근거:

- [config.py](/home/cwj/llm-project/datagen/config.py#L41)
- [config.py](/home/cwj/llm-project/datagen/config.py#L101)
- [config.py](/home/cwj/llm-project/datagen/config.py#L136)

`UNSUPPORTED_SCENARIOS`에는 아래가 한 리스트에 들어 있다.

- 주문 취소, 환불, 영수증, 리뷰, 회원정보 같은 **in-domain unsupported**
- 연애 상담, 날씨 문의, 심리 상담 같은 **off-domain 잡담**

이 구조의 문제:

- schema 밖 요청과 완전한 오프도메인 잡담이 같은 supervision 역할로 취급된다.
- 모델이 "tool을 쓰지 말아야 하는 이유"를 세밀하게 배우기 어렵다.
- unsupported와 direct-answer/autonomy, off-domain refusal이 분리되지 않는다.

## 3.6 `preprocess.py`와 `datavalidator`는 구조적 오류는 보지만 semantic quality는 보지 못한다

핵심 근거:

- [preprocess.py](/home/cwj/llm-project/datagen/preprocess.py#L67)
- [preprocess.py](/home/cwj/llm-project/datagen/preprocess.py#L269)
- [validate.py](/home/cwj/llm-project/datavalidator/validate.py#L30)
- [validate.py](/home/cwj/llm-project/datavalidator/validate.py#L47)
- [validate.py](/home/cwj/llm-project/datavalidator/validate.py#L64)

현재 후처리와 검증은 주로 아래를 본다.

- 형식 파싱 가능 여부
- tool_call / tool_response 스키마 적합성
- 일부 inferability 오류

하지만 아래는 잡지 못한다.

- unsupported 샘플에서 허구의 완료형 fallback 문구 사용
- pure tool 샘플에 불필요한 unsupported가 끼어든 경우
- clarification이 필요한데 성급히 tool call한 경우
- 한 샘플 내 intent 과적재
- scenario type 분포 붕괴

즉, 형식은 맞아도 **decision quality와 tool faithfulness가 나쁜 샘플**이 그대로 통과할 수 있다.

## 4. 수정 방향 요약

수정 방향은 단기 패치와 중기 재설계를 함께 가는 **혼합 접근**으로 잡는다.

핵심 목표는 다음과 같다.

- 생성 단위를 "무작위 주제 혼합"에서 "scenario type 기반"으로 바꾼다.
- unsupported를 잡담과 분리해 핵심 negative data로 관리한다.
- `담당자 전달`류의 허구 실행 템플릿을 제거한다.
- pure tool, clarification, unsupported, autonomy, irrelevant negative를 별도 분포로 관리한다.
- semantic validator를 추가해 문서에서 지적한 문제를 자동으로 걸러낸다.

## 5. 단기 수정 계획

단기 목표는 **현 파이프라인을 크게 깨지 않고 분포 왜곡을 우선 멈추는 것**이다.

### 5.1 샘플 강제 혼합 제거

- `generate_batch.py`에서 모든 샘플에 `combined_unsupported`를 넣는 구조를 제거한다.
- pure tool 샘플과 unsupported 샘플을 서로 다른 generation path로 분리한다.
- `QUESTION_TOPICS` 2개 + unsupported 1개 + 잡담 1개라는 기본 조합을 폐기한다.

### 5.2 외부 잡담 데이터 의존성 제거 또는 격리

- 기본 학습셋 생성 경로에서 `ChatbotData.csv` 로드를 제거한다.
- 오프도메인 잡담이 필요하면 별도 augmentation 옵션으로만 사용한다.
- count는 외부 CSV 길이가 아니라 명시적인 배치 설정으로 결정한다.

### 5.3 unsupported 응답 템플릿 수정

- `담당자에게 전달하겠습니다`
- `신속히 처리하겠습니다`
- `전달하여 안내드리겠습니다`

같은 허구의 완료형 문구를 학습 기본값에서 제거한다.

대신 아래 형태를 기본 정책으로 둔다.

- 현재 도구로 직접 처리할 수 없는 점 설명
- 사용 가능한 대안 또는 다음 경로 제시
- 가능하면 tool로 도와줄 수 있는 인접 작업으로 복귀 유도

### 5.4 시나리오 버킷 1차 분리

`config.py`를 당장 완전 재설계하지 않더라도 아래 정도는 바로 분리한다.

- tool-capable scenarios
- in-domain unsupported scenarios
- off-domain scenarios
- clarification-needed scenarios

## 6. 중기 구조 재설계 계획

중기 목표는 **scenario-type 기반 생성기**로 전환하는 것이다.

### 6.1 새 라벨 체계 도입

최소 아래 7개 역할 라벨을 기준으로 생성 로직을 재구성한다.

1. `pure_tool_use`
2. `tool_use_with_clarification_needed`
3. `direct_answer_autonomy`
4. `out_of_schema_unsupported`
5. `irrelevant_function_negative`
6. `multi_turn_followup_stateful`
7. `policy_refusal_or_safe_fallback`

### 6.2 scenario catalog 기반 설정 구조

`QUESTION_TOPICS` / `UNSUPPORTED_SCENARIOS`의 평면 리스트를 아래처럼 바꾼다.

- `TOOL_SCENARIOS`
- `CLARIFICATION_SCENARIOS`
- `AUTONOMY_SCENARIOS`
- `UNSUPPORTED_IN_DOMAIN_SCENARIOS`
- `IRRELEVANT_NEGATIVE_SCENARIOS`
- `OFF_DOMAIN_SCENARIOS`

### 6.3 배치 생성 입력 구조 변경

새 배치 생성기는 요청 1건마다 아래 메타데이터를 명시적으로 받도록 설계한다.

- `scenario_type`
- `primary_intent`
- `secondary_intents`
- `allowed_turn_types`
- `forbidden_patterns`
- `target_length`

이렇게 해야 샘플이 "우연히 섞인" 것이 아니라 "의도적으로 생성된 타입"으로 관리된다.

### 6.4 프롬프트 구조 변경

현재 단일 프롬프트에서 모든 상황을 다 지시하는 방식 대신 아래로 분리한다.

- 공통 시스템 규칙
- scenario type별 생성 지시
- 예시도 type별로 별도 제공

특히 `pure_tool_use` 프롬프트에는 unsupported 삽입 지시를 넣지 않고, `unsupported` 프롬프트에는 tool 흐름을 억지로 섞지 않는다.

## 7. 검증 계획

## 7.1 생성 후 기본 확인

- 문서만 읽어도 수정 범위와 순서가 결정 가능해야 한다.
- 다음 구현 턴에서 `config -> prompts -> generate_batch -> preprocess/validator` 순으로 바로 작업 가능한 수준이어야 한다.

## 7.2 구현 후 자동 검증 목표

향후 구현 시 아래 검증을 추가한다.

- scenario type별 목표 분포 검증
- pure tool 샘플의 unsupported 혼입률 측정
- unsupported 샘플의 tool call 발생률 측정
- clarification 샘플의 premature tool call 탐지
- 금지 fallback 문구 탐지
- multi-intent overload 샘플 탐지

## 7.3 수동 리뷰 목표

소량 샘플을 생성해 최소 아래를 직접 점검한다.

- pure tool 20건
- clarification 10건
- unsupported/policy 10건
- irrelevant negative 10건

확인 포인트:

- 언제 tool을 써야 하는지
- 언제 추가 질문을 해야 하는지
- 언제 직접 답해야 하는지
- 언제 현재 도구로는 불가하다고 말해야 하는지

위 4가지 decision boundary가 자연스럽고 일관되게 드러나는지 본다.

## 8. 기본 실행 순서

다음 구현 턴에서는 아래 순서로 진행한다.

### 1단계: 분포 왜곡 제거

- `combined_unsupported` 제거
- 외부 잡담 CSV 기본 의존성 제거
- unsupported 고정 혼입 제거
- `담당자 전달` 템플릿 제거

### 2단계: scenario-type 기반 재설계

- 시나리오 카탈로그 분리
- type별 프롬프트 분리
- 배치 생성 입력 구조 개선
- metadata 보존 설계 추가

### 3단계: semantic validator 추가

- fallback hallucination 탐지
- clarification 누락 탐지
- intent overload 탐지
- 분포 리포트 추가

## 9. 참고 파일 및 근거 라인

### 핵심 대상 파일

- [generate_batch.py](/home/cwj/llm-project/datagen/generate_batch.py)
- [prompts.py](/home/cwj/llm-project/datagen/prompts.py)
- [config.py](/home/cwj/llm-project/datagen/config.py)
- [preprocess.py](/home/cwj/llm-project/datagen/preprocess.py)
- [validate.py](/home/cwj/llm-project/datavalidator/validate.py)

### 특히 중요한 근거 위치

- [generate_batch.py](/home/cwj/llm-project/datagen/generate_batch.py#L77)
- [generate_batch.py](/home/cwj/llm-project/datagen/generate_batch.py#L83)
- [generate_batch.py](/home/cwj/llm-project/datagen/generate_batch.py#L149)
- [prompts.py](/home/cwj/llm-project/datagen/prompts.py#L25)
- [prompts.py](/home/cwj/llm-project/datagen/prompts.py#L187)
- [prompts.py](/home/cwj/llm-project/datagen/prompts.py#L193)
- [config.py](/home/cwj/llm-project/datagen/config.py#L101)
- [config.py](/home/cwj/llm-project/datagen/config.py#L136)
- [preprocess.py](/home/cwj/llm-project/datagen/preprocess.py#L269)
- [validate.py](/home/cwj/llm-project/datavalidator/validate.py#L47)

## 10. 메모

이 문서는 구현 전용 설계 문서다.  
이번 단계에서는 문서만 저장하고, 실제 코드 수정은 다음 실행 턴에서 이 문서를 근거로 진행한다.
