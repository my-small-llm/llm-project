"""
vLLM 기반 평가 실행기.

GT 히스토리 기반 싱글턴 분할 → vLLM batch 추론 → 메트릭 계산 → 결과 저장.

실행:
    python -m evaluations.runner \\
        --model Qwen/Qwen2.5-7B-Instruct \\
        --dataset eval_data/dataset.jsonl \\
        --output eval_output

    # LoRA 어댑터 적용
    python -m evaluations.runner \\
        --model Qwen/Qwen2.5-7B-Instruct \\
        --lora outputs/default \\
        --dataset eval_data/dataset.jsonl \\
        --output eval_output

    # 추론만 수행 (스코어링 생략)
    python -m evaluations.runner \\
        --model Qwen/Qwen2.5-7B-Instruct \\
        --dataset eval_data/dataset.jsonl \\
        --output eval_output \\
        --inference-only
"""

import argparse
import json
import os
from pathlib import Path


def _build_chatml_prompt(messages: list[dict]) -> str:
    """
    messages 리스트를 ChatML 프롬프트 문자열로 변환한다.

    마지막에 '<|im_start|>assistant\n'을 붙여 모델이 이어서 생성하도록 한다.
    """
    parts = []
    for msg in messages:
        role = msg["role"]
        content = msg.get("content", "")
        parts.append(f"<|im_start|>{role}\n{content}<|im_end|>")
    parts.append("<|im_start|>assistant\n")
    return "\n".join(parts)


def _load_conversations(dataset_path: str) -> list[dict]:
    """JSONL 파일 또는 HuggingFace 데이터셋 ID에서 대화 목록을 로드한다."""
    if os.path.exists(dataset_path):
        with open(dataset_path, encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]
    else:
        # HuggingFace 데이터셋 ID로 간주
        from datasets import load_dataset
        ds = load_dataset(dataset_path, split="test")
        return list(ds)


def _run_vllm_inference(
    prompts: list[str],
    model_name: str,
    max_new_tokens: int = 512,
    lora_path: str | None = None,
    max_model_len: int | None = None,
    seed: int = 42,
) -> list[str]:
    """
    vLLM을 사용해 batch 추론을 수행한다.

    Parameters
    ----------
    prompts : ChatML 프롬프트 리스트
    model_name : 모델 경로 또는 HuggingFace ID
    max_new_tokens : 최대 생성 토큰 수
    lora_path : LoRA 어댑터 경로 (None이면 베이스 모델만 사용)

    Returns
    -------
    생성된 텍스트 리스트 (프롬프트 제외)
    """
    from vllm import LLM, SamplingParams
    from vllm.lora.request import LoRARequest

    llm_kwargs = {
        "model": model_name,
        "trust_remote_code": True,
        "enable_lora": lora_path is not None,
        "max_lora_rank": 128,
        "seed": seed,
    }
    if max_model_len is not None:
        llm_kwargs["max_model_len"] = max_model_len

    llm = LLM(**llm_kwargs)
    sampling_params = SamplingParams(
        temperature=0.0,
        max_tokens=max_new_tokens,
        stop=["<|im_end|>"],
        seed=seed,
    )

    lora_request = None
    if lora_path:
        lora_request = LoRARequest("eval_lora", 1, lora_path)

    outputs = llm.generate(prompts, sampling_params, lora_request=lora_request)
    return [output.outputs[0].text for output in outputs]


def _save_predictions(records: list[dict], output_dir: Path) -> Path:
    """predictions.jsonl 저장."""
    output_dir.mkdir(parents=True, exist_ok=True)
    pred_path = output_dir / "predictions.jsonl"

    with open(pred_path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    return pred_path


def run_evaluation(
    model_name: str,
    dataset_path: str,
    output_dir: str,
    max_new_tokens: int = 512,
    inference_only: bool = False,
    lora_path: str | None = None,
    max_model_len: int | None = None,
    seed: int = 42,
) -> None:
    """
    전체 평가 파이프라인 실행.

    1. 데이터 로드 → 싱글턴 분할
    2. vLLM batch 추론
    3. predictions.jsonl 저장
    4. 메트릭 계산 + 결과 저장 (inference_only=True이면 생략)

    Parameters
    ----------
    model_name : 모델 경로 또는 HuggingFace ID
    dataset_path : 평가 데이터셋 경로 또는 HuggingFace ID
    output_dir : 결과 저장 디렉토리
    max_new_tokens : 최대 생성 토큰 수
    inference_only : True이면 predictions.jsonl 저장 후 스코어링 생략
    lora_path : LoRA 어댑터 경로 (None이면 베이스 모델만 사용)
    """
    from evaluations.turn_splitter import split_conversations
    from evaluations.preprocessing import extract_tool_schemas
    from evaluations.scorer import score_predictions

    output_path = Path(output_dir)

    # 1. 데이터 로드 및 싱글턴 분할
    print(f"[1/4] 데이터셋 로드: {dataset_path}")
    conversations = _load_conversations(dataset_path)
    print(f"  총 대화 수: {len(conversations)}")

    inference_inputs = split_conversations(conversations)
    print(f"  총 InferenceInput 수: {len(inference_inputs)}")

    # 2. 프롬프트 생성 및 vLLM 추론
    print(f"[2/4] vLLM 추론 시작: {model_name}")
    prompts = [_build_chatml_prompt(inp.messages) for inp in inference_inputs]
    if lora_path:
        print(f"  LoRA 어댑터: {lora_path}")
    if max_model_len is not None:
        print(f"  max_model_len: {max_model_len}")
    predictions = _run_vllm_inference(
        prompts,
        model_name,
        max_new_tokens,
        lora_path=lora_path,
        max_model_len=max_model_len,
        seed=seed,
    )
    print(f"  추론 완료: {len(predictions)}개 예측")

    # 3. 예측 저장
    records = [
        {
            "conversation_id": inp.conversation_id,
            "turn_index": inp.turn_index,
            "step_index": inp.step_index,
            "is_tool_call": inp.is_tool_call,
            "gt_response": inp.gt_response,
            "prediction": pred,
        }
        for inp, pred in zip(inference_inputs, predictions)
    ]
    pred_path = _save_predictions(records, output_path)
    print(f"[3/4] 예측 저장: {pred_path}")

    if inference_only:
        print("--inference-only 지정: 스코어링 생략")
        return

    # 4. 메트릭 계산
    print("[4/4] 메트릭 계산")

    tool_schemas = None
    if conversations and conversations[0].get("tools"):
        tool_schemas = extract_tool_schemas(conversations[0]["tools"])

    score_predictions(
        records=records,
        tool_schemas=tool_schemas,
        output_dir=output_path,
        model_name=model_name,
        dataset_name=dataset_path,
    )


def main():
    parser = argparse.ArgumentParser(description="GT 히스토리 기반 Function Calling 평가")
    parser.add_argument("--model", required=True, help="모델 경로 또는 HuggingFace ID")
    parser.add_argument(
        "--dataset",
        default="eval_data/dataset.jsonl",
        help="평가 데이터셋 경로 또는 HuggingFace ID",
    )
    parser.add_argument(
        "--output",
        default="eval_output",
        help="결과 저장 디렉토리",
    )
    parser.add_argument(
        "--max-new-tokens",
        type=int,
        default=512,
        help="최대 생성 토큰 수",
    )
    parser.add_argument(
        "--inference-only",
        action="store_true",
        help="predictions.jsonl 저장까지만 수행하고 스코어링 생략",
    )
    parser.add_argument(
        "--lora",
        default=None,
        help="LoRA 어댑터 경로 (지정하면 베이스 모델에 LoRA를 적용하여 추론)",
    )
    parser.add_argument(
        "--max-model-len",
        type=int,
        default=None,
        help="vLLM에 명시적으로 전달할 최대 컨텍스트 길이 (예: 8192)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="추론 재현성을 위한 랜덤 시드 (기본값: 42)",
    )
    args = parser.parse_args()

    run_evaluation(
        model_name=args.model,
        dataset_path=args.dataset,
        output_dir=args.output,
        max_new_tokens=args.max_new_tokens,
        inference_only=args.inference_only,
        lora_path=args.lora,
        max_model_len=args.max_model_len,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
