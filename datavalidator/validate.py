"""python -m datavalidator.validate 진입점"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path

from datavalidator.rules.format import check_im_pairing, FormatError
from datavalidator.rules.schema import (
    check_tool_call,
    check_tool_response,
    extract_called_func_name,
    SchemaError,
)
from datavalidator.utils import load_text, parse_blocks


@dataclass
class FileResult:
    path: Path
    format_errors: list[FormatError] = field(default_factory=list)
    schema_errors: list[SchemaError] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.format_errors and not self.schema_errors

    @property
    def error_count(self) -> int:
        return len(self.format_errors) + len(self.schema_errors)


def validate_file(path: Path) -> FileResult:
    text = load_text(path)
    result = FileResult(path=path)

    # Rule 1
    result.format_errors = check_im_pairing(text)

    # Rule 1 실패 시 블록 파싱이 불가하므로 Rule 2, 3 건너뜀
    if result.format_errors:
        return result

    blocks = parse_blocks(text)
    last_called_func: str | None = None

    for block in blocks:
        if block.role == "assistant":
            result.schema_errors.extend(
                check_tool_call(block.content, block.index)
            )
            name = extract_called_func_name(block.content)
            if name is not None:
                last_called_func = name

        elif block.role == "user":
            result.schema_errors.extend(
                check_tool_response(block.content, block.index, last_called_func)
            )
            # tool_response 블록이 소비됐으면 추적 초기화
            if "<tool_response>" in block.content:
                last_called_func = None

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
                print(f"         [{e.rule}] block#{e.block_index}: {e.message}")

    print()
    print(f"결과: {total}개 파일 중 {valid}개 통과, {invalid}개 실패")


def main() -> None:
    parser = argparse.ArgumentParser(description="생성된 학습 데이터 유효성 검증")
    parser.add_argument("--target_dir", required=True, help="검증할 .txt 파일이 있는 디렉토리")
    args = parser.parse_args()

    target = Path(args.target_dir)
    if not target.exists():
        print(f"[오류] 디렉토리를 찾을 수 없습니다: {target}")
        raise SystemExit(1)

    print(f"검증 시작: {target.resolve()}\n")
    results = validate_directory(target)
    print_results(results)


if __name__ == "__main__":
    main()
