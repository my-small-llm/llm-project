"""지원 불가 쿼리(거절) 합성 데이터 생성기."""
from __future__ import annotations

from datagenerator.config import CHATBOT_SYSTEM_PROMPT
from datagenerator.generators.base import BaseGenerator
from datagenerator.generators.conversation import _split_segments


class RejectionGenerator(BaseGenerator):
    """도구로 처리할 수 없는 요청에 대한 거절 응답 대화를 생성한다."""

    prompt_filename = "rejection.txt"

    # ------------------------------------------------------------------
    # BaseGenerator 구현
    # ------------------------------------------------------------------

    def build_messages(self, context: dict) -> list[dict]:
        """프롬프트를 조립하여 OpenAI API용 messages 리스트를 반환.

        Args:
            context: 다음 키를 포함해야 한다.
                - function_specs (str): 전체 함수 스펙 텍스트 (어떤 기능이 지원되는지 알아야 정확한 거절 생성 가능)
        """
        prompt = self.prompt_template.format(
            function_specs=context["function_specs"],
        )
        return [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt},
        ]

    def parse_response(self, text: str) -> list[dict]:
        """LLM 출력 텍스트를 messages 배열로 변환.

        거절 응답은 tool_call/tool_response 없이 user/assistant 교환으로만 구성된다.

        반환 형식:
            [
                {"role": "system", "content": CHATBOT_SYSTEM_PROMPT},
                {"role": "user", "content": "..."},
                {"role": "assistant", "content": "..."},
                ...
            ]
        """
        messages: list[dict] = [
            {"role": "system", "content": CHATBOT_SYSTEM_PROMPT}
        ]

        segments = _split_segments(text)
        for role, content in segments:
            content = content.strip()
            if role == "user":
                messages.append({"role": "user", "content": content})
            elif role == "assistant":
                messages.append({"role": "assistant", "content": content})
            # tool_call / tool_response는 거절 응답에서 무시

        return messages
