"""
Batch API 결과 텍스트를 Qwen 파인튜닝용 messages 형식으로 파싱.

주요 함수:
    - parse_metadata(text) → (customer_id, date)
    - parse_to_qwen_format(text) → list[dict]  (role/content 메시지 리스트)

사용법:
    from datagen.parse import parse_metadata, parse_to_qwen_format
"""

import ast
import json
import re


# ================================================================
# 메타데이터 추출
# ================================================================

def parse_metadata(text: str) -> tuple[str | None, str | None]:
    """
    생성된 대화 텍스트에서 고객 ID와 대화날짜를 추출합니다.

    Args:
        text: GPT가 생성한 원본 텍스트
              예) "[고객 ID] a1661d37-... \n[대화날짜] 2024-05-23\n..."

    Returns:
        (customer_id, date) 튜플. 매칭 실패 시 None.
    """
    customer_id_match = re.search(r'\[고객 ID\]\s*([^\s]+)', text)
    date_match = re.search(r'\[대화날짜\]\s*([\d\-]+)', text)
    customer_id = customer_id_match.group(1) if customer_id_match else None
    date = date_match.group(1) if date_match else None
    return customer_id, date


# ================================================================
# JSON / Python literal 파싱 헬퍼
# ================================================================

def _safe_parse(content: str):
    """
    JSON 또는 Python literal_eval로 content를 파싱합니다.
    - json.loads: true/false/null 대응
    - ast.literal_eval: True/False/None 대응
    """
    content = content.strip()

    # 1️⃣ JSON 먼저 시도
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # 2️⃣ Python literal fallback
    try:
        return ast.literal_eval(content)
    except Exception as e:
        raise ValueError(f"JSON/Python literal 파싱 실패: {content}") from e


# ================================================================
# Qwen 포맷 변환
# ================================================================

def parse_to_qwen_format(text: str) -> list[dict]:
    """
    GPT가 생성한 대화 텍스트를 Qwen 파인튜닝용 messages 리스트로 변환합니다.

    변환 규칙:
        - (고객)         → role: "user"
        - (AI 상담사)    → role: "assistant"
        - (function_call)     → role: "assistant", <tool_call> 태그로 감싸기
        - (function_response) → role: "user", <tool_response> 태그로 감싸기

    특수 처리:
        - function_call 직전의 assistant 메시지는 제거
          (GPT가 먼저 응답 텍스트를 생성한 뒤 function_call을 호출하는 패턴 대응)

    Args:
        text: GPT 생성 원본 텍스트

    Returns:
        [{"role": "user"|"assistant", "content": "..."}, ...]
    """
    messages = []
    pattern = re.compile(
        r'\((고객|AI 상담사|function_call|function_response)\)\s*(.+?)(?=\n\(|\Z)',
        re.DOTALL,
    )

    last_role = None  # 직전 메시지의 역할 추적

    for match in pattern.finditer(text.strip()):
        role_type, content = match.groups()
        content = content.strip()

        if role_type == "고객":
            messages.append({
                "role": "user",
                "content": content,
            })
            last_role = "user"

        elif role_type == "AI 상담사":
            messages.append({
                "role": "assistant",
                "content": content,
            })
            last_role = "assistant"

        elif role_type == "function_call":
            try:
                calls = _safe_parse(content)

                if not isinstance(calls, list):
                    raise ValueError("function_call은 list 형태여야 합니다.")

                # 직전 assistant 메시지 제거
                if last_role == "assistant" and messages:
                    messages.pop()

                for call in calls:
                    messages.append({
                        "role": "assistant",
                        "content": f"<tool_call>\n{json.dumps(call, ensure_ascii=False)}\n</tool_call>",
                    })
                last_role = "assistant"

            except Exception as e:
                raise ValueError(
                    f"[function_call 파싱 실패] 원본: {content}\n오류: {e}"
                ) from e

        elif role_type == "function_response":
            try:
                parsed = _safe_parse(content)
                payload = json.dumps(parsed, ensure_ascii=False)
                messages.append({
                    "role": "user",
                    "content": f"<tool_response>\n{payload}\n</tool_response>",
                })
                last_role = "user"

            except Exception as e:
                raise ValueError(
                    f"[function_response 파싱 실패] 원본: {content}\n오류: {e}"
                ) from e

    return messages
