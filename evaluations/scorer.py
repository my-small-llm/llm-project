"""
predictions.jsonl 기반 독립 스코어링 실행기.

vLLM 추론 없이 저장된 예측 결과만으로 메트릭을 계산한다.
API 기반 모델(GPT, Claude 등)의 결과나 기존 predictions.jsonl 재평가에 활용한다.

실행:
    python -m evaluations.scorer \\
        --predictions eval_output/predictions.jsonl \\
        --dataset eval_data/dataset.jsonl \\
        --output eval_output
"""

import argparse
import csv
import json
import os
from collections import defaultdict
from pathlib import Path


def _group_turn_passes(records: list[dict], step_results) -> list[list[bool]]:
    """step 평가 결과를 turn pass/fail로 집계한다."""
    grouped = defaultdict(lambda: defaultdict(list))

    for record, step_result in zip(records, step_results):
        conv_id = record["conversation_id"]
        turn_idx = record["turn_index"]
        step_idx = record["step_index"]
        grouped[conv_id][turn_idx].append((step_idx, step_result))

    if not grouped:
        return []

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


def score_predictions(
    records: list[dict],
    tool_schemas: dict | None,
    output_dir: Path,
    model_name: str = "",
    dataset_name: str = "",
) -> None:
    """
    predictions.jsonl 레코드들로 메트릭을 계산하고 결과를 저장한다.

    Parameters
    ----------
    records : predictions.jsonl의 레코드 리스트
        각 레코드는 conversation_id, turn_index, step_index,
        is_tool_call, gt_response, prediction 필드를 가진다.
    tool_schemas : {함수명: {properties, required}} 형태의 스키마 (없으면 None)
        None이면 param_hallucination, argument_type 메트릭은 N/A로 처리된다.
    output_dir : 결과 저장 경로
    model_name : eval_results.json에 기록할 모델명
    dataset_name : eval_results.json에 기록할 데이터셋명
    """
    from evaluations.metrics import evaluate_function_calls, evaluate_function_call_step
    from evaluations.multi_turn_metrics import evaluate_multi_turn

    output_dir.mkdir(parents=True, exist_ok=True)

    labels = [r["gt_response"] for r in records]
    predictions = [r["prediction"] for r in records]

    # Tool Call Level
    tc_results = evaluate_function_calls(labels, predictions, tool_schemas=tool_schemas)
    print(tc_results.summary())

    step_results = [
        evaluate_function_call_step(label, pred, tool_schemas=tool_schemas)
        for label, pred in zip(labels, predictions)
    ]

    # Turn/Conversation Level
    conv_turn_passes = _group_turn_passes(records, step_results)
    mt_results = evaluate_multi_turn(conv_turn_passes, aggregated=tc_results)
    print(mt_results.summary())

    # 결과 저장
    results = {
        "model": model_name,
        "dataset": dataset_name,
        "tool_call_level": tc_results.to_dict(),
        "multi_turn": mt_results.to_dict(),
    }

    result_json_path = output_dir / "eval_results.json"
    with open(result_json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"결과 저장: {result_json_path}")

    result_csv_path = output_dir / "eval_results.csv"
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


def _load_predictions(predictions_path: str) -> list[dict]:
    """predictions.jsonl 파일을 로드한다."""
    with open(predictions_path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _load_tool_schemas_from_dataset(dataset_path: str) -> dict | None:
    """데이터셋 파일의 첫 번째 대화에서 tool_schemas를 추출한다."""
    from evaluations.preprocessing import extract_tool_schemas

    if os.path.exists(dataset_path):
        with open(dataset_path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    conv = json.loads(line)
                    if conv.get("tools"):
                        return extract_tool_schemas(conv["tools"])
    else:
        from datasets import load_dataset
        ds = load_dataset(dataset_path, split="test")
        if len(ds) > 0 and ds[0].get("tools"):
            return extract_tool_schemas(ds[0]["tools"])
    return None


def main():
    parser = argparse.ArgumentParser(description="predictions.jsonl 기반 독립 스코어링")
    parser.add_argument("--predictions", required=True, help="predictions.jsonl 파일 경로")
    parser.add_argument(
        "--dataset",
        required=True,
        help="tool_schemas 추출용 데이터셋 경로 또는 HuggingFace ID",
    )
    parser.add_argument(
        "--output",
        default="eval_output",
        help="결과 저장 디렉토리",
    )
    parser.add_argument(
        "--model",
        default="",
        help="결과 JSON에 기록할 모델명 (선택)",
    )
    args = parser.parse_args()

    print(f"predictions 로드: {args.predictions}")
    records = _load_predictions(args.predictions)
    print(f"  총 레코드 수: {len(records)}")

    print(f"tool_schemas 추출: {args.dataset}")
    tool_schemas = _load_tool_schemas_from_dataset(args.dataset)
    print(f"  추출된 함수 수: {len(tool_schemas) if tool_schemas else 0}")

    score_predictions(
        records=records,
        tool_schemas=tool_schemas,
        output_dir=Path(args.output),
        model_name=args.model,
        dataset_name=args.dataset or "",
    )


if __name__ == "__main__":
    main()
