"""
파싱된 대화를 Qwen 파인튜닝용 데이터셋으로 전처리 및 HuggingFace 업로드.

사용법:
    python -m data.preprocess [--input data/result_lst.json]

출력:
    data/dataset.jsonl    (로컬 저장)
"""

import argparse
import json
import random
from pathlib import Path

import pandas as pd

from datagen.config import tools
from datagen.parse import parse_metadata, parse_to_qwen_format


# ================================================================
# Qwen 시스템 프롬프트 생성
# ================================================================

def generate_qwen_system_prompt(
    tools: list,
    uid: str,
    current_date: str = "2024-09-30",
) -> str:
    """
    Qwen 2.5 Function Calling 형식의 시스템 프롬프트를 생성합니다.

    Args:
        tools: 함수 스펙 리스트 (config.tools)
        uid: 고객 ID (예: "U002")
        current_date: 대화 날짜

    Returns:
        Qwen chat template에 맞는 시스템 프롬프트 문자열
    """
    header = """당신은 배달 앱 AI 상담사입니다. 성심성의껏 상담하십시오.

로그인한 사용자의 현재 ID: %s
오늘 날짜: %s

# Tools

You may call one or more functions to assist with the user query.

You are provided with function signatures within <tools></tools> XML tags:
<tools>
""" % (uid, current_date)

    # 도구 순서 셔플 (학습 다양성)
    shuffled_tools = tools[:]
    random.shuffle(shuffled_tools)

    tool_defs = ""
    for tool in shuffled_tools:
        entry = {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["parameters"],
            },
        }
        tool_defs += json.dumps(entry, ensure_ascii=False) + "\n"

    footer = """</tools>

For each function call, return a json object with function name and arguments within <tool_call></tool_call> XML tags:
<tool_call>
{"name": <function-name>, "arguments": <args-json-object>}
</tool_call>"""

    return header + tool_defs + footer


# ================================================================
# 메인: 전처리 파이프라인
# ================================================================

def main():
    parser = argparse.ArgumentParser(
        description="result_lst.json을 Qwen 파인튜닝 데이터셋으로 전처리합니다."
    )
    parser.add_argument(
        "--input",
        type=str,
        default=None,
        help="결과 JSON 경로 (기본값: data/output/result_lst.json)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="출력 jsonl 경로 (기본값: data/output/dataset.jsonl)",
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="랜덤 시드 (기본값: 42)",
    )
    args = parser.parse_args()

    # 경로 설정
    if args.input is None:
        input_path = Path(__file__).parent / "output" / "result_lst.json"
    else:
        input_path = Path(args.input)

    if args.output is None:
        output_path = Path(__file__).parent / "output" / "dataset.jsonl"
    else:
        output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    random.seed(args.seed)

    # ── Step 1: 결과 로드 ──
    if not input_path.exists():
        print(f"[오류] 입력 파일이 없습니다: {input_path}")
        print("[힌트] 먼저 `python -m data.retrieve_batch`를 실행하세요.")
        return

    with open(input_path, "r", encoding="utf-8") as f:
        result_lst = json.load(f)
    print(f"[1/4] 결과 로드: {len(result_lst)}건")

    # ── Step 2: 파싱 (메타데이터 + Qwen 포맷) ──
    uids = []
    dates = []
    messages_lst = []
    skipped = 0

    for sample in result_lst:
        try:
            uid, date = parse_metadata(sample)
            message = parse_to_qwen_format(sample)
            if not message:
                skipped += 1
                continue
            uids.append(uid)
            dates.append(date)
            messages_lst.append(message)
        except Exception:
            skipped += 1
            continue

    print(f"[2/4] 파싱 완료: 성공 {len(messages_lst)}건, 스킵 {skipped}건")

    # ── Step 3: 시스템 프롬프트 생성 + DataFrame ──
    system_prompts = []
    for uid, date in zip(uids, dates):
        system_prompts.append(
            generate_qwen_system_prompt(tools, uid, date or "2024-09-30")
        )

    tools_lst = [tools] * len(messages_lst)

    df = pd.DataFrame({
        "tools": tools_lst,
        "uid": uids,
        "dates": dates,
        "messages": messages_lst,
        "system_prompt": system_prompts,
    })
    print(f"[3/4] DataFrame 생성: {len(df)}행 × {len(df.columns)}열")

    # ── Step 4: 저장 ──
    df.to_json(output_path, orient="records", lines=True, force_ascii=False)
    print(f"[완료] 로컬 저장: {output_path} ({output_path.stat().st_size / 1024:.1f} KB)")




if __name__ == "__main__":
    main()
