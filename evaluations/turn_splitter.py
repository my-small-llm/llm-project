"""
GT 히스토리 기반 싱글턴 분할 모듈.

각 턴에 정답(GT) 히스토리를 넣어 턴별 순수 tool calling 능력을 독립 평가한다.

싱글턴 정의:
  user 입력 1회에 대해 assistant가 수행하는 모든 출력을 하나로 묶은 단위.
  sequential call (TC → TR → TC → TR → final)도 하나의 싱글턴이다.

분할 전략 (GT 히스토리):
  Step 0: [system, ...GT_prev_turns..., user(real)] → 첫 assistant 예측
  Step 1: [system, ...GT_prev_turns..., user(real), GT_tc0, GT_tr0] → 두 번째 assistant 예측
  ...
  Step N: [..., GT_tc(N-1), GT_tr(N-1)] → final response 예측
"""

from dataclasses import dataclass, field


@dataclass
class InferenceInput:
    """한 step에 대한 추론 입력 단위."""

    conversation_id: int        # 대화 인덱스
    turn_index: int             # 대화 내 턴 인덱스 (real user 기준)
    step_index: int             # 턴 내 step (sequential call용, 0부터)
    messages: list[dict]        # 추론에 넘길 메시지 리스트 (system + GT history + current)
    gt_response: str            # 이 step의 정답 assistant 응답
    is_tool_call: bool          # 정답이 tool_call인지 여부
    tools: list[dict] = field(default_factory=list)  # 함수 스키마


def _is_tool_response(msg: dict) -> bool:
    """user 메시지가 tool_response인지 판단."""
    return msg.get("role") == "user" and "<tool_response>" in msg.get("content", "")


def _split_turns(messages: list[dict]) -> list[list[dict]]:
    """
    메시지 리스트를 turn 단위로 분할한다.

    turn 경계: tool_response가 아닌 실제 user 발화.
    """
    turns: list[list[dict]] = []
    current: list[dict] = []

    for msg in messages:
        if msg["role"] == "user" and not _is_tool_response(msg):
            if current:
                turns.append(current)
            current = [msg]
        else:
            current.append(msg)

    if current:
        turns.append(current)

    return turns


def split_conversations(conversations: list[dict]) -> list[InferenceInput]:
    """
    대화 리스트를 InferenceInput 리스트로 변환한다.

    Parameters
    ----------
    conversations : list[dict]
        각 원소는 아래 필드를 가진 dict:
        - system_prompt: str
        - messages: list[{"role": "user"|"assistant", "content": str}]
        - tools: list[dict]

    Returns
    -------
    list[InferenceInput]
        GT 히스토리 기반으로 분할된 step 단위 추론 입력 목록
    """
    result: list[InferenceInput] = []

    for conv_id, conv in enumerate(conversations):
        system_prompt = conv.get("system_prompt", "")
        messages = conv.get("messages", [])
        tools = conv.get("tools", [])

        system_msg = {"role": "system", "content": system_prompt}
        turns = _split_turns(messages)

        # GT 히스토리: 이전 턴들의 모든 메시지를 누적
        gt_history: list[dict] = []

        for turn_idx, turn_msgs in enumerate(turns):
            # 현재 턴 처리용 누적 컨텍스트 (시스템 + GT history + 현재 턴의 지금까지 메시지)
            current_context: list[dict] = gt_history.copy()

            step_idx = 0
            i = 0
            while i < len(turn_msgs):
                msg = turn_msgs[i]

                if msg["role"] == "assistant":
                    is_tc = "<tool_call>" in msg.get("content", "")

                    result.append(InferenceInput(
                        conversation_id=conv_id,
                        turn_index=turn_idx,
                        step_index=step_idx,
                        messages=[system_msg] + current_context,
                        gt_response=msg["content"],
                        is_tool_call=is_tc,
                        tools=tools,
                    ))

                    # assistant 메시지를 컨텍스트에 추가
                    current_context = current_context + [msg]

                    # 뒤따르는 user(tool_response)가 있으면 함께 컨텍스트에 추가
                    if i + 1 < len(turn_msgs) and _is_tool_response(turn_msgs[i + 1]):
                        current_context = current_context + [turn_msgs[i + 1]]
                        i += 2
                    else:
                        i += 1

                    step_idx += 1

                else:
                    # user(real) 또는 user(tool_response): 컨텍스트에 추가
                    current_context = current_context + [msg]
                    i += 1

            # 현재 턴 전체를 GT 히스토리에 누적
            gt_history = gt_history + turn_msgs

    return result
