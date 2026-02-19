"""
Function Calling 성능 평가 메트릭 계산.

BFCL 3대 메트릭 + Unitxt 6종 분해 메트릭을 한 번에 계산합니다.

BFCL 메트릭:
    - exact_match (≈ ASTAcc): 함수명+인자 구조/값이 정답과 완전 일치
    - relevance_detection_f1 (≈ IrrelAcc): 호출 거부해야 할 때 올바르게 거부

Unitxt 분해 메트릭:
    - tool_selection (= Tool Choice): 함수 선택 맞았나?
    - param_name_recall: 필수 인자 빠짐없이 넣었나?
    - param_name_precision: 쓸데없는 인자 넣지 않았나?
    - params_value_accuracy (= Value Precision): 값이 맞나?
    - schema_valid_rate: 타입/스키마 준수율

사용법:
    from evaluations.metrics import evaluate_function_calls

    results = evaluate_function_calls(labels, predictions)
    print(results.summary())
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field


# ================================================================
# 결과 데이터 클래스
# ================================================================

@dataclass
class EvalResults:
    """평가 결과를 담는 데이터 클래스.

    BFCL 메트릭과 Unitxt 분해 메트릭을 모두 포함합니다.
    """

    # ── BFCL 메트릭 ──
    exact_match: float = 0.0
    relevance_detection_f1: float = 0.0

    # ── Unitxt 분해 메트릭 ──
    tool_selection: float = 0.0
    param_name_recall: float = 0.0
    param_name_precision: float = 0.0
    params_value_accuracy: float = 0.0
    schema_valid_rate: float = -1.0  # -1.0 = 스키마 미제공(N/A)

    # ── 샘플 카운트 ──
    total_tool_call_samples: int = 0
    total_non_tool_call_samples: int = 0
    total_samples: int = 0

    # 상세 카운트 (디버깅용)
    _details: dict = field(default_factory=dict, repr=False)

    def to_dict(self) -> dict:
        """결과를 딕셔너리로 반환."""
        return {
            # BFCL
            "exact_match": self.exact_match,
            "relevance_detection_f1": self.relevance_detection_f1,
            # Unitxt
            "tool_selection": self.tool_selection,
            "param_name_recall": self.param_name_recall,
            "param_name_precision": self.param_name_precision,
            "params_value_accuracy": self.params_value_accuracy,
            "schema_valid_rate": self.schema_valid_rate,
            # 카운트
            "total_tool_call_samples": self.total_tool_call_samples,
            "total_non_tool_call_samples": self.total_non_tool_call_samples,
            "total_samples": self.total_samples,
        }

    def summary(self) -> str:
        """사람이 읽기 좋은 요약 문자열 반환."""
        schema_str = (
            f"{self.schema_valid_rate:.2%}"
            if self.schema_valid_rate >= 0
            else "N/A (스키마 미제공)"
        )
        lines = [
            "=== Function Calling 평가 결과 ===",
            "",
            "[BFCL 메트릭]",
            f"  exact_match (ASTAcc)     : {self.exact_match:.2%}",
            f"  relevance_detection (F1) : {self.relevance_detection_f1:.2%}",
            "",
            "[Unitxt 분해 메트릭]",
            f"  tool_selection           : {self.tool_selection:.2%}",
            f"  param_name_recall        : {self.param_name_recall:.2%}",
            f"  param_name_precision     : {self.param_name_precision:.2%}",
            f"  params_value_accuracy    : {self.params_value_accuracy:.2%}",
            f"  schema_valid_rate        : {schema_str}",
            "",
            f"  ---",
            f"  tool_call 샘플 수        : {self.total_tool_call_samples}",
            f"  non-tool_call 샘플 수    : {self.total_non_tool_call_samples}",
            f"  전체 샘플 수             : {self.total_samples}",
        ]
        return "\n".join(lines)


# ================================================================
# tool_call 파싱 정규표현식
# ================================================================

_TOOL_CALL_PATTERN = re.compile(r"<tool_call>(.*?)</tool_call>", re.DOTALL)


def _parse_tool_call(text: str) -> dict | None:
    """
    텍스트에서 <tool_call>...</tool_call> 블록을 찾아 JSON으로 파싱.

    Returns:
        파싱 성공 시 dict, 실패 시 None.
    """
    match = _TOOL_CALL_PATTERN.search(text)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


def _is_tool_call(text: str) -> bool:
    """텍스트에 <tool_call> 태그가 포함되어 있는지 확인."""
    return "<tool_call>" in text


def _validate_schema(arguments: dict, tool_schema: dict) -> bool:
    """
    인자 값이 tool 스키마의 타입 정의에 맞는지 검증.

    간단한 타입 매칭만 수행합니다 (jsonschema 없이도 동작).

    Args:
        arguments: 모델이 생성한 인자 딕셔너리
        tool_schema: {"properties": {"key": {"type": "string"}, ...}} 형태

    Returns:
        모든 인자가 스키마에 부합하면 True.
    """
    properties = tool_schema.get("properties", {})
    type_map = {
        "string": str,
        "integer": int,
        "number": (int, float),
        "boolean": bool,
        "array": list,
        "object": dict,
    }

    for key, value in arguments.items():
        if key not in properties:
            continue  # 스키마에 없는 키는 스킵 (precision에서 처리)
        expected_type_str = properties[key].get("type")
        if expected_type_str is None:
            continue
        expected_type = type_map.get(expected_type_str)
        if expected_type is None:
            continue
        if not isinstance(value, expected_type):
            return False

    return True


# ================================================================
# 메인 평가 함수
# ================================================================

def evaluate_function_calls(
    labels: list[str],
    predictions: list[str],
    tool_schemas: dict[str, dict] | None = None,
) -> EvalResults:
    """
    Function Calling 성능을 평가합니다.

    BFCL 메트릭과 Unitxt 분해 메트릭을 한 번에 계산합니다.

    BFCL 메트릭:
        - exact_match: tool_call JSON 완전 일치율 (≈ ASTAcc)
        - relevance_detection_f1: 비-tool_call 분류 F1 (≈ IrrelAcc)

    Unitxt 분해 메트릭:
        - tool_selection: 함수 이름 일치율 (= Tool Choice)
        - param_name_recall: 정답 파라미터 중 예측에 포함된 비율
        - param_name_precision: 예측 파라미터 중 정답에 포함된 비율
        - params_value_accuracy: 공통 파라미터의 값 일치율 (= Value Precision)
        - schema_valid_rate: tool 스키마 타입 준수율

    Args:
        labels: 정답 레이블 목록
        predictions: 모델 예측 결과 목록
        tool_schemas: 함수별 파라미터 스키마.
            {"함수명": {"properties": {"param": {"type": "string"}}}} 형태.
            None이면 schema_valid_rate = -1.0 (N/A).

    Returns:
        EvalResults 인스턴스
    """
    if len(labels) != len(predictions):
        raise ValueError(
            f"labels와 predictions의 길이가 다릅니다: {len(labels)} vs {len(predictions)}"
        )

    # 카운터 초기화
    tool_sel = {"correct": 0, "total": 0}
    param_recall = {"correct": 0, "total": 0}
    param_precision = {"correct": 0, "total": 0}
    params_val = {"correct": 0, "total": 0}
    exact = {"correct": 0, "total": 0}
    schema = {"valid": 0, "total": 0}

    # Relevance Detection: label이 tool_call이 아닌 경우의 분류 정확도
    rel_tp = 0
    rel_fp = 0
    rel_fn = 0

    tool_call_count = 0
    non_tool_call_count = 0

    for label, pred in zip(labels, predictions):
        label_is_tool = _is_tool_call(label)
        pred_is_tool = _is_tool_call(pred)

        # ── Relevance Detection ──
        if not label_is_tool:
            non_tool_call_count += 1
            if not pred_is_tool:
                rel_tp += 1  # 올바르게 non-tool로 분류
            else:
                rel_fn += 1  # non-tool인데 tool로 분류
            continue  # 이후 메트릭은 tool_call만 대상

        # 여기서부터 label이 tool_call인 경우만 처리
        tool_call_count += 1

        if not pred_is_tool:
            # 예측이 tool_call이 아닌 경우 → 모든 지표 틀림 처리
            tool_sel["total"] += 1
            exact["total"] += 1
            # label 파라미터 전체를 recall 미스로 카운트
            label_json_for_miss = _parse_tool_call(label)
            if label_json_for_miss:
                miss_params = label_json_for_miss.get("arguments", {}).keys()
                param_recall["total"] += len(miss_params)
            else:
                param_recall["total"] += 1
            rel_fp += 1  # tool인데 non-tool로 분류
            continue

        # JSON 파싱
        label_json = _parse_tool_call(label)
        pred_json = _parse_tool_call(pred)

        if label_json is None or pred_json is None:
            # 파싱 실패 → 모든 지표 틀림
            tool_sel["total"] += 1
            param_recall["total"] += 1
            exact["total"] += 1
            continue

        # ── 1. Tool Selection (함수 이름 일치) ──
        tool_sel["total"] += 1
        if label_json.get("name") == pred_json.get("name"):
            tool_sel["correct"] += 1

        # ── 2. Param Name Recall / Precision (분리) ──
        label_params = set(label_json.get("arguments", {}).keys())
        pred_params = set(pred_json.get("arguments", {}).keys())

        # Recall: 정답 파라미터 중 예측에 포함된 비율
        for param in label_params:
            param_recall["total"] += 1
            if param in pred_params:
                param_recall["correct"] += 1

        # Precision: 예측 파라미터 중 정답에 포함된 비율
        for param in pred_params:
            param_precision["total"] += 1
            if param in label_params:
                param_precision["correct"] += 1

        # ── 3. Params Value Accuracy ──
        label_args = label_json.get("arguments", {})
        pred_args = pred_json.get("arguments", {})
        common_params = label_params.intersection(pred_params)

        if common_params:
            params_val["total"] += 1
            values_match = all(
                label_args.get(k) == pred_args.get(k) for k in common_params
            )
            if values_match:
                params_val["correct"] += 1

        # ── 4. Exact Match ──
        exact["total"] += 1
        if label_json == pred_json:
            exact["correct"] += 1

        # ── 5. Schema Validation ──
        if tool_schemas is not None:
            pred_name = pred_json.get("name", "")
            if pred_name in tool_schemas:
                schema["total"] += 1
                if _validate_schema(pred_args, tool_schemas[pred_name]):
                    schema["valid"] += 1

    # ── 최종 결과 계산 ──
    def _safe_div(correct: int, total: int) -> float:
        return correct / total if total > 0 else 0.0

    # Relevance Detection F1
    rel_precision = _safe_div(rel_tp, rel_tp + rel_fp)
    rel_recall = _safe_div(rel_tp, rel_tp + rel_fn)
    rel_f1 = (
        2 * rel_precision * rel_recall / (rel_precision + rel_recall)
        if (rel_precision + rel_recall) > 0
        else 0.0
    )

    # Schema valid rate: -1.0 if 스키마 미제공
    schema_rate = (
        _safe_div(schema["valid"], schema["total"])
        if tool_schemas is not None
        else -1.0
    )

    return EvalResults(
        # BFCL
        exact_match=_safe_div(exact["correct"], exact["total"]),
        relevance_detection_f1=rel_f1,
        # Unitxt
        tool_selection=_safe_div(tool_sel["correct"], tool_sel["total"]),
        param_name_recall=_safe_div(param_recall["correct"], param_recall["total"]),
        param_name_precision=_safe_div(param_precision["correct"], param_precision["total"]),
        params_value_accuracy=_safe_div(params_val["correct"], params_val["total"]),
        schema_valid_rate=schema_rate,
        # 카운트
        total_tool_call_samples=tool_call_count,
        total_non_tool_call_samples=non_tool_call_count,
        total_samples=len(labels),
        _details={
            "tool_selection": tool_sel,
            "param_name_recall": param_recall,
            "param_name_precision": param_precision,
            "params_value_accuracy": params_val,
            "exact_match": exact,
            "schema_validation": schema,
            "relevance_detection": {
                "tp": rel_tp,
                "fp": rel_fp,
                "fn": rel_fn,
                "precision": rel_precision,
                "recall": rel_recall,
            },
        },
    )
