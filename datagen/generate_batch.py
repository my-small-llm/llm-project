"""
OpenAI Batch API용 JSONL 입력 파일 생성.

사용법:
    python -m data.generate_batch --count 400

출력:
    data/output/batch_input.jsonl
"""

import argparse
import json
import random
import sys
from io import StringIO
from pathlib import Path

import pandas as pd

from data.config import (
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
from data.prompts import SYSTEM_PROMPT_FIXED, build_user_prompt


# ================================================================
# 잡담 데이터 로드 (questions 리스트)
# ================================================================

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


# ================================================================
# 단일 요청 생성
# ================================================================

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
    instructions = (
        "당신은 배달 앱 AI 상담사를 위해 멀티턴 챗봇 파인튜닝용 데이터를 생성하는 전문가입니다.\n\n"
        + SYSTEM_PROMPT_FIXED
    )

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


# ================================================================
# 메인: JSONL 파일 생성
# ================================================================

def main():
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
        help="출력 파일 경로 (기본값: data/output/batch_input.jsonl)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="랜덤 시드 (재현성, 기본값: 42)",
    )
    args = parser.parse_args()

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
