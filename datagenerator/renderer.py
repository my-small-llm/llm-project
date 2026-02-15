"""Jinja2로 Qwen3 chat-template을 렌더링하는 유틸리티."""
from __future__ import annotations

import json

from jinja2 import Environment, FileSystemLoader

from datagenerator.config import JINJA_TEMPLATE_DIR, JINJA_TEMPLATE_NAME


def _tojson_no_ascii(obj: object) -> str:
    return json.dumps(obj, ensure_ascii=False)


def render(messages: list[dict], tools: list[dict]) -> str:
    """messages와 tools를 Qwen3 chat-template 포맷으로 렌더링하여 반환.

    Args:
        messages: role/content/(tool_calls) 구조의 메시지 리스트.
            예: [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}, ...]
        tools: OpenAI function calling 형식의 tool 정의 리스트.
            예: [{"type": "function", "function": {"name": "...", "description": "...", "parameters": {...}}}]

    Returns:
        Qwen3 chat-template 포맷으로 렌더링된 문자열.
    """
    env = Environment(
        loader=FileSystemLoader(JINJA_TEMPLATE_DIR),
        keep_trailing_newline=True,
    )
    env.filters["tojson"] = _tojson_no_ascii
    template = env.get_template(JINJA_TEMPLATE_NAME)
    return template.render(
        messages=messages,
        tools=tools,
        add_generation_prompt=False,
    )
