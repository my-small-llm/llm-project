# Function Calling 학습 데이터 생성 파이프라인

배달 앱 AI 챗봇 파인튜닝을 위한 **펑션콜링 멀티턴 대화 데이터**를 OpenAI Batch API로 대량 생성하는 파이프라인입니다.

## 사전 준비

```bash
# 필요 패키지
pip install openai pandas

# OpenAI API 키 설정
export OPENAI_API_KEY="sk-..."
```

## 파이프라인 실행

### Step 1. JSONL 입력 파일 생성

```bash
python -m data.generate_batch --count 400
```

| 옵션       | 설명               | 기본값                   |
| ---------- | ------------------ | ------------------------ |
| `--count`  | 생성할 요청 수     | 400                      |
| `--output` | 출력 파일 경로     | `data/batch_input.jsonl` |
| `--seed`   | 랜덤 시드 (재현성) | 42                       |

- 잡담 CSV 데이터를 자동 다운로드하여 unsupported scenario에 활용합니다.
- 각 요청은 랜덤한 user_id, 시나리오, 날짜, complain 여부로 구성됩니다.
- **API 호출 없이** 로컬에서 JSONL 파일만 생성합니다.

---

### Step 2. Batch API 제출

```bash
# 제출만 (백그라운드 실행)
python -m data.submit_batch

# 제출 + 완료 대기
python -m data.submit_batch --wait
```

| 옵션              | 설명                | 기본값                   |
| ----------------- | ------------------- | ------------------------ |
| `--input`         | 업로드할 JSONL 경로 | `data/batch_input.jsonl` |
| `--wait`          | 완료까지 폴링 대기  | off                      |
| `--poll-interval` | 폴링 간격 (초)      | 60                       |

- 배치 ID와 상태를 `data/batch_status.json`에 저장합니다.
- Batch API는 일반 API 대비 **50% 비용 절감** + 높은 rate limit을 제공합니다.

---

### Step 3. 결과 다운로드

```bash
python -m data.retrieve_batch
```

| 옵션         | 설명                | 기본값                       |
| ------------ | ------------------- | ---------------------------- |
| `--batch-id` | 배치 ID (수동 지정) | `batch_status.json`에서 로드 |
| `--output`   | 결과 저장 경로      | `data/result_lst.json`       |

- 성공한 결과는 `data/result_lst.json`에 저장됩니다.
- 실패한 요청은 `data/batch_errors.json`에 기록됩니다.

---

### Step 4. 파싱 및 전처리

```bash
# 로컬 parquet 저장
python -m data.preprocess

# HuggingFace Hub에도 업로드
python -m data.preprocess --push-to-hub "wonjun/delivery-app-function-calling-datasets-korean"
```

| 옵션            | 설명                      | 기본값                 |
| --------------- | ------------------------- | ---------------------- |
| `--input`       | result_lst.json 경로      | `data/result_lst.json` |
| `--output`      | parquet 저장 경로         | `data/dataset.parquet` |
| `--push-to-hub` | HuggingFace Hub 리포 이름 | (미지정 시 로컬만)     |
| `--seed`        | 도구 셔플 시드            | 42                     |

- `result_lst.json`의 텍스트를 **Qwen 파인튜닝용 messages 형식**으로 파싱합니다.
- 각 대화에 Qwen Function Calling 시스템 프롬프트(`<tools>` 태그 포함)를 생성합니다.

---

## 파일 구조

```
data/
├── __init__.py           # 패키지 초기화
├── config.py             # 설정 (user_ids, 시나리오, tools, tools_return_format)
├── prompts.py            # 시스템 프롬프트 + 유저 프롬프트 빌더
├── generate_batch.py     # Step 1: JSONL 생성
├── submit_batch.py       # Step 2: 배치 제출
├── retrieve_batch.py     # Step 3: 결과 다운로드
├── parse.py              # 파싱 (메타데이터 + Qwen 포맷 변환)
├── preprocess.py         # Step 4: 전처리 + HuggingFace 업로드
├── README.md             # 이 문서
│
└── output/               # ── 생성되는 파일 (코드와 분리) ──
    ├── batch_input.jsonl  # Batch API 입력 파일
    ├── batch_status.json  # 배치 상태 정보
    ├── batch_errors.json  # 에러 로그
    ├── result_lst.json    # 원본 대화 텍스트 목록
    └── dataset.parquet    # 최종 파인튜닝 데이터셋
```

## 전체 흐름 요약

```
generate_batch  →  batch_input.jsonl  →  submit_batch  →  retrieve_batch  →  result_lst.json  →  preprocess  →  dataset.parquet
 (JSONL 생성)                            (API 제출)       (결과 다운로드)     (원본 텍스트)        (파싱+변환)     (파인튜닝용)
```

## 참고

- **모델**: `gpt-5-2025-08-07`
- **API**: OpenAI Responses API (`/v1/responses`)
- **Batch 처리 시간**: 최대 24시간 (보통 수십 분 내 완료)
- 결과물(`result_lst.json`)은 이후 **파싱 및 전처리** 단계에서 Qwen 파인튜닝 포맷으로 변환합니다.
