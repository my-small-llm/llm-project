"""ChatML 형식의 collate_fn을 제공합니다.

assistant 응답 부분만 레이블링하고 나머지는 -100으로 마스킹하여
모델이 응답 생성만 학습하도록 합니다.
"""

from typing import Dict, List

import torch
from transformers import PreTrainedTokenizer


class ChatMLCollator:
    """Qwen ChatML 형식의 데이터 배치를 준비하는 collator.

    assistant 세그먼트의 내용 + 종료 토큰만 레이블로 설정하고,
    system/user 메시지 및 assistant 헤더는 -100으로 마스킹합니다.
    """

    def __init__(self, tokenizer: PreTrainedTokenizer, max_seq_length: int = 8192):
        self.tokenizer = tokenizer
        self.max_seq_length = max_seq_length

        # Qwen ChatML 토큰 사전 계산
        self.start_token = "<|im_start|>"
        self.end_token = "<|im_end|>"
        self.assistant_tokens = tokenizer.encode(
            f"{self.start_token}assistant\n", add_special_tokens=False
        )
        self.end_tokens = tokenizer.encode(
            self.end_token, add_special_tokens=False
        )

    def __call__(self, batch: List[dict]) -> Dict[str, torch.Tensor]:
        new_batch: Dict[str, list] = {
            "input_ids": [],
            "attention_mask": [],
            "labels": [],
        }

        for example in batch:
            messages = example["messages"]

            # ChatML 형식으로 prompt 조합
            prompt = ""
            for msg in messages:
                role = msg["role"]
                content = msg["content"].strip()
                prompt += f"{self.start_token}{role}\n{content}{self.end_token}"

            # 토크나이징
            tokenized = self.tokenizer(
                prompt,
                truncation=True,
                max_length=self.max_seq_length,
                padding=False,
                return_tensors=None,
            )
            input_ids = tokenized["input_ids"]
            attention_mask = tokenized["attention_mask"]
            labels = [-100] * len(input_ids)

            # assistant 세그먼트만 레이블에 복사 (종료 토큰 포함)
            self._label_assistant_segments(input_ids, labels)

            new_batch["input_ids"].append(input_ids)
            new_batch["attention_mask"].append(attention_mask)
            new_batch["labels"].append(labels)

        # 배치 내 패딩 및 Tensor 변환
        self._pad_and_tensorize(new_batch)

        return new_batch

    def _label_assistant_segments(
        self, input_ids: List[int], labels: List[int]
    ) -> None:
        """input_ids에서 assistant 응답 영역을 찾아 labels에 복사합니다."""
        i = 0
        n = len(input_ids)
        ast_len = len(self.assistant_tokens)
        end_len = len(self.end_tokens)

        while i <= n - ast_len:
            if input_ids[i : i + ast_len] == self.assistant_tokens:
                start_idx = i + ast_len
                end_idx = start_idx

                # <|im_end|> 위치까지 탐색
                while end_idx <= n - end_len:
                    if input_ids[end_idx : end_idx + end_len] == self.end_tokens:
                        end_idx += end_len
                        break
                    end_idx += 1

                # 응답 본문 + 종료 토큰을 레이블링
                for j in range(start_idx, end_idx):
                    labels[j] = input_ids[j]

                i = end_idx
            else:
                i += 1

    def _pad_and_tensorize(self, batch: Dict[str, list]) -> None:
        """배치 내 시퀀스를 동일 길이로 패딩하고 텐서로 변환합니다."""
        max_len = max(len(ids) for ids in batch["input_ids"])

        for idx in range(len(batch["input_ids"])):
            pad_len = max_len - len(batch["input_ids"][idx])
            batch["input_ids"][idx].extend(
                [self.tokenizer.pad_token_id] * pad_len
            )
            batch["attention_mask"][idx].extend([0] * pad_len)
            batch["labels"][idx].extend([-100] * pad_len)

        for k in batch:
            batch[k] = torch.tensor(batch[k])
