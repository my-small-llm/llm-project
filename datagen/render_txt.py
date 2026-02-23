"""
dataset.jsonl의 각 레코드를 Qwen chat template 형식의 .txt 파일로 변환하여 저장합니다.

사용법:
    python -m datagen.render_txt [--input PATH] [--output PATH]

출력:
    datagen/output/samples/sample_0001.txt  (레코드별 개별 파일)

CLI 인수:
    --input PATH    입력 JSONL 파일 경로.
                    기본값: datagen/output/dataset.jsonl

    --output PATH   출력 디렉토리 경로.
                    기본값: 입력 파일과 같은 폴더의 samples/
"""

import argparse
import json
from pathlib import Path


def to_qwen_text(record: dict) -> str:
    system_prompt = record.get("system_prompt", "")
    messages = record.get("messages", [])

    parts = [f"<|im_start|>system\n{system_prompt}<|im_end|>"]
    for msg in messages:
        parts.append(f"<|im_start|>{msg['role']}\n{msg['content']}<|im_end|>")

    return "\n".join(parts) + "\n"


def main():
    parser = argparse.ArgumentParser(
        description="dataset.jsonl을 대화별 .txt 파일로 내보냅니다."
    )
    parser.add_argument(
        "--input",
        default=None,
        help="입력 JSONL 파일 경로 (기본값: datagen/output/dataset.jsonl)",
    )
    parser.add_argument(
        "--output", default=None,
        help="출력 디렉토리 경로 (기본값: 입력 파일과 같은 폴더의 samples/)"
    )
    args = parser.parse_args()

    if args.input is None:
        input_path = Path(__file__).parent / "output" / "dataset.jsonl"
    else:
        input_path = Path(args.input)
    if not input_path.exists():
        print(f"[오류] 파일을 찾을 수 없습니다: {input_path}")
        return

    output_dir = Path(args.output) if args.output else input_path.parent / "samples"
    output_dir.mkdir(parents=True, exist_ok=True)

    lines = [l for l in input_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    total = len(lines)

    for i, line in enumerate(lines, start=1):
        record = json.loads(line)
        txt = to_qwen_text(record)
        out_file = output_dir / f"sample_{i:04d}.txt"
        out_file.write_text(txt, encoding="utf-8")

    print(f"완료: {total}개 파일 → {output_dir.resolve()}")


if __name__ == "__main__":
    main()
