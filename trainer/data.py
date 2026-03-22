"""데이터 로드, train/val split, collate_fn."""

from __future__ import annotations

import json
import random
from pathlib import Path

import torch
from datasets import Dataset


def load_dataset_split(
    dataset_path: str,
    val_ratio: float,
    seed: int,
) -> tuple[Dataset, Dataset, list[dict]]:
    """
    dataset.jsonl을 로드하여 train/val로 분할한다.

    Parameters
    ----------
    dataset_path : dataset.jsonl 경로
    val_ratio : validation 비율 (0.0 ~ 1.0)
    seed : shuffle seed (재현성 보장)

    Returns
    -------
    (train_dataset, val_dataset, val_conversations)
    val_conversations는 validation callback에서 turn_splitter에 넘길 원본 대화 리스트
    """
    path = Path(dataset_path)
    if not path.exists():
        raise FileNotFoundError(f"데이터셋을 찾을 수 없습니다: {path}")

    with open(path, encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]

    if not records:
        raise ValueError(f"데이터셋이 비어있습니다: {path}")

    # seed 기반 shuffle
    indices = list(range(len(records)))
    random.Random(seed).shuffle(indices)

    val_size = int(len(records) * val_ratio)
    val_indices = indices[:val_size]
    train_indices = indices[val_size:]

    train_records = [records[i] for i in train_indices]
    val_records = [records[i] for i in val_indices]

    # HF Dataset으로 변환 (train용)
    train_dataset = Dataset.from_list(_format_for_sft(train_records))
    val_dataset = Dataset.from_list(_format_for_sft(val_records))

    print(f"데이터 분할: train {len(train_dataset)}개, val {len(val_dataset)}개")

    return train_dataset, val_dataset, val_records


def _format_for_sft(records: list[dict]) -> list[dict]:
    """dataset.jsonl 레코드를 SFT 학습용 messages 형태로 변환한다."""
    formatted = []
    for rec in records:
        system_prompt = rec.get("system_prompt", "")
        tools = rec.get("tools", [])
        messages = rec.get("messages", [])

        full_messages = [
            {"role": "system", "content": system_prompt},
            *messages,
        ]

        formatted.append({"messages": full_messages, "tools": tools})

    return formatted


def build_collate_fn(tokenizer, max_seq_length: int):
    """assistant 세그먼트만 레이블링하는 collate_fn을 반환한다."""

    start_token = "<|im_start|>"
    end_token = "<|im_end|>"
    assistant_tokens = tokenizer.encode(
        f"{start_token}assistant\n", add_special_tokens=False
    )
    end_tokens = tokenizer.encode(end_token, add_special_tokens=False)

    def collate_fn(batch: list[dict]) -> dict:
        new_batch = {"input_ids": [], "attention_mask": [], "labels": []}

        for example in batch:
            messages = example["messages"]

            # ChatML 형식으로 조합
            prompt = ""
            for msg in messages:
                role = msg["role"]
                content = msg["content"].strip()
                prompt += f"{start_token}{role}\n{content}{end_token}"

            # 토크나이징
            tokenized = tokenizer(
                prompt,
                truncation=True,
                max_length=max_seq_length,
                padding=False,
                return_tensors=None,
            )
            input_ids = tokenized["input_ids"]
            attention_mask = tokenized["attention_mask"]
            labels = [-100] * len(input_ids)

            # assistant 세그먼트만 레이블에 복사
            i = 0
            n = len(input_ids)
            while i <= n - len(assistant_tokens):
                if input_ids[i : i + len(assistant_tokens)] == assistant_tokens:
                    start_idx = i + len(assistant_tokens)
                    end_idx = start_idx
                    while end_idx <= n - len(end_tokens):
                        if input_ids[end_idx : end_idx + len(end_tokens)] == end_tokens:
                            end_idx += len(end_tokens)
                            break
                        end_idx += 1
                    for j in range(start_idx, end_idx):
                        labels[j] = input_ids[j]
                    i = end_idx
                else:
                    i += 1

            new_batch["input_ids"].append(input_ids)
            new_batch["attention_mask"].append(attention_mask)
            new_batch["labels"].append(labels)

        # 동적 패딩
        max_len = max(len(ids) for ids in new_batch["input_ids"])
        pad_id = tokenizer.pad_token_id or 0

        for idx in range(len(new_batch["input_ids"])):
            pad_len = max_len - len(new_batch["input_ids"][idx])
            new_batch["input_ids"][idx].extend([pad_id] * pad_len)
            new_batch["attention_mask"][idx].extend([0] * pad_len)
            new_batch["labels"][idx].extend([-100] * pad_len)

        for k in new_batch:
            new_batch[k] = torch.tensor(new_batch[k])

        return new_batch

    return collate_fn
