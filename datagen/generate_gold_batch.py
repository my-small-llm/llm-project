"""
평가용 골드 데이터 세트(Gold Testset) JSONL 생성 파이프라인.

사용법:
    python -m datagen.generate_gold_batch [--output PATH] [--seed N]

출력:
    datagen/output/gold_batch_input.jsonl

CLI 인수:
    --output PATH  생성된 JSONL 파일의 저장 경로.
                   지정하지 않으면 스크립트 위치 기준으로
                   datagen/output/gold_batch_input.jsonl 에 저장됩니다.
                   부모 디렉터리가 없으면 자동으로 생성합니다.

    --seed   INT   random 모듈의 시드값.
                   동일한 시드를 사용하면 USER_IDS 샘플링 결과가 재현됩니다.
                   기본값: 42
"""

import argparse
import json
import random
from pathlib import Path

from datagen.config import (
    MODEL,
    USER_IDS,
    GOLD_CATEGORIES,
    generate_random_date,
    tools,
    tools_return_format,
)
from datagen.prompts import SYSTEM_PROMPT_FIXED, build_gold_user_prompt


def make_gold_request_body(category_name: str, instruction: str, request_idx: int) -> dict:
    """
    하나의 골드 Batch API 요청을 JSONL 형식의 dict로 만듭니다.
    """
    uid = random.choice(USER_IDS)
    chat_date = generate_random_date()

    user_prompt = build_gold_user_prompt(
        tools=tools,
        tools_return_format=tools_return_format,
        uid=uid,
        chat_date=chat_date,
        category_name=category_name,
        category_instruction=instruction,
    )

    return {
        "custom_id": f"gold-req-{request_idx}",
        "method": "POST",
        "url": "/v1/responses",
        "body": {
            "model": MODEL,
            "instructions": SYSTEM_PROMPT_FIXED,
            "input": user_prompt,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="평가용 골드 Batch API 입력 파일(JSONL)을 생성합니다."
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="출력 파일 경로 (기본값: datagen/output/gold_batch_input.jsonl)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="랜덤 시드 (재현성, 기본값: 42)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if args.output is None:
        output_path = Path(__file__).parent / "output" / "gold_batch_input.jsonl"
    else:
        output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    random.seed(args.seed)

    total_count = 0
    with open(output_path, "w", encoding="utf-8") as f:
        for category_name, info in GOLD_CATEGORIES.items():
            run_count = info["count"]
            instruction = info["instruction"]

            for i in range(run_count):
                request_body = make_gold_request_body(category_name, instruction, total_count)
                f.write(json.dumps(request_body, ensure_ascii=False) + "\n")
                total_count += 1

    print(f"[완료] 총 {total_count}건의 평가용 골드 요청을 {output_path}에 저장했습니다.")
    print(f"[파일 크기] {output_path.stat().st_size / 1024:.1f} KB")
    print(f"[힌트] 배치 제출: python -m datagen.submit_batch --input datagen/output/gold_batch_input.jsonl")


if __name__ == "__main__":
    main()
