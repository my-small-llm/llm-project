"""
로컬에 저장된 전처리된 데이터셋(parquet 등)을 HuggingFace Hub에 업로드합니다.

사용법:
    python -m datagen.push_to_hub --input data/output/dataset.jsonl --repo-id REPO_NAME
"""

import argparse
from pathlib import Path

import pandas as pd
from datasets import Dataset


def main():
    parser = argparse.ArgumentParser(
        description="로컬 데이터셋을 HuggingFace Hub에 업로드합니다."
    )
    parser.add_argument(
        "--input",
        type=str,
        default=None,
        help="업로드할 로컬 데이터 파일 경로 (기본값: data/output/dataset.jsonl)",
    )
    parser.add_argument(
        "--repo-id",
        type=str,
        required=True,
        help="HuggingFace Hub 리포 이름 (예: 'my-org/dataset-name')",
    )
    args = parser.parse_args()

    # 경로 설정
    if args.input is None:
        input_path = Path(__file__).parent / "output" / "dataset.jsonl"
    else:
        input_path = Path(args.input)
        if not input_path.is_absolute():
            # If not absolute, try to resolve relative to current working dir, 
            # and if that fails, try relative to the script's directory.
            cwd_path = Path.cwd() / input_path
            script_dir_path = Path(__file__).parent.parent / input_path
            
            if cwd_path.exists():
                input_path = cwd_path
            elif script_dir_path.exists():
                input_path = script_dir_path

    if not input_path.exists():
        print(f"[오류] 입력 파일이 없습니다: {input_path}")
        print("[힌트] 먼저 `python -m datagen.preprocess`를 실행하세요.")
        return

    print(f"[1/2] 데이터 로드 중: {input_path}")
    try:
        if input_path.suffix == ".parquet":
            df = pd.read_parquet(input_path)
        elif input_path.suffix in [".json", ".jsonl"]:
            df = pd.read_json(input_path, lines=(input_path.suffix == ".jsonl"))
        else:
            print(f"[오류] 지원하지 않는 파일 형식입니다. (.parquet, .json, .jsonl): {input_path}")
            return
        
        print(f"  → 로드 완료: {len(df)}행 × {len(df.columns)}열")
    except Exception as e:
        print(f"[오류] 데이터 로드 실패: {e}")
        return

    # ── Step 2: HuggingFace Hub 업로드 ──
    print(f"[2/2] HuggingFace Hub 업로드 중: {args.repo_id}")
    try:
        import datasets
        dataset = datasets.Dataset.from_pandas(df)
        dataset.push_to_hub(args.repo_id)
        print(f"[완료] HuggingFace Hub 업로드 성공: {args.repo_id}")
    except ImportError:
        print("[오류] `pip install datasets`를 먼저 실행하세요.")
    except Exception as e:
        print(f"[오류] Hub 업로드 실패: {e}")


if __name__ == "__main__":
    main()
