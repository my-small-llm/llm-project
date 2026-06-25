"""Rule 1: im_start / im_end 짝 검증 및 연속 블록 탐지"""
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


def check_consecutive_roles(text: str) -> list[FormatError]:
    """assistant 블록이 연속으로 등장하는지 검사한다.

    올바른 ChatML 포맷에서 여러 tool_call은 단일 assistant 블록 안에
    나란히 위치해야 한다. 연속된 assistant 블록은 병렬 함수 호출을
    별도 블록으로 잘못 분리한 패턴을 나타낸다.
    """
    roles = re.findall(r"<\|im_start\|>(\w+)", text)
    errors: list[FormatError] = []

    for i in range(1, len(roles)):
        if roles[i] == "assistant" and roles[i - 1] == "assistant":
            errors.append(FormatError(
                message=f"assistant 블록이 연속으로 등장 (병렬 tool_call 패턴 의심)",
                token_index=i,
            ))

    return errors
