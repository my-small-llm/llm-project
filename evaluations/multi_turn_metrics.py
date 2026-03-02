"""
Turn/Conversation Level 집계 메트릭.

Turn pass 여부가 먼저 계산된 상태를 입력으로 받아
eval/eval_plan.md 기준 Turn / Conversation Level 지표를 집계한다.
"""

from dataclasses import dataclass, field

from evaluations.metrics import EvalResults


@dataclass
class MultiTurnResults:
    """멀티턴 평가 결과."""

    turn_level_accuracy: float = 0.0
    conversation_success_rate: float = 0.0
    conversation_progress_rate: float = 0.0
    first_failure_turn_avg: float = -1.0
    error_cascade_rate: float = 0.0

    total_conversations: int = 0
    total_turns: int = 0

    aggregated: EvalResults = field(default_factory=EvalResults)

    def to_dict(self) -> dict:
        return {
            "turn_level_accuracy": self.turn_level_accuracy,
            "conversation_success_rate": self.conversation_success_rate,
            "conversation_progress_rate": self.conversation_progress_rate,
            "first_failure_turn_avg": self.first_failure_turn_avg,
            "error_cascade_rate": self.error_cascade_rate,
            "total_conversations": self.total_conversations,
            "total_turns": self.total_turns,
            "aggregated": self.aggregated.to_dict(),
        }

    def summary(self) -> str:
        return (
            f"[MultiTurnResults] conversations={self.total_conversations}, turns={self.total_turns}\n"
            f"  turn_level_accuracy:       {self.turn_level_accuracy * 100:.2f}%\n"
            f"  conversation_success_rate: {self.conversation_success_rate * 100:.2f}%\n"
            f"  conversation_progress_rate:{self.conversation_progress_rate * 100:.2f}%\n"
            f"  first_failure_turn_avg:    {self.first_failure_turn_avg:.2f}\n"
            f"  error_cascade_rate:        {self.error_cascade_rate * 100:.2f}%"
        )


def evaluate_multi_turn(
    conv_turn_passes: list[list[bool]],
    aggregated: EvalResults | None = None,
) -> MultiTurnResults:
    """
    대화별 turn pass/fail 결과를 받아 Turn / Conversation Level 지표를 계산한다.

    Parameters
    ----------
    conv_turn_passes : conv_turn_passes[i][j] = i번째 대화 j번째 턴의 pass 여부
    aggregated : 전체 step에 대한 Tool Call Level 집계 결과
    """
    if not conv_turn_passes:
        return MultiTurnResults(aggregated=aggregated or EvalResults())

    total_turns = sum(len(turns) for turns in conv_turn_passes)
    if total_turns == 0:
        return MultiTurnResults(
            total_conversations=len(conv_turn_passes),
            aggregated=aggregated or EvalResults(),
        )

    turn_pass_total = 0
    conversation_successes = 0
    progress_rates = []
    first_failures = []
    cascade_opportunities = 0
    cascade_hits = 0

    for turn_results in conv_turn_passes:
        if not turn_results:
            continue

        pass_count = sum(turn_results)
        turn_pass_total += pass_count

        if all(turn_results):
            conversation_successes += 1

        progress_rates.append(pass_count / len(turn_results))

        for index, passed in enumerate(turn_results):
            if not passed:
                first_failures.append(index)
                break

        for index in range(1, len(turn_results)):
            if not turn_results[index - 1]:
                cascade_opportunities += 1
                if not turn_results[index]:
                    cascade_hits += 1

    return MultiTurnResults(
        turn_level_accuracy=turn_pass_total / total_turns,
        conversation_success_rate=conversation_successes / len(conv_turn_passes),
        conversation_progress_rate=sum(progress_rates) / len(progress_rates),
        first_failure_turn_avg=(
            sum(first_failures) / len(first_failures) if first_failures else -1.0
        ),
        error_cascade_rate=(
            cascade_hits / cascade_opportunities if cascade_opportunities > 0 else 0.0
        ),
        total_conversations=len(conv_turn_passes),
        total_turns=total_turns,
        aggregated=aggregated or EvalResults(),
    )
