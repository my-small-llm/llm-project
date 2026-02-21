"""
평가용 골드 데이터 세트(Gold Testset) JSONL 생성 파이프라인.

사용법:
    python -m datagen.generate_gold_batch

출력:
    datagen/output/gold_batch_input.jsonl
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


# ================================================================
# 단일 골드 요청 생성
# ================================================================

def make_gold_request_body(category_name: str, instruction: str, request_idx: int) -> dict:
    """
    하나의 골드 Batch API 요청을 JSONL 형식의 dict로 만듭니다.
    """
    uid = random.choice(USER_IDS)
    chat_date = generate_random_date()

    # 골드 전용 유저 프롬프트 생성 (시나리오 주입)
    user_prompt = build_gold_user_prompt(
        tools=tools,
        tools_return_format=tools_return_format,
        uid=uid,
        chat_date=chat_date,
        category_name=category_name,
        category_instruction=instruction,
    )

    instructions = (
        "당신은 배달 앱 AI 상담사를 위해 멀티턴 챗봇 파인튜닝용 데이터를 생성하는 전문가입니다.\n\n"
        + SYSTEM_PROMPT_FIXED
    )

    return {
        "custom_id": f"gold-req-{request_idx}",
        "method": "POST",
        "url": "/v1/responses",
        "body": {
            "model": MODEL,
            "instructions": instructions,
            "input": user_prompt,
        },
    }


# ================================================================
# 메인: 골드 JSONL 파일 생성
# ================================================================

def main():
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
    args = parser.parse_args()

    if args.output is None:
        output_path = Path(__file__).parent / "output" / "gold_batch_input.jsonl"
    else:
        output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    random.seed(args.seed)

    total_count = 0
    with open(output_path, "w", encoding="utf-8") as f:
        # GOLD_CATEGORIES 딕셔너리를 순회
        for category_name, info in GOLD_CATEGORIES.items():
            run_count = info["count"]
            instruction = info["instruction"]

            # 지정된 수량만큼 생성
            for i in range(run_count):
                request_body = make_gold_request_body(category_name, instruction, total_count)
                f.write(json.dumps(request_body, ensure_ascii=False) + "\n")
                total_count += 1
                
    print(f"[완료] 총 {total_count}건의 평가용 골드 요청을 {output_path}에 저장했습니다.")
    print(f"[정보] 골드 배치 제출은 `python -m datagen.submit_batch --input datagen/output/gold_batch_input.jsonl` 을 사용하세요.")


if __name__ == "__main__":
    main()
