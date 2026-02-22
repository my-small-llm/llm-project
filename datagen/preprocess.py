"""
파싱된 대화를 Qwen 파인튜닝용 데이터셋으로 전처리.

사용법:
    python -m datagen.preprocess [--input PATH] [--output PATH] [--seed N]

출력:
    datagen/output/dataset.jsonl

CLI 인수:
    --input  PATH  배치 결과 JSON 파일 경로.
                   지정하지 않으면 datagen/output/result_lst.json을 사용합니다.

    --output PATH  출력 JSONL 파일 경로.
                   지정하지 않으면 datagen/output/dataset.jsonl에 저장합니다.
                   부모 디렉터리가 없으면 자동으로 생성합니다.

    --seed   INT   random 모듈의 시드값.
                   시스템 프롬프트 내 도구 순서 셔플에 사용됩니다.
                   기본값: 42
"""

import argparse
import ast
import json
import random
import re
from pathlib import Path

import pandas as pd

from datagen.config import tools


def parse_metadata(text: str) -> tuple[str | None, str | None]:
    """
    생성된 대화 텍스트에서 고객 ID와 대화날짜를 추출합니다.

    Args:
        text: GPT가 생성한 원본 텍스트
              예) "[고객 ID] a1661d37-... \n[대화날짜] 2024-05-23\n..."

    Returns:
        (customer_id, date) 튜플. 매칭 실패 시 None.
    """
    customer_id_match = re.search(r'\[고객 ID\]\s*([^\s]+)', text)
    date_match = re.search(r'\[대화날짜\]\s*([\d\-]+)', text)
    customer_id = customer_id_match.group(1) if customer_id_match else None
    date = date_match.group(1) if date_match else None
    return customer_id, date


def _safe_parse(content: str):
    """
    JSON 또는 Python literal_eval로 content를 파싱합니다.
    - json.loads: true/false/null 대응
    - ast.literal_eval: True/False/None 대응
    """
    content = content.strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    try:
        return ast.literal_eval(content)
    except Exception as e:
        raise ValueError(f"JSON/Python literal 파싱 실패: {content}") from e


def parse_to_qwen_format(text: str) -> list[dict]:
    """
    GPT가 생성한 대화 텍스트를 Qwen 파인튜닝용 messages 리스트로 변환합니다.

    변환 규칙:
        - (고객)              → role: "user"
        - (AI 상담사)         → role: "assistant"
        - (function_call)     → role: "assistant", <tool_call> 태그로 감싸기
        - (function_response) → role: "user", <tool_response> 태그로 감싸기

    특수 처리:
        - function_call 직전의 assistant 메시지는 제거
          (GPT가 먼저 응답 텍스트를 생성한 뒤 function_call을 호출하는 패턴 대응)

    Args:
        text: GPT 생성 원본 텍스트

    Returns:
        [{"role": "user"|"assistant", "content": "..."}, ...]
    """
    messages = []
    pattern = re.compile(
        r'\((고객|AI 상담사|function_call|function_response)\)\s*(.+?)(?=\n\(|\Z)',
        re.DOTALL,
    )

    last_role = None

    for match in pattern.finditer(text.strip()):
        role_type, content = match.groups()
        content = content.strip()

        if role_type == "고객":
            messages.append({"role": "user", "content": content})
            last_role = "user"

        elif role_type == "AI 상담사":
            messages.append({"role": "assistant", "content": content})
            last_role = "assistant"

        elif role_type == "function_call":
            try:
                calls = _safe_parse(content)

                if not isinstance(calls, list):
                    raise ValueError("function_call은 list 형태여야 합니다.")

                # 직전 assistant 메시지 제거
                if last_role == "assistant" and messages:
                    messages.pop()

                for call in calls:
                    messages.append({
                        "role": "assistant",
                        "content": f"<tool_call>\n{json.dumps(call, ensure_ascii=False)}\n</tool_call>",
                    })
                last_role = "assistant"

            except Exception as e:
                raise ValueError(
                    f"[function_call 파싱 실패] 원본: {content}\n오류: {e}"
                ) from e

        elif role_type == "function_response":
            try:
                parsed = _safe_parse(content)
                payload = json.dumps(parsed, ensure_ascii=False)
                messages.append({
                    "role": "user",
                    "content": f"<tool_response>\n{payload}\n</tool_response>",
                })
                last_role = "user"

            except Exception as e:
                raise ValueError(
                    f"[function_response 파싱 실패] 원본: {content}\n오류: {e}"
                ) from e

    return messages


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="result_lst.json을 Qwen 파인튜닝 데이터셋으로 전처리합니다."
    )
    parser.add_argument(
        "--input",
        type=str,
        default=None,
        help="결과 JSON 경로 (기본값: datagen/output/result_lst.json)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="출력 JSONL 경로 (기본값: datagen/output/dataset.jsonl)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="랜덤 시드 (기본값: 42)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

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

    # 결과 로드
    if not input_path.exists():
        print(f"[오류] 입력 파일이 없습니다: {input_path}")
        print("[힌트] 먼저 `python -m datagen.retrieve_batch`를 실행하세요.")
        return

    with open(input_path, "r", encoding="utf-8") as f:
        result_lst = json.load(f)
    print(f"[1/4] 결과 로드: {len(result_lst)}건")

    # 파싱 (메타데이터 + Qwen 포맷)
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

    # 시스템 프롬프트 생성
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

    # 저장
    df.to_json(output_path, orient="records", lines=True, force_ascii=False)
    print(f"[완료] 로컬 저장: {output_path} ({output_path.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
