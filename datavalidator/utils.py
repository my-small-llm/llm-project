"""공통 유틸: 파일 로딩, im 블록 파싱"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Block:
    role: str        # "system" | "user" | "assistant"
    content: str
    index: int       # 파일 내 몇 번째 블록인지 (0-based)


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_blocks(text: str) -> list[Block]:
    """<|im_start|>role ... <|im_end|> 단위로 블록을 분리한다."""
    pattern = re.compile(
        r"<\|im_start\|>(\w+)\n(.*?)<\|im_end\|>",
        re.DOTALL,
    )
    return [
        Block(role=m.group(1), content=m.group(2), index=i)
        for i, m in enumerate(pattern.finditer(text))
    ]
