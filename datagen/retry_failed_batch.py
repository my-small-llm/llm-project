"""
배치 실패 로그를 읽어 원본 입력 JSONL에서 실패한 요청만 다시 추출합니다.

사용법:
    python -m datagen.retry_failed_batch \
        --input train_data/batch_input_500.jsonl \
        --errors train_data/result_lst_500_request_errors.jsonl \
        --output train_data/batch_input_500_retry.jsonl
"""

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="실패한 배치 요청만 다시 추출합니다."
    )
    parser.add_argument("--input", required=True, help="원본 batch input JSONL 경로")
    parser.add_argument("--errors", required=True, help="실패 로그 JSONL 경로")
    parser.add_argument("--output", required=True, help="재시도용 JSONL 출력 경로")
    return parser.parse_args()


def load_failed_custom_ids(error_path: Path) -> set[str]:
    failed_ids = set()
    with error_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            custom_id = obj.get("custom_id")
            if custom_id:
                failed_ids.add(custom_id)
    return failed_ids


def main():
    args = parse_args()
    input_path = Path(args.input)
    error_path = Path(args.errors)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    failed_ids = load_failed_custom_ids(error_path)
    kept = 0

    with input_path.open("r", encoding="utf-8") as src, output_path.open(
        "w", encoding="utf-8"
    ) as dst:
        for line in src:
            if not line.strip():
                continue
            obj = json.loads(line)
            if obj.get("custom_id") in failed_ids:
                dst.write(json.dumps(obj, ensure_ascii=False) + "\n")
                kept += 1

    print(f"[완료] 실패 요청 {kept}건을 {output_path}에 저장했습니다.")


if __name__ == "__main__":
    main()
