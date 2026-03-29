"""Rule 4: 사용자 발화 기반 추론 불가 파라미터(환각) 탐지

tool_call의 파라미터 값이 대화 컨텍스트에서 추론 가능한지 검증한다.

검증 항목:
- 비기본값 파라미터(page_size, sort, only_open, is_default)에 대한 발화 근거
- quantity, special_request 등 사용자 명시 파라미터의 발화 존재 여부
- ID 값이 이전 tool_response에서 제공된 값인지 여부
- payment_method, delivery_note, gate_password 등 발화 기반 확인
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from datavalidator.utils import Block


@dataclass
class ContentError:
    rule: str           # "content"
    block_index: int
    message: str
    line_start: int = 0
    param: str = ""
    value: str = ""


# ── 상수 ────────────────────────────────────────────────────────

_UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)
_TOOL_CALL_RE = re.compile(r"<tool_call>\s*(.*?)\s*</tool_call>", re.DOTALL)
_TOOL_RESPONSE_RE = re.compile(r"<tool_response>\s*(.*?)\s*</tool_response>", re.DOTALL)
_NUMBER_RE = re.compile(r"\d+\.?\d*")

DEFAULTS = {
    "page_size": 20,
    "page": 1,
    "sort": "relevance",
    "only_open": False,
    "is_default": False,
}

SORT_KEYWORDS: dict[str, list[str]] = {
    "rating": ["평점", "별점", "높은 순", "높은순", "평점순", "별점순"],
    "delivery_fee": ["배달비", "배달료", "싼 순", "싼순", "저렴", "배달비순"],
    "relevance": ["관련", "관련성", "관련순"],
}

DEFAULT_ADDR_KEYWORDS = ["기본", "기본 배송지", "기본배송지", "디폴트", "default"]

PAYMENT_KEYWORDS: dict[str, list[str]] = {
    "card": ["카드", "신용카드", "체크카드"],
    "kakao": ["카카오", "카카오페이"],
    "naver": ["네이버", "네이버페이"],
    "toss": ["토스", "토스페이"],
    "cash": ["현금"],
}

KOREAN_NUMS: dict[str, int] = {
    "하나": 1, "한": 1, "한개": 1, "한 개": 1,
    "두": 2, "두개": 2, "두 개": 2, "둘": 2,
    "세": 3, "세개": 3, "세 개": 3, "셋": 3,
    "네": 4, "네개": 4, "네 개": 4, "넷": 4,
    "다섯": 5, "여섯": 6, "일곱": 7, "여덟": 8, "아홉": 9, "열": 10,
}


# ── 유틸 함수 ───────────────────────────────────────────────────

def _extract_user_id(blocks: list[Block]) -> str:
    """system 블록에서 로그인 사용자 ID를 추출한다."""
    for b in blocks:
        if b.role == "system":
            m = re.search(r"로그인한 사용자의 현재 ID:\s*(\S+)", b.content)
            if m:
                return m.group(1)
    return ""


def _extract_numbers(text: str) -> set[int | float]:
    """텍스트에서 숫자를 추출한다."""
    nums: set[int | float] = set()
    for m in _NUMBER_RE.finditer(text):
        s = m.group()
        nums.add(float(s) if "." in s else int(s))
    return nums


def _collect_available_ids(blocks: list[Block], up_to_index: int) -> set[str]:
    """up_to_index 이전까지의 tool_response + 사용자 발화에서 UUID를 수집한다."""
    ids: set[str] = set()
    for b in blocks[:up_to_index]:
        if b.role == "user":
            ids.update(_UUID_RE.findall(b.content))
    return ids


def _get_preceding_user_message(blocks: list[Block], assistant_idx: int) -> str:
    """해당 assistant 블록 직전의 사용자 일반 발화(tool_response 제외)를 반환한다."""
    for i in range(assistant_idx - 1, -1, -1):
        b = blocks[i]
        if b.role == "user" and "<tool_response>" not in b.content:
            return b.content
        if b.role == "assistant":
            break
    return ""


def _get_all_prior_user_messages(blocks: list[Block], assistant_idx: int) -> str:
    """해당 assistant 블록 이전의 모든 사용자 일반 발화를 합쳐 반환한다."""
    parts: list[str] = []
    for b in blocks[:assistant_idx]:
        if b.role == "user" and "<tool_response>" not in b.content:
            parts.append(b.content)
    return "\n".join(parts)


def _has_korean_number(text: str, target: int) -> bool:
    """텍스트에 target에 해당하는 한국어 수사가 있는지 확인한다."""
    for word, num in KOREAN_NUMS.items():
        if word in text and num == target:
            return True
    return False


# ── 단일 tool_call 검증 ────────────────────────────────────────

def _check_single_call(
    call: dict,
    user_msg: str,
    all_prior_msgs: str,
    available_ids: set[str],
    user_id: str,
    block_index: int,
    line_start: int,
) -> list[ContentError]:
    """하나의 tool_call에서 발화 기반 추론 불가 파라미터를 탐지한다."""
    errors: list[ContentError] = []
    name = call.get("name", "")
    args = call.get("arguments", {})
    user_numbers = _extract_numbers(user_msg)

    def _err(param: str, value: str, reason: str) -> ContentError:
        return ContentError(
            rule="content",
            block_index=block_index,
            message=f"[{name}] {param}={value!r}: {reason}",
            line_start=line_start,
            param=param,
            value=value,
        )

    # 1. page_size 비기본값
    if "page_size" in args and args["page_size"] != DEFAULTS["page_size"]:
        val = args["page_size"]
        all_numbers = _extract_numbers(all_prior_msgs)
        if val not in user_numbers and val not in all_numbers:
            errors.append(_err(
                "page_size", str(val),
                f"사용자가 페이지 크기 {val}을 언급하지 않음 (기본값: 20)",
            ))

    # 2. page 비기본값
    if "page" in args and args["page"] != DEFAULTS["page"]:
        val = args["page"]
        if val not in user_numbers:
            errors.append(_err(
                "page", str(val),
                f"사용자가 페이지 번호 {val}을 언급하지 않음",
            ))

    # 3. quantity
    if "quantity" in args:
        val = args["quantity"]
        if val not in user_numbers and not _has_korean_number(user_msg, val):
            # quantity=1은 암묵적으로 합리적 ("이거 담아줘" = 1개)
            if val != 1:
                errors.append(_err(
                    "quantity", str(val),
                    f"사용자가 수량 {val}을 언급하지 않음",
                ))

    # 4. special_request
    if "special_request" in args and args["special_request"]:
        val = args["special_request"]
        keywords = [w for w in val.split() if len(w) >= 2]
        match_count = sum(1 for kw in keywords if kw in user_msg or kw in all_prior_msgs)
        if keywords and match_count == 0:
            errors.append(_err(
                "special_request", val,
                f"사용자 발화에서 관련 내용을 찾을 수 없음",
            ))

    # 5. delivery_note
    if "delivery_note" in args and args["delivery_note"]:
        val = args["delivery_note"]
        keywords = [w for w in val.split() if len(w) >= 2]
        match_count = sum(1 for kw in keywords if kw in all_prior_msgs)
        if keywords and match_count == 0:
            errors.append(_err(
                "delivery_note", val,
                f"사용자 발화에서 관련 내용을 찾을 수 없음",
            ))

    # 6. gate_password
    if "gate_password" in args and args["gate_password"]:
        val = args["gate_password"]
        if val not in all_prior_msgs:
            errors.append(_err(
                "gate_password", val,
                f"사용자 발화에서 비밀번호를 찾을 수 없음",
            ))

    # 7. payment_method
    if "payment_method" in args:
        val = args["payment_method"]
        found = False
        for method, keywords in PAYMENT_KEYWORDS.items():
            if val == method and any(kw in all_prior_msgs for kw in keywords):
                found = True
                break
        if not found and val not in all_prior_msgs:
            errors.append(_err(
                "payment_method", val,
                f"사용자 발화에서 결제 수단 관련 언급을 찾을 수 없음",
            ))

    # 8. is_default=true
    if "is_default" in args and args["is_default"] is True:
        if not any(kw in all_prior_msgs for kw in DEFAULT_ADDR_KEYWORDS):
            errors.append(_err(
                "is_default", "true",
                "사용자가 기본 배송지 설정을 요청하지 않음",
            ))

    # 9. sort 비기본값
    if "sort" in args and args["sort"] != DEFAULTS["sort"]:
        val = args["sort"]
        keywords = SORT_KEYWORDS.get(val, [])
        if not any(kw in user_msg for kw in keywords):
            errors.append(_err(
                "sort", val,
                f"사용자가 정렬 기준 관련 언급을 하지 않음",
            ))

    # 10. ID 값이 이전 대화에 없는 경우 (user_id, snapshot 제외)
    for param, val in args.items():
        if param == "snapshot":
            continue
        if isinstance(val, str) and _UUID_RE.fullmatch(val):
            if val == user_id:
                continue
            if val not in available_ids:
                errors.append(_err(
                    param, val,
                    "이전 대화/응답에서 해당 ID를 찾을 수 없음",
                ))

    return errors


# ── 파일 단위 검증 (public API) ─────────────────────────────────

def check_inferability(blocks: list[Block]) -> list[ContentError]:
    """전체 대화 블록을 순회하며 추론 불가 파라미터를 탐지한다.

    Args:
        blocks: parse_blocks()가 반환한 Block 리스트

    Returns:
        ContentError 리스트
    """
    user_id = _extract_user_id(blocks)
    all_errors: list[ContentError] = []

    for i, block in enumerate(blocks):
        if block.role != "assistant":
            continue

        match = _TOOL_CALL_RE.search(block.content)
        if not match:
            continue

        try:
            call = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue

        user_msg = _get_preceding_user_message(blocks, i)
        all_prior_msgs = _get_all_prior_user_messages(blocks, i)
        available_ids = _collect_available_ids(blocks, i)

        errors = _check_single_call(
            call, user_msg, all_prior_msgs,
            available_ids, user_id,
            block.index, block.line_start,
        )
        all_errors.extend(errors)

    return all_errors
