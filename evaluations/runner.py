"""
vLLM 기반 평가 실행기.

GT 히스토리 기반 싱글턴 분할 → vLLM batch 추론 → 메트릭 계산 → 결과 저장.

실행:
    python -m evaluations.runner \\
        --model Qwen/Qwen2.5-7B-Instruct \\
        --dataset eval_data/dataset.jsonl \\
        --output eval_output
"""

import argparse
import csv
import json
import os
from pathlib import Path


def _build_chatml_prompt(messages: list[dict]) -> str:
    """
    messages 리스트를 ChatML 프롬프트 문자열로 변환한다.

    마지막에 '<|im_start|>assistant\\n'을 붙여 모델이 이어서 생성하도록 한다.
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
) -> list[str]:
    """
    vLLM을 사용해 batch 추론을 수행한다.

    Parameters
    ----------
    prompts : ChatML 프롬프트 리스트
    model_name : 모델 경로 또는 HuggingFace ID
    max_new_tokens : 최대 생성 토큰 수

    Returns
    -------
    생성된 텍스트 리스트 (프롬프트 제외)
    """
    from vllm import LLM, SamplingParams

    llm = LLM(model=model_name, trust_remote_code=True)
    sampling_params = SamplingParams(
        temperature=0.0,
        max_tokens=max_new_tokens,
        stop=["<|im_end|>"],
    )

    outputs = llm.generate(prompts, sampling_params)
    return [output.outputs[0].text for output in outputs]


def _save_predictions(
    inference_inputs,
    predictions: list[str],
    output_dir: Path,
) -> Path:
    """predictions.jsonl 저장."""
    output_dir.mkdir(parents=True, exist_ok=True)
    pred_path = output_dir / "predictions.jsonl"

    with open(pred_path, "w", encoding="utf-8") as f:
        for inp, pred in zip(inference_inputs, predictions):
            record = {
                "conversation_id": inp.conversation_id,
                "turn_index": inp.turn_index,
                "step_index": inp.step_index,
                "is_tool_call": inp.is_tool_call,
                "gt_response": inp.gt_response,
                "prediction": pred,
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    return pred_path


def _group_turn_passes(inference_inputs, step_results):
    """step 평가 결과를 turn pass/fail로 집계한다."""
    from collections import defaultdict

    grouped = defaultdict(lambda: defaultdict(list))

    for inp, step_result in zip(inference_inputs, step_results):
        grouped[inp.conversation_id][inp.turn_index].append((inp.step_index, step_result))

    n_convs = max(grouped.keys()) + 1
    conv_turn_passes = []

    for conv_id in range(n_convs):
        turn_dict = grouped[conv_id]
        n_turns = max(turn_dict.keys()) + 1
        turn_passes = []

        for turn_idx in range(n_turns):
            steps = [
                step_result
                for _, step_result in sorted(turn_dict[turn_idx], key=lambda item: item[0])
            ]
            tool_steps = [step for step in steps if step.is_tool_label]
            if tool_steps:
                turn_passes.append(all(step.tool_call_pass for step in tool_steps))
            else:
                turn_passes.append(all(step.relevance_pass for step in steps))
        conv_turn_passes.append(turn_passes)

    return conv_turn_passes


def _flatten_all(inference_inputs, predictions):
    """모든 step의 gt, pred를 flat 리스트로 반환 (Tool Call Level 평가용)."""
    labels = [inp.gt_response for inp in inference_inputs]
    return labels, predictions


def run_evaluation(
    model_name: str,
    dataset_path: str,
    output_dir: str,
    max_new_tokens: int = 512,
) -> dict:
    """
    전체 평가 파이프라인 실행.

    1. 데이터 로드 → 싱글턴 분할
    2. vLLM batch 추론
    3. 메트릭 계산 (Tool Call Level + Turn/Conversation Level)
    4. 결과 저장

    Returns
    -------
    결과 딕셔너리
    """
    from evaluations.turn_splitter import split_conversations
    from evaluations.metrics import evaluate_function_call_step, evaluate_function_calls
    from evaluations.multi_turn_metrics import evaluate_multi_turn
    from evaluations.preprocessing import extract_tool_schemas

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
    predictions = _run_vllm_inference(prompts, model_name, max_new_tokens)
    print(f"  추론 완료: {len(predictions)}개 예측")

    # 3. 예측 저장
    pred_path = _save_predictions(inference_inputs, predictions, output_path)
    print(f"[3/4] 예측 저장: {pred_path}")

    # 4. 메트릭 계산
    print("[4/4] 메트릭 계산")

    # Tool Call Level (모든 step 대상)
    flat_labels, flat_preds = _flatten_all(inference_inputs, predictions)

    # 첫 번째 대화의 tools로 스키마 추출 (동일 schema 사용)
    tool_schemas = None
    if conversations and conversations[0].get("tools"):
        tool_schemas = extract_tool_schemas(conversations[0]["tools"])

    tc_results = evaluate_function_calls(flat_labels, flat_preds, tool_schemas=tool_schemas)
    print(tc_results.summary())

    step_results = [
        evaluate_function_call_step(label, pred, tool_schemas=tool_schemas)
        for label, pred in zip(flat_labels, flat_preds)
    ]

    # Turn/Conversation Level (각 턴의 모든 tool call이 pass여야 turn pass)
    conv_turn_passes = _group_turn_passes(inference_inputs, step_results)
    mt_results = evaluate_multi_turn(conv_turn_passes, aggregated=tc_results)
    print(mt_results.summary())

    # 5. 결과 저장
    results = {
        "model": model_name,
        "dataset": dataset_path,
        "tool_call_level": tc_results.to_dict(),
        "multi_turn": mt_results.to_dict(),
    }

    result_json_path = output_path / "eval_results.json"
    with open(result_json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"결과 저장: {result_json_path}")

    # CSV 요약 저장
    result_csv_path = output_path / "eval_results.csv"
    flat_result = {
        "model": model_name,
        **{f"tc_{k}": v for k, v in tc_results.to_dict().items()},
        **{f"mt_{k}": v for k, v in mt_results.to_dict().items() if k != "aggregated"},
    }
    with open(result_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(flat_result.keys()))
        writer.writeheader()
        writer.writerow(flat_result)
    print(f"CSV 저장: {result_csv_path}")

    return results


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
    args = parser.parse_args()

    run_evaluation(
        model_name=args.model,
        dataset_path=args.dataset,
        output_dir=args.output,
        max_new_tokens=args.max_new_tokens,
    )


if __name__ == "__main__":
    main()
