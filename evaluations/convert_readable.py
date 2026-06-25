"""
predictions.jsonl을 가독성 좋은 마크다운 파일로 변환한다.

실행:
    python -m evaluations.convert_readable \
        --predictions eval_output_api/predictions.jsonl \
        --output eval_output_api/predictions_readable.md
"""

import argparse
import json


def convert(predictions_path: str, output_path: str) -> None:
    with open(predictions_path, encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]

    lines = []
    for r in records:
        tc = "tool_call" if r["is_tool_call"] else "non_tool_call"
        lines.append(
            f'# conv={r["conversation_id"]} turn={r["turn_index"]} '
            f'step={r["step_index"]} {tc}'
        )
        lines.append("")
        lines.append("**GT**")
        lines.append(f'```\n{r["gt_response"]}\n```')
        lines.append("")
        lines.append("**PRED**")
        lines.append(f'```\n{r["prediction"]}\n```')
        lines.append("")
        lines.append("---")
        lines.append("")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"총 {len(records)}개 레코드 → {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="predictions.jsonl을 가독성 좋은 마크다운으로 변환"
    )
    parser.add_argument(
        "--predictions",
        required=True,
        help="predictions.jsonl 파일 경로",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="출력 파일 경로 (기본: predictions.jsonl과 같은 디렉토리에 predictions_readable.md)",
    )
    args = parser.parse_args()

    output = args.output
    if output is None:
        output = args.predictions.replace(".jsonl", "_readable.md")

    convert(args.predictions, output)


if __name__ == "__main__":
    main()
