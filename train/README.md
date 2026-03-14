# train — Qwen Function-Calling SFT 학습 모듈

Qwen2.5-7B-Instruct 모델을 **QLoRA (4-bit NF4 양자화) + SFT(Supervised Fine-Tuning)**로 학습하는 패키지입니다.
배달앱 Function-Calling 데이터셋을 사용하여 모델이 도구 호출(tool calling) 응답을 생성하도록 미세조정합니다.

## 디렉토리 구조

```
train/
├── README.md              # 이 문서
├── __init__.py             # 패키지 초기화
├── config.py               # TrainConfig — 하이퍼파라미터 및 QLoRA/LoRA 설정 관리
├── data.py                 # 데이터셋 로드 및 train/test 분할
├── collator.py             # ChatMLCollator — assistant 응답만 레이블링
├── run.py                  # 학습 실행 스크립트 (CLI 진입점)
├── vram_analysis.md        # VRAM 메모리 분석 문서 (LoRA vs QLoRA 비교)
├── data_analysis.ipynb     # 데이터셋 분포 분석 노트북

```

## 실행 방법

```bash
# uv 가상환경 활성화 상태에서
python -m train.run
```

> 학습 로그는 **Weights & Biases (wandb)**에 자동 기록됩니다.
> `config.py`에서 `report_to=None`으로 설정하면 비활성화됩니다.

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

#### 모델 / 데이터셋

| 항목             | 기본값                              | 설명                 |
| ---------------- | ----------------------------------- | -------------------- |
| `model_id`       | `Qwen/Qwen2.5-7B-Instruct`          | 베이스 모델          |
| `dataset_id`     | `jjun123/deliveryapp-traindata-100` | HuggingFace 데이터셋 |
| `output_dir`     | `qwen-2.5-7b-function-calling`      | 체크포인트 저장 경로 |
| `max_seq_length` | `4096`                              | 최대 시퀀스 길이     |

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
| `report_to`     | `None`    | 로깅 대상 (`"wandb"` 등)  |

> wandb가 설치되어 있으면 자동으로 wandb에 로깅됩니다.
> 비활성화하려면 `report_to="none"`으로 설정하세요.

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
