# train — Qwen Function-Calling SFT 학습 모듈

Qwen2.5-7B-Instruct 모델을 **QLoRA (4-bit NF4 양자화) + SFT(Supervised Fine-Tuning)**로 학습하는 패키지입니다.
배달앱 Function-Calling 데이터셋을 사용하여 모델이 도구 호출(tool calling) 응답을 생성하도록 미세조정합니다.

학습 설정은 프로젝트 루트의 [`.env`](.env)에서 읽습니다.
`train/config.py`가 `.env`를 자동 로드하므로, 별도 export 없이 값만 수정해도 됩니다.

## 디렉토리 구조

```
train/
├── README.md              # 이 문서
├── __init__.py             # 패키지 초기화
├── config.py               # TrainConfig — 하이퍼파라미터 및 QLoRA/LoRA 설정 관리
├── data.py                 # 데이터셋 로드 및 train/test 분할
├── collator.py             # ChatMLCollator — assistant 응답만 레이블링
├── run.py                  # 학습 실행 스크립트 (CLI 진입점)
├── vram_analysis.md        # CUDA OOM 원인 분석 및 allocator 튜닝 기록 (LoRA vs QLoRA 비교 포함)
├── data_analysis.ipynb     # 데이터셋 분포 분석 노트북

```

## 실행 방법

```bash
# reserved 메모리 단편화로 인한 CUDA OOM 완화
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128

# uv 가상환경 활성화 상태에서 학습 실행
python -m train.run
```

한 줄로 실행하려면:

```bash
PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128 python -m train.run
```

실행 전에 프로젝트 루트의 [`.env`](.env)를 확인하세요.

```bash
# 예시
TRAIN_MODEL_ID=Qwen/Qwen2.5-7B-Instruct
TRAIN_DATASET_ID=jjun123/deliveryapp-traindata-100
TRAIN_OUTPUT_DIR=qwen-2.5-7b-function-calling
TRAIN_REPORT_TO=wandb
WANDB_PROJECT=deliveryapp-sft
WANDB_NAME=qwen2.5-7b-lora-run1
```

학습 로그는 기본적으로 **Weights & Biases (wandb)**에 기록됩니다.
비활성화하려면 `.env`에서 `TRAIN_REPORT_TO=none`으로 설정하세요.

`Qwen/Qwen2.5-7B-Instruct`를 긴 시퀀스로 학습할 때는 PyTorch allocator의 reserved 메모리 단편화 때문에 OOM이 날 수 있습니다.
그 경우 위의 `PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128` 설정을 함께 사용하는 것을 권장합니다.

> 배경 및 원인 분석: [vram_analysis.md](vram_analysis.md)

## 학습 파이프라인 요약

```
1. 데이터 로드 (HuggingFace Hub)
   └→ system_prompt를 messages에 삽입, train/test 분할

2. 모델 로드 (QLoRA 4-bit 양자화)
   └→ NF4 양자화로 14.2GB → 3.5GB 압축

3. 배치 준비 (ChatMLCollator)
   └→ assistant 응답만 labels에 반영, 나머지 -100 마스킹

4. SFTTrainer 학습
   └→ CrossEntropyLoss (labels ≠ -100인 토큰만)
   └→ LoRA 어댑터 파라미터만 업데이트

5. 모델 저장
   └→ 어댑터 가중치만 저장 (~수 MB)
```

## 모듈 설명

### `config.py` — TrainConfig

모든 학습 관련 설정을 `@dataclass`로 관리합니다.
기본값은 코드에 내장되어 있지만, 실제 실행 시에는 먼저 [`.env`](.env)의 `TRAIN_*` 값을 읽어 override합니다.

#### 모델 / 데이터셋

| 항목             | 기본값                              | 설명                 |
| ---------------- | ----------------------------------- | -------------------- |
| `model_id`       | `Qwen/Qwen2.5-7B-Instruct`          | 베이스 모델          |
| `dataset_id`     | `jjun123/deliveryapp-traindata-100` | HuggingFace 데이터셋 |
| `output_dir`     | `qwen-2.5-7b-function-calling`      | 체크포인트 저장 경로 |
| `test_ratio`     | `0.2`                               | test 분할 비율       |
| `max_seq_length` | `8192`                              | 최대 시퀀스 길이     |

#### QLoRA (4-bit 양자화)

| 항목                        | 기본값       | 설명                                            |
| --------------------------- | ------------ | ----------------------------------------------- |
| `use_qlora`                 | `True`       | QLoRA 사용 여부 (`False`로 일반 LoRA 전환 가능) |
| `bnb_4bit_quant_type`       | `"nf4"`      | 양자화 타입 (NormalFloat4 권장)                 |
| `bnb_4bit_compute_dtype`    | `"bfloat16"` | 연산 정밀도                                     |
| `bnb_4bit_use_double_quant` | `True`       | 이중 양자화 (추가 메모리 절약)                  |

#### LoRA

| 항목                  | 기본값                                     | 설명                         |
| --------------------- | ------------------------------------------ | ---------------------------- |
| `lora_r`              | `8`                                        | LoRA rank                    |
| `lora_alpha`          | `32`                                       | LoRA 스케일링 계수           |
| `lora_dropout`        | `0.1`                                      | LoRA 드롭아웃                |
| `lora_target_modules` | `["q_proj", "k_proj", "v_proj", "o_proj"]` | LoRA 적용 대상 (어텐션 전체) |

#### SFT 학습

| 항목                          | 기본값               | 설명                          |
| ----------------------------- | -------------------- | ----------------------------- |
| `num_epochs`                  | `3`                  | 학습 에포크 수                |
| `batch_size`                  | `1`                  | GPU당 배치 크기               |
| `gradient_accumulation_steps` | `2`                  | 그래디언트 누적 (유효 배치=2) |
| `gradient_checkpointing`      | `True`               | 활성화 재계산으로 메모리 절약 |
| `optim`                       | `"paged_adamw_8bit"` | 8비트 페이지드 옵티마이저     |
| `learning_rate`               | `1e-4`               | 학습률                        |
| `lr_scheduler_type`           | `"constant"`         | 학습률 스케줄러               |

#### 로깅 / 저장

| 항목            | 기본값    | 설명                      |
| --------------- | --------- | ------------------------- |
| `logging_steps` | `10`      | 로그 출력 간격            |
| `save_strategy` | `"steps"` | 체크포인트 저장 전략      |
| `save_steps`    | `50`      | 체크포인트 저장 간격      |
| `push_to_hub`   | `False`   | HuggingFace Hub 푸시 여부 |
| `report_to`     | `"wandb"` | 로깅 대상 (`"wandb"`, `"none"` 등) |

추가로 wandb 관련 환경변수도 [`.env`](.env)에서 관리합니다.

| 환경변수 | 예시 | 설명 |
| -------- | ---- | ---- |
| `WANDB_PROJECT` | `deliveryapp-sft` | W&B 프로젝트 이름 |
| `WANDB_NAME` | `qwen2.5-7b-lora-run1` | 실행(run) 이름 |
| `WANDB_LOG_MODEL` | `false` | 모델 아티팩트 로깅 여부 |
| `WANDB_API_KEY` | 선택 | `wandb login` 대신 직접 지정할 때만 사용 |

팩토리 메서드:
- `get_bnb_config()` → `BitsAndBytesConfig` 반환 (`use_qlora=False`이면 `None`)
- `get_lora_config()` → `peft.LoraConfig` 반환
- `get_sft_config()` → `trl.SFTConfig` 반환

### `data.py` — 데이터 전처리

- `format_conversations(sample)`: `system_prompt` + `messages`를 OpenAI messages 포맷으로 변환
- `load_and_split(dataset_id, test_ratio)`: 데이터셋 로드 → 앞 20% test, 뒤 80% train 분할

### `collator.py` — ChatMLCollator

학습 시 **assistant 응답 부분만 레이블링**하는 핵심 전처리 로직입니다.

```
입력:  <|im_start|>system\n...<|im_end|><|im_start|>user\n...<|im_end|><|im_start|>assistant\n응답<|im_end|>
labels:     -100 (무시)                    -100 (무시)                  -100        실제토큰ID    
                                                                    (헤더 무시)   (학습 대상!)
```

동작 순서:
1. messages를 Qwen ChatML 형식으로 조합
2. 토크나이저로 인코딩 (truncation=max_seq_length)
3. `<|im_start|>assistant\n` ~ `<|im_end|>` 구간만 labels에 복사
4. 나머지는 `-100`으로 마스킹
5. 배치 내 패딩 + 텐서 변환

### `run.py` — 학습 파이프라인

`main()` 함수 실행 순서:

1. `TrainConfig` 생성
2. `load_and_split()`으로 데이터 준비
3. 모델 로드 (`QLoRA` 사용 시 NF4 4-bit 양자화 적용)
4. `ChatMLCollator` + `LoraConfig` + `SFTConfig` 구성
5. `SFTTrainer.train()` 실행 → `save_model()` 저장

## 설정 변경 방법

대부분의 실험 설정은 [`.env`](.env)만 수정하면 됩니다.

```bash
# 예시: 출력 경로와 학습률 변경
TRAIN_OUTPUT_DIR=qwen-2.5-7b-function-calling-exp2
TRAIN_LEARNING_RATE=5e-5
TRAIN_NUM_EPOCHS=5
```

대표적으로 조정 가능한 항목:
- `TRAIN_MODEL_ID`
- `TRAIN_DATASET_ID`
- `TRAIN_OUTPUT_DIR`
- `TRAIN_MAX_SEQ_LENGTH`
- `TRAIN_USE_QLORA`
- `TRAIN_BATCH_SIZE`
- `TRAIN_GRADIENT_ACCUMULATION_STEPS`
- `TRAIN_LEARNING_RATE`
- `TRAIN_REPORT_TO`

## 참고할 학습 계획

| eff batch | LR     | LoRA rank (r) | alpha | max_grad_norm | epoch | 왜 이렇게 설정하나 (핵심 이유) |
| --------- | ------ | ------------- | ----- | ------------- | ----- | ------------------------------ |
| 1         | 2.5e-4 | 64            | 32    | 0.7           | 3     | batch가 매우 작아 noise가 큼 → LR을 크게 해서 학습 진행 속도 확보 / noise로 튀는 step 많으므로 clipping 완화(0.7) / rank는 capacity 유지용 (noise 환경에서 rank 영향 거의 없음) |
| 2         | 2e-4   | 64            | 32    | 0.5           | 4     | 여전히 noisy → LR 높게 유지 / batch=1보다 안정적이라 clipping 약간 강화 / alpha로 update scale 확보 / 빠른 수렴용 |
| 4         | 1.5e-4 | 64            | 32    | 0.5           | 5     | noise 감소 시작 → LR 줄여 overshoot 방지 / 아직 exploration 필요해서 alpha 유지 / clipping 안정 유지 |
| 8         | 1.2e-4 | 64            | 64    | 0.5           | 6     | gradient 안정화 → LR 더 낮춤 / 대신 alpha 증가로 update scale 보정 / rank는 그대로 (성능 영향 적음) |
| 16        | 1e-4   | 64            | 64    | 0.5           | 8     | 안정적인 gradient → LR standard 값 / alpha로 충분한 update 확보 / clipping 안정 유지 / production baseline |
| 32        | 8e-5   | 64            | 64    | 0.7           | 10    | gradient 거의 deterministic → LR 낮춰 정밀 수렴 / batch 커서 update 약해지므로 alpha 유지 / 긴 학습 필요 / 드물게 큰 grad 나올 수 있어 clipping 완화 |

## wandb 메모

- `TRAIN_REPORT_TO=wandb`이면 wandb 로깅이 활성화됩니다.
- `wandb login`이 이미 되어 있으면 `WANDB_API_KEY`는 없어도 됩니다.
- 계정을 강제로 바꾸고 싶을 때만 `.env`에 `WANDB_API_KEY`를 넣으면 됩니다.
