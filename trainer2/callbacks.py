"""학습 중 validation 평가 callback."""

from __future__ import annotations

import random

import torch
import wandb
from tqdm import tqdm
from transformers import TrainerCallback

from evaluations.metrics import evaluate_function_call_step
from evaluations.preprocessing import extract_tool_schemas
from evaluations.turn_splitter import split_conversations


class EvalCallback(TrainerCallback):
    """
    N step마다 model.generate()로 validation 평가를 수행한다.

    - validation 대화에서 eval_samples개를 eval_seed로 샘플링 (재현성)
    - turn_splitter로 InferenceInput 생성
    - model.generate()로 예측
    - turn_level_accuracy 계산
    - wandb 로깅
    """

    def __init__(
        self,
        val_conversations: list[dict],
        tokenizer,
        eval_steps: int,
        eval_samples: int,
        eval_seed: int,
        eval_max_new_tokens: int,
        max_seq_length: int = 4096,
    ):
        self.val_conversations = val_conversations
        self.tokenizer = tokenizer
        self.eval_steps = eval_steps
        self.eval_samples = eval_samples
        self.eval_seed = eval_seed
        self.eval_max_new_tokens = eval_max_new_tokens
        self.max_seq_length = max_seq_length

        # 재현성 보장: seed 기반으로 고정 샘플 선택
        if len(val_conversations) > eval_samples:
            indices = list(range(len(val_conversations)))
            random.Random(eval_seed).shuffle(indices)
            self.sample_indices = sorted(indices[:eval_samples])
        else:
            self.sample_indices = list(range(len(val_conversations)))

        self.sampled_conversations = [
            val_conversations[i] for i in self.sample_indices
        ]

        # tool_schemas 추출 (첫 대화 기준)
        self.tool_schemas = None
        if self.sampled_conversations and self.sampled_conversations[0].get("tools"):
            self.tool_schemas = extract_tool_schemas(
                self.sampled_conversations[0]["tools"]
            )

        # InferenceInput 사전 생성 (매번 재계산 불필요)
        self.inference_inputs = split_conversations(self.sampled_conversations)

    def on_train_begin(self, args, state, control, model=None, **kwargs):
        if model is None:
            return

        print(f"\n[Eval] step 0 (baseline) 평가 시작 ({len(self.inference_inputs)}개 step)")

        model.eval()
        metrics = self._evaluate(model)
        model.train()

        log_data = {f"eval/{k}": v for k, v in metrics.items()}
        log_data["eval/step"] = 0
        wandb.log(log_data, step=0)

        print(
            f"[Eval] step 0 (baseline) 완료 | "
            f"turn_level_accuracy: {metrics['turn_level_accuracy']:.2%} "
            f"({metrics['turn_pass']}/{metrics['turn_total']})"
        )

    def on_step_end(self, args, state, control, model=None, **kwargs):
        if state.global_step % self.eval_steps != 0 or state.global_step == 0:
            return

        if model is None:
            return

        print(f"\n[Eval] step {state.global_step} 평가 시작 ({len(self.inference_inputs)}개 step)")

        model.eval()
        metrics = self._evaluate(model)
        model.train()

        # wandb 로깅
        log_data = {f"eval/{k}": v for k, v in metrics.items()}
        log_data["eval/step"] = state.global_step
        wandb.log(log_data, step=state.global_step)

        print(
            f"[Eval] step {state.global_step} 완료 | "
            f"turn_level_accuracy: {metrics['turn_level_accuracy']:.2%} "
            f"({metrics['turn_pass']}/{metrics['turn_total']})"
        )

    def _evaluate(self, model) -> dict:
        """model.generate()로 예측 생성 후 메트릭 계산."""
        predictions = []

        for inp in tqdm(self.inference_inputs, desc="Eval generate", leave=False):
            prompt = self._build_chatml_prompt(inp.messages)
            input_ids = self.tokenizer(
                prompt, return_tensors="pt", truncation=True, max_length=self.max_seq_length
            ).input_ids.to(model.device)

            with torch.no_grad(), torch.amp.autocast("cuda", dtype=torch.bfloat16):
                output_ids = model.generate(
                    input_ids,
                    max_new_tokens=self.eval_max_new_tokens,
                    do_sample=False,
                    pad_token_id=self.tokenizer.pad_token_id,
                )

            # 프롬프트 부분 제거
            generated_ids = output_ids[0][input_ids.shape[1]:]
            prediction = self.tokenizer.decode(generated_ids, skip_special_tokens=False)

            # <|im_end|> 이후 제거
            if "<|im_end|>" in prediction:
                prediction = prediction[:prediction.index("<|im_end|>")]

            predictions.append(prediction.strip())

        return self._compute_metrics(predictions)

    def _compute_metrics(self, predictions: list[str]) -> dict:
        """predictions와 gt_response를 비교하여 메트릭을 계산한다."""
        from collections import defaultdict

        # step 단위 평가
        step_results = []
        for inp, pred in zip(self.inference_inputs, predictions):
            step_result = evaluate_function_call_step(
                inp.gt_response, pred, tool_schemas=self.tool_schemas
            )
            step_results.append((inp, step_result))

        # turn 단위 집계
        grouped = defaultdict(lambda: defaultdict(list))
        for inp, step_result in step_results:
            grouped[inp.conversation_id][inp.turn_index].append(step_result)

        turn_pass = 0
        turn_total = 0

        for conv_id in sorted(grouped.keys()):
            for turn_idx in sorted(grouped[conv_id].keys()):
                steps = grouped[conv_id][turn_idx]
                tool_steps = [s for s in steps if s.is_tool_label]

                if tool_steps:
                    passed = all(s.tool_call_pass for s in tool_steps)
                else:
                    passed = all(s.relevance_pass for s in steps)

                turn_total += 1
                if passed:
                    turn_pass += 1

        turn_level_accuracy = turn_pass / turn_total if turn_total > 0 else 0.0

        return {
            "turn_level_accuracy": turn_level_accuracy,
            "turn_pass": turn_pass,
            "turn_total": turn_total,
            "total_steps": len(step_results),
        }

    def _build_chatml_prompt(self, messages: list[dict]) -> str:
        """messages를 ChatML 프롬프트로 변환한다."""
        parts = []
        for msg in messages:
            role = msg["role"]
            content = msg.get("content", "")
            parts.append(f"<|im_start|>{role}\n{content}<|im_end|>")
        parts.append("<|im_start|>assistant\n")
        return "\n".join(parts)
