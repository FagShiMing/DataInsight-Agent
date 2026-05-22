from app.main import AnalysisSuggestionsRequest, analysis_suggestions


def sample_profile():
    return {
        "shape": {"rows": 5, "columns": 5},
        "columns": ["date", "product", "region", "sales", "profit"],
        "missing_values": {
            "date": 0,
            "product": 0,
            "region": 0,
            "sales": 1,
            "profit": 0,
        },
        "missing_rate": {
            "date": 0.0,
            "product": 0.0,
            "region": 0.0,
            "sales": 0.2,
            "profit": 0.0,
        },
        "numeric_summary": {
            "sales": {"mean": 1650.0, "min": 1200.0, "max": 2100.0},
            "profit": {"mean": 450.0, "min": 300.0, "max": 620.0},
        },
    }


def test_analysis_suggestions_returns_success_response():
    response = analysis_suggestions(
        AnalysisSuggestionsRequest(profile=sample_profile())
    )

    assert response["success"] is True


def test_analysis_suggestions_returns_suggestions_field():
    response = analysis_suggestions(
        AnalysisSuggestionsRequest(profile=sample_profile())
    )

    assert response["source"] == "rule"
    assert isinstance(response["suggestions"], list)
    assert response["suggestions"]
    assert "sales" in " ".join(response["suggestions"])


def test_analysis_suggestions_works_without_api_key(monkeypatch):
    monkeypatch.delenv("ZHIPUAI_API_KEY", raising=False)
    response = analysis_suggestions(
        AnalysisSuggestionsRequest(profile=sample_profile())
    )

    assert response["source"] == "rule"
