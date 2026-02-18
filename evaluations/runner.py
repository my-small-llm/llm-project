"""
평가 파이프라인 실행기.

데이터셋 로드 → 전처리 → vLLM 추론 → 메트릭 계산 → 결과 출력/저장.

사용법:
    # 싱글턴 평가
    python -m evaluations.runner \\
        --model Qwen/Qwen2.5-7B-Instruct \\
        --dataset jjun123/delivery-app-function-calling-datasets-korean

    # 멀티턴 평가 포함
    python -m evaluations.runner \\
        --model Qwen/Qwen2.5-7B-Instruct \\
        --dataset jjun123/delivery-app-function-calling-datasets-korean \\
        --multi-turn

※ vLLM이 설치된 GPU 환경에서만 실행 가능합니다.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from evaluations.metrics import evaluate_function_calls
from evaluations.multi_turn_metrics import evaluate_multi_turn
from evaluations.preprocessing import (
    prepare_eval_data,
    prepare_multi_turn_eval_data,
    extract_tool_schemas,
)


def run_evaluation(
    model_name: str,
    dataset_name: str,
    test_ratio: float = 0.2,
    output_path: str = "evaluation_results.csv",
    temperature: float = 0,
    max_tokens: int = 2048,
    multi_turn: bool = False,
) -> None:
    """
    전체 평가 파이프라인을 실행합니다.

    Args:
        model_name: HuggingFace 모델 경로
        dataset_name: HuggingFace 데이터셋 경로
        test_ratio: 테스트 데이터 비율
        output_path: 결과 CSV 저장 경로
        temperature: 샘플링 온도 (0 = greedy)
        max_tokens: 최대 생성 토큰 수
        multi_turn: 멀티턴(HammerBench) 평가 포함 여부
    """
    # ── Step 1: 데이터셋 로드 ──
    print(f"[1/4] 데이터셋 로드: {dataset_name}")
    try:
        from datasets import load_dataset
    except ImportError:
        print("[오류] `pip install datasets`를 먼저 실행하세요.")
        sys.exit(1)

    dataset = load_dataset(dataset_name, split="train")
    print(f"  → 전체 {len(dataset)}개 샘플")

    # ── Step 2: 전처리 ──
    print(f"[2/4] 전처리 (test_ratio={test_ratio})")

    # tool 스키마 추출 시도
    tool_schemas = None
    if "tools" in dataset.column_names:
        first_tools = dataset[0]["tools"]
        if first_tools:
            tool_schemas = extract_tool_schemas(first_tools)
            print(f"  → tool 스키마 {len(tool_schemas)}개 함수 추출 완료")

    if multi_turn:
        conv_prompts, conv_labels, schemas = prepare_multi_turn_eval_data(
            dataset, test_ratio=test_ratio
        )
        # 스키마가 prepare_multi_turn에서도 나오면 사용
        if schemas and tool_schemas is None:
            tool_schemas = schemas
        # 플랫 리스트도 생성 (CSV 저장용)
        prompts = [p for conv in conv_prompts for p in conv]
        labels = [l for conv in conv_labels for l in conv]
        print(f"  → 대화 {len(conv_prompts)}개, 총 턴: {len(prompts)}개")
    else:
        prompts, labels = prepare_eval_data(dataset, test_ratio=test_ratio)
        print(f"  → 테스트 프롬프트: {len(prompts)}개")

    # ── Step 3: vLLM 추론 ──
    print(f"[3/4] vLLM 추론: {model_name}")
    try:
        from vllm import LLM, SamplingParams
    except ImportError:
        print("[오류] `pip install vllm`을 먼저 실행하세요.")
        print("[힌트] GPU 환경에서만 vLLM이 동작합니다.")
        sys.exit(1)

    sampling_params = SamplingParams(
        temperature=temperature,
        max_tokens=max_tokens,
        stop=["<|im_end|>"],
    )

    llm = LLM(model=model_name)
    outputs = llm.generate(prompts, sampling_params)
    predictions = [sample.outputs[0].text.strip() for sample in outputs]

    # ── Step 4: 메트릭 계산 ──
    print("[4/4] 메트릭 계산")
    print("=" * 50)

    # 기본 메트릭 (BFCL + Unitxt)
    results = evaluate_function_calls(labels, predictions, tool_schemas=tool_schemas)
    print(results.summary())

    # 멀티턴 메트릭 (HammerBench)
    mt_results = None
    if multi_turn:
        # predictions을 대화별로 다시 그룹핑
        conv_predictions: list[list[str]] = []
        idx = 0
        for conv in conv_labels:
            conv_predictions.append(predictions[idx : idx + len(conv)])
            idx += len(conv)

        mt_results = evaluate_multi_turn(
            conv_labels, conv_predictions, tool_schemas=tool_schemas
        )
        print()
        print(mt_results.summary())

    print("=" * 50)

    # ── 결과 저장 ──
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame({
        "prompt": prompts,
        "label": labels,
        "output": predictions,
    })
    df.to_csv(output_file, index=False, encoding="utf-8-sig")
    print(f"\n[완료] 결과 저장: {output_file}")

    # 메트릭 JSON 저장
    metrics_dict = results.to_dict()
    if mt_results is not None:
        metrics_dict["multi_turn"] = mt_results.to_dict()

    metrics_path = output_file.with_suffix(".metrics.json")
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics_dict, f, ensure_ascii=False, indent=2)
    print(f"[완료] 메트릭 저장: {metrics_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Function Calling 모델 평가 파이프라인을 실행합니다."
    )
    parser.add_argument(
        "--model",
        type=str,
        required=True,
        help="HuggingFace 모델 경로 (예: Qwen/Qwen2.5-7B-Instruct)",
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default="jjun123/delivery-app-function-calling-datasets-korean",
        help="HuggingFace 데이터셋 경로",
    )
    parser.add_argument(
        "--test-ratio",
        type=float,
        default=0.2,
        help="테스트 데이터 비율 (기본값: 0.2)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="evaluation_results.csv",
        help="결과 CSV 저장 경로 (기본값: evaluation_results.csv)",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0,
        help="샘플링 온도 (기본값: 0 = greedy)",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=2048,
        help="최대 생성 토큰 수 (기본값: 2048)",
    )
    parser.add_argument(
        "--multi-turn",
        action="store_true",
        help="멀티턴(HammerBench) 평가도 함께 실행",
    )
    args = parser.parse_args()

    run_evaluation(
        model_name=args.model,
        dataset_name=args.dataset,
        test_ratio=args.test_ratio,
        output_path=args.output,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        multi_turn=args.multi_turn,
    )


if __name__ == "__main__":
    main()
