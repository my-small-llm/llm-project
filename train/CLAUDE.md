## 제약 조건

- `.env` 파일 읽기 금지 (WANDB_API_KEY, OPENAI_API_KEY 포함)
- GPU/CUDA 환경 필수 (bitsandbytes QLoRA 사용)
- 학습 체크포인트(`outputs/`, `qwen-*`) 디렉터리는 git-ignore 대상 — 커밋하지 않는다

## 이 폴더의 역할

Qwen2.5-7B-Instruct를 QLoRA (4-bit NF4 + LoRA 어댑터) + SFT로 파인튜닝한다. 모든 하이퍼파라미터는 `.env`에서 관리하고, 학습 로그는 Weights & Biases에 기록한다.

## 디렉터리 지도

```
config.py           TrainConfig — 하이퍼파라미터 및 QLoRA/LoRA 설정 관리
data.py             데이터셋 로드 및 train/test 분할
collator.py         ChatMLCollator — assistant 응답만 레이블링
run.py              학습 실행 스크립트 (CLI 진입점)
vram_analysis.md    VRAM 메모리 분석 문서 (LoRA vs QLoRA 비교)
data_analysis.ipynb 데이터셋 분포 분석 노트북
```

## 작업 흐름

1. `.env` 설정 확인 (사용자에게 내용 확인 요청)
2. `config.py`의 `TrainConfig` 기본값 확인
3. 학습 실행
4. wandb 로그로 수렴 확인

## 도구

```bash
# CUDA OOM 완화 설정 포함 학습 실행
PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128 python -m train.run
```

`.env` 주요 설정:
```
TRAIN_MODEL_ID=Qwen/Qwen2.5-7B-Instruct
TRAIN_DATASET_ID=jjun123/deliveryapp-traindata-100
TRAIN_OUTPUT_DIR=qwen-2.5-7b-function-calling
TRAIN_REPORT_TO=wandb          # wandb 비활성화 시 none
WANDB_PROJECT=deliveryapp-sft
WANDB_NAME=qwen2.5-7b-lora-run1
```

## 도메인 컨텍스트

- QLoRA: NF4 4-bit 양자화로 14.2GB → 3.5GB 압축, LoRA 어댑터만 업데이트
- ChatMLCollator: assistant 응답 구간만 labels에 반영, 나머지는 -100 마스킹
- LoRA target modules: `q_proj`, `k_proj`, `v_proj`, `o_proj` (어텐션 전체)
- 저장 산출물: LoRA 어댑터 가중치만 (~수 MB)

## 폴더별 규칙

- 하이퍼파라미터 변경은 코드가 아닌 `.env`에서 수행 — `config.py`의 기본값은 레퍼런스로만 사용
- `collator.py`의 레이블 마스킹 로직 변경 시 학습 손실 계산 전체에 영향 — 신중히 검토
- OOM 발생 시 `TRAIN_BATCH_SIZE`, `TRAIN_GRADIENT_ACCUMULATION_STEPS`, `TRAIN_MAX_SEQ_LENGTH` 순으로 조정
