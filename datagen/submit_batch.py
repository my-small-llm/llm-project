"""
OpenAI Batch API 배치 제출 및 상태 확인.

사용법:
    python -m datagen.submit_batch [--input PATH] [--output PATH] [--wait] [--poll-interval N]

출력:
    입력 파일명을 기반으로 자동 결정됩니다.
    예) batch_input.jsonl      → datagen/output/batch_input_status.json
        gold_batch_input.jsonl → datagen/output/gold_batch_input_status.json

CLI 인수:
    --input PATH        업로드할 JSONL 파일 경로.
                        지정하지 않으면 스크립트 위치 기준으로
                        datagen/output/batch_input.jsonl 을 사용합니다.

    --output PATH       상태 파일 저장 경로.
                        지정하지 않으면 입력 파일과 같은 디렉터리에
                        {입력파일명}_status.json 으로 저장됩니다.

    --wait              배치 완료까지 폴링 대기합니다.
                        지정하지 않으면 제출 후 즉시 종료합니다.

    --poll-interval N   폴링 간격 (초).
                        기본값: 60
"""

import argparse
import json
import time
from pathlib import Path

import openai


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Batch API 배치를 제출하고 상태를 확인합니다."
    )
    parser.add_argument(
        "--input",
        type=str,
        default=None,
        help="업로드할 JSONL 파일 경로 (기본값: datagen/output/batch_input.jsonl)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="상태 파일 저장 경로 (기본값: 입력 파일과 같은 디렉터리에 {입력파일명}_status.json)",
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="배치 완료까지 폴링 대기 (기본: 제출 후 즉시 종료)",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=60,
        help="폴링 간격 (초, 기본값: 60)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # 입력 경로 설정
    if args.input is None:
        input_path = Path(__file__).parent / "output" / "batch_input.jsonl"
    else:
        input_path = Path(args.input)

    if not input_path.exists():
        print(f"[오류] 입력 파일이 없습니다: {input_path}")
        print("[힌트] 먼저 `python -m datagen.generate_batch`를 실행하세요.")
        return

    if args.output is None:
        status_path = input_path.parent / f"{input_path.stem}_status.json"
    else:
        status_path = Path(args.output)
    status_path.parent.mkdir(parents=True, exist_ok=True)
    client = openai.OpenAI()

    # Step 1: 파일 업로드
    print(f"[1/3] 파일 업로드 중: {input_path}")
    with open(input_path, "rb") as f:
        uploaded_file = client.files.create(file=f, purpose="batch")
    print(f"  → 파일 ID: {uploaded_file.id}")

    # Step 2: 배치 생성
    print("[2/3] 배치 생성 중...")
    batch = client.batches.create(
        input_file_id=uploaded_file.id,
        endpoint="/v1/responses",
        completion_window="24h",
        metadata={
            "description": "Function calling 학습 데이터 생성",
        },
    )
    print(f"  → 배치 ID: {batch.id}")
    print(f"  → 상태: {batch.status}")

    # 상태 정보 저장
    status_info = {
        "batch_id": batch.id,
        "input_file_id": uploaded_file.id,
        "status": batch.status,
        "created_at": str(batch.created_at),
    }
    with open(status_path, "w", encoding="utf-8") as f:
        json.dump(status_info, f, ensure_ascii=False, indent=2)
    print(f"  → 상태 저장: {status_path}")

    # Step 3: (선택) 폴링 대기
    if args.wait:
        print(f"[3/3] 배치 완료 대기 중 (폴링 간격: {args.poll_interval}초)...")
        while True:
            batch = client.batches.retrieve(batch.id)
            print(f"  상태: {batch.status} | "
                  f"완료: {batch.request_counts.completed}/{batch.request_counts.total} | "
                  f"실패: {batch.request_counts.failed}")

            if batch.status in ("completed", "failed", "expired", "cancelled"):
                break
            time.sleep(args.poll_interval)

        # 최종 상태 업데이트
        status_info["status"] = batch.status
        status_info["output_file_id"] = batch.output_file_id
        status_info["error_file_id"] = batch.error_file_id
        with open(status_path, "w", encoding="utf-8") as f:
            json.dump(status_info, f, ensure_ascii=False, indent=2)

        if batch.status == "completed":
            print(f"[완료] 배치가 성공적으로 완료되었습니다.")
            print(f"  → 결과 파일 ID: {batch.output_file_id}")
            print(f"  → 다음 단계: `python -m datagen.retrieve_batch`")
        else:
            print(f"[실패] 배치 상태: {batch.status}")
            if batch.error_file_id:
                print(f"  → 에러 파일 ID: {batch.error_file_id}")
    else:
        print("[완료] 배치가 제출되었습니다.")
        print(f"  → 상태 확인: `python -m datagen.submit_batch` (--wait 옵션)")
        print(f"  → 결과 다운로드: `python -m datagen.retrieve_batch`")


if __name__ == "__main__":
    main()
