# 🤖 배달 앱 AI 상담사 파인튜닝 데이터 생성 파이프라인 (`datagen`)

배달 앱 AI 챗봇 파인튜닝을 위한 **펑션콜링 멀티턴 대화 데이터**를 OpenAI Batch API로 대량 생성하고, 검증 및 허깅페이스 업로드까지 수행하는 파이프라인입니다.

## 사전 준비

```bash
# 필요 패키지
pip install openai pandas datasets

# OpenAI API 키 설정
export OPENAI_API_KEY="sk-..."
```

## 🏗️ 전체 파이프라인 개요

전체 파이프라인은 5개의 주요 단계로 나뉩니다. 각 단계가 성공적으로 끝나면 다음 단계의 입력 파일로 사용되는 파일이 생성됩니다.

```ascii
[1. 입력 파일 생성]                         [2. 배치 API 제출]        [3. 결과 다운로드]      [4. 파싱 및 전처리]     [5. HF 허브 업로드]
generate_batch.py (대량)            →
generate_gold_batch.py (평가용 80건) →  submit_batch.py  →  retrieve_batch.py  →  preprocess.py  →  push_to_hub.py
```

1. **파인튜닝 입력 파일 생성 (`generate_batch.py`)**: 사용자 정보, 프롬프트, 도구 명세(Tools)를 조합하여 Batch API 요청 규격인 대량의 JSONL 파일을 생성
2. **골드 평가 입력 파일 생성 (`generate_gold_batch.py`)**: 철저하게 통제된 80건의 평가 전용 JSONL 파일 생성
3. **배치 API 제출 (`submit_batch.py`)**: 생성된 JSONL 파일을 (학습이든 평가용이든) OpenAI에 업로드하고 배치를 실행
4. **결과 다운로드 (`retrieve_batch.py`)**: 완료된 배치의 결과를 확인하고 모델이 생성한 원본 대화 텍스트 다운로드
5. **파싱 및 전처리 (`preprocess.py`, `parse.py`)**: 원본 텍스트를 파싱하고 검증하기 쉽게 `dataset.jsonl` 파일로 저장
6. **HuggingFace 허브 업로드 (`push_to_hub.py`)**: 전처리/검증이 완료된 `jsonl`을 허브에 업로드

---

## 🛠️ 단계별 실행 및 데이터 형태 예시

### Step 1. JSONL 입력 파일 생성 (`generate_batch.py`)

지정된 개수만큼의 대화 요청 시나리오를 생성하여, OpenAI Batch API가 이해할 수 있는 JSONL 형태로 파일(`data/output/batch_input.jsonl`)을 생성합니다.

```bash
python -m datagen.generate_batch --count 400
```
- **API 호출 없이** 로컬에서 파일만 생성합니다.

### Step 1-B. 평가용 골드 데이터셋 JSONL 생성 (`generate_gold_batch.py`) [신규]

파인튜닝된 모델의 성능을 벤치마킹하기 위해 철저하게 통제된 시나리오와 엣지 케이스를 포함한 80건(8카테고리 $\times$ 10건)의 평가용 배치 파일을 생성합니다. 

```bash
python -m datagen.generate_gold_batch
```
- 실행 시 `data/output/gold_batch_input.jsonl` 경로에 파일이 생성됩니다.
- 이후 스텝에서 `--input` 파라미터로 이 파일을 지정하여 API 제출을 진행할 수 있습니다.

---

### Step 2. Batch API 제출 (`submit_batch.py`)

Step 1에서 만든 JSONL 파일을 OpenAI Batch API(`/v1/responses`)에 제출합니다. 비용을 크게 절감할 수 있으며, 이 스크립트를 통해 진행 상태(`batch_status.json`)를 추적합니다.

```bash
# 제출과 동시에 완료될 때까지 대기
python -m datagen.submit_batch --wait
```

---

### Step 3. 결과 다운로드 (`retrieve_batch.py`)

OpenAI 서버에서 배치 처리가 완료되면 이 스크립트를 사용하여 결과 대화 데이터를 리스트 형태의 JSON 파일(`data/output/result_lst.json`)로 다운로드합니다. 

```bash
python -m datagen.retrieve_batch
```

---

### Step 4. 파싱 및 중간 전처리 (`preprocess.py` & `parse.py`)

다운로드된 텍스트(`result_lst.json`)를 파싱하여 Qwen 계열 모델 등이 필요로 하는 `<tool_call>` 등 XML 태그 형식으로 1차 변환합니다. 
이 단계에서는 데이터 검증(Schema Validation 등)을 쉽게 할 수 있도록 시스템 지시문(`system_prompt`)과 대화 내역(`messages`)을 분리하여 **JSON Lines(`dataset.jsonl`)** 형식으로 저장합니다.

```bash
python -m datagen.preprocess
```

**전처리 후 저장되는 데이터 형태 (`dataset.jsonl` 전체 구조 예시)**:
이 파일은 한 줄(행)이 하나의 완전한 대화 세션 전체 정보를 담고 있는 JSON Lines 형식입니다. 로컬에서 데이터 품질 평가(LLM-as-a-Judge 등)나 스키마 검증 스크립트(`validate.py`)가 읽고 파싱하기 쉽도록 설계되었습니다.

```json
{
  "tools": [
    {"type": "function", "function": {"name": "search_restaurants", "description": "...", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": []}}}
  ],
  "uid": "fac75497-7df8-4902-bda6-066e60a1f5ef",
  "dates": "2026-02-14",
  "system_prompt": "당신은 배달 앱 AI 상담사입니다. 성심성의껏 상담하십시오.\n\n로그인한 사용자의 현재 ID: fac75497-7df8-4902-bda6-066e60a1f5ef\n오늘 날짜: 2026-02-14\n\n# Tools\n\nYou may call one or more functions to assist with the user query.\n\nYou are provided with function signatures within <tools></tools> XML tags:\n<tools>\n{\"type\": \"function\", \"function\": {\"name\": \"search_restaurants\", ...}}\n...</tools>\n\nFor each function call, return a json object with function name and arguments within <tool_call></tool_call> XML tags:\n<tool_call>\n{\"name\": <function-name>, \"arguments\": <args-json-object>}\n</tool_call>",
  "messages": [
    {
      "role": "user",
      "content": "안녕하세요, 짜장면 맛있는 집 좀 찾아주세요."
    },
    {
      "role": "assistant",
      "content": "<tool_call>\n{\"name\": \"search_restaurants\", \"arguments\": {\"query\": \"짜장면\"}}\n</tool_call>"
    },
    {
      "role": "user",
      "content": "<tool_response>\n[{\"items\": [{\"restaurant_id\": \"uuid1\", \"name\": \"홍콩반점\"}]}]\n</tool_response>"
    },
    {
      "role": "assistant",
      "content": "홍콩반점이 주변에 있습니다. 주문하시겠습니까?"
    }
  ]
}
```

---

### Step 5. HF 로컬 데이터 포맷 변환 및 업로드 (`push_to_hub.py`) [신규]

`preprocess.py`가 만든(그리고 데이터 검증을 정상적으로 통과한) `dataset.jsonl` 파일을 읽어들여 HuggingFace Hub에 최종 파인튜닝용으로 업로드합니다.

```bash
python -m datagen.push_to_hub --input data/output/dataset.jsonl --repo-id "your-hf-account/delivery-dataset"
```

**업로드 전 최종 변환되는 HF Dataset의 구조**:
이 단계에서는 데이터셋 형식 변환(`system_prompt`와 `messages` 컬럼 병합 등)을 수행하지 않으며, **`dataset.jsonl`에 있는 컬럼 구조 그대로 HuggingFace Hub에 업로드**됩니다.

- 파인튜닝 시 라이브러리 (예: unsloth, trl 등) 측에서 직접 `dataset["system_prompt"]`와 `dataset["messages"]`를 매핑하여 활용하게 됩니다.
```json
// HF 데이터셋의 레코드 하나가 아래와 같이 구성됨 
{
  "system_prompt": "당신은 배달 앱 AI 상담사...",
  "messages": [
    {
      "role": "user",
      "content": "안녕하세요..."
    },
    ...
  ],
  "uid": "...",
  "dates": "...",
  "tools": [...]
}
```

---

## ⚙️ 설정 관리 가이드 (`config.py` & `prompts.py`)

데이터 생성 시 특정 설정이나 대화 규칙을 제어하려면 위 두 파일을 수정해야 합니다.

*   `datagen/config.py`: 
    *   `USER_IDS`, `QUESTION_TOPICS` (지원 시나리오 모음), `UNSUPPORTED_SCENARIOS` (처리할 수 없는 불만/기타 대응 리스트)
    *   **도구의 스펙(`tools`)과 반환 포맷(`tools_return_format`)**에 대한 명세 관리. 데이터 구조가 변경되면 이 곳을 가장 먼저 수정해야 합니다.
*   `datagen/prompts.py`: 
    *   `SYSTEM_PROMPT_FIXED`: 생성 모델에게 지시하는 상담사의 기본 지침들. 
    *   출력의 모범 형식이 텍스트로 하드-코딩되어 있습니다. 응답의 턴 수를 제어하거나 챗봇의 어투 변경을 원할 경우 여기서 제어하세요.

---

## 📁 파일 구조

```
datagen/
├── __init__.py           # 패키지 초기화
├── config.py             # 설정 (user_ids, 시나리오, tools, tools_return_format)
├── prompts.py            # 시스템 프롬프트 + 유저 프롬프트 빌더
├── generate_batch.py     # Step 1: 파인튜닝용 대량 JSONL 생성
├── generate_gold_batch.py# Step 1-B: 평가용 골드 데이터(80건) JSONL 생성
├── submit_batch.py       # Step 2: 배치 제출
├── retrieve_batch.py     # Step 3: 결과 다운로드
├── parse.py              # 파싱 도구
├── preprocess.py         # Step 4: 파싱 및 jsonl 추출
├── push_to_hub.py        # Step 5: 데이터셋 허브 업로드
├── README.md             # 이 문서
│
└── output/               # ── 단계별 출력 파일 ──
    ├── batch_input.jsonl  # Batch API 입력 파일
    ├── batch_status.json  # 배치 상태 정보
    ├── result_lst.json    # 결과 다운로드 원본 리스트
    └── dataset.jsonl      # 검증용 및 전처리용 데이터셋
```
