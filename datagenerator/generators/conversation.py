"""멀티턴 대화 합성 데이터 생성기."""
from __future__ import annotations

import json
import re

from datagenerator.config import CHATBOT_SYSTEM_PROMPT
from datagenerator.generators.base import BaseGenerator

# (role) 로 시작하는 줄을 찾는 패턴
_ROLE_PATTERN = re.compile(r"^\((user|assistant|tool_call|tool_response)\)\s*", re.MULTILINE)


class ConversationGenerator(BaseGenerator):
    """--fns 인자로 지정된 함수들을 사용하는 멀티턴 대화를 생성한다."""

    prompt_filename = "conversation.txt"

    def __init__(self, target_fns: list[str]) -> None:
        super().__init__()
        self.target_fns = target_fns

    # ------------------------------------------------------------------
    # BaseGenerator 구현
    # ------------------------------------------------------------------

    def build_messages(self, context: dict) -> list[dict]:
        """프롬프트를 조립하여 OpenAI API용 messages 리스트를 반환.

        Args:
            context: 다음 키를 포함해야 한다.
                - function_specs (str): 대상 함수 스펙 텍스트
                - target_functions (str): 반드시 사용해야 할 함수 목록 텍스트
        """
        prompt = self.prompt_template.format(
            function_specs=context["function_specs"],
            target_functions=context["target_functions"],
        )
        return [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt},
        ]

    def parse_response(self, text: str) -> list[dict]:
        """LLM 출력 텍스트를 messages 배열로 변환.

        출력 형식:
            (user) 고객 발화
            (assistant) AI 응답
            (tool_call) {"name": "...", "arguments": {...}}
            (tool_response) {...}

        반환 형식:
            [
                {"role": "system", "content": CHATBOT_SYSTEM_PROMPT},
                {"role": "user", "content": "..."},
                {"role": "assistant", "content": "...", "tool_calls": [...]},
                {"role": "tool", "content": "..."},
                ...
            ]
        """
        messages: list[dict] = [
            {"role": "system", "content": CHATBOT_SYSTEM_PROMPT}
        ]

        # 텍스트를 세그먼트로 분리
        segments = _split_segments(text)

        for role, content in segments:
            content = content.strip()

            if role == "user":
                messages.append({"role": "user", "content": content})

            elif role == "assistant":
                messages.append({"role": "assistant", "content": content})

            elif role == "tool_call":
                # 직전 assistant 메시지에 tool_calls 병합
                tool_data = _parse_json_safe(content)
                if tool_data is None:
                    continue

                # tool_data가 리스트인 경우와 단일 dict인 경우 모두 처리
                calls = tool_data if isinstance(tool_data, list) else [tool_data]
                tool_calls = [
                    {
                        "function": {
                            "name": c.get("name", ""),
                            "arguments": c.get("arguments", {}),
                        }
                    }
                    for c in calls
                    if isinstance(c, dict)
                ]

                # 직전 메시지가 assistant면 병합, 아니면 새 assistant 메시지 추가
                if messages and messages[-1]["role"] == "assistant":
                    existing = messages[-1].get("tool_calls", [])
                    messages[-1]["tool_calls"] = existing + tool_calls
                else:
                    messages.append(
                        {"role": "assistant", "content": "", "tool_calls": tool_calls}
                    )

            elif role == "tool_response":
                messages.append({"role": "tool", "content": content})

        return messages


# ------------------------------------------------------------------
# 파싱 헬퍼
# ------------------------------------------------------------------

def _split_segments(text: str) -> list[tuple[str, str]]:
    """텍스트를 (role, content) 세그먼트 목록으로 분리."""
    matches = list(_ROLE_PATTERN.finditer(text))
    if not matches:
        return []

    segments: list[tuple[str, str]] = []
    for i, match in enumerate(matches):
        role = match.group(1)
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[start:end]
        segments.append((role, content))

    return segments


def _parse_json_safe(text: str) -> dict | list | None:
    """JSON 파싱을 시도하고, 실패 시 None 반환."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # 코드 펜스 안에 JSON이 있는 경우 처리
        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if fence_match:
            try:
                return json.loads(fence_match.group(1).strip())
            except json.JSONDecodeError:
                pass
    return None
