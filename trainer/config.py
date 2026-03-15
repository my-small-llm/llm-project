"""YAML 기반 학습 설정 관리."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class TrainConfig:
    """학습 설정. YAML 파일에서 로드하며, 없는 키는 기본값을 사용한다."""

    # 모델
    model_name: str = "Qwen/Qwen2.5-7B-Instruct"

    # 데이터
    dataset_path: str = "train_data/dataset.jsonl"
    val_ratio: float = 0.2
    data_seed: int = 42

    # QLoRA
    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.1
    target_modules: list[str] = field(
        default_factory=lambda: ["q_proj", "k_proj", "v_proj", "o_proj"]
    )
    bnb_4bit_quant_type: str = "nf4"

    # 학습
    max_seq_length: int = 4096
    num_train_epochs: int = 3
    max_steps: int = -1  # -1이면 num_train_epochs 사용, 양수면 epoch 무시
    per_device_train_batch_size: int = 1
    gradient_accumulation_steps: int = 4
    learning_rate: float = 1e-4
    lr_scheduler_type: str = "constant"
    warmup_ratio: float = 0.03
    max_grad_norm: float = 0.3
    optim: str = "adamw_torch_fused"
    bf16: bool = True
    gradient_checkpointing: bool = True

    # 저장
    output_dir: str = "outputs/default"
    save_steps: int = 50
    logging_steps: int = 10

    # validation
    eval_steps: int = 50
    eval_samples: int = 50
    eval_seed: int = 42
    eval_max_new_tokens: int = 512

    # wandb
    wandb_project: str = "delivery-fc-sft"
    wandb_entity: str | None = None
    wandb_run_name: str | None = None


def load_config(yaml_path: str) -> TrainConfig:
    """YAML 파일에서 설정을 로드한다. 없는 키는 기본값을 사용한다."""
    path = Path(yaml_path)
    if not path.exists():
        raise FileNotFoundError(f"설정 파일을 찾을 수 없습니다: {path}")

    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    return TrainConfig(**{k: v for k, v in raw.items() if hasattr(TrainConfig, k)})
