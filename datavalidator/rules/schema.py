"""Rule 2: tool_call 검증 / Rule 3: tool_response 검증"""
from __future__ import annotations

import inspect
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, get_args, get_origin, get_type_hints

# docs/custom_functions.py를 동적으로 import
import importlib.util

_CUSTOM_FUNCTIONS_PATH = (
    Path(__file__).parent.parent.parent / "docs" / "custom_functions.py"
)


def _load_custom_functions_module():
    spec = importlib.util.spec_from_file_location("custom_functions", _CUSTOM_FUNCTIONS_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_mod = _load_custom_functions_module()

# 함수 이름 → 함수 객체 매핑
FUNCTIONS: dict[str, Any] = {
    name: obj
    for name, obj in inspect.getmembers(_mod, inspect.isfunction)
}


def _get_param_hints(func) -> dict[str, type]:
    """함수의 파라미터 이름 → 타입 힌트 매핑 반환 (return 제외)."""
    hints = get_type_hints(func)
    hints.pop("return", None)
    return hints


def _get_return_hint(func) -> type | None:
    hints = get_type_hints(func)
    return hints.get("return")


def _python_type_of(value: Any) -> type:
    return type(value)


def _is_optional(hint) -> bool:
    """Optional[X] 여부 확인."""
    return get_origin(hint) is type(None) or (
        get_origin(hint) is __import__("typing").Union
        and type(None) in get_args(hint)
    )


def _unwrap_optional(hint):
    """Optional[X] → X 반환."""
    args = get_args(hint)
    non_none = [a for a in args if a is not type(None)]
    return non_none[0] if non_none else hint


def _type_matches(value: Any, hint) -> bool:
    """value가 hint 타입과 호환되는지 확인 (shallow + origin 기준)."""
    import datetime
    import typing

    origin = get_origin(hint)

    # Optional[X] → None 허용
    if origin is typing.Union:
        return any(_type_matches(value, a) for a in get_args(hint))

    # list[X] → list 인스턴스인지만 확인 (원소 타입은 미검사)
    if origin is list:
        return isinstance(value, list)

    # TypedDict → dict 인스턴스인지 확인
    if isinstance(hint, type) and issubclass(hint, dict):
        return isinstance(value, dict)

    # 기본 타입
    if isinstance(hint, type):
        # int와 float 호환 허용 (JSON 숫자)
        if hint is float:
            return isinstance(value, (int, float))
        # datetime 계열은 JSON에서 str로 직렬화되므로 str도 허용
        if issubclass(hint, datetime.datetime):
            return isinstance(value, (str, datetime.datetime))
        return isinstance(value, hint)

    return True  # 판별 불가 시 통과


@dataclass
class SchemaError:
    rule: str          # "tool_call" | "tool_response"
    block_index: int   # 파일 내 몇 번째 블록인지
    message: str


# ── Rule 2 ────────────────────────────────────────────────────────────────────

_TOOL_CALL_RE = re.compile(r"<tool_call>\s*(.*?)\s*</tool_call>", re.DOTALL)


def check_tool_call(block_content: str, block_index: int) -> list[SchemaError]:
    """assistant 블록의 <tool_call> JSON을 검증한다."""
    errors: list[SchemaError] = []
    match = _TOOL_CALL_RE.search(block_content)
    if not match:
        return errors  # tool_call 없는 assistant 블록은 정상

    raw = match.group(1)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        errors.append(SchemaError("tool_call", block_index, f"JSON 파싱 실패: {e}"))
        return errors

    name = data.get("name")
    arguments = data.get("arguments", {})

    # 함수 이름 존재 여부
    if name not in FUNCTIONS:
        errors.append(SchemaError(
            "tool_call", block_index,
            f"알 수 없는 함수명: '{name}'"
        ))
        return errors

    param_hints = _get_param_hints(FUNCTIONS[name])

    # arguments key 유효성 + 타입 검증
    for key, value in arguments.items():
        if key not in param_hints:
            errors.append(SchemaError(
                "tool_call", block_index,
                f"함수 '{name}'에 존재하지 않는 파라미터: '{key}'"
            ))
            continue
        if not _type_matches(value, param_hints[key]):
            errors.append(SchemaError(
                "tool_call", block_index,
                f"파라미터 '{key}': 기대 타입 {param_hints[key]}, 실제 값 타입 {type(value).__name__}"
            ))

    return errors


# ── Rule 3 ────────────────────────────────────────────────────────────────────

_TOOL_RESPONSE_RE = re.compile(r"<tool_response>\s*(.*?)\s*</tool_response>", re.DOTALL)


def check_tool_response(
    block_content: str,
    block_index: int,
    last_called_func: str | None,
) -> list[SchemaError]:
    """user 블록의 <tool_response> JSON을 검증한다."""
    errors: list[SchemaError] = []
    match = _TOOL_RESPONSE_RE.search(block_content)
    if not match:
        return errors  # tool_response 없는 user 블록은 정상

    if last_called_func is None:
        errors.append(SchemaError(
            "tool_response", block_index,
            "대응하는 tool_call 없이 tool_response 등장"
        ))
        return errors

    if last_called_func not in FUNCTIONS:
        return errors  # 함수명 자체가 틀린 건 Rule 2에서 이미 잡힘

    raw = match.group(1)
    return_hint = _get_return_hint(FUNCTIONS[last_called_func])

    # 반환 타입이 str인 함수 (upsert_address, place_order)
    if return_hint is str:
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            value = raw.strip()
        if not isinstance(value, str):
            errors.append(SchemaError(
                "tool_response", block_index,
                f"함수 '{last_called_func}' 반환 타입은 str이어야 하나 {type(value).__name__} 수신"
            ))
        return errors

    # 나머지: JSON dict 또는 list
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        errors.append(SchemaError("tool_response", block_index, f"JSON 파싱 실패: {e}"))
        return errors

    # list 반환 타입 (list_addresses, get_cart 등)
    import typing
    origin = get_origin(return_hint)
    if origin is list:
        if not isinstance(data, list):
            errors.append(SchemaError(
                "tool_response", block_index,
                f"함수 '{last_called_func}' 반환 타입은 list이어야 하나 {type(data).__name__} 수신"
            ))
        return errors

    # Optional → None 허용
    if origin is typing.Union and type(None) in get_args(return_hint):
        if data is None:
            return errors
        return_hint = _unwrap_optional(return_hint)

    # TypedDict → key/타입 검증
    if isinstance(return_hint, type) and issubclass(return_hint, dict):
        if not isinstance(data, dict):
            errors.append(SchemaError(
                "tool_response", block_index,
                f"함수 '{last_called_func}' 반환 타입은 dict이어야 하나 {type(data).__name__} 수신"
            ))
            return errors

        try:
            field_hints = get_type_hints(return_hint)
        except Exception:
            return errors

        for key, hint in field_hints.items():
            if key not in data:
                errors.append(SchemaError(
                    "tool_response", block_index,
                    f"필드 누락: '{key}' (함수: '{last_called_func}')"
                ))
                continue
            if not _type_matches(data[key], hint):
                errors.append(SchemaError(
                    "tool_response", block_index,
                    f"필드 '{key}': 기대 타입 {hint}, 실제 값 타입 {type(data[key]).__name__}"
                ))

        for key in data:
            if key not in field_hints:
                errors.append(SchemaError(
                    "tool_response", block_index,
                    f"스펙에 없는 필드: '{key}' (함수: '{last_called_func}')"
                ))

    return errors


def extract_called_func_name(block_content: str) -> str | None:
    """assistant 블록에서 호출된 함수 이름을 추출한다."""
    match = _TOOL_CALL_RE.search(block_content)
    if not match:
        return None
    try:
        data = json.loads(match.group(1))
        return data.get("name")
    except json.JSONDecodeError:
        return None
