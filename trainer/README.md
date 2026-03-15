# trainer

TRL SFTTrainer 기반 QLoRA 파인튜닝 모듈.
배달 앱 챗봇의 function calling 능력을 학습시킨다.

## 실행

```bash
python -m trainer.train --config trainer/configs/default.yaml
```

CLI 인수:
- `--config PATH` : YAML 설정 파일 경로 (필수)

.env 파일에 WANDB_API_KEY를 설정해야 한다.

## 설정 (YAML)

`trainer/configs/default.yaml`에 기본값이 정의되어 있다.
실험마다 YAML 파일을 복사하여 하이퍼파라미터를 변경한다.

주요 설정 항목:

```yaml
# 모델
model_name: "Qwen/Qwen2.5-7B-Instruct"

# 데이터
dataset_path: "train_data/dataset.jsonl"   # 데이터셋 경로
val_ratio: 0.2                              # validation 비율
data_seed: 42                               # split shuffle seed

# QLoRA
lora_r: 16
lora_alpha: 32
lora_dropout: 0.1
target_modules: ["q_proj", "k_proj", "v_proj", "o_proj"]
bnb_4bit_quant_type: "nf4"

# 학습
max_seq_length: 8192
num_train_epochs: 3
max_steps: -1             # -1이면 epoch 기준, 양수면 epoch 무시
per_device_train_batch_size: 1
gradient_accumulation_steps: 4
learning_rate: 2.0e-4
lr_scheduler_type: "cosine"
warmup_ratio: 0.1
bf16: true

# 저장
output_dir: "outputs/default"
save_steps: 50
logging_steps: 5

# validation
eval_steps: 50            # N step마다 validation 수행
eval_samples: 10          # validation에 사용할 대화 수
eval_seed: 42             # validation 샘플링 seed (재현성)
eval_max_new_tokens: 512  # generate 시 최대 생성 토큰 수

# wandb
wandb_project: "delivery-fc-sft"
wandb_entity: null        # 팀 entity (null이면 개인 기본값)
wandb_run_name: null      # null이면 자동 생성
```

## 학습 흐름

```
1. YAML 설정 로드
2. wandb 초기화
3. 모델 로드 (4bit QLoRA)
4. dataset.jsonl 로드 + train/val split (seed 기반 재현성)
5. LoRA + SFTTrainer 구성
6. 학습 시작
   ├── step 0: baseline validation 평가
   ├── N step마다 checkpoint 저장
   ├── N step마다 validation 평가
   │   ├── model.eval() + model.generate()
   │   ├── turn_level_accuracy 계산
   │   └── wandb 로깅
   └── train loss wandb 로깅
7. 최종 모델 저장
```

## validation 평가

학습 시작 전(step 0)과 eval_steps마다 자동으로 validation을 수행한다.

- validation 대화에서 eval_samples개를 eval_seed로 고정 샘플링 (재현성 보장)
- turn_splitter로 대화를 step 단위로 분할
- model.generate()로 각 step의 예측 생성 (tqdm 진행바 표시)
- evaluations.metrics로 turn_level_accuracy 계산
- wandb에 eval/turn_level_accuracy 로깅

vLLM 없이 학습 중인 모델로 직접 추론하므로 추가 VRAM이 불필요하다.

## 최종 평가

학습 완료 후 전체 평가는 evaluations 파이프라인으로 별도 실행한다.

```bash
python -m evaluations.runner \
    --model outputs/default \
    --dataset eval_data/dataset.jsonl \
    --output eval_output
```

## 파일 구조

```
trainer/
├── train.py          # 진입점
├── config.py         # YAML 로드 + dataclass 기본값
├── data.py           # 데이터 로드, split, collate_fn
├── callbacks.py      # validation callback (baseline + N step 평가)
├── configs/
│   └── default.yaml  # 기본 설정 파일
└── README.md
```

## 의존성

- trl, transformers, peft, bitsandbytes, accelerate
- wandb, pyyaml, python-dotenv
- evaluations 패키지 (validation callback에서 metrics, turn_splitter 사용)
