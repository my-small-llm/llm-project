"""Rule 1: im_start / im_end 짝 검증 (엄격 순서)"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class FormatError:
    message: str
    token_index: int   # 문제가 된 토큰의 순서 (0-based)


def check_im_pairing(text: str) -> list[FormatError]:
    """<|im_start|>와 <|im_end|>의 짝이 순서대로 맞는지 검증한다.

    오류 케이스:
    - 열린 상태에서 다시 <|im_start|> 등장
    - <|im_start|> 없이 <|im_end|> 등장
    - 파일 끝에 닫히지 않은 블록 존재
    """
    tokens = re.findall(r"<\|im_start\|>|<\|im_end\|>", text)
    errors: list[FormatError] = []
    depth = 0

    for i, token in enumerate(tokens):
        if token == "<|im_start|>":
            if depth != 0:
                errors.append(FormatError(
                    message="이전 블록이 닫히지 않은 상태에서 <|im_start|> 등장",
                    token_index=i,
                ))
            depth += 1
        else:  # <|im_end|>
            if depth == 0:
                errors.append(FormatError(
                    message="대응하는 <|im_start|> 없이 <|im_end|> 등장",
                    token_index=i,
                ))
            else:
                depth -= 1

    if depth != 0:
        errors.append(FormatError(
            message="파일 끝에 닫히지 않은 블록 존재",
            token_index=len(tokens),
        ))

    return errors
