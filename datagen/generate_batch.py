"""
OpenAI Batch API용 JSONL 입력 파일 생성.

사용법:
    python -m datagen.generate_batch [--count N] [--output PATH] [--seed N]

출력:
    datagen/output/batch_input.jsonl

CLI 인수:
    --count  INT   생성할 Batch API 요청 수.
                   잡담 데이터(ChatbotData.csv)를 정상적으로 로드한 경우
                   실제 생성 수는 min(count, 잡담데이터 건수)로 결정됩니다.
                   로드에 실패하면 UNSUPPORTED_SCENARIOS를 반복하여 count건을
                   채웁니다.
                   기본값: 400

    --output PATH  생성된 JSONL 파일의 저장 경로.
                   지정하지 않으면 스크립트 위치 기준으로
                   datagen/output/batch_input.jsonl 에 저장됩니다.
                   부모 디렉터리가 없으면 자동으로 생성합니다.

    --seed   INT   random 모듈의 시드값.
                   동일한 시드를 사용하면 USER_IDS·QUESTION_TOPICS·
                   UNSUPPORTED_SCENARIOS의 샘플링 결과가 재현됩니다.
                   기본값: 42
"""

import argparse
import json
import random
import sys
from io import StringIO
from pathlib import Path

import pandas as pd

from datagen.config import (
    CHATBOT_DATA_URL,
    MODEL,
    QUESTION_TOPICS,
    UNSUPPORTED_SCENARIOS,
    USER_IDS,
    generate_random_date,
    pick_random_yn,
    tools,
    tools_return_format,
)
from datagen.prompts import SYSTEM_PROMPT_FIXED, build_user_prompt


def load_questions(url: str = CHATBOT_DATA_URL) -> list[str]:
    """잡담 CSV 데이터를 다운로드하여 question 목록을 반환합니다."""
    try:
        df = pd.read_csv(url)
        questions = df.iloc[:, 0].dropna().tolist()
        print(f"[INFO] 잡담 데이터 {len(questions)}건 로드 완료")
        return questions
    except Exception as e:
        print(f"[WARN] 잡담 데이터 로드 실패: {e}")
        print("[WARN] unsupported_scenarios만 사용합니다.")
        return []


def make_request_body(question: str, request_idx: int) -> dict:
    """
    하나의 Batch API 요청을 JSONL 형식의 dict로 만듭니다.

    Args:
        question: 잡담 데이터에서 가져온 unsupported scenario 추가 항목
        request_idx: 요청 인덱스 (custom_id 생성용)

    Returns:
        JSONL에 한 줄로 저장될 dict
    """
    # 랜덤 파라미터 생성
    uid = random.choice(USER_IDS)
    two_question_topics = random.sample(QUESTION_TOPICS, 2)
    one_unsupported_scenario = random.sample(UNSUPPORTED_SCENARIOS, 1)
    chat_date = generate_random_date()
    complain = pick_random_yn()

    # unsupported_scenarios에 잡담 question을 추가
    combined_unsupported = one_unsupported_scenario + [question]

    # 유저 프롬프트 생성
    user_prompt = build_user_prompt(
        tools=tools,
        tools_return_format=tools_return_format,
        uid=uid,
        chat_date=chat_date,
        complain=complain,
        two_question_topics=two_question_topics,
        one_unsupported_scenario=combined_unsupported,
    )

    # instructions: 고정 시스템 프롬프트 (prompt caching 대상)
    instructions = SYSTEM_PROMPT_FIXED

    return {
        "custom_id": f"req-{request_idx}",
        "method": "POST",
        "url": "/v1/responses",
        "body": {
            "model": MODEL,
            "instructions": instructions,
            "input": user_prompt,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Batch API용 JSONL 입력 파일을 생성합니다."
    )
    parser.add_argument(
        "--count",
        type=int,
        default=400,
        help="생성할 요청 수 (기본값: 400)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="출력 파일 경로 (기본값: datagen/output/batch_input.jsonl)",
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

    # 출력 경로 설정
    if args.output is None:
        output_path = Path(__file__).parent / "output" / "batch_input.jsonl"
    else:
        output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 랜덤 시드 설정
    random.seed(args.seed)

    # 잡담 데이터 로드
    questions = load_questions()
    count = min(args.count, len(questions)) if questions else args.count

    if not questions:
        # 잡담 데이터 없으면 unsupported_scenarios를 반복 사용
        questions = UNSUPPORTED_SCENARIOS * (count // len(UNSUPPORTED_SCENARIOS) + 1)

    # JSONL 파일 생성
    with open(output_path, "w", encoding="utf-8") as f:
        for i in range(count):
            request = make_request_body(questions[i], i)
            f.write(json.dumps(request, ensure_ascii=False) + "\n")

    print(f"[완료] {count}건의 요청을 {output_path}에 저장했습니다.")
    print(f"[파일 크기] {output_path.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
