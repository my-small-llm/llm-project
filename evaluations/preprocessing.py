"""
평가용 데이터 전처리 유틸리티.

reference/3. fine_tuned_model_eval.ipynb, reference/4. base_model_eval.ipynb의
전처리 함수들을 모듈화.

사용법:
    from evaluations.preprocessing import prepare_eval_data

    prompts, labels = prepare_eval_data(dataset, test_ratio=0.2)
"""

from __future__ import annotations

import re
from typing import Any


# ================================================================
# 포맷 변환
# ================================================================

def format_conversations(sample: dict) -> dict:
    """
    데이터셋 샘플을 OpenAI 대화 포맷으로 변환합니다.

    시스템 프롬프트를 messages 리스트의 맨 앞에 삽입합니다.

    Args:
        sample: {"system_prompt": str, "messages": list[dict]} 형태의 데이터

    Returns:
        {"messages": [{"role": "system", "content": ...}, ...]}
    """
    return {
        "messages": [
            {"role": "system", "content": sample["system_prompt"]},
            *sample["messages"],
        ]
    }


def to_chatml(data: dict | list) -> str:
    """
    messages 리스트를 ChatML 포맷 문자열로 변환합니다.

    Args:
        data: messages 리스트 또는 {"messages": [...]} 형태의 dict

    Returns:
        ChatML 포맷 문자열

    Example:
        >>> msgs = [{"role": "user", "content": "안녕"}]
        >>> print(to_chatml(msgs))
        <|im_start|>user
        안녕<|im_end|>
    """
    messages = (
        data.get("messages")
        if isinstance(data, dict) and "messages" in data
        else data
    )

    parts = []
    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        parts.append(f"<|im_start|>{role}\n{content}<|im_end|>")
    return "\n".join(parts)


# ================================================================
# 예시 추출
# ================================================================

_ASSISTANT_PATTERN = re.compile(
    r"<\|im_start\|>assistant(.*?)(?=<\|im_end\|>)", re.DOTALL
)


def extract_examples(chatml: str) -> list[dict[str, str]]:
    """
    ChatML 문자열에서 각 assistant 응답을 분리하여
    'input'과 'label' 쌍을 생성합니다.

    - input: 해당 assistant 응답 직전까지의 모든 대화 + '<|im_start|>assistant'
    - label: 해당 assistant의 응답 내용

    Args:
        chatml: ChatML 포맷 문자열

    Returns:
        [{"input": "...", "label": "..."}, ...]
    """
    examples: list[dict[str, str]] = []

    for match in _ASSISTANT_PATTERN.finditer(chatml):
        start_idx = match.start()
        input_text = chatml[:start_idx].strip() + "\n<|im_start|>assistant"
        label_text = match.group(1).strip()
        examples.append({"input": input_text, "label": label_text})

    return examples


# ================================================================
# 평가 데이터 준비
# ================================================================

def prepare_eval_data(
    dataset: Any,
    test_ratio: float = 0.2,
) -> tuple[list[str], list[str]]:
    """
    HuggingFace Dataset을 평가 가능한 (prompts, labels) 쌍으로 변환합니다.

    데이터셋의 앞쪽 test_ratio 비율을 테스트용으로 사용합니다.

    Args:
        dataset: HuggingFace Dataset 객체 (system_prompt, messages 컬럼 필요)
        test_ratio: 테스트 데이터 비율 (기본값: 0.2)

    Returns:
        (prompts, labels) — 각각 문자열 리스트
    """
    total_len = len(dataset)
    test_size = int(total_len * test_ratio)

    # 앞에서부터 테스트 데이터
    test_indices = list(range(test_size))

    # OpenAI 포맷 변환 → ChatML 변환 → 예시 추출
    test_data = [format_conversations(dataset[i]) for i in test_indices]

    prompts: list[str] = []
    labels: list[str] = []

    for item in test_data:
        chatml = to_chatml(item)
        examples = extract_examples(chatml)
        for ex in examples:
            prompts.append(ex["input"])
            labels.append(ex["label"])

    return prompts, labels


# ================================================================
# Tool 스키마 추출
# ================================================================

def extract_tool_schemas(tools: list[dict]) -> dict[str, dict]:
    """
    데이터셋의 tools 필드에서 evaluate_function_calls용 스키마를 추출합니다.

    tools 배열의 각 함수에서 None이 아닌 property만 필터링하여
    {"함수명": {"properties": {"param": {"type": ...}}}} 형태로 반환합니다.

    Args:
        tools: 데이터셋의 tools 컬럼 값.
            [{"name": "search", "parameters": {"properties": {"q": {"type": "string"}, "x": None, ...}}}]

    Returns:
        {"search": {"properties": {"q": {"type": "string"}}}} 형태의 딕셔너리.

    Example:
        >>> dataset = load_dataset("jjun123/delivery-app-...", split="train")
        >>> schemas = extract_tool_schemas(dataset[0]["tools"])
        >>> results = evaluate_function_calls(labels, preds, tool_schemas=schemas)
    """
    schemas: dict[str, dict] = {}

    for tool in tools:
        name = tool.get("name", "")
        params = tool.get("parameters", {})
        properties = params.get("properties", {})

        # None이 아닌 property만 필터
        valid_props = {
            k: v for k, v in properties.items() if v is not None
        }

        if name:
            schemas[name] = {"properties": valid_props}

    return schemas


# ================================================================
# 멀티턴 평가 데이터 준비
# ================================================================

def prepare_multi_turn_eval_data(
    dataset: Any,
    test_ratio: float = 0.2,
) -> tuple[list[list[str]], list[list[str]], dict[str, dict] | None]:
    """
    HuggingFace Dataset을 멀티턴 평가용 데이터로 변환합니다.

    각 대화를 하나의 단위로 유지하면서 턴별 (prompt, label) 쌍을 그룹핑합니다.
    evaluate_multi_turn()에 직접 넘길 수 있는 형태를 반환합니다.

    Args:
        dataset: HuggingFace Dataset 객체 (system_prompt, messages 컬럼 필요)
        test_ratio: 테스트 데이터 비율 (기본값: 0.2)

    Returns:
        (conversation_prompts, conversation_labels, tool_schemas)
        - conversation_prompts: [[턴1_prompt, 턴2_prompt, ...], ...]
        - conversation_labels: [[턴1_label, 턴2_label, ...], ...]
        - tool_schemas: tools 필드 기반 스키마 (없으면 None)
    """
    total_len = len(dataset)
    test_size = int(total_len * test_ratio)
    test_indices = list(range(test_size))

    conv_prompts: list[list[str]] = []
    conv_labels: list[list[str]] = []
    tool_schemas: dict[str, dict] | None = None

    for i in test_indices:
        sample = dataset[i]
        formatted = format_conversations(sample)
        chatml = to_chatml(formatted)
        examples = extract_examples(chatml)

        if examples:
            conv_prompts.append([ex["input"] for ex in examples])
            conv_labels.append([ex["label"] for ex in examples])

        # 첫 번째 샘플에서 tools 스키마 추출 (모든 대화가 동일한 tools 사용 가정)
        if tool_schemas is None and "tools" in sample and sample["tools"]:
            tool_schemas = extract_tool_schemas(sample["tools"])

    return conv_prompts, conv_labels, tool_schemas
