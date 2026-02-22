# 배달 앱 AI 상담사 파인튜닝 데이터 생성 파이프라인 (`datagen`)

배달 앱 AI 챗봇 파인튜닝을 위한 **펑션콜링 멀티턴 대화 데이터**를 OpenAI Batch API로 대량 생성하고, 검증 및 허깅페이스 업로드까지 수행하는 파이프라인입니다.

## 사전 준비

```bash
# 필요 패키지
pip install openai pandas datasets

# OpenAI API 키 설정
export OPENAI_API_KEY="sk-..."
```

---

## 학습용 데이터 생성 파이프라인

파인튜닝에 사용할 대량의 멀티턴 대화 데이터를 생성하고 HuggingFace Hub에 업로드하는 5단계 파이프라인입니다.

```
[Step 1]               [Step 2]         [Step 3]            [Step 4]        [Step 5]
generate_batch.py  →  submit_batch.py  →  retrieve_batch.py  →  preprocess.py  →  push_to_hub.py
```

### Step 1. JSONL 입력 파일 생성 (`generate_batch.py`)

지정된 개수만큼의 대화 요청 시나리오를 생성하여, OpenAI Batch API가 이해할 수 있는 JSONL 형태로 파일을 생성합니다.

```bash
python -m datagen.generate_batch --count 400
```

- **API 호출 없이** 로컬에서 파일만 생성합니다.
- 출력: `datagen/output/batch_input.jsonl`

### Step 2. Batch API 제출 (`submit_batch.py`)

Step 1에서 만든 JSONL 파일을 OpenAI Batch API에 제출합니다. 비용을 크게 절감할 수 있으며, 진행 상태는 `batch_status.json`으로 추적합니다.

```bash
# 제출과 동시에 완료될 때까지 대기
python -m datagen.submit_batch --wait
```

- 출력: `datagen/output/batch_status.json`

### Step 3. 결과 다운로드 (`retrieve_batch.py`)

OpenAI 서버에서 배치 처리가 완료되면 결과 대화 데이터를 다운로드합니다.

```bash
python -m datagen.retrieve_batch
```

- 출력: `datagen/output/result_lst.json`

### Step 4. 파싱 및 전처리 (`preprocess.py` & `parse.py`)

다운로드된 텍스트를 파싱하여 Qwen 계열 모델이 필요로 하는 `<tool_call>` 등 XML 태그 형식으로 변환합니다. 시스템 지시문(`system_prompt`)과 대화 내역(`messages`)을 분리하여 JSON Lines 형식으로 저장합니다.

```bash
python -m datagen.preprocess
```

- 출력: `datagen/output/dataset.jsonl`

**저장되는 데이터 형태 (`dataset.jsonl` 예시)**:

```json
{
  "tools": [
    {"type": "function", "function": {"name": "search_restaurants", "description": "...", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": []}}}
  ],
  "uid": "fac75497-7df8-4902-bda6-066e60a1f5ef",
  "dates": "2026-02-14",
  "system_prompt": "당신은 배달 앱 AI 상담사입니다...",
  "messages": [
    {"role": "user", "content": "안녕하세요, 짜장면 맛있는 집 좀 찾아주세요."},
    {"role": "assistant", "content": "<tool_call>\n{\"name\": \"search_restaurants\", \"arguments\": {\"query\": \"짜장면\"}}\n</tool_call>"},
    {"role": "user", "content": "<tool_response>\n[{\"items\": [{\"restaurant_id\": \"uuid1\", \"name\": \"홍콩반점\"}]}]\n</tool_response>"},
    {"role": "assistant", "content": "홍콩반점이 주변에 있습니다. 주문하시겠습니까?"}
  ]
}
```

### Step 5. HuggingFace Hub 업로드 (`push_to_hub.py`)

전처리가 완료된 `dataset.jsonl`을 HuggingFace Hub에 업로드합니다. `dataset.jsonl`의 컬럼 구조 그대로 업로드되며, 파인튜닝 라이브러리(unsloth, trl 등)에서 `dataset["system_prompt"]`와 `dataset["messages"]`를 직접 매핑하여 활용합니다.

```bash
python -m datagen.push_to_hub --input datagen/output/dataset.jsonl --repo-id "your-hf-account/delivery-dataset"
```

---

## 평가용 골드 데이터 생성 파이프라인

파인튜닝된 모델의 성능을 벤치마킹하기 위한 별도 파이프라인입니다. 카테고리별로 철저하게 통제된 시나리오를 생성합니다.

```
[Step 1]                    [Step 2]         [Step 3]
generate_gold_batch.py  →  submit_batch.py  →  retrieve_batch.py
```

### Step 1. 평가용 골드 배치 생성 (`generate_gold_batch.py`)

8개 카테고리 × 10건 = **80건**의 평가 전용 배치 파일을 생성합니다.

| 카테고리 | 설명 |
|----------|------|
| 단순/연속 검색 | `search_restaurants` 반복 호출 |
| 메뉴 조회 | `get_restaurant_detail` 컨텍스트 의존성 |
| 장바구니 조작 | `add/update/remove_cart_*` 복합 사용 |
| 주문 이력/상태 | `get_order_status` 제약(order_id 필수) 처리 |
| 주문 처리 | `prepare_checkout` → `place_order` 파라미터 체인 |
| 멀티턴 복합 | 검색 → 메뉴 → 장바구니 → 결제 풀사이클 |
| 비지원 시나리오 | 도구 미호출(no_call) 시나리오 |
| 엣지 케이스 | 오타, 번복, 모호한 지시 등 |

```bash
python -m datagen.generate_gold_batch
```

- 출력: `datagen/output/gold_batch_input.jsonl`

### Step 2. Batch API 제출 (`submit_batch.py`)

학습용 파이프라인과 동일한 스크립트를 사용하되, `--input`으로 골드 배치 파일을 지정합니다.

```bash
python -m datagen.submit_batch --input datagen/output/gold_batch_input.jsonl --wait
```

- 출력: `datagen/output/batch_status.json`

### Step 3. 결과 다운로드 (`retrieve_batch.py`)

학습용 파이프라인과 동일한 스크립트로 결과를 다운로드합니다.

```bash
python -m datagen.retrieve_batch
```

- 출력: `datagen/output/result_lst.json`

---

## 설정 관리 (`config.py` & `prompts.py`)

| 파일 | 주요 내용 |
|------|-----------|
| `config.py` | `USER_IDS`, `QUESTION_TOPICS`, `UNSUPPORTED_SCENARIOS`, `GOLD_CATEGORIES`, 도구 명세(`tools`), 반환 포맷(`tools_return_format`). **데이터 구조가 변경되면 이 파일을 가장 먼저 수정합니다.** |
| `prompts.py` | `SYSTEM_PROMPT_FIXED` (상담사 기본 지침). 응답 턴 수 제어 또는 어투 변경 시 이 파일을 수정합니다. |

---

## 파일 구조

```
datagen/
├── __init__.py                  # 패키지 초기화
├── config.py                    # 설정 (user_ids, 시나리오, tools, tools_return_format)
├── prompts.py                   # 시스템 프롬프트 + 유저 프롬프트 빌더
├── generate_batch.py            # 학습용 Step 1: 대량 JSONL 생성
├── generate_gold_batch.py       # 평가용 Step 1: 골드 데이터(80건) JSONL 생성
├── submit_batch.py              # Step 2: 배치 제출 (학습·평가 공용)
├── retrieve_batch.py            # Step 3: 결과 다운로드 (학습·평가 공용)
├── parse.py                     # 파싱 도구
├── preprocess.py                # 학습용 Step 4: 파싱 및 jsonl 추출
├── push_to_hub.py               # 학습용 Step 5: 데이터셋 허브 업로드
├── README.md                    # 이 문서
│
└── output/                      # 단계별 출력 파일
    ├── batch_input.jsonl        # 학습용 Batch API 입력 파일
    ├── gold_batch_input.jsonl   # 평가용 Batch API 입력 파일
    ├── batch_status.json        # 배치 상태 정보
    ├── result_lst.json          # 결과 다운로드 원본 리스트
    └── dataset.jsonl            # 전처리 완료 데이터셋
```
