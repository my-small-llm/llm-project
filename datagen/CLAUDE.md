## 제약 조건

- `.env` 파일 읽기 금지
- `tool_specs.py` 변경 시 `datavalidator/rules/schema.py`와 `evaluations/` tool_schemas 영향 반드시 함께 검토
- `train_data/`, `eval_data/` 산출물은 git-ignore 대상 — 커밋하지 않는다
- Batch API 제출(`submit_batch.py`)은 비용 발생 — 사용자가 명시적으로 요청한 경우만 실행

## 이 폴더의 역할

OpenAI Batch API를 통해 배달 앱 function calling 학습·평가 데이터를 대량 생성한다. `tool_specs.py`가 함수 계약의 단일 원본(SSoT)이며, datavalidator·evaluations 모두 이 파일에 의존한다.

## 디렉터리 지도

```
config.py            USER_IDS, 시나리오, 골드 카테고리 등 생성 설정
tool_specs.py        함수 계약 SSoT (tools, 반환 포맷, validator stub)
prompts.py           SYSTEM_PROMPT_FIXED, 유저 프롬프트 빌더
generate_batch.py    학습용 Step 1: 대량 JSONL 생성
generate_gold_batch.py  평가용 Step 1: 골드 데이터(80건) 생성
submit_batch.py      Step 2: 배치 제출 (학습·평가 공용)
retrieve_batch.py    Step 3: 결과 다운로드 (학습·평가 공용)
preprocess.py        Step 4: 파싱 → dataset.jsonl 추출
render_txt.py        Step 5: dataset.jsonl → 개별 .txt 파일
push_to_hub.py       Step 7: 데이터셋 HuggingFace Hub 업로드
retry_failed_batch.py   실패 배치 요청 재추출
strip_search_pagination.py  페이지네이션 파라미터 제거 스크립트
```

## 작업 흐름

### 학습 데이터

```
generate_batch → submit_batch → retrieve_batch → preprocess → render_txt
  → datavalidator.validate → push_to_hub
```

### 평가 데이터

```
generate_gold_batch → submit_batch → retrieve_batch → preprocess → render_txt
  → datavalidator.validate
```

함수 계약 변경 시 순서: `tool_specs.py` 수정 → `config.py`의 `tools` 업데이트 → datavalidator·evaluations 영향 확인

## 도구

```bash
# 학습 데이터 생성
python -m datagen.generate_batch --count 400

# 배치 제출 (비용 발생 — 명시적 요청 시만)
python -m datagen.submit_batch --wait

# 결과 다운로드
python -m datagen.retrieve_batch

# 전처리 (ChatML JSONL 추출)
python -m datagen.preprocess

# .txt 샘플 내보내기
python -m datagen.render_txt

# 검증
python -m datavalidator.validate --target_dir train_data/samples/

# HuggingFace Hub 업로드
python -m datagen.push_to_hub --input train_data/dataset.jsonl --repo-id "org/repo-name"
```

## 도메인 컨텍스트

- `tool_call`: `<tool_call>\n{"name": "...", "arguments": {...}}\n</tool_call>` XML 블록
- `tool_response`: `<tool_response>\n{...}\n</tool_response>` XML 블록
- `dataset.jsonl` 레코드: `tools`, `uid`, `dates`, `system_prompt`, `messages` 필드 포함
- 골드 데이터: 8개 카테고리 × 10건 = 80건 고정 평가셋

## 폴더별 규칙

- `tool_specs.py`가 유일한 함수 계약 원본 — 시그니처 변경 시 이 파일만 수정하고 나머지는 import로 해결
- `prompts.py`만 수정해도 응답 어투·턴 수 변경 가능
- `config.py`의 `tools` 리스트는 `tool_specs.py`의 함수 목록과 항상 동기화 유지
