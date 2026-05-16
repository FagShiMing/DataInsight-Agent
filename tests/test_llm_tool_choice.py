from app.services.agent_service import run_agent


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


def test_llm_tool_choice_success(monkeypatch):
    def fake_ask_llm_for_tool_choice(question, profile_summary, tools_schema):
        return '{"tool_name": "missing_value_analysis", "arguments": {}}'

    monkeypatch.setattr(
        "app.services.llm_service.ask_llm_for_tool_choice",
        fake_ask_llm_for_tool_choice,
    )

    response = run_agent(
        "哪些字段有缺失值？",
        profile=sample_profile(),
        use_llm_tool_choice=True,
    )

    trace = response["tool_trace"][0]
    assert response["tool_name"] == "missing_value_analysis"
    assert trace["tool_choice_source"] == "llm"
    assert trace["fallback_used"] is False
    assert trace["fallback_reason"] is None


def test_llm_invalid_json_falls_back_to_rules(monkeypatch):
    def fake_ask_llm_for_tool_choice(question, profile_summary, tools_schema):
        return "不是 JSON"

    monkeypatch.setattr(
        "app.services.llm_service.ask_llm_for_tool_choice",
        fake_ask_llm_for_tool_choice,
    )

    response = run_agent(
        "哪些字段有缺失值？",
        profile=sample_profile(),
        use_llm_tool_choice=True,
    )

    trace = response["tool_trace"][0]
    assert response["tool_name"] == "missing_value_analysis"
    assert trace["tool_choice_source"] == "rule"
    assert trace["fallback_used"] is True
    assert "合法 JSON" in trace["fallback_reason"]
    assert trace["llm_choice_raw"] == "不是 JSON"


def test_llm_unknown_tool_falls_back_to_rules(monkeypatch):
    def fake_ask_llm_for_tool_choice(question, profile_summary, tools_schema):
        return '{"tool_name": "unknown_tool", "arguments": {}}'

    monkeypatch.setattr(
        "app.services.llm_service.ask_llm_for_tool_choice",
        fake_ask_llm_for_tool_choice,
    )

    response = run_agent(
        "哪些字段有缺失值？",
        profile=sample_profile(),
        use_llm_tool_choice=True,
    )

    trace = response["tool_trace"][0]
    assert response["tool_name"] == "missing_value_analysis"
    assert trace["tool_choice_source"] == "rule"
    assert trace["fallback_used"] is True
    assert "工具不存在" in trace["fallback_reason"]


def test_run_agent_uses_rules_when_llm_tool_choice_disabled():
    response = run_agent(
        "哪些字段有缺失值？",
        profile=sample_profile(),
        use_llm_tool_choice=False,
    )

    trace = response["tool_trace"][0]
    assert response["tool_name"] == "missing_value_analysis"
    assert trace["tool_choice_source"] == "rule"
    assert trace["fallback_used"] is False
