"""
데이터셋 전처리 유틸리티.

HuggingFace 데이터셋 또는 로컬 JSONL을 평가 입력 형식으로 변환한다.
"""

import re


def to_chatml(data) -> str:
    """messages 리스트(또는 {"messages": [...]} 딕셔너리)를 ChatML 문자열로 변환."""
    if isinstance(data, dict):
        messages = data.get("messages", [])
    else:
        messages = data

    parts = []
    for msg in messages:
        role = msg["role"]
        content = msg.get("content", "")
        parts.append(f"<|im_start|>{role}\n{content}<|im_end|>")
    return "\n".join(parts)


def extract_examples(chatml: str) -> list[dict]:
    """
    ChatML 문자열에서 (input, label) 쌍을 추출한다.

    각 assistant 턴에 대해:
    - input: 해당 assistant 턴 직전까지의 전체 컨텍스트 + '<|im_start|>assistant\\n'
    - label: assistant 턴의 실제 응답 텍스트
    """
    pattern = re.compile(
        r"(<\|im_start\|>assistant\n)(.*?)(<\|im_end\|>)",
        re.DOTALL,
    )
    examples = []
    for match in pattern.finditer(chatml):
        start = match.start()
        label = match.group(2)
        input_text = chatml[:start] + match.group(1)
        examples.append({"input": input_text, "label": label})
    return examples


def format_conversations(sample: dict) -> dict:
    """
    system_prompt를 messages 앞에 system 역할로 삽입한다.

    sample 구조: {"system_prompt": str, "messages": [...]}
    반환: {"messages": [{"role": "system", ...}, ...나머지]}
    """
    system_prompt = sample.get("system_prompt", "")
    messages = sample.get("messages", [])
    new_messages = [{"role": "system", "content": system_prompt}] + list(messages)
    return {**sample, "messages": new_messages}


def extract_tool_schemas(tools: list[dict]) -> dict[str, dict]:
    """
    tools 리스트에서 {함수명: {"properties": {...}, "required": [...]}} 형태로 변환한다.

    parameters.properties 중 None 값인 항목은 필터링한다.
    """
    schemas = {}
    for tool in tools:
        name = tool.get("name") or (tool.get("function") or {}).get("name")
        if not name:
            continue

        params = tool.get("parameters") or {}
        if not params:
            # OpenAI format: tool["function"]["parameters"]
            fn = tool.get("function") or {}
            params = fn.get("parameters") or {}

        raw_props = params.get("properties") or {}
        required = params.get("required") or []
        filtered = {k: v for k, v in raw_props.items() if v is not None}
        schemas[name] = {"properties": filtered, "required": list(required)}
    return schemas
