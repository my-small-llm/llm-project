"""학습 실행 스크립트.

사용법:
    python -m train.run
    python train/run.py
"""

import json
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from trl import SFTTrainer

from train.collator import ChatMLCollator
from train.config import TrainConfig
from train.data import load_and_split


def _save_train_metadata(config: TrainConfig) -> Path:
    """학습 출력 폴더에 핵심 하이퍼파라미터를 저장한다."""
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = output_dir / "train_metadata.json"

    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(config.to_metadata_dict(), f, ensure_ascii=False, indent=2)

    return metadata_path


def main(config: TrainConfig | None = None) -> None:
    """학습 파이프라인을 실행합니다."""
    if config is None:
        config = TrainConfig()

    # ── 1. 데이터 준비 ───────────────────────────────────
    train_dataset, eval_dataset = load_and_split(
        dataset_id=config.dataset_id,
        test_ratio=config.test_ratio,
        seed=config.data_seed,
    )

    # ── 2. 모델 / 토크나이저 로드 ────────────────────────
    print(f"모델 로드 중: {config.model_id}")
    model = AutoModelForCausalLM.from_pretrained(
        config.model_id,
        device_map="auto",
        torch_dtype=torch.bfloat16,
        quantization_config=config.get_bnb_config(),
    )
    tokenizer = AutoTokenizer.from_pretrained(config.model_id)

    # ── 3. Collator / Config 구성 ────────────────────────
    collator = ChatMLCollator(tokenizer, max_seq_length=config.max_seq_length)
    peft_config = config.get_lora_config()
    sft_config = config.get_sft_config()

    # ── 4. Trainer 구성 ──────────────────────────────────
    trainer = SFTTrainer(
        model=model,
        args=sft_config,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        data_collator=collator,
        peft_config=peft_config,
    )

    # ── 5. 학습 실행 ─────────────────────────────────────
    print("학습을 시작합니다...")
    trainer.train()

    # ── 6. 모델 저장 ─────────────────────────────────────
    trainer.save_model()
    print(f"모델 저장 완료: {config.output_dir}")

    metadata_path = _save_train_metadata(config)
    print(f"학습 메타데이터 저장 완료: {metadata_path}")


if __name__ == "__main__":
    main()
