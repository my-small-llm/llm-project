## 제약 조건

- GPU/CUDA 환경 필수 (`runner.py`는 vLLM 사용)
- 메트릭 코드 수정 후 추론 재실행 금지 — `--inference-only`로 predictions 저장 후 `scorer.py`로 스코어링
- `predictions.jsonl`, `eval_results.*`는 중간 산출물로 git-ignore 대상 — 커밋하지 않는다
- `.env` 파일 읽기 금지 (OPENAI_API_KEY 포함)

## 이 폴더의 역할

GT 히스토리 기반 싱글턴 분할로 파인튜닝 모델의 tool calling 능력을 7단계 의존 체인 메트릭으로 평가한다. vLLM 추론(`runner.py`)과 OpenAI API 추론(`api_runner.py`)을 모두 지원한다.

## 디렉터리 지도

```
runner.py           vLLM 추론 + 스코어링 통합 실행기
api_runner.py       OpenAI API 추론 + 스코어링 통합 실행기
scorer.py           predictions.jsonl 기반 독립 스코어링
metrics.py          Tool Call Level 7단계 메트릭 계산
multi_turn_metrics.py  Turn / Conversation Level 집계
turn_splitter.py    GT 히스토리 기반 싱글턴 분할 핵심 로직
preprocessing.py    데이터셋 → 평가 입력 형식 변환 유틸
convert_readable.py predictions.jsonl → 가독성 텍스트 변환
```

## 작업 흐름

메트릭 코드 변경 시:
```bash
# 1. predictions 1회 저장
python -m evaluations.runner --model <model> --dataset eval_data/dataset.jsonl \
    --output eval_output --inference-only --seed 42

# 2. 수정 전 스코어링
python -m evaluations.scorer --predictions eval_output/predictions.jsonl \
    --dataset eval_data/dataset.jsonl --output eval_output_before

# 3. 코드 수정 후 동일 predictions로 재스코어링
python -m evaluations.scorer --predictions eval_output/predictions.jsonl \
    --dataset eval_data/dataset.jsonl --output eval_output_after
```

## 도구

```bash
# 기본 추론 + 스코어링
python -m evaluations.runner \
    --model Qwen/Qwen2.5-7B-Instruct \
    --dataset eval_data/dataset.jsonl \
    --output eval_output

# LoRA 어댑터 적용
python -m evaluations.runner \
    --model Qwen/Qwen2.5-7B-Instruct \
    --lora outputs/default \
    --max-model-len 8192 \
    --dataset eval_data/dataset.jsonl \
    --output eval_output_lora

# OpenAI API 모델 평가
python -m evaluations.api_runner \
    --model gpt-4o \
    --dataset eval_data/dataset.jsonl \
    --output eval_output_api

# predictions를 가독성 텍스트로 변환
python -m evaluations.convert_readable --predictions eval_output/predictions.jsonl
```

## 도메인 컨텍스트

7단계 의존 체인 (앞 단계 실패 시 뒷 단계 분모에서 제외):
1. relevance_detection_acc — tool call 필요 여부 판단
2. format_compliance_acc — JSON 형식 유효성
3. function_matching_acc — 함수 이름 일치
4. param_hallucination_acc — 스키마 미정의 파라미터 사용 여부
5. required_params_acc — 필수 파라미터 포함 여부
6. argument_type_acc — 파라미터 타입 일치
7. argument_value_acc — 파라미터 값 exact match

## 폴더별 규칙

- `turn_splitter.py`는 GT 히스토리 기반 분할 핵심 로직 — 변경 시 sequential call 처리 영향 필수 확인
- `metrics.py`의 7단계 체인은 순서 의존성 있음 — 단계 순서·분모 변경 시 전후 비교 테스트 필수
- `scorer.py`는 `runner.py`와 독립 실행 가능 — predictions.jsonl만 있으면 GPU 없이도 스코어링 가능
