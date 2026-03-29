# 배달 앱 AI 상담사 파인튜닝 데이터 생성 파이프라인 (`datagen`)

배달 앱 AI 챗봇 파인튜닝을 위한 **펑션콜링 멀티턴 대화 데이터**를 OpenAI Batch API로 대량 생성하고, 검증 및 허깅페이스 업로드까지 수행하는 파이프라인입니다.

## 사전 준비

```bash
# 필요 패키지
pip install openai pandas datasets python-dotenv
```

OpenAI API 키는 프로젝트 루트의 `.env` 파일에 설정하거나 환경변수로 export합니다.

```bash
# .env 파일 (권장)
OPENAI_API_KEY=sk-...

# 또는 환경변수
export OPENAI_API_KEY="sk-..."
```

---

## 학습용 데이터 생성 파이프라인

파인튜닝에 사용할 대량의 멀티턴 대화 데이터를 생성하고 HuggingFace Hub에 업로드하는 파이프라인입니다.

```text
generate_batch → submit_batch → retrieve_batch → preprocess → render_txt → validate → push_to_hub
```

### Step 1. JSONL 입력 파일 생성 (`generate_batch.py`)

지정된 개수만큼의 대화 요청 시나리오를 생성하여, OpenAI Batch API가 이해할 수 있는 JSONL 형태로 파일을 생성합니다.

```bash
python -m datagen.generate_batch --count 400
```

CLI 인수:
- `--count INT` : 생성할 Batch API 요청 수. 잡담 데이터를 정상 로드한 경우 min(count, 잡담데이터 건수)로 결정. 기본값: 400
- `--output PATH` : 생성된 JSONL 파일 저장 경로. 기본값: train_data/batch_input.jsonl
- `--seed INT` : random 시드값. 동일 시드로 샘플링 결과 재현 가능. 기본값: 42

- **API 호출 없이** 로컬에서 파일만 생성합니다.
- 입력: 없음 (ChatbotData.csv를 원격 URL에서 로드, API 호출 없음)
- 출력: `train_data/batch_input.jsonl`

```json
{
  "custom_id": "req-0",
  "method": "POST",
  "url": "/v1/responses",
  "body": {
    "model": "gpt-5-2025-08-07",
    "instructions": "당신은 배달 앱 AI 상담사 역할을 부여하는 시스템 프롬프트입니다...",
    "input": "[고객 ID] a1661d37-...\n[대화날짜] 2024-05-23\n..."
  }
}
```

### Step 2. Batch API 제출 (`submit_batch.py`)

Step 1에서 만든 JSONL 파일을 OpenAI Batch API에 제출합니다.

```bash
# 제출 후 완료될 때까지 폴링 대기
python -m datagen.submit_batch --wait
```

CLI 인수:
- `--input PATH` : 업로드할 JSONL 파일 경로. 기본값: train_data/batch_input.jsonl
- `--output PATH` : 상태 파일 저장 경로. 기본값: 입력 파일과 같은 디렉터리에 {입력파일명}_status.json
- `--wait` : 배치 완료까지 폴링 대기. 지정하지 않으면 제출 후 즉시 종료
- `--poll-interval N` : 폴링 간격 (초). 기본값: 60

- 입력: `train_data/batch_input.jsonl`
- 출력: `train_data/batch_input_status.json`

```json
{
  "batch_id": "batch_699e7fc6c2c88190bf2b40deb2b7012e",
  "input_file_id": "file-WcrgY9JLGue8J9tdHEvqq9",
  "status": "completed",
  "created_at": "1748000000",
  "output_file_id": "file-AbCdEfGh1234",
  "error_file_id": null
}
```

### Step 3. 결과 다운로드 (`retrieve_batch.py`)

OpenAI 서버에서 배치 처리가 완료되면 결과 대화 데이터를 다운로드합니다.

```bash
python -m datagen.retrieve_batch
```

CLI 인수:
- `--batch-id BATCH_ID` : 배치 ID를 직접 지정. 지정하면 --status-file은 무시됨
- `--status-file PATH` : 배치 상태 파일 경로. 기본값: train_data/batch_input_status.json
- `--output PATH` : 결과 저장 경로. 기본값: train_data/result_lst.json

인수 우선순위: --batch-id를 지정하면 status 파일 없이 해당 ID로 직접 조회. 생략 시 --status-file에서 batch_id를 읽음.

- 입력: `train_data/batch_input_status.json` (batch_id 추출)
- 출력: `train_data/result_lst.json`

```json
[
  "[고객 ID] a1661d37-87bb-44e9-b2b3-ad951c237ba5\n[대화날짜] 2024-05-23\n(고객) 짜장면 맛있는 집 찾아줘\n(function_call) [{\"name\": \"search_restaurants\", \"arguments\": {\"query\": \"짜장면\"}}]\n(function_response) {\"items\": [...]}\n(AI 상담사) 홍콩반점이 인근에 있습니다.",
  "..."
]
```

### Step 4. 파싱 및 전처리 (`preprocess.py`)

다운로드된 텍스트를 파싱하여 Qwen 계열 모델이 필요로 하는 `<tool_call>` 등 XML 태그 형식으로 변환합니다. 시스템 지시문(`system_prompt`)과 대화 내역(`messages`)을 분리하여 JSON Lines 형식으로 저장합니다.

```bash
python -m datagen.preprocess
```

CLI 인수:
- `--input PATH` : 배치 결과 JSON 파일 경로. 기본값: train_data/result_lst.json
- `--output PATH` : 출력 JSONL 파일 경로. 기본값: train_data/dataset.jsonl
- `--seed INT` : random 시드값. 시스템 프롬프트 내 도구 순서 셔플에 사용. 기본값: 42

- 입력: `train_data/result_lst.json`
- 출력: `train_data/dataset.jsonl`

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

### Step 5. 샘플 텍스트 내보내기 (`render_txt.py`)

`dataset.jsonl`의 각 레코드를 Qwen chat template 형식의 `.txt` 파일로 변환하여 저장합니다. 데이터를 육안으로 확인하거나 디버깅할 때 활용합니다.

```bash
python -m datagen.render_txt
```

CLI 인수:
- `--input PATH` : 입력 JSONL 파일 경로. 기본값: train_data/dataset.jsonl
- `--output PATH` : 출력 디렉토리 경로. 기본값: 입력 파일과 같은 폴더의 samples/

- 입력: `train_data/dataset.jsonl`
- 출력: `train_data/samples/sample_0001.txt`, `sample_0002.txt`, ...

```text
<|im_start|>system
당신은 배달 앱 AI 상담사입니다...
<tools>
{"type": "function", "function": {"name": "search_restaurants", ...}}
...
</tools>
<|im_end|>
<|im_start|>user
짜장면 맛있는 집 찾아줘
<|im_end|>
<|im_start|>assistant
<tool_call>
{"name": "search_restaurants", "arguments": {"query": "짜장면"}}
</tool_call>
<|im_end|>
<|im_start|>user
<tool_response>
{"items": [{"restaurant_id": "uuid1", "name": "홍콩반점", ...}]}
</tool_response>
<|im_end|>
<|im_start|>assistant
홍콩반점이 인근에 있습니다. 주문하시겠습니까?
<|im_end|>
```

### Step 6. 데이터 유효성 검증 (`datavalidator.validate`)

render_txt로 생성된 ChatML .txt 파일의 형식과 스키마를 검증한다.

```bash
# 검증만
python -m datavalidator.validate --target_dir train_data/samples/

# 검증 + 실패 샘플 삭제
python -m datavalidator.validate \
    --target_dir train_data/samples/ \
    --purge \
    --dataset train_data/dataset.jsonl
```

CLI 인수:
- `--target_dir PATH` : 검증할 .txt 파일이 있는 디렉토리 (필수)
- `--purge` : 검증 실패 샘플의 .txt 및 dataset.jsonl 레코드 삭제
- `--dataset PATH` : --purge 시 레코드를 삭제할 dataset.jsonl 경로

검증 항목:
- format: `<|im_start|>`/`<|im_end|>` 페어링, 연속 역할 검사
- schema: `<tool_call>` JSON 구조, 파라미터 타입 검증
- content: 사용자 발화 기반 추론 불가 파라미터(환각) 탐지

### Step 7. HuggingFace Hub 업로드 (`push_to_hub.py`)

전처리가 완료된 `dataset.jsonl`을 HuggingFace Hub에 업로드합니다.

```bash
python -m datagen.push_to_hub --input train_data/dataset.jsonl --repo-id "your-hf-account/delivery-dataset"
```

CLI 인수:
- `--input PATH` : 업로드할 로컬 데이터 파일 경로. 기본값: train_data/dataset.jsonl
- `--repo-id TEXT` : HuggingFace Hub 리포 이름 (필수). 예: "my-org/dataset-name"

---

## 평가용 골드 데이터 생성 파이프라인

파인튜닝된 모델의 성능을 벤치마킹하기 위한 별도 파이프라인입니다.

```text
generate_gold_batch → submit_batch → retrieve_batch → preprocess → render_txt → validate
```

### Step 1. 평가용 골드 배치 생성 (`generate_gold_batch.py`)

8개 카테고리 × 10건 = **80건**의 평가 전용 배치 파일을 생성합니다.

| 카테고리 | 설명 |
| -------- | ---- |
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

CLI 인수:
- `--output PATH` : 생성된 JSONL 파일 저장 경로. 기본값: eval_data/gold_batch_input.jsonl
- `--seed INT` : random 시드값. USER_IDS 샘플링 결과 재현용. 기본값: 42
- `--count INT` : 카테고리당 생성 개수. 지정하면 모든 카테고리의 count를 이 값으로 덮어씀. 미지정 시 각 카테고리 기본값 사용

- 출력: `eval_data/gold_batch_input.jsonl`

### Step 2. Batch API 제출 — 평가용 (`submit_batch.py`)

```bash
python -m datagen.submit_batch \
    --input eval_data/gold_batch_input.jsonl \
    --output eval_data/gold_batch_input_status.json \
    --wait
```

- 입력: `eval_data/gold_batch_input.jsonl`
- 출력: `eval_data/gold_batch_input_status.json`

### Step 3. 결과 다운로드 — 평가용 (`retrieve_batch.py`)

```bash
python -m datagen.retrieve_batch \
    --status-file eval_data/gold_batch_input_status.json \
    --output eval_data/result_lst.json
```

- 입력: `eval_data/gold_batch_input_status.json`
- 출력: `eval_data/result_lst.json`

### Step 4. 파싱 및 전처리 — 평가용 (`preprocess.py`)

```bash
python -m datagen.preprocess \
    --input  eval_data/result_lst.json \
    --output eval_data/dataset.jsonl
```

- 입력: `eval_data/result_lst.json`
- 출력: `eval_data/dataset.jsonl`

### Step 5. 샘플 텍스트 내보내기 — 평가용 (`render_txt.py`)

```bash
python -m datagen.render_txt \
    --input  eval_data/dataset.jsonl \
    --output eval_data/samples
```

- 입력: `eval_data/dataset.jsonl`
- 출력: `eval_data/samples/sample_0001.txt`, `sample_0002.txt`, ...

### Step 6. 데이터 유효성 검증 — 평가용 (`datavalidator.validate`)

```bash
# 검증만
python -m datavalidator.validate --target_dir eval_data/samples/

# 검증 + 실패 샘플 삭제
python -m datavalidator.validate \
    --target_dir eval_data/samples/ \
    --purge \
    --dataset eval_data/dataset.jsonl
```

---

## 설정 관리 (`config.py` & `prompts.py`)

| 파일 | 주요 내용 |
| ---- | --------- |
| `config.py` | `USER_IDS`, `QUESTION_TOPICS`, `UNSUPPORTED_SCENARIOS`, `GOLD_CATEGORIES`, 도구 명세(`tools`), 반환 포맷(`tools_return_format`). **데이터 구조가 변경되면 이 파일을 가장 먼저 수정합니다.** |
| `prompts.py` | `SYSTEM_PROMPT_FIXED` (상담사 기본 지침). 응답 턴 수 제어 또는 어투 변경 시 이 파일을 수정합니다. |

---

## 파일 구조

```text
datagen/
├── __init__.py                  # 패키지 초기화
├── config.py                    # 설정 (user_ids, 시나리오, tools, tools_return_format)
├── prompts.py                   # 시스템 프롬프트 + 유저 프롬프트 빌더
├── generate_batch.py            # 학습용 Step 1: 대량 JSONL 생성
├── generate_gold_batch.py       # 평가용 Step 1: 골드 데이터(80건) JSONL 생성
├── submit_batch.py              # Step 2: 배치 제출 (학습·평가 공용)
├── retrieve_batch.py            # Step 3: 결과 다운로드 (학습·평가 공용)
├── retry_failed_batch.py        # 실패한 배치 요청 재추출
├── preprocess.py                # 학습용 Step 4: 파싱 및 jsonl 추출
├── render_txt.py                # 학습용 Step 5: dataset.jsonl → 개별 .txt 파일
├── push_to_hub.py               # 학습용 Step 6: 데이터셋 허브 업로드
├── README.md                    # 이 문서
│
├── train_data/                  # 학습용 단계별 출력 파일 (git-ignored)
│   ├── batch_input.jsonl        # 학습용 Batch API 입력 파일
│   ├── batch_input_status.json  # 학습용 배치 상태 정보
│   ├── result_lst.json          # 결과 다운로드 원본 리스트
│   ├── dataset.jsonl            # 전처리 완료 데이터셋
│   └── samples/                 # render_txt.py 출력 디렉터리
│
└── eval_data/                        # 평가용 단계별 출력 파일 (git-ignored)
    ├── gold_batch_input.jsonl        # 평가용 Batch API 입력 파일
    ├── gold_batch_input_status.json  # 평가용 배치 상태 정보
    ├── result_lst.json               # 결과 다운로드 원본 리스트
    ├── dataset.jsonl                 # 전처리 완료 데이터셋
    └── samples/                      # render_txt.py 출력 디렉터리
```
