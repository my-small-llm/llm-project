# llm-project

배달 앱 AI 상담사를 위한 멀티턴 Function Calling 파인튜닝 파이프라인.
OpenAI Batch API로 학습 데이터를 생성하고, Qwen2.5-7B-Base를 QLoRA SFT로 학습한 뒤 GT 히스토리 기반 7단계 메트릭으로 tool calling 정확도를 평가한다.

## 파이프라인 구조

```
datagen        OpenAI Batch API → 멀티턴 Function Calling 데이터 생성
  └→ datavalidator   format / schema / content 검증
       └→ dataanalyzer    데이터셋 품질·분포 분석
            └→ HuggingFace Hub 업로드
                 └→ train         QLoRA SFT (Qwen2.5-7B-Base)
                      └→ evaluations  7단계 tool calling 메트릭 평가
```

## 디렉터리 구조

```
datagen/        데이터 생성 파이프라인 (Batch API → ChatML JSONL)
datavalidator/  생성 데이터 검증
dataanalyzer/   데이터셋 품질·분포 분석 및 시각화
evaluations/    vLLM·OpenAI API 추론 + 7단계 메트릭 평가
train/          QLoRA SFT 학습 파이프라인
docs/           설계 문서, 메트릭 리포트, 트러블슈팅 기록
eval_data/      평가 기준 gold 데이터셋 (git-tracked)
```

## 환경 설정

```bash
uv python install 3.10.12
uv sync
source .venv/bin/activate
```

의존성 변경 후에는 `uv lock` 재실행 → `pyproject.toml`, `uv.lock` 함께 커밋.

## 주요 실행 명령

```bash
# vLLM 추론 + 스코어링 (GPU 필요)
python -m evaluations.runner \
    --model Qwen/Qwen2.5-7B-Instruct \
    --dataset eval_data/dataset.jsonl \
    --output eval_output

# LoRA 어댑터 적용 평가
python -m evaluations.runner \
    --model Qwen/Qwen2.5-7B-Instruct \
    --lora outputs/default \
    --dataset eval_data/dataset.jsonl \
    --output eval_output_lora

# OpenAI API 모델 평가
python -m evaluations.api_runner \
    --model gpt-4o \
    --dataset eval_data/dataset.jsonl \
    --output eval_output_api
```

## 평가 메트릭 (7단계 의존 체인)

앞 단계 실패 시 뒷 단계 분모에서 제외된다.

| 단계 | 지표 | 설명 |
|---:|---|---|
| 1 | relevance_detection_acc | tool call 필요 여부 판단 |
| 2 | format_compliance_acc | JSON 형식 유효성 |
| 3 | function_matching_acc | 함수 이름 일치 |
| 4 | param_hallucination_acc | 스키마 미정의 파라미터 사용 여부 |
| 5 | required_params_acc | 필수 파라미터 포함 여부 |
| 6 | argument_type_acc | 파라미터 타입 일치 |
| 7 | argument_value_acc | 파라미터 값 exact match |

최종 성능 결과: [`docs/result_report.md`](docs/result_report.md)

## 참고

- `evaluations/runner.py`는 vLLM 사용 → GPU + CUDA 런타임 필수
- `datagen/tool_specs.py`는 함수 계약의 단일 원본(SSoT) — 변경 시 `datavalidator`, `evaluations` 함께 검증
- 각 모듈의 상세 설명과 실행 방법은 해당 폴더의 `CLAUDE.md` 참고
