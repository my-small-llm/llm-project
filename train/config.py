"""학습 하이퍼파라미터 및 설정을 dataclass로 관리합니다."""

from dataclasses import dataclass, field
from typing import List, Optional

import torch
from peft import LoraConfig
from transformers import BitsAndBytesConfig
from trl import SFTConfig


@dataclass
class TrainConfig:
    """Qwen Function-Calling SFT 학습 설정."""

    # ── 모델 / 데이터셋 ──────────────────────────────────
    model_id: str = "Qwen/Qwen2.5-7B-Instruct"
    dataset_id: str = "jjun123/deliveryapp-traindata-100"
    output_dir: str = "qwen-2.5-7b-function-calling"

    # ── 데이터 분할 ──────────────────────────────────────
    test_ratio: float = 0.2
    max_seq_length: int = 8192

    # ── LoRA ─────────────────────────────────────────────
    lora_r: int = 8
    lora_alpha: int = 32
    lora_dropout: float = 0.1
    lora_target_modules: List[str] = field(
        default_factory=lambda: ["q_proj", "k_proj", "v_proj", "o_proj"]
    )

    # ── QLoRA (4-bit 양자화) ─────────────────────────────
    use_qlora: bool = True
    bnb_4bit_quant_type: str = "nf4"
    bnb_4bit_compute_dtype: str = "bfloat16"
    bnb_4bit_use_double_quant: bool = True

    # ── SFT 학습 ─────────────────────────────────────────
    num_epochs: int = 3
    batch_size: int = 1
    gradient_accumulation_steps: int = 2
    gradient_checkpointing: bool = True
    optim: str = "paged_adamw_8bit"
    learning_rate: float = 1e-4
    max_grad_norm: float = 0.3
    warmup_ratio: float = 0.03
    lr_scheduler_type: str = "constant"
    bf16: bool = True

    # ── 로깅 / 저장 ─────────────────────────────────────
    logging_steps: int = 10
    save_strategy: str = "steps"
    save_steps: int = 50
    push_to_hub: bool = False
    report_to: str = None  # "wandb" 등으로 변경 가능

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
        return SFTConfig(
            output_dir=self.output_dir,
            max_seq_length=self.max_seq_length,
            num_train_epochs=self.num_epochs,
            per_device_train_batch_size=self.batch_size,
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
