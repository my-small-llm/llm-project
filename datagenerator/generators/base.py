"""제너레이터 추상 기반 클래스."""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from datagenerator.config import PROMPTS_DIR


class BaseGenerator(ABC):
    """합성 데이터 생성기의 공통 인터페이스."""

    #: 서브클래스가 사용할 프롬프트 파일명 (PROMPTS_DIR 기준)
    prompt_filename: str = ""

    def __init__(self) -> None:
        prompt_path = Path(PROMPTS_DIR) / self.prompt_filename
        self.prompt_template: str = prompt_path.read_text(encoding="utf-8")

        system_path = Path(PROMPTS_DIR) / "system.txt"
        self.system_prompt: str = system_path.read_text(encoding="utf-8")

    @abstractmethod
    def build_messages(self, context: dict) -> list[dict]:
        """OpenAI API에 전달할 messages 리스트를 조립한다."""
        ...

    @abstractmethod
    def parse_response(self, text: str) -> list[dict]:
        """LLM이 반환한 텍스트를 messages 배열로 변환한다."""
        ...
