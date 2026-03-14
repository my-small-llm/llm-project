"""
OpenAI API 기반 평가 실행기.

GT 히스토리 기반 싱글턴 분할 → OpenAI API 추론 → 메트릭 계산 → 결과 저장.
.env 파일에서 OPENAI_API_KEY를 로드한다.

실행:
    python -m evaluations.api_runner \
        --model gpt-4o \
        --dataset eval_data/dataset.jsonl \
        --output eval_output_api

    # 추론만 수행 (스코어링 생략)
    python -m evaluations.api_runner \
        --model gpt-4o \
        --dataset eval_data/dataset.jsonl \
        --output eval_output_api \
        --inference-only
"""

import argparse
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from tqdm import tqdm

load_dotenv()


def _load_conversations(dataset_path: str) -> list[dict]:
    """JSONL 파일 또는 HuggingFace 데이터셋 ID에서 대화 목록을 로드한다."""
    if os.path.exists(dataset_path):
        with open(dataset_path, encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]
    else:
        from datasets import load_dataset
        ds = load_dataset(dataset_path, split="test")
        return list(ds)


def _run_api_inference(
    inference_inputs: list,
    model_name: str,
    max_new_tokens: int = 512,
) -> list[str]:
    """
    OpenAI API를 사용해 순차 추론을 수행한다.

    Parameters
    ----------
    inference_inputs : InferenceInput 리스트
    model_name : OpenAI 모델명 (gpt-4o, gpt-4o-mini 등)
    max_new_tokens : 최대 생성 토큰 수

    Returns
    -------
    생성된 텍스트 리스트
    """
    client = OpenAI()
    predictions = []
    max_retries = 5

    for inp in tqdm(inference_inputs, desc="API 추론"):
        for attempt in range(max_retries):
            try:
                response = client.chat.completions.create(
                    model=model_name,
                    messages=inp.messages,
                    temperature=0.0,
                    max_tokens=max_new_tokens,
                )
                prediction = response.choices[0].message.content or ""
                predictions.append(prediction)
                break
            except Exception as e:
                if "rate_limit" in str(e).lower() or "429" in str(e):
                    wait = 2 ** attempt
                    tqdm.write(f"  Rate limit 도달, {wait}초 대기 후 재시도...")
                    time.sleep(wait)
                else:
                    raise

    return predictions


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
) -> None:
    """
    OpenAI API 기반 전체 평가 파이프라인 실행.

    1. 데이터 로드 → 싱글턴 분할
    2. OpenAI API 추론
    3. predictions.jsonl 저장
    4. 메트릭 계산 + 결과 저장 (inference_only=True이면 생략)
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

    # 2. OpenAI API 추론
    print(f"[2/4] OpenAI API 추론 시작: {model_name}")
    predictions = _run_api_inference(inference_inputs, model_name, max_new_tokens)
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
    parser = argparse.ArgumentParser(
        description="OpenAI API 기반 Function Calling 평가"
    )
    parser.add_argument(
        "--model",
        default="gpt-4o",
        help="OpenAI 모델명 (gpt-4o, gpt-4o-mini 등)",
    )
    parser.add_argument(
        "--dataset",
        default="eval_data/dataset.jsonl",
        help="평가 데이터셋 경로 또는 HuggingFace ID",
    )
    parser.add_argument(
        "--output",
        default="eval_output_api",
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
    args = parser.parse_args()

    run_evaluation(
        model_name=args.model,
        dataset_path=args.dataset,
        output_dir=args.output,
        max_new_tokens=args.max_new_tokens,
        inference_only=args.inference_only,
    )


if __name__ == "__main__":
    main()
