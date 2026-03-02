"""
Tool Call Level 메트릭.

eval/eval_plan.md 기준 단계별 의존 체인 micro acc를 계산한다.

  1. Relevance Detection
  2. Format Compliance
  3. Function Matching
  4. Param Hallucination
  5. Required Params
  6. Argument Type
  7. Argument Value
"""

import json
import re
from dataclasses import dataclass


def _parse_tool_call(text: str) -> dict | None:
    """
    텍스트에서 <tool_call>...</tool_call> 블록을 파싱하여 dict를 반환한다.

    - 없으면 None
    - JSON 파싱 실패 시 None
    - name/arguments 필드 중 하나라도 없으면 None
    """
    match = re.search(r"<tool_call>(.*?)</tool_call>", text, re.DOTALL)
    if not match:
        return None

    try:
        parsed = json.loads(match.group(1).strip())
    except (json.JSONDecodeError, ValueError):
        return None

    if "name" not in parsed or "arguments" not in parsed:
        return None

    if not isinstance(parsed.get("arguments"), dict):
        return None

    return parsed


def _normalize_schema(tool_schemas: dict | None, function_name: str) -> dict | None:
    if not tool_schemas:
        return None
    return tool_schemas.get(function_name)


def _expected_python_type(type_name: str):
    return {
        "string": str,
        "integer": int,
        "number": (int, float),
        "boolean": bool,
        "array": list,
        "object": dict,
    }.get(type_name)


def _matches_type(value, type_name: str | None) -> bool:
    if type_name is None:
        return True

    expected = _expected_python_type(type_name)
    if expected is None:
        return True

    if type_name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if type_name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, expected)


@dataclass
class StepEvaluation:
    """한 step의 단계별 판정 결과."""

    is_tool_label: bool
    relevance_pass: bool
    format_pass: bool | None = None
    function_pass: bool | None = None
    hallucination_pass: bool | None = None
    required_pass: bool | None = None
    type_pass: bool | None = None
    value_pass: bool | None = None

    @property
    def tool_call_pass(self) -> bool:
        return self.value_pass is True


@dataclass
class EvalResults:
    """계획서 기준 Tool Call Level 집계 결과."""

    relevance_detection_acc: float = 0.0
    format_compliance_acc: float = 0.0
    function_matching_acc: float = 0.0
    param_hallucination_acc: float = -1.0
    required_params_acc: float = 0.0
    argument_type_acc: float = -1.0
    argument_value_acc: float = 0.0

    total_samples: int = 0
    total_tool_calls: int = 0
    total_non_tool_calls: int = 0

    relevance_detection_denominator: int = 0
    format_compliance_denominator: int = 0
    function_matching_denominator: int = 0
    param_hallucination_denominator: int = 0
    required_params_denominator: int = 0
    argument_type_denominator: int = 0
    argument_value_denominator: int = 0

    def to_dict(self) -> dict:
        return {
            "relevance_detection_acc": self.relevance_detection_acc,
            "format_compliance_acc": self.format_compliance_acc,
            "function_matching_acc": self.function_matching_acc,
            "param_hallucination_acc": self.param_hallucination_acc,
            "required_params_acc": self.required_params_acc,
            "argument_type_acc": self.argument_type_acc,
            "argument_value_acc": self.argument_value_acc,
            "total_samples": self.total_samples,
            "total_tool_calls": self.total_tool_calls,
            "total_non_tool_calls": self.total_non_tool_calls,
            "relevance_detection_denominator": self.relevance_detection_denominator,
            "format_compliance_denominator": self.format_compliance_denominator,
            "function_matching_denominator": self.function_matching_denominator,
            "param_hallucination_denominator": self.param_hallucination_denominator,
            "required_params_denominator": self.required_params_denominator,
            "argument_type_denominator": self.argument_type_denominator,
            "argument_value_denominator": self.argument_value_denominator,
        }

    def summary(self) -> str:
        def _fmt(value: float) -> str:
            return "N/A" if value == -1.0 else f"{value * 100:.2f}%"

        return (
            f"[EvalResults] total={self.total_samples} "
            f"(tool_call={self.total_tool_calls}, non_tool_call={self.total_non_tool_calls})\n"
            f"  relevance_detection_acc: {self.relevance_detection_acc * 100:.2f}%\n"
            f"  format_compliance_acc:   {self.format_compliance_acc * 100:.2f}%\n"
            f"  function_matching_acc:   {self.function_matching_acc * 100:.2f}%\n"
            f"  param_hallucination_acc: {_fmt(self.param_hallucination_acc)}\n"
            f"  required_params_acc:     {self.required_params_acc * 100:.2f}%\n"
            f"  argument_type_acc:       {_fmt(self.argument_type_acc)}\n"
            f"  argument_value_acc:      {self.argument_value_acc * 100:.2f}%"
        )


def evaluate_function_call_step(
    label: str,
    prediction: str,
    tool_schemas: dict | None = None,
) -> StepEvaluation:
    """한 step을 계획서 기준 단계별로 평가한다."""
    label_tc = _parse_tool_call(label)
    pred_tc = _parse_tool_call(prediction)

    label_is_tool = label_tc is not None
    pred_is_tool = pred_tc is not None

    step = StepEvaluation(
        is_tool_label=label_is_tool,
        relevance_pass=(label_is_tool == pred_is_tool),
    )

    if not label_is_tool:
        return step

    if not pred_is_tool:
        step.format_pass = False
        return step

    step.format_pass = True

    label_name = label_tc["name"]
    pred_name = pred_tc["name"]
    step.function_pass = label_name == pred_name
    if not step.function_pass:
        return step

    schema = _normalize_schema(tool_schemas, label_name)
    label_args = label_tc.get("arguments") or {}
    pred_args = pred_tc.get("arguments") or {}

    if schema is None:
        step.hallucination_pass = None
        required_keys = set(label_args.keys())
        allowed_properties = None
    else:
        properties = schema.get("properties") or {}
        allowed_properties = set(properties.keys())
        step.hallucination_pass = set(pred_args.keys()).issubset(allowed_properties)
        if not step.hallucination_pass:
            return step
        required_keys = set(schema.get("required") or [])

    step.required_pass = required_keys.issubset(set(pred_args.keys()))
    if not step.required_pass:
        return step

    if schema is None:
        step.type_pass = None
    else:
        properties = schema.get("properties") or {}
        step.type_pass = all(
            _matches_type(pred_args[key], (properties.get(key) or {}).get("type"))
            for key in pred_args
        )
        if not step.type_pass:
            return step

    # Value는 정답 경로 exact match를 요구한다.
    step.value_pass = pred_args == label_args
    return step


def evaluate_function_calls(
    labels: list[str],
    predictions: list[str],
    tool_schemas: dict | None = None,
) -> EvalResults:
    """step 리스트를 계획서 기준 micro acc로 집계한다."""
    if len(labels) != len(predictions):
        raise ValueError(
            f"labels({len(labels)})와 predictions({len(predictions)}) 길이가 다릅니다."
        )

    if not labels:
        return EvalResults()

    step_results = [
        evaluate_function_call_step(label, pred, tool_schemas=tool_schemas)
        for label, pred in zip(labels, predictions)
    ]

    total_samples = len(step_results)
    total_tool_calls = sum(result.is_tool_label for result in step_results)
    total_non_tool_calls = total_samples - total_tool_calls

    relevance_den = total_samples
    relevance_num = sum(result.relevance_pass for result in step_results)

    format_targets = [result for result in step_results if result.is_tool_label]
    format_den = len(format_targets)
    format_num = sum(result.format_pass is True for result in format_targets)

    function_targets = [result for result in format_targets if result.format_pass is True]
    function_den = len(function_targets)
    function_num = sum(result.function_pass is True for result in function_targets)

    halluc_targets = [result for result in function_targets if result.function_pass is True]
    halluc_defined = [result for result in halluc_targets if result.hallucination_pass is not None]
    halluc_den = len(halluc_defined)
    halluc_num = sum(result.hallucination_pass is True for result in halluc_defined)

    required_targets = [
        result for result in halluc_targets
        if result.hallucination_pass is not False
    ]
    required_den = len(required_targets)
    required_num = sum(result.required_pass is True for result in required_targets)

    type_targets = [result for result in required_targets if result.required_pass is True]
    type_defined = [result for result in type_targets if result.type_pass is not None]
    type_den = len(type_defined)
    type_num = sum(result.type_pass is True for result in type_defined)

    value_targets = [result for result in type_targets if result.type_pass is not False]
    value_den = len(value_targets)
    value_num = sum(result.value_pass is True for result in value_targets)

    def _ratio(num: int, den: int, na_value: float = 0.0) -> float:
        return num / den if den > 0 else na_value

    return EvalResults(
        relevance_detection_acc=_ratio(relevance_num, relevance_den),
        format_compliance_acc=_ratio(format_num, format_den),
        function_matching_acc=_ratio(function_num, function_den),
        param_hallucination_acc=_ratio(halluc_num, halluc_den, -1.0),
        required_params_acc=_ratio(required_num, required_den),
        argument_type_acc=_ratio(type_num, type_den, -1.0),
        argument_value_acc=_ratio(value_num, value_den),
        total_samples=total_samples,
        total_tool_calls=total_tool_calls,
        total_non_tool_calls=total_non_tool_calls,
        relevance_detection_denominator=relevance_den,
        format_compliance_denominator=format_den,
        function_matching_denominator=function_den,
        param_hallucination_denominator=halluc_den,
        required_params_denominator=required_den,
        argument_type_denominator=type_den,
        argument_value_denominator=value_den,
    )
