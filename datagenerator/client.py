"""OpenAI API 클라이언트 래퍼 (지수 백오프 재시도 포함)."""
from __future__ import annotations

import time
import logging

import openai

from datagenerator.config import MODEL, TEMPERATURE

logger = logging.getLogger(__name__)

# 재시도 설정
_MAX_RETRIES = 3
_RETRY_DELAY = 2.0  # 초 (지수 증가)


class OpenAIClient:
    """OpenAI chat.completions.create를 래핑하는 클라이언트."""

    def __init__(self, model: str = MODEL, temperature: float = TEMPERATURE) -> None:
        self.client = openai.OpenAI()
        self.model = model
        self.temperature = temperature

    def complete(self, messages: list[dict]) -> str:
        """messages를 받아 assistant 응답 텍스트를 반환.

        재시도 횟수 초과 시 마지막 예외를 그대로 raise한다.
        """
        last_error: Exception | None = None
        delay = _RETRY_DELAY

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                )
                return response.choices[0].message.content or ""

            except openai.RateLimitError as e:
                logger.warning("RateLimitError (시도 %d/%d): %s", attempt, _MAX_RETRIES, e)
                last_error = e
            except openai.APIConnectionError as e:
                logger.warning("APIConnectionError (시도 %d/%d): %s", attempt, _MAX_RETRIES, e)
                last_error = e
            except openai.APIError as e:
                logger.warning("APIError (시도 %d/%d): %s", attempt, _MAX_RETRIES, e)
                last_error = e

            if attempt < _MAX_RETRIES:
                logger.info("%.1f초 후 재시도합니다.", delay)
                time.sleep(delay)
                delay *= 2  # 지수 백오프

        raise last_error  # type: ignore[misc]
