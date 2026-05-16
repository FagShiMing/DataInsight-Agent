from app.services.agent_service import choose_tool_by_rules, parse_llm_tool_choice, run_agent
from app.services.tools import (
    TOOL_REGISTRY,
    call_tool,
    get_tool,
    missing_value_analysis,
    numeric_summary,
)


def sample_profile():
    return {
        "shape": {"rows": 3, "columns": 3},
        "columns": ["product", "sales", "profit"],
        "dtypes": {"product": "object", "sales": "float64", "profit": "int64"},
        "missing_values": {"product": 0, "sales": 1, "profit": 0},
        "missing_rate": {"product": 0.0, "sales": 0.3333, "profit": 0.0},
        "numeric_summary": {
            "sales": {
                "count": 2,
                "mean": 200.0,
                "min": 100.0,
                "max": 300.0,
                "median": 200.0,
                "std": 141.4213562373095,
            }
        },
        "categorical_summary": {
            "product": {"unique_count": 2, "top_values": {"A": 2, "B": 1}}
        },
        "preview": [],
    }


def test_tool_registry_can_find_required_tools():
    required_tools = {
        "profile_csv",
        "missing_value_analysis",
        "numeric_summary",
        "answer_data_question",
        "generate_report",
    }

    assert required_tools.issubset(set(TOOL_REGISTRY))
    assert get_tool("missing_value_analysis").name == "missing_value_analysis"


def test_missing_value_analysis_returns_missing_columns():
    result = missing_value_analysis(sample_profile())

    assert result["total_missing"] == 1
    assert result["columns_with_missing"][0]["column"] == "sales"


def test_numeric_summary_returns_numeric_columns():
    result = numeric_summary(sample_profile())

    assert "sales" in result["numeric_summary"]
    assert result["numeric_summary"]["sales"]["max"] == 300.0


def test_call_unknown_tool_returns_error():
    try:
        call_tool("unknown_tool", {})
    except ValueError as exc:
        assert "工具不存在" in str(exc)
    else:
        raise AssertionError("不存在的工具应该抛出 ValueError")


def test_agent_completes_one_tool_call():
    response = run_agent("哪些字段有缺失值？", profile=sample_profile())

    assert response["tool_name"] == "missing_value_analysis"
    assert response["tool_trace"][0]["status"] == "success"
    assert "缺失" in response["answer"]


def test_agent_handles_unknown_llm_tool():
    response = run_agent(
        "测试不存在的工具",
        profile=sample_profile(),
        llm_tool_choice_json='{"tool_name": "not_exist", "arguments": {}}',
    )

    assert response["tool_trace"][0]["status"] == "failed"
    assert "工具不存在" in response["answer"]


def test_agent_handles_invalid_llm_json():
    response = run_agent(
        "测试非法 JSON",
        profile=sample_profile(),
        llm_tool_choice_json="not json",
    )

    assert response["tool_trace"][0]["status"] == "failed"
    assert "合法 JSON" in response["answer"]


def test_parse_llm_tool_choice_requires_arguments_object():
    try:
        parse_llm_tool_choice('{"tool_name": "numeric_summary", "arguments": []}')
    except ValueError as exc:
        assert "arguments" in str(exc)
    else:
        raise AssertionError("arguments 不是对象时应该抛出 ValueError")


def test_rule_choice_generates_report_for_boss_report_request():
    choice = choose_tool_by_rules("生成一份可以发给老板看的报告")

    assert choice["tool_name"] == "generate_report"


def test_rule_choice_detects_missing_value_request():
    choice = choose_tool_by_rules("哪些字段缺失比较严重")

    assert choice["tool_name"] == "missing_value_analysis"


def test_rule_choice_detects_numeric_summary_request():
    choice = choose_tool_by_rules("销售额和利润的平均值是多少")

    assert choice["tool_name"] == "numeric_summary"


def test_rule_choice_detects_profile_csv_with_local_path():
    choice = choose_tool_by_rules("帮我看看 data/sample_sales.csv 这个数据整体怎么样")

    assert choice["tool_name"] == "profile_csv"
    assert choice["arguments"]["file_path"] == "data/sample_sales.csv"


def test_rule_choice_keeps_business_question_as_data_question():
    choice = choose_tool_by_rules("这份数据有什么值得关注的业务问题")

    assert choice["tool_name"] == "answer_data_question"
