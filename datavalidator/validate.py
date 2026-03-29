"""python -m datavalidator.validate 진입점"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path

from datavalidator.rules.format import check_im_pairing, check_consecutive_roles, FormatError
from datavalidator.rules.schema import (
    check_tool_call,
    check_tool_response,
    extract_called_func_name,
    SchemaError,
)
from datavalidator.rules.content import check_inferability, ContentError
from datavalidator.utils import load_text, parse_blocks


@dataclass
class FileResult:
    path: Path
    format_errors: list[FormatError] = field(default_factory=list)
    schema_errors: list[SchemaError] = field(default_factory=list)
    content_errors: list[ContentError] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.format_errors and not self.schema_errors and not self.content_errors

    @property
    def error_count(self) -> int:
        return len(self.format_errors) + len(self.schema_errors) + len(self.content_errors)


def validate_file(path: Path) -> FileResult:
    text = load_text(path)
    result = FileResult(path=path)

    # Rule 1-a: im_start/im_end 짝 검증
    result.format_errors = check_im_pairing(text)

    # Rule 1-a 실패 시 블록 파싱이 불가하므로 이후 규칙 건너뜀
    if result.format_errors:
        return result

    # Rule 1-b: 연속 assistant 블록 탐지 (병렬 tool_call 패턴)
    result.format_errors.extend(check_consecutive_roles(text))

    if result.format_errors:
        return result

    blocks = parse_blocks(text)
    last_called_func: str | None = None

    for block in blocks:
        if block.role == "assistant":
            result.schema_errors.extend(
                check_tool_call(block.content, block.index, block.line_start)
            )
            name = extract_called_func_name(block.content)
            if name is not None:
                last_called_func = name

        elif block.role == "user":
            result.schema_errors.extend(
                check_tool_response(block.content, block.index, last_called_func, block.line_start)
            )
            # tool_response 블록이 소비됐으면 추적 초기화
            if "<tool_response>" in block.content:
                last_called_func = None

    # Rule 4: 사용자 발화 기반 추론 불가 파라미터(환각) 탐지
    result.content_errors = check_inferability(blocks)

    return result


def validate_directory(target_dir: Path) -> list[FileResult]:
    txt_files = sorted(target_dir.glob("*.txt"))
    if not txt_files:
        print(f"[경고] {target_dir} 에 .txt 파일이 없습니다.")
        return []
    return [validate_file(f) for f in txt_files]


def print_results(results: list[FileResult]) -> None:
    total = len(results)
    valid = sum(1 for r in results if r.is_valid)
    invalid = total - valid

    for r in results:
        if r.is_valid:
            print(f"  [PASS] {r.path.name}")
        else:
            print(f"  [FAIL] {r.path.name}  ({r.error_count}건)")
            for e in r.format_errors:
                print(f"         [format] token#{e.token_index}: {e.message}")
            for e in r.schema_errors:
                print(f"         [{e.rule}] block#{e.block_index} L{e.line_start}: {e.message}")
            for e in r.content_errors:
                print(f"         [{e.rule}] block#{e.block_index} L{e.line_start}: {e.message}")

    print()
    print(f"결과: {total}개 파일 중 {valid}개 통과, {invalid}개 실패")


def _extract_sample_index(path: Path) -> int | None:
    """sample_0001.txt → 0 (0-indexed)"""
    stem = path.stem
    if stem.startswith("sample_"):
        try:
            return int(stem.replace("sample_", "")) - 1
        except ValueError:
            return None
    return None


def purge_failed(
    results: list[FileResult],
    dataset_path: Path,
) -> int:
    """검증 실패한 샘플의 .txt와 dataset.jsonl 레코드를 삭제한다."""
    failed = [r for r in results if not r.is_valid]
    if not failed:
        print("[purge] 삭제할 실패 샘플 없음")
        return 0

    # dataset.jsonl 로드
    import json

    with open(dataset_path, encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]

    # 삭제할 인덱스 수집
    indices_to_remove = set()
    for r in failed:
        idx = _extract_sample_index(r.path)
        if idx is not None and idx < len(records):
            indices_to_remove.add(idx)

    # dataset.jsonl에서 레코드 제거
    remaining = [rec for i, rec in enumerate(records) if i not in indices_to_remove]
    with open(dataset_path, "w", encoding="utf-8") as f:
        for rec in remaining:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # .txt 파일 삭제
    for r in failed:
        r.path.unlink(missing_ok=True)

    removed = len(indices_to_remove)
    print(f"[purge] {removed}개 레코드 삭제 (dataset.jsonl: {len(records)} → {len(remaining)})")
    return removed


def main() -> None:
    parser = argparse.ArgumentParser(description="생성된 학습 데이터 유효성 검증")
    parser.add_argument("--target_dir", required=True, help="검증할 .txt 파일이 있는 디렉토리")
    parser.add_argument("--purge", action="store_true", help="검증 실패 샘플의 .txt 및 dataset.jsonl 레코드 삭제")
    parser.add_argument("--dataset", default=None, help="--purge 시 레코드를 삭제할 dataset.jsonl 경로")
    args = parser.parse_args()

    target = Path(args.target_dir)
    if not target.exists():
        print(f"[오류] 디렉토리를 찾을 수 없습니다: {target}")
        raise SystemExit(1)

    if args.purge and not args.dataset:
        print("[오류] --purge 사용 시 --dataset 경로를 지정해야 합니다.")
        raise SystemExit(1)

    print(f"검증 시작: {target.resolve()}\n")
    results = validate_directory(target)
    print_results(results)

    if args.purge:
        dataset_path = Path(args.dataset)
        if not dataset_path.exists():
            print(f"[오류] dataset 파일을 찾을 수 없습니다: {dataset_path}")
            raise SystemExit(1)
        purge_failed(results, dataset_path)

    # 실패가 있으면 exit code 1
    if any(not r.is_valid for r in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
