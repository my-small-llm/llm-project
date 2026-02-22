"""
완료된 OpenAI Batch API 결과를 다운로드합니다.

사용법:
    python -m datagen.retrieve_batch [--batch-id <BATCH_ID>]

출력:
    datagen/output/result_lst.json  (생성된 대화 텍스트 목록)
"""

import argparse
import json
from pathlib import Path

import openai


def main():
    parser = argparse.ArgumentParser(
        description="완료된 배치 결과를 다운로드합니다."
    )
    parser.add_argument(
        "--batch-id",
        type=str,
        default=None,
        help="배치 ID (생략 시 datagen/output/batch_status.json에서 로드)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="결과 저장 경로 (기본값: datagen/output/result_lst.json)",
    )
    args = parser.parse_args()

    # 출력 경로 설정
    if args.output is None:
        output_path = Path(__file__).parent / "output" / "result_lst.json"
    else:
        output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    status_path = Path(__file__).parent / "output" / "batch_status.json"
    client = openai.OpenAI()

    # ── 배치 ID 확인 ──
    batch_id = args.batch_id
    if batch_id is None:
        if not status_path.exists():
            print("[오류] batch_status.json이 없습니다.")
            print("[힌트] 먼저 `python -m datagen.submit_batch`를 실행하세요.")
            return
        with open(status_path, "r", encoding="utf-8") as f:
            status_info = json.load(f)
        batch_id = status_info["batch_id"]

    # ── 배치 상태 확인 ──
    print(f"[1/3] 배치 상태 확인 중: {batch_id}")
    batch = client.batches.retrieve(batch_id)
    print(f"  → 상태: {batch.status}")
    print(f"  → 완료: {batch.request_counts.completed}/{batch.request_counts.total}")
    print(f"  → 실패: {batch.request_counts.failed}")

    if batch.status != "completed":
        print(f"[대기] 배치가 아직 완료되지 않았습니다 (현재: {batch.status})")
        print("[힌트] `python -m datagen.submit_batch --wait`로 대기하거나 나중에 다시 실행하세요.")
        return

    # ── 결과 다운로드 ──
    print(f"[2/3] 결과 파일 다운로드 중: {batch.output_file_id}")
    result_content = client.files.content(batch.output_file_id)
    raw_text = result_content.text

    # ── 결과 파싱 ──
    print("[3/3] 결과 파싱 중...")
    result_lst = []
    errors = []

    for line in raw_text.strip().split("\n"):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
            custom_id = obj.get("custom_id", "unknown")

            # 에러 체크
            if obj.get("error"):
                errors.append({"custom_id": custom_id, "error": obj["error"]})
                continue

            # Responses API 응답 텍스트 추출
            response_body = obj.get("response", {}).get("body", {})

            # output_text 필드가 있으면 바로 사용
            output_text = response_body.get("output_text")
            if output_text:
                result_lst.append(output_text)
            else:
                # output 배열에서 message 타입의 content 추출
                output_items = response_body.get("output", [])
                text = ""
                for item in output_items:
                    if item.get("type") == "message":
                        for content_part in item.get("content", []):
                            if content_part.get("type") == "output_text":
                                text += content_part.get("text", "")
                if text:
                    result_lst.append(text)
                else:
                    errors.append({"custom_id": custom_id, "error": "no output text"})

        except json.JSONDecodeError as e:
            errors.append({"line": line[:100], "error": str(e)})

    # ── 결과 저장 ──
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result_lst, f, ensure_ascii=False, indent=2)

    print(f"\n[완료] 결과 저장: {output_path}")
    print(f"  → 성공: {len(result_lst)}건")
    print(f"  → 실패: {len(errors)}건")

    if errors:
        error_path = output_path.parent / "batch_errors.json"
        with open(error_path, "w", encoding="utf-8") as f:
            json.dump(errors, f, ensure_ascii=False, indent=2)
        print(f"  → 에러 로그: {error_path}")

    # batch_status.json 업데이트
    if status_path.exists():
        with open(status_path, "r", encoding="utf-8") as f:
            status_info = json.load(f)
        status_info["status"] = "completed"
        status_info["output_file_id"] = batch.output_file_id
        status_info["result_count"] = len(result_lst)
        status_info["error_count"] = len(errors)
        with open(status_path, "w", encoding="utf-8") as f:
            json.dump(status_info, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
