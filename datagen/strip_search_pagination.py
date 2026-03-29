"""dataset.jsonl의 search_restaurants page/page_size 관련 필드를 정리한다.

사용법:
    python -m datagen.strip_search_pagination \
        --input train_data/dataset_500_redownload.jsonl \
        --output train_data/dataset_500_redownload_stripped.jsonl
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


_TOOL_CALL_RE = re.compile(r"<tool_call>\s*(.*?)\s*</tool_call>", re.DOTALL)
_TOOL_RESPONSE_RE = re.compile(r"<tool_response>\s*(.*?)\s*</tool_response>", re.DOTALL)


def _strip_pagination_from_content(content: str) -> tuple[str, bool]:
    """assistant content 안의 search_restaurants tool_call에서 page/page_size를 제거한다."""
    match = _TOOL_CALL_RE.search(content)
    if not match:
        return content, False

    raw = match.group(1)
    try:
        tool_call = json.loads(raw)
    except json.JSONDecodeError:
        return content, False

    if tool_call.get("name") != "search_restaurants":
        return content, False

    arguments = tool_call.get("arguments")
    if not isinstance(arguments, dict):
        return content, False

    removed = False
    for key in ("page", "page_size"):
        if key in arguments:
            del arguments[key]
            removed = True

    if not removed:
        return content, False

    replacement = "<tool_call>\n" + json.dumps(tool_call, ensure_ascii=False) + "\n</tool_call>"
    return content[: match.start()] + replacement + content[match.end() :], True


def _normalize_pagination_in_response(content: str) -> tuple[str, bool]:
    """user content 안의 tool_response pagination.page_size를 20으로 통일한다."""
    match = _TOOL_RESPONSE_RE.search(content)
    if not match:
        return content, False

    raw = match.group(1)
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return content, False

    changed = False

    def normalize_item(item: dict) -> None:
        nonlocal changed
        pagination = item.get("pagination")
        if isinstance(pagination, dict) and pagination.get("page_size") != 20:
            pagination["page_size"] = 20
            changed = True

    if isinstance(payload, dict):
        normalize_item(payload)
    elif isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                normalize_item(item)

    if not changed:
        return content, False

    replacement = "<tool_response>\n" + json.dumps(payload, ensure_ascii=False) + "\n</tool_response>"
    return content[: match.start()] + replacement + content[match.end() :], True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="dataset.jsonl의 search_restaurants tool_call에서 page/page_size 제거"
    )
    parser.add_argument("--input", required=True, help="입력 dataset.jsonl 경로")
    parser.add_argument("--output", required=True, help="출력 dataset.jsonl 경로")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        raise SystemExit(f"[오류] 입력 파일이 없습니다: {input_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    total_records = 0
    touched_records = 0
    touched_tool_calls = 0
    normalized_responses = 0

    with input_path.open("r", encoding="utf-8") as fin, output_path.open(
        "w", encoding="utf-8"
    ) as fout:
        for line in fin:
            if not line.strip():
                continue

            total_records += 1
            record = json.loads(line)
            record_touched = False

            for message in record.get("messages", []):
                role = message.get("role")
                content = message.get("content", "")

                if role == "assistant":
                    new_content, changed = _strip_pagination_from_content(content)
                    if changed:
                        message["content"] = new_content
                        record_touched = True
                        touched_tool_calls += 1

                elif role == "user":
                    new_content, changed = _normalize_pagination_in_response(content)
                    if changed:
                        message["content"] = new_content
                        record_touched = True
                        normalized_responses += 1

            if record_touched:
                touched_records += 1

            fout.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"[완료] 저장: {output_path}")
    print(f"  → 총 레코드: {total_records}")
    print(f"  → 수정된 레코드: {touched_records}")
    print(f"  → 수정된 tool_call: {touched_tool_calls}")
    print(f"  → 정규화된 tool_response.pagination.page_size: {normalized_responses}")


if __name__ == "__main__":
    main()
