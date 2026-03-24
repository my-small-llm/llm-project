"""학습 하이퍼파라미터 및 설정을 dataclass로 관리합니다."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import torch
from peft import LoraConfig
from transformers import BitsAndBytesConfig
from trl import SFTConfig


ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


def _load_train_env() -> None:
    """프로젝트 루트 .env 값을 현재 프로세스 환경변수로 로드합니다."""
    if not ENV_PATH.exists():
        return

    for raw_line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        os.environ.setdefault(key, value)


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value is not None else default


def _get_float(name: str, default: float) -> float:
    value = os.getenv(name)
    return float(value) if value is not None else default


def _get_str(name: str, default: Optional[str]) -> Optional[str]:
    return os.getenv(name, default)


def _get_list(name: str, default: List[str]) -> List[str]:
    value = os.getenv(name)
    if value is None:
        return list(default)
    return [item.strip() for item in value.split(",") if item.strip()]


_load_train_env()


@dataclass
class TrainConfig:
    """Qwen Function-Calling SFT 학습 설정."""

    # ── 모델 / 데이터셋 ──────────────────────────────────
    model_id: str = field(
        default_factory=lambda: _get_str("TRAIN_MODEL_ID", "Qwen/Qwen2.5-7B-Instruct")
    )
    dataset_id: str = field(
        default_factory=lambda: _get_str(
            "TRAIN_DATASET_ID",
            "jjun123/deliveryapp-traindata-100",
        )
    )
    output_dir: str = field(
        default_factory=lambda: _get_str(
            "TRAIN_OUTPUT_DIR",
            "qwen-2.5-7b-function-calling",
        )
    )

    # ── 데이터 분할 ──────────────────────────────────────
    test_ratio: float = field(default_factory=lambda: _get_float("TRAIN_TEST_RATIO", 0.2))
    data_seed: int = field(default_factory=lambda: _get_int("TRAIN_DATA_SEED", 42))
    max_seq_length: int = field(
        default_factory=lambda: _get_int("TRAIN_MAX_SEQ_LENGTH", 8192)
    )

    # ── LoRA ─────────────────────────────────────────────
    lora_r: int = field(default_factory=lambda: _get_int("TRAIN_LORA_R", 8))
    lora_alpha: int = field(default_factory=lambda: _get_int("TRAIN_LORA_ALPHA", 32))
    lora_dropout: float = field(
        default_factory=lambda: _get_float("TRAIN_LORA_DROPOUT", 0.1)
    )
    lora_target_modules: List[str] = field(
        default_factory=lambda: _get_list(
            "TRAIN_LORA_TARGET_MODULES",
            ["q_proj", "k_proj", "v_proj", "o_proj"],
        )
    )

    # ── QLoRA (4-bit 양자화) ─────────────────────────────
    use_qlora: bool = field(default_factory=lambda: _get_bool("TRAIN_USE_QLORA", True))
    bnb_4bit_quant_type: str = field(
        default_factory=lambda: _get_str("TRAIN_BNB_4BIT_QUANT_TYPE", "nf4")
    )
    bnb_4bit_compute_dtype: str = field(
        default_factory=lambda: _get_str("TRAIN_BNB_4BIT_COMPUTE_DTYPE", "bfloat16")
    )
    bnb_4bit_use_double_quant: bool = field(
        default_factory=lambda: _get_bool("TRAIN_BNB_4BIT_USE_DOUBLE_QUANT", True)
    )

    # ── SFT 학습 ─────────────────────────────────────────
    num_epochs: int = field(default_factory=lambda: _get_int("TRAIN_NUM_EPOCHS", 3))
    batch_size: int = field(default_factory=lambda: _get_int("TRAIN_BATCH_SIZE", 1))
    gradient_accumulation_steps: int = field(
        default_factory=lambda: _get_int("TRAIN_GRADIENT_ACCUMULATION_STEPS", 2)
    )
    gradient_checkpointing: bool = field(
        default_factory=lambda: _get_bool("TRAIN_GRADIENT_CHECKPOINTING", True)
    )
    optim: str = field(default_factory=lambda: _get_str("TRAIN_OPTIM", "paged_adamw_8bit"))
    learning_rate: float = field(
        default_factory=lambda: _get_float("TRAIN_LEARNING_RATE", 1e-4)
    )
    max_grad_norm: float = field(
        default_factory=lambda: _get_float("TRAIN_MAX_GRAD_NORM", 0.3)
    )
    warmup_ratio: float = field(
        default_factory=lambda: _get_float("TRAIN_WARMUP_RATIO", 0.03)
    )
    lr_scheduler_type: str = field(
        default_factory=lambda: _get_str("TRAIN_LR_SCHEDULER_TYPE", "constant")
    )
    bf16: bool = field(default_factory=lambda: _get_bool("TRAIN_BF16", True))

    # ── 로깅 / 저장 ─────────────────────────────────────
    logging_steps: int = field(
        default_factory=lambda: _get_int("TRAIN_LOGGING_STEPS", 10)
    )
    eval_strategy: str = field(
        default_factory=lambda: _get_str("TRAIN_EVAL_STRATEGY", "steps")
    )
    eval_steps: int = field(default_factory=lambda: _get_int("TRAIN_EVAL_STEPS", 50))
    save_strategy: str = field(
        default_factory=lambda: _get_str("TRAIN_SAVE_STRATEGY", "steps")
    )
    save_steps: int = field(default_factory=lambda: _get_int("TRAIN_SAVE_STEPS", 50))
    load_best_model_at_end: bool = field(
        default_factory=lambda: _get_bool("TRAIN_LOAD_BEST_MODEL_AT_END", True)
    )
    push_to_hub: bool = field(
        default_factory=lambda: _get_bool("TRAIN_PUSH_TO_HUB", False)
    )
    report_to: Optional[str] = field(
        default_factory=lambda: _get_str("TRAIN_REPORT_TO", "wandb")
    )

    # ── 유틸 메서드 ──────────────────────────────────────

    def get_bnb_config(self) -> Optional[BitsAndBytesConfig]:
        """BitsAndBytesConfig 객체를 반환합니다. use_qlora=False이면 None."""
        if not self.use_qlora:
            return None

        compute_dtype = getattr(torch, self.bnb_4bit_compute_dtype)
        return BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type=self.bnb_4bit_quant_type,
            bnb_4bit_compute_dtype=compute_dtype,
            bnb_4bit_use_double_quant=self.bnb_4bit_use_double_quant,
        )

    def get_lora_config(self) -> LoraConfig:
        """LoraConfig 객체를 반환합니다."""
        return LoraConfig(
            lora_alpha=self.lora_alpha,
            lora_dropout=self.lora_dropout,
            r=self.lora_r,
            bias="none",
            target_modules=self.lora_target_modules,
            task_type="CAUSAL_LM",
        )

    def get_sft_config(self) -> SFTConfig:
        """SFTConfig 객체를 반환합니다."""
        sft_config = SFTConfig(
            output_dir=self.output_dir,
            max_seq_length=self.max_seq_length,
            num_train_epochs=self.num_epochs,
            per_device_train_batch_size=self.batch_size,
            per_device_eval_batch_size=self.batch_size,
            gradient_accumulation_steps=self.gradient_accumulation_steps,
            gradient_checkpointing=self.gradient_checkpointing,
            optim=self.optim,
            logging_steps=self.logging_steps,
            save_strategy=self.save_strategy,
            save_steps=self.save_steps,
            bf16=self.bf16,
            learning_rate=self.learning_rate,
            max_grad_norm=self.max_grad_norm,
            warmup_ratio=self.warmup_ratio,
            lr_scheduler_type=self.lr_scheduler_type,
            push_to_hub=self.push_to_hub,
            remove_unused_columns=False,
            dataset_kwargs={"skip_prepare_dataset": True},
            report_to=self.report_to,
        )
        if hasattr(sft_config, "eval_strategy"):
            sft_config.eval_strategy = self.eval_strategy
        elif hasattr(sft_config, "evaluation_strategy"):
            sft_config.evaluation_strategy = self.eval_strategy
        sft_config.eval_steps = self.eval_steps
        sft_config.load_best_model_at_end = self.load_best_model_at_end
        sft_config.metric_for_best_model = "eval_loss"
        sft_config.greater_is_better = False
        return sft_config

    def to_metadata_dict(self) -> dict:
        """평가/추적용 학습 메타데이터를 핵심 하이퍼파라미터 중심으로 반환합니다."""
        return {
            "model_id": self.model_id,
            "dataset_id": self.dataset_id,
            "test_ratio": self.test_ratio,
            "data_seed": self.data_seed,
            "max_seq_length": self.max_seq_length,
            "use_qlora": self.use_qlora,
            "bnb_4bit_quant_type": self.bnb_4bit_quant_type,
            "bnb_4bit_compute_dtype": self.bnb_4bit_compute_dtype,
            "bnb_4bit_use_double_quant": self.bnb_4bit_use_double_quant,
            "lora_r": self.lora_r,
            "lora_alpha": self.lora_alpha,
            "lora_dropout": self.lora_dropout,
            "lora_target_modules": self.lora_target_modules,
            "num_epochs": self.num_epochs,
            "batch_size": self.batch_size,
            "gradient_accumulation_steps": self.gradient_accumulation_steps,
            "gradient_checkpointing": self.gradient_checkpointing,
            "optim": self.optim,
            "learning_rate": self.learning_rate,
            "max_grad_norm": self.max_grad_norm,
            "warmup_ratio": self.warmup_ratio,
            "lr_scheduler_type": self.lr_scheduler_type,
            "bf16": self.bf16,
            "eval_strategy": self.eval_strategy,
            "eval_steps": self.eval_steps,
            "save_strategy": self.save_strategy,
            "save_steps": self.save_steps,
            "load_best_model_at_end": self.load_best_model_at_end,
        }
