"""
TRL SFTTrainer 기반 QLoRA 파인튜닝 진입점.

실행:
    python -m trainer.train --config trainer/configs/default.yaml
"""

import argparse

import torch
import wandb
from dotenv import load_dotenv

load_dotenv()
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import LoraConfig
from trl import SFTConfig, SFTTrainer

from trainer.config import load_config
from trainer.data import load_dataset_split, build_collate_fn
from trainer.callbacks import EvalCallback


def main():
    parser = argparse.ArgumentParser(description="QLoRA SFT 파인튜닝")
    parser.add_argument("--config", required=True, help="YAML 설정 파일 경로")
    args = parser.parse_args()

    cfg = load_config(args.config)

    # 1. wandb 초기화
    wandb.init(
        project=cfg.wandb_project,
        entity=cfg.wandb_entity,
        name=cfg.wandb_run_name,
        config=vars(cfg),
    )
    print(f"[1/6] wandb 초기화: {cfg.wandb_project}")

    # 2. 모델 로드 (4bit 양자화)
    print(f"[2/6] 모델 로드: {cfg.model_name}")
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type=cfg.bnb_4bit_quant_type,
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )

    model = AutoModelForCausalLM.from_pretrained(
        cfg.model_name,
        quantization_config=bnb_config,
        device_map="auto",
        dtype=torch.bfloat16,
    )

    tokenizer = AutoTokenizer.from_pretrained(cfg.model_name)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # 3. 데이터 로드 + split
    print(f"[3/6] 데이터 로드: {cfg.dataset_path}")
    train_dataset, val_dataset, val_conversations = load_dataset_split(
        cfg.dataset_path, cfg.val_ratio, cfg.data_seed
    )

    # 4. LoRA 설정
    print("[4/6] LoRA 설정")
    peft_config = LoraConfig(
        r=cfg.lora_r,
        lora_alpha=cfg.lora_alpha,
        lora_dropout=cfg.lora_dropout,
        target_modules=cfg.target_modules,
        bias="none",
        task_type="CAUSAL_LM",
    )

    # 5. SFT 설정
    print("[5/6] SFTTrainer 설정")
    sft_config = SFTConfig(
        output_dir=cfg.output_dir,
        num_train_epochs=cfg.num_train_epochs,
        max_steps=cfg.max_steps,
        per_device_train_batch_size=cfg.per_device_train_batch_size,
        gradient_accumulation_steps=cfg.gradient_accumulation_steps,
        gradient_checkpointing=cfg.gradient_checkpointing,
        optim=cfg.optim,
        learning_rate=cfg.learning_rate,
        lr_scheduler_type=cfg.lr_scheduler_type,
        warmup_ratio=cfg.warmup_ratio,
        max_grad_norm=cfg.max_grad_norm,
        bf16=cfg.bf16,
        logging_steps=cfg.logging_steps,
        save_strategy="steps",
        save_steps=cfg.save_steps,
        push_to_hub=False,
        remove_unused_columns=False,
        max_seq_length=cfg.max_seq_length,
        dataset_kwargs={"skip_prepare_dataset": True},
        report_to="wandb",
    )

    collate_fn = build_collate_fn(tokenizer, cfg.max_seq_length)

    eval_callback = EvalCallback(
        val_conversations=val_conversations,
        tokenizer=tokenizer,
        eval_steps=cfg.eval_steps,
        eval_samples=cfg.eval_samples,
        eval_seed=cfg.eval_seed,
        eval_max_new_tokens=cfg.eval_max_new_tokens,
        max_seq_length=cfg.max_seq_length,
    )

    # 6. 학습
    print("[6/6] 학습 시작")
    trainer = SFTTrainer(
        model=model,
        args=sft_config,
        train_dataset=train_dataset,
        data_collator=collate_fn,
        peft_config=peft_config,
        callbacks=[eval_callback],
    )

    trainer.train()
    trainer.save_model()
    wandb.finish()
    print(f"[완료] 모델 저장: {cfg.output_dir}")


if __name__ == "__main__":
    main()
