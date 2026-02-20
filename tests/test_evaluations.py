"""
evaluations 패키지 단위 테스트.

BFCL + Unitxt + HammerBench 메트릭을 통합 검증합니다.

실행:
    python -m pytest tests/test_evaluations.py -v
"""

import pytest

from evaluations.metrics import evaluate_function_calls, _parse_tool_call, EvalResults
from evaluations.multi_turn_metrics import evaluate_multi_turn, MultiTurnResults
from evaluations.preprocessing import to_chatml, extract_examples, format_conversations, extract_tool_schemas


# ================================================================
# metrics.py 테스트 — BFCL + Unitxt 통합
# ================================================================


class TestParseToolCall:
    """_parse_tool_call 헬퍼 함수 테스트."""

    def test_valid_tool_call(self):
        text = '<tool_call>\n{"name": "search_product", "arguments": {"keyword": "노트북"}}\n</tool_call>'
        result = _parse_tool_call(text)
        assert result == {"name": "search_product", "arguments": {"keyword": "노트북"}}

    def test_no_tool_call(self):
        text = "안녕하세요! 무엇을 도와드릴까요?"
        result = _parse_tool_call(text)
        assert result is None

    def test_invalid_json(self):
        text = "<tool_call>\n{invalid json}\n</tool_call>"
        result = _parse_tool_call(text)
        assert result is None


class TestPerfectMatch:
    """모든 예측이 정답과 완전 일치하는 경우."""

    def test_all_correct(self):
        labels = [
            "안녕하세요! 상준몰 AI 상담사입니다. 무엇을 도와드릴까요?",
            '<tool_call>\n{"name": "view_user_profile", "arguments": {"user_id": "U002"}}\n</tool_call>',
            "고객님의 주소는 '서울특별시 강남구 테헤란로 123'으로 등록되어 있습니다.",
            '<tool_call>\n{"name": "view_order_history", "arguments": {"user_id": "U002"}}\n</tool_call>',
        ]
        predictions = labels.copy()

        results = evaluate_function_calls(labels, predictions)

        # BFCL
        assert results.exact_match == 1.0
        assert results.relevance_detection_f1 == 1.0

        # Unitxt
        assert results.tool_selection == 1.0
        assert results.param_name_recall == 1.0
        assert results.param_name_precision == 1.0
        assert results.params_value_accuracy == 1.0

        # 카운트
        assert results.total_tool_call_samples == 2
        assert results.total_non_tool_call_samples == 2


class TestParamRecallPrecisionSplit:
    """Param Name Recall과 Precision이 올바르게 분리되는지 검증."""

    def test_missing_param(self):
        """필수 파라미터 누락 → Recall 감소, Precision 유지."""
        labels = [
            '<tool_call>\n{"name": "search_product", "arguments": {"keyword": "노트북", "category": "전자기기"}}\n</tool_call>',
        ]
        predictions = [
            '<tool_call>\n{"name": "search_product", "arguments": {"keyword": "노트북"}}\n</tool_call>',
        ]

        results = evaluate_function_calls(labels, predictions)

        # Recall: 정답 {keyword, category} 중 예측에 있는 것 = {keyword} → 1/2
        assert abs(results.param_name_recall - 0.5) < 0.01

        # Precision: 예측 {keyword} 중 정답에 있는 것 = {keyword} → 1/1
        assert results.param_name_precision == 1.0

    def test_extra_param(self):
        """불필요 파라미터 추가 → Recall 유지, Precision 감소."""
        labels = [
            '<tool_call>\n{"name": "search_product", "arguments": {"keyword": "노트북"}}\n</tool_call>',
        ]
        predictions = [
            '<tool_call>\n{"name": "search_product", "arguments": {"keyword": "노트북", "include_soldout": true}}\n</tool_call>',
        ]

        results = evaluate_function_calls(labels, predictions)

        # Recall: 정답 {keyword} 중 예측에 있는 것 = {keyword} → 1/1
        assert results.param_name_recall == 1.0

        # Precision: 예측 {keyword, include_soldout} 중 정답에 있는 것 = {keyword} → 1/2
        assert abs(results.param_name_precision - 0.5) < 0.01

    def test_both_missing_and_extra(self):
        """파라미터 누락 + 불필요 추가 → 둘 다 감소."""
        labels = [
            '<tool_call>\n{"name": "fn", "arguments": {"a": 1, "b": 2}}\n</tool_call>',
        ]
        predictions = [
            '<tool_call>\n{"name": "fn", "arguments": {"a": 1, "c": 3}}\n</tool_call>',
        ]

        results = evaluate_function_calls(labels, predictions)

        # Recall: 정답 {a, b} 중 예측에 있는 것 = {a} → 1/2
        assert abs(results.param_name_recall - 0.5) < 0.01

        # Precision: 예측 {a, c} 중 정답에 있는 것 = {a} → 1/2
        assert abs(results.param_name_precision - 0.5) < 0.01


class TestSchemaValidation:
    """schema_valid_rate 검증."""

    def test_no_schema_provided(self):
        """스키마 미제공 시 -1.0 (N/A)."""
        labels = [
            '<tool_call>\n{"name": "fn", "arguments": {"x": 1}}\n</tool_call>',
        ]
        results = evaluate_function_calls(labels, labels.copy())
        assert results.schema_valid_rate == -1.0

    def test_schema_valid(self):
        """스키마 통과."""
        labels = [
            '<tool_call>\n{"name": "search", "arguments": {"keyword": "치킨", "limit": 10}}\n</tool_call>',
        ]
        schemas = {
            "search": {
                "properties": {
                    "keyword": {"type": "string"},
                    "limit": {"type": "integer"},
                },
            },
        }
        results = evaluate_function_calls(labels, labels.copy(), tool_schemas=schemas)
        assert results.schema_valid_rate == 1.0

    def test_schema_invalid(self):
        """스키마 위반 (integer 자리에 string)."""
        labels = [
            '<tool_call>\n{"name": "search", "arguments": {"keyword": "치킨", "limit": 10}}\n</tool_call>',
        ]
        predictions = [
            '<tool_call>\n{"name": "search", "arguments": {"keyword": "치킨", "limit": "많이"}}\n</tool_call>',
        ]
        schemas = {
            "search": {
                "properties": {
                    "keyword": {"type": "string"},
                    "limit": {"type": "integer"},
                },
            },
        }
        results = evaluate_function_calls(labels, predictions, tool_schemas=schemas)
        assert results.schema_valid_rate == 0.0


class TestErrorCases:
    """레퍼런스 노트북의 에러 케이스 검증."""

    def test_error_cases(self):
        """
        - 1st: 함수 이름 틀림 (view_user_profile → view_profile)
        - 2nd: 파라미터 누락 (category 누락)
        - 3rd: 예측이 tool_call이 아닌 텍스트
        """
        labels = [
            '<tool_call>\n{"name": "view_user_profile", "arguments": {"user_id": "U002"}}\n</tool_call>',
            '<tool_call>\n{"name": "search_product", "arguments": {"keyword": "노트북", "category": "전자기기"}}\n</tool_call>',
            '<tool_call>\n{"name": "check_stock", "arguments": {"product_id": "P001"}}\n</tool_call>',
        ]
        predictions = [
            '<tool_call>\n{"name": "view_profile", "arguments": {"user_id": "U002"}}\n</tool_call>',
            '<tool_call>\n{"name": "search_product", "arguments": {"keyword": "노트북"}}\n</tool_call>',
            "죄송합니다. 재고 확인은 제품 번호가 필요합니다.",
        ]

        results = evaluate_function_calls(labels, predictions)

        # tool_selection: 3개 중 1개만 맞음 (search_product)
        assert abs(results.tool_selection - 1 / 3) < 0.01

        # param_name_recall:
        #   1st: {user_id} → pred에 {user_id} 있음 → 1/1
        #   2nd: {keyword, category} → pred에 {keyword}만 → 1/2
        #   3rd: {product_id} → pred가 tool_call 아님 → 0/1
        # 총 correct=2, total=4 → 0.5
        assert abs(results.param_name_recall - 0.5) < 0.01

        # param_name_precision:
        #   1st: pred {user_id} → label에 있음 → 1/1
        #   2nd: pred {keyword} → label에 있음 → 1/1
        #   3rd: pred가 tool_call 아님 → 카운트 안 됨
        # 총 correct=2, total=2 → 1.0
        assert results.param_name_precision == 1.0

        assert results.total_tool_call_samples == 3

    def test_mismatched_lengths(self):
        """labels와 predictions 길이가 다르면 ValueError."""
        with pytest.raises(ValueError):
            evaluate_function_calls(["a", "b"], ["a"])


class TestEdgeCases:
    """경계 케이스 테스트."""

    def test_empty_input(self):
        results = evaluate_function_calls([], [])
        assert results.total_samples == 0
        assert results.tool_selection == 0.0

    def test_all_non_tool_calls(self):
        labels = ["안녕하세요", "감사합니다"]
        preds = ["안녕하세요", "감사합니다"]

        results = evaluate_function_calls(labels, preds)
        assert results.total_tool_call_samples == 0
        assert results.total_non_tool_call_samples == 2
        assert results.relevance_detection_f1 == 1.0

    def test_relevance_detection_false_negative(self):
        """비-tool_call 레이블에 대해 tool_call로 응답 → FN."""
        labels = ["죄송하지만 그 기능은 지원하지 않습니다."]
        predictions = [
            '<tool_call>\n{"name": "search_product", "arguments": {"keyword": "test"}}\n</tool_call>',
        ]

        results = evaluate_function_calls(labels, predictions)
        assert results.total_non_tool_call_samples == 1
        assert results.relevance_detection_f1 == 0.0


class TestEvalResults:
    """EvalResults 데이터 클래스 테스트."""

    def test_to_dict(self):
        results = EvalResults(tool_selection=0.9, param_name_recall=0.8)
        d = results.to_dict()
        assert d["tool_selection"] == 0.9
        assert d["param_name_recall"] == 0.8
        assert "total_samples" in d

    def test_summary(self):
        results = EvalResults(tool_selection=0.95, total_samples=100)
        summary = results.summary()
        assert "95.00%" in summary
        assert "100" in summary

    def test_summary_schema_na(self):
        """스키마 미제공 시 N/A 표시."""
        results = EvalResults(schema_valid_rate=-1.0)
        assert "N/A" in results.summary()


# ================================================================
# multi_turn_metrics.py 테스트 — HammerBench
# ================================================================


class TestMultiTurnPerfect:
    """모든 대화가 모든 턴 정답인 경우."""

    def test_all_correct(self):
        conv_labels = [
            [
                '<tool_call>\n{"name": "search", "arguments": {"q": "치킨"}}\n</tool_call>',
                '<tool_call>\n{"name": "order", "arguments": {"id": "1"}}\n</tool_call>',
            ],
            [
                '<tool_call>\n{"name": "search", "arguments": {"q": "피자"}}\n</tool_call>',
            ],
        ]
        conv_preds = [
            [
                '<tool_call>\n{"name": "search", "arguments": {"q": "치킨"}}\n</tool_call>',
                '<tool_call>\n{"name": "order", "arguments": {"id": "1"}}\n</tool_call>',
            ],
            [
                '<tool_call>\n{"name": "search", "arguments": {"q": "피자"}}\n</tool_call>',
            ],
        ]

        results = evaluate_multi_turn(conv_labels, conv_preds)

        assert results.turn_level_accuracy == 1.0
        assert results.conversation_success_rate == 1.0
        assert results.first_failure_turn_avg == -1.0  # 실패 없음
        assert results.error_cascade_rate == 0.0
        assert results.total_conversations == 2
        assert results.total_turns == 3

        # 종합 메트릭도 완벽
        assert results.aggregated.exact_match == 1.0


class TestMultiTurnErrors:
    """턴별 오류가 있는 경우."""

    def test_partial_errors(self):
        """대화 1: 2턴 모두 정답, 대화 2: 1턴 정답 + 2턴 오답."""
        conv_labels = [
            [
                '<tool_call>\n{"name": "search", "arguments": {"q": "치킨"}}\n</tool_call>',
                '<tool_call>\n{"name": "order", "arguments": {"id": "1"}}\n</tool_call>',
            ],
            [
                '<tool_call>\n{"name": "search", "arguments": {"q": "피자"}}\n</tool_call>',
                '<tool_call>\n{"name": "order", "arguments": {"id": "2"}}\n</tool_call>',
            ],
        ]
        conv_preds = [
            [
                '<tool_call>\n{"name": "search", "arguments": {"q": "치킨"}}\n</tool_call>',
                '<tool_call>\n{"name": "order", "arguments": {"id": "1"}}\n</tool_call>',
            ],
            [
                '<tool_call>\n{"name": "search", "arguments": {"q": "피자"}}\n</tool_call>',
                '<tool_call>\n{"name": "wrong_fn", "arguments": {"id": "2"}}\n</tool_call>',
            ],
        ]

        results = evaluate_multi_turn(conv_labels, conv_preds)

        # 4턴 중 3턴 정답
        assert abs(results.turn_level_accuracy - 3 / 4) < 0.01

        # 2대화 중 1대화만 완벽
        assert abs(results.conversation_success_rate - 0.5) < 0.01

        # 대화 1은 실패 없음, 대화 2는 턴 1(index=1)에서 첫 실패 → 평균 1.0
        assert results.first_failure_turn_avg == 1.0


class TestMultiTurnCascade:
    """오류 연쇄율 검증."""

    def test_error_cascade(self):
        """턴 0 틀림 → 턴 1도 틀림 → 연쇄율 100%."""
        conv_labels = [
            [
                '<tool_call>\n{"name": "a", "arguments": {"x": 1}}\n</tool_call>',
                '<tool_call>\n{"name": "b", "arguments": {"y": 2}}\n</tool_call>',
                '<tool_call>\n{"name": "c", "arguments": {"z": 3}}\n</tool_call>',
            ],
        ]
        conv_preds = [
            [
                '<tool_call>\n{"name": "wrong", "arguments": {"x": 1}}\n</tool_call>',
                '<tool_call>\n{"name": "wrong2", "arguments": {"y": 2}}\n</tool_call>',
                '<tool_call>\n{"name": "c", "arguments": {"z": 3}}\n</tool_call>',
            ],
        ]

        results = evaluate_multi_turn(conv_labels, conv_preds)

        # 턴 0 틀림 → 턴 1 틀림 (연쇄 1회)
        # 턴 1 틀림 → 턴 2 맞음 (비연쇄 1회)
        # cascade_opportunities=2, cascade_hits=1 → 50%
        assert abs(results.error_cascade_rate - 0.5) < 0.01

    def test_no_cascade(self):
        """오류가 있지만 연쇄하지 않는 경우."""
        conv_labels = [
            [
                '<tool_call>\n{"name": "a", "arguments": {"x": 1}}\n</tool_call>',
                '<tool_call>\n{"name": "b", "arguments": {"y": 2}}\n</tool_call>',
                '<tool_call>\n{"name": "c", "arguments": {"z": 3}}\n</tool_call>',
            ],
        ]
        conv_preds = [
            [
                '<tool_call>\n{"name": "wrong", "arguments": {"x": 1}}\n</tool_call>',
                '<tool_call>\n{"name": "b", "arguments": {"y": 2}}\n</tool_call>',
                '<tool_call>\n{"name": "c", "arguments": {"z": 3}}\n</tool_call>',
            ],
        ]

        results = evaluate_multi_turn(conv_labels, conv_preds)

        # 턴 0 틀림 → 턴 1 맞음 → 연쇄 안 됨
        assert results.error_cascade_rate == 0.0


class TestMultiTurnEdgeCases:
    """멀티턴 경계 케이스."""

    def test_empty_input(self):
        results = evaluate_multi_turn([], [])
        assert results.total_conversations == 0
        assert results.total_turns == 0

    def test_mismatched_conversation_count(self):
        with pytest.raises(ValueError):
            evaluate_multi_turn([["a"]], [["a"], ["b"]])

    def test_mismatched_turn_count(self):
        with pytest.raises(ValueError):
            evaluate_multi_turn([["a", "b"]], [["a"]])

    def test_to_dict(self):
        results = MultiTurnResults(
            turn_level_accuracy=0.75,
            conversation_success_rate=0.5,
            total_conversations=2,
            total_turns=4,
        )
        d = results.to_dict()
        assert d["turn_level_accuracy"] == 0.75
        assert "aggregated" in d

    def test_summary(self):
        results = MultiTurnResults(
            turn_level_accuracy=0.75,
            total_conversations=2,
            total_turns=4,
        )
        summary = results.summary()
        assert "75.00%" in summary
        assert "HammerBench" in summary


# ================================================================
# preprocessing.py 테스트 (기존 유지)
# ================================================================


class TestToChatml:
    """to_chatml 함수 테스트."""

    def test_basic_conversion(self):
        messages = [
            {"role": "system", "content": "시스템 프롬프트"},
            {"role": "user", "content": "안녕하세요"},
            {"role": "assistant", "content": "무엇을 도와드릴까요?"},
        ]
        result = to_chatml(messages)

        assert "<|im_start|>system\n시스템 프롬프트<|im_end|>" in result
        assert "<|im_start|>user\n안녕하세요<|im_end|>" in result
        assert "<|im_start|>assistant\n무엇을 도와드릴까요?<|im_end|>" in result

    def test_dict_input(self):
        data = {"messages": [{"role": "user", "content": "테스트"}]}
        result = to_chatml(data)
        assert "<|im_start|>user\n테스트<|im_end|>" in result


class TestExtractExamples:
    """extract_examples 함수 테스트."""

    def test_single_assistant(self):
        chatml = (
            "<|im_start|>user\n안녕하세요<|im_end|>\n"
            "<|im_start|>assistant\n반갑습니다!<|im_end|>"
        )
        examples = extract_examples(chatml)

        assert len(examples) == 1
        assert examples[0]["label"] == "반갑습니다!"
        assert "<|im_start|>assistant" in examples[0]["input"]

    def test_multiple_assistants(self):
        chatml = (
            "<|im_start|>user\n첫 번째 질문<|im_end|>\n"
            "<|im_start|>assistant\n첫 번째 답변<|im_end|>\n"
            "<|im_start|>user\n두 번째 질문<|im_end|>\n"
            "<|im_start|>assistant\n두 번째 답변<|im_end|>"
        )
        examples = extract_examples(chatml)

        assert len(examples) == 2
        assert examples[0]["label"] == "첫 번째 답변"
        assert examples[1]["label"] == "두 번째 답변"

    def test_tool_call_extraction(self):
        chatml = (
            '<|im_start|>user\n주문 내역 조회<|im_end|>\n'
            '<|im_start|>assistant\n<tool_call>\n'
            '{"name": "view_order_history", "arguments": {"user_id": "U001"}}\n'
            '</tool_call><|im_end|>'
        )
        examples = extract_examples(chatml)

        assert len(examples) == 1
        assert "<tool_call>" in examples[0]["label"]
        assert "view_order_history" in examples[0]["label"]


class TestFormatConversations:
    """format_conversations 함수 테스트."""

    def test_basic(self):
        sample = {
            "system_prompt": "시스템 프롬프트",
            "messages": [
                {"role": "user", "content": "안녕"},
                {"role": "assistant", "content": "네!"},
            ],
        }
        result = format_conversations(sample)

        assert result["messages"][0]["role"] == "system"
        assert result["messages"][0]["content"] == "시스템 프롬프트"
        assert len(result["messages"]) == 3


class TestExtractToolSchemas:
    """extract_tool_schemas 함수 테스트."""

    def test_filters_none_properties(self):
        """None인 property는 필터링되고 유효한 것만 남아야 함."""
        tools = [
            {
                "name": "search_restaurants",
                "parameters": {
                    "properties": {
                        "query": {"type": "string", "description": "검색어"},
                        "category": {"type": "string", "description": "카테고리"},
                        "user_id": None,
                        "order_id": None,
                    },
                },
            },
            {
                "name": "get_cart",
                "parameters": {
                    "properties": {
                        "user_id": {"type": "string", "description": "사용자 ID"},
                        "query": None,
                        "category": None,
                    },
                },
            },
        ]

        schemas = extract_tool_schemas(tools)

        assert "search_restaurants" in schemas
        assert "get_cart" in schemas

        # None이 필터링되었는지 확인
        assert "user_id" not in schemas["search_restaurants"]["properties"]
        assert "query" in schemas["search_restaurants"]["properties"]
        assert "category" in schemas["search_restaurants"]["properties"]

        assert "user_id" in schemas["get_cart"]["properties"]
        assert "query" not in schemas["get_cart"]["properties"]

    def test_works_with_evaluate(self):
        """추출된 스키마를 evaluate_function_calls에 넘겨서 정상 동작 확인."""
        tools = [
            {
                "name": "search",
                "parameters": {
                    "properties": {
                        "keyword": {"type": "string"},
                        "limit": {"type": "integer"},
                        "other": None,
                    },
                },
            },
        ]
        schemas = extract_tool_schemas(tools)

        labels = [
            '<tool_call>\n{"name": "search", "arguments": {"keyword": "치킨", "limit": 10}}\n</tool_call>',
        ]
        results = evaluate_function_calls(labels, labels.copy(), tool_schemas=schemas)
        assert results.schema_valid_rate == 1.0

