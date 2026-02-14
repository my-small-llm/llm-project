"""docs/custom_functions.py에서 함수 스펙을 추출하는 유틸리티.

- extract_specs_text(): 프롬프트 삽입용 텍스트 반환
- extract_tools_schema(): Jinja2 렌더링용 OpenAI tools 형식 리스트 반환
"""
from __future__ import annotations

import ast
from pathlib import Path

from datagenerator.config import CUSTOM_FUNCTIONS_PATH

# Python 타입 → JSON Schema 타입 매핑
_TYPE_MAP: dict[str, str] = {
    "str": "string",
    "int": "integer",
    "float": "number",
    "bool": "boolean",
    "list": "array",
    "dict": "object",
    "datetime": "string",
}


def _annotation_to_json_type(node: ast.expr | None) -> dict:
    """ast 타입 어노테이션을 JSON Schema 타입 dict로 변환."""
    if node is None:
        return {"type": "string"}

    if isinstance(node, ast.Name):
        json_type = _TYPE_MAP.get(node.id, "string")
        return {"type": json_type}

    if isinstance(node, ast.Subscript):
        value = node.value
        if isinstance(value, ast.Name):
            if value.id == "Optional":
                return _annotation_to_json_type(node.slice)
            if value.id == "list":
                items = _annotation_to_json_type(node.slice)
                return {"type": "array", "items": items}

    # 기타 (Union, Attribute 등) → string으로 폴백
    return {"type": "string"}


def _get_default_value(default_node: ast.expr | None):
    """ast 기본값 노드에서 Python 값을 추출."""
    if default_node is None:
        return None
    if isinstance(default_node, ast.Constant):
        return default_node.value
    return None


def _parse_functions(source: str, fn_names: list[str]) -> list[dict]:
    """소스 텍스트를 파싱하여 대상 함수 정보를 fn_names 순서대로 추출."""
    tree = ast.parse(source)
    fn_names_set = set(fn_names)

    # 이름 → 파싱 결과 매핑
    name_to_info: dict[str, dict] = {}

    for node in ast.walk(tree):
        if not isinstance(node, ast.AsyncFunctionDef):
            continue
        if node.name not in fn_names_set:
            continue

        docstring = ast.get_docstring(node) or ""
        args = node.args
        kwonly_args = args.kwonlyargs
        kw_defaults = args.kw_defaults  # None이 포함될 수 있는 리스트

        params: list[dict] = []
        for i, arg in enumerate(kwonly_args):
            default_node = kw_defaults[i] if i < len(kw_defaults) else None
            annotation = arg.annotation

            # Optional 여부 판단
            is_optional = False
            if isinstance(annotation, ast.Subscript) and isinstance(annotation.value, ast.Name):
                is_optional = annotation.value.id == "Optional"

            default_val = _get_default_value(default_node)
            has_default = default_node is not None

            params.append(
                {
                    "name": arg.arg,
                    "json_type": _annotation_to_json_type(annotation),
                    "has_default": has_default,
                    "default": default_val,
                    "is_optional": is_optional,
                }
            )

        name_to_info[node.name] = {
            "name": node.name,
            "docstring": docstring,
            "params": params,
        }

    # fn_names 원래 순서대로 반환
    return [name_to_info[name] for name in fn_names if name in name_to_info]


def extract_specs_text(fn_names: list[str]) -> str:
    """프롬프트에 삽입할 함수 스펙 텍스트를 반환."""
    source = Path(CUSTOM_FUNCTIONS_PATH).read_text(encoding="utf-8")
    parsed = _parse_functions(source, fn_names)

    lines: list[str] = []
    for fn in parsed:
        # 시그니처
        param_strs = []
        for p in fn["params"]:
            s = p["name"]
            if p["has_default"]:
                s += f"={p['default']!r}"
            param_strs.append(s)
        sig = f"{fn['name']}({', '.join(param_strs)})"

        # docstring 첫 줄 (요약)
        first_line = fn["docstring"].split("\n")[0].strip() if fn["docstring"] else ""

        # Args 섹션
        args_section = ""
        if "Args:" in fn["docstring"]:
            args_raw = fn["docstring"].split("Args:")[1]
            if "Returns:" in args_raw:
                args_raw = args_raw.split("Returns:")[0]
            args_section = "\n  Args:" + args_raw.rstrip()

        lines.append(f"[{sig}]\n  설명: {first_line}{args_section}")

    return "\n\n".join(lines)


def extract_tools_schema(fn_names: list[str]) -> list[dict]:
    """Jinja2 렌더링에 사용할 OpenAI tools 형식 리스트를 반환."""
    source = Path(CUSTOM_FUNCTIONS_PATH).read_text(encoding="utf-8")
    parsed = _parse_functions(source, fn_names)

    tools: list[dict] = []
    for fn in parsed:
        properties: dict[str, dict] = {}
        required: list[str] = []

        for p in fn["params"]:
            properties[p["name"]] = p["json_type"].copy()
            if not p["has_default"] and not p["is_optional"]:
                required.append(p["name"])

        # docstring 첫 줄을 description으로 사용
        description = fn["docstring"].split("\n")[0].strip() if fn["docstring"] else fn["name"]

        tools.append(
            {
                "type": "function",
                "function": {
                    "name": fn["name"],
                    "description": description,
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": required,
                    },
                },
            }
        )

    return tools
