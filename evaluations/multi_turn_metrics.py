"""
HammerBench 스타일 멀티턴 평가 메트릭.

대화 단위로 턴별 function_call 정확도를 세밀하게 측정합니다.
각 턴마다 evaluate_function_calls()를 호출하여 결과를 수집하고,
멀티턴 전용 메트릭(대화 성공률, 오류 연쇄율 등)을 추가 계산합니다.

사용법:
    from evaluations.multi_turn_metrics import evaluate_multi_turn

    results = evaluate_multi_turn(
        conversation_labels=[["label_turn1", "label_turn2"], ...],
        conversation_predictions=[["pred_turn1", "pred_turn2"], ...],
    )
    print(results.summary())
"""

from __future__ import annotations

from dataclasses import dataclass, field

from evaluations.metrics import EvalResults, evaluate_function_calls


@dataclass
class MultiTurnResults:
    """멀티턴 평가 결과.

    HammerBench 스타일의 턴별 세밀 진단 메트릭을 포함합니다.
    """

    # ── 멀티턴 전용 메트릭 ──
    turn_level_accuracy: float = 0.0
    """턴별 exact_match 평균. 개별 턴이 얼마나 정확한지."""

    conversation_success_rate: float = 0.0
    """대화 전체가 모든 턴 정답인 비율. 완벽한 대화의 비율."""

    first_failure_turn_avg: float = -1.0
    """처음 틀리는 턴의 평균 위치 (0-indexed). -1.0이면 실패 없음.
    자기 조건화(self-conditioning) 진단에 활용."""

    error_cascade_rate: float = 0.0
    """한 턴 틀린 후 바로 다음 턴도 틀리는 비율.
    오류가 연쇄적으로 전파되는지 측정."""

    # ── 집계 메트릭 (전체 턴을 합산한 BFCL+Unitxt) ──
    aggregated: EvalResults = field(default_factory=EvalResults)
    """모든 턴의 label/prediction을 합산하여 계산한 종합 메트릭."""

    # ── 카운트 ──
    total_conversations: int = 0
    total_turns: int = 0

    # ── 상세 (턴별 결과) ──
    per_turn_results: list[EvalResults] = field(default_factory=list, repr=False)
    """각 턴별 EvalResults. 디버깅/상세 분석용."""

    def to_dict(self) -> dict:
        """결과를 딕셔너리로 반환."""
        return {
            "turn_level_accuracy": self.turn_level_accuracy,
            "conversation_success_rate": self.conversation_success_rate,
            "first_failure_turn_avg": self.first_failure_turn_avg,
            "error_cascade_rate": self.error_cascade_rate,
            "total_conversations": self.total_conversations,
            "total_turns": self.total_turns,
            "aggregated": self.aggregated.to_dict(),
        }

    def summary(self) -> str:
        """사람이 읽기 좋은 요약."""
        first_fail_str = (
            f"{self.first_failure_turn_avg:.1f}"
            if self.first_failure_turn_avg >= 0
            else "없음 (전부 성공)"
        )
        lines = [
            "=== 멀티턴 평가 결과 (HammerBench) ===",
            "",
            "[멀티턴 메트릭]",
            f"  turn_level_accuracy      : {self.turn_level_accuracy:.2%}",
            f"  conversation_success_rate: {self.conversation_success_rate:.2%}",
            f"  first_failure_turn_avg   : {first_fail_str}",
            f"  error_cascade_rate       : {self.error_cascade_rate:.2%}",
            "",
            f"  대화 수: {self.total_conversations}",
            f"  총 턴 수: {self.total_turns}",
            "",
            "[종합 메트릭 (전체 턴 합산)]",
            self.aggregated.summary(),
        ]
        return "\n".join(lines)


def evaluate_multi_turn(
    conversation_labels: list[list[str]],
    conversation_predictions: list[list[str]],
    tool_schemas: dict[str, dict] | None = None,
) -> MultiTurnResults:
    """
    멀티턴 대화를 턴별로 평가합니다.

    각 대화는 턴별 label/prediction 리스트로 구성됩니다.
    내부적으로 각 턴마다 evaluate_function_calls()를 호출하여
    BFCL+Unitxt 메트릭을 계산하고, 추가로 멀티턴 전용 메트릭을 산출합니다.

    Args:
        conversation_labels: 대화별 정답 리스트의 리스트.
            [[turn1_label, turn2_label, ...], ...]
        conversation_predictions: 대화별 예측 리스트의 리스트.
            [[turn1_pred, turn2_pred, ...], ...]
        tool_schemas: 함수별 파라미터 스키마 (선택).

    Returns:
        MultiTurnResults 인스턴스.
    """
    if len(conversation_labels) != len(conversation_predictions):
        raise ValueError(
            f"conversation 수가 다릅니다: "
            f"{len(conversation_labels)} vs {len(conversation_predictions)}"
        )

    per_turn_results: list[EvalResults] = []
    all_labels: list[str] = []
    all_predictions: list[str] = []

    # 턴별 exact_match 리스트 (대화별로 묶어서 관리)
    conversation_turn_matches: list[list[bool]] = []

    for conv_labels, conv_preds in zip(conversation_labels, conversation_predictions):
        if len(conv_labels) != len(conv_preds):
            raise ValueError(
                f"대화 내 턴 수가 다릅니다: "
                f"{len(conv_labels)} vs {len(conv_preds)}"
            )

        turn_matches: list[bool] = []

        for label, pred in zip(conv_labels, conv_preds):
            # 턴별 개별 평가
            turn_result = evaluate_function_calls(
                [label], [pred], tool_schemas=tool_schemas
            )
            per_turn_results.append(turn_result)
            all_labels.append(label)
            all_predictions.append(pred)

            # exact_match가 1.0이면 이 턴은 정답
            turn_matches.append(turn_result.exact_match == 1.0)

        conversation_turn_matches.append(turn_matches)

    total_conversations = len(conversation_labels)
    total_turns = len(all_labels)

    if total_turns == 0:
        return MultiTurnResults(
            total_conversations=0,
            total_turns=0,
        )

    # ── 종합 메트릭 (전체 턴 합산) ──
    aggregated = evaluate_function_calls(
        all_labels, all_predictions, tool_schemas=tool_schemas
    )

    # ── 턴별 정확도 (turn_level_accuracy) ──
    correct_turns = sum(
        1 for r in per_turn_results if r.exact_match == 1.0
    )
    turn_level_accuracy = correct_turns / total_turns

    # ── 대화 성공률 (conversation_success_rate) ──
    perfect_conversations = sum(
        1 for matches in conversation_turn_matches if all(matches)
    )
    conversation_success_rate = (
        perfect_conversations / total_conversations
        if total_conversations > 0
        else 0.0
    )

    # ── 첫 실패 턴 평균 (first_failure_turn_avg) ──
    first_failure_turns: list[int] = []
    for matches in conversation_turn_matches:
        for turn_idx, is_correct in enumerate(matches):
            if not is_correct:
                first_failure_turns.append(turn_idx)
                break
    first_failure_turn_avg = (
        sum(first_failure_turns) / len(first_failure_turns)
        if first_failure_turns
        else -1.0
    )

    # ── 오류 연쇄율 (error_cascade_rate) ──
    # 한 턴이 틀린 후 바로 다음 턴도 틀리는 비율
    cascade_opportunities = 0  # 틀린 턴 다음에 턴이 있는 횟수
    cascade_hits = 0  # 그 중 실제로 다음 턴도 틀린 횟수

    for matches in conversation_turn_matches:
        for i in range(len(matches) - 1):
            if not matches[i]:  # 이번 턴이 틀림
                cascade_opportunities += 1
                if not matches[i + 1]:  # 다음 턴도 틀림
                    cascade_hits += 1

    error_cascade_rate = (
        cascade_hits / cascade_opportunities
        if cascade_opportunities > 0
        else 0.0
    )

    return MultiTurnResults(
        turn_level_accuracy=turn_level_accuracy,
        conversation_success_rate=conversation_success_rate,
        first_failure_turn_avg=first_failure_turn_avg,
        error_cascade_rate=error_cascade_rate,
        aggregated=aggregated,
        total_conversations=total_conversations,
        total_turns=total_turns,
        per_turn_results=per_turn_results,
    )
