"""합성 데이터 생성 파이프라인 CLI 진입점.

사용 예:
    # 특정 함수를 활용하는 멀티턴 대화 100건 생성
    python -m datagenerator.pipeline --type conversation --fns add_to_cart,get_cart --n 100 --output data/raw/

    # 전체 함수 허용
    python -m datagenerator.pipeline --type conversation --fns all --n 200 --output data/raw/

    # 지원 불가 쿼리 샘플 50건 생성
    python -m datagenerator.pipeline --type rejection --n 50 --output data/raw/
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from datagenerator._extractor import extract_specs_text, extract_tools_schema
from datagenerator.client import OpenAIClient
from datagenerator.config import ALL_FUNCTIONS
from datagenerator.generators.conversation import ConversationGenerator
from datagenerator.generators.rejection import RejectionGenerator
from datagenerator.renderer import render

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# CLI 파서
# ------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m datagenerator.pipeline",
        description="음식 배달 서비스 function calling 파인튜닝용 합성 데이터 생성",
    )
    parser.add_argument(
        "--type",
        dest="gen_type",
        choices=["conversation", "rejection"],
        default="conversation",
        help="생성 유형 (기본값: conversation)",
    )
    parser.add_argument(
        "--fns",
        default="all",
        help=(
            "사용할 함수 목록 (쉼표 구분). "
            "'all'이면 전체 함수 허용. --type rejection 시 무시됨."
        ),
    )
    parser.add_argument(
        "--n",
        type=int,
        default=1,
        help="생성할 샘플 수 (기본값: 1)",
    )
    parser.add_argument(
        "--output",
        default="data/raw",
        help="출력 디렉토리 (기본값: data/raw)",
    )
    return parser


# ------------------------------------------------------------------
# 함수 목록 파싱
# ------------------------------------------------------------------

def _resolve_fns(fns_arg: str) -> list[str]:
    """--fns 인자를 함수명 리스트로 변환."""
    if fns_arg.strip().lower() == "all":
        return list(ALL_FUNCTIONS)

    names = [n.strip() for n in fns_arg.split(",") if n.strip()]
    unknown = set(names) - set(ALL_FUNCTIONS)
    if unknown:
        logger.warning("알 수 없는 함수명이 포함되어 있습니다: %s", unknown)
    return [n for n in names if n in ALL_FUNCTIONS]


# ------------------------------------------------------------------
# 저장 헬퍼
# ------------------------------------------------------------------

def _save_sample(
    output_dir: Path,
    index: int,
    messages: list[dict],
    tools: list[dict],
) -> None:
    """샘플을 .json(raw messages)과 .txt(렌더링된 텍스트)로 저장."""
    stem = f"sample_{index:04d}"

    # raw JSON 저장
    # 일단 막아둡니다. 왜냐하면 레퍼런스와 양식이 다릅니다.
    # 추후 SFT Trainer를 사용하게되면 후처리 로직이 필요합니다.
    # json_path = output_dir / f"{stem}.json"
    # json_path.write_text(
    #     json.dumps(messages, ensure_ascii=False, indent=2),
    #     encoding="utf-8",
    # )

    # Qwen3 포맷 렌더링 후 .txt 저장
    txt_path = output_dir / f"{stem}.txt"
    rendered = render(messages, tools)
    txt_path.write_text(rendered, encoding="utf-8")

    logger.info("저장 완료")


# ------------------------------------------------------------------
# 메인 파이프라인
# ------------------------------------------------------------------

def run(gen_type: str, fns: list[str], n: int, output_dir: Path) -> None:
    """합성 데이터 생성 파이프라인 실행."""
    output_dir.mkdir(parents=True, exist_ok=True)
    client = OpenAIClient()

    if gen_type == "conversation":
        generator = ConversationGenerator(target_fns=fns)
        # include_returns=True: LLM이 tool_response 형식을 알고 생성하도록 리턴 타입 포함
        # 저장되는 학습 데이터(system prompt)에는 리턴 타입 힌트가 없으므로 이원화됨
        function_specs = extract_specs_text(fns, include_returns=True)
        tools_schema = extract_tools_schema(ALL_FUNCTIONS)
        context = {
            "function_specs": function_specs,
            "target_functions": ", ".join(fns),
        }
    else:  # rejection
        generator = RejectionGenerator()
        function_specs = extract_specs_text(ALL_FUNCTIONS)
        tools_schema = extract_tools_schema(ALL_FUNCTIONS)
        context = {
            "function_specs": function_specs,
        }

    logger.info("=== 생성 시작: type=%s, n=%d, output=%s ===", gen_type, n, output_dir)

    success = 0
    for i in range(1, n + 1):
        logger.info("[%d/%d] 생성 중...", i, n)
        try:
            messages_for_llm = generator.build_messages(context)
            raw_text = client.complete(messages_for_llm)
            parsed_messages = generator.parse_response(raw_text)

            if len(parsed_messages) <= 1:
                # system 메시지만 있으면 파싱 실패로 간주
                logger.warning("[%d/%d] 파싱 결과가 비어 있습니다. 건너뜁니다.", i, n)
                logger.debug("LLM 원본 출력:\n%s", raw_text)
                continue

            _save_sample(output_dir, i, parsed_messages, tools_schema)
            success += 1

        except Exception as e:
            logger.error("[%d/%d] 생성 실패: %s", i, n, e)

    logger.info("=== 완료: %d/%d건 성공 ===", success, n)


# ------------------------------------------------------------------
# 진입점
# ------------------------------------------------------------------

def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    gen_type: str = args.gen_type
    n: int = args.n
    output_dir = Path(args.output)

    if gen_type == "conversation":
        fns = _resolve_fns(args.fns)
        if not fns:
            logger.error("--fns에 유효한 함수명이 없습니다. 종료합니다.")
            sys.exit(1)
        logger.info("대상 함수: %s", fns)
    else:
        fns = list(ALL_FUNCTIONS)  # rejection은 --fns 무시

    run(gen_type=gen_type, fns=fns, n=n, output_dir=output_dir)


if __name__ == "__main__":
    main()
