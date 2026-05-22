from app.main import DataChatRequest, chat_with_data
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


def test_chat_data_keeps_rule_answer_when_llm_answer_disabled(monkeypatch):
    def fake_generate_llm_answer(**kwargs):
        raise AssertionError("use_llm_answer=false 时不应该调用 LLM 最终回答")

    monkeypatch.setattr(
        "app.services.llm_service.generate_llm_answer",
        fake_generate_llm_answer,
    )

    response = chat_with_data(
        DataChatRequest(
            question="哪些字段有缺失值？",
            profile=sample_profile(),
            use_llm_answer=False,
        )
    )

    assert "缺失" in response["answer"]
    assert response["llm_used"] is False
    assert response["fallback_reason"] is None


def test_chat_data_uses_mock_llm_answer_when_enabled(monkeypatch):
    received = {}

    def fake_generate_llm_answer(**kwargs):
        received.update(kwargs)
        return "这是 mock LLM 生成的最终回答。"

    monkeypatch.setattr(
        "app.services.llm_service.generate_llm_answer",
        fake_generate_llm_answer,
    )

    response = chat_with_data(
        DataChatRequest(
            question="哪些字段有缺失值？",
            profile=sample_profile(),
            use_llm_answer=True,
        )
    )

    assert response["answer"] == "这是 mock LLM 生成的最终回答。"
    assert response["llm_used"] is True
    assert response["fallback_reason"] is None
    assert received["selected_tool"] == "missing_value_analysis"
    assert "columns_with_missing" in received["tool_result"]


def test_run_agent_falls_back_when_llm_answer_api_key_missing(monkeypatch):
    monkeypatch.delenv("ZHIPUAI_API_KEY", raising=False)
    monkeypatch.setattr("app.services.llm_service.ZHIPUAI_API_KEY", None)

    response = run_agent(
        "哪些字段有缺失值？",
        profile=sample_profile(),
        use_llm_answer=True,
    )

    assert "缺失" in response["answer"]
    assert response["llm_used"] is False
    assert response["fallback_reason"] == "missing_api_key"


def test_run_agent_falls_back_when_llm_answer_call_failed(monkeypatch):
    def fake_generate_llm_answer(**kwargs):
        raise ValueError("LLM service timeout")

    monkeypatch.setattr(
        "app.services.llm_service.generate_llm_answer",
        fake_generate_llm_answer,
    )

    response = run_agent(
        "哪些字段有缺失值？",
        profile=sample_profile(),
        use_llm_answer=True,
    )

    assert "缺失" in response["answer"]
    assert response["llm_used"] is False
    assert response["fallback_reason"] == "llm_call_failed"


def test_chat_data_response_contains_llm_fields_when_using_rule_answer():
    response = chat_with_data(
        DataChatRequest(
            question="哪些字段有缺失值？",
            profile=sample_profile(),
        )
    )

    assert "llm_used" in response
    assert "fallback_reason" in response
    assert response["llm_used"] is False
    assert response["fallback_reason"] is None
