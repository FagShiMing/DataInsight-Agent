from app.services.report_service import generate_markdown_report


def test_generate_markdown_report_contains_required_sections():
    profile = {
        "shape": {"rows": 2, "columns": 2},
        "columns": ["product", "sales"],
        "missing_values": {"product": 0, "sales": 1},
        "missing_rate": {"product": 0.0, "sales": 0.5},
        "numeric_summary": {
            "sales": {
                "count": 1,
                "mean": 100.0,
                "min": 100.0,
                "max": 100.0,
                "median": 100.0,
                "std": None,
            }
        },
        "categorical_summary": {
            "product": {"unique_count": 1, "top_values": {"A": 1}}
        },
    }

    markdown = generate_markdown_report(
        profile=profile,
        insights="建议关注 sales 缺失值。",
        tool_trace=[
            {
                "tool_name": "missing_value_analysis",
                "status": "success",
                "result_summary": "发现 sales 缺失。",
            }
        ],
    )

    assert "# CSV 数据分析报告" in markdown
    assert "## 数据概览" in markdown
    assert "## 缺失值分析" in markdown
    assert "## 数值列摘要" in markdown
    assert "建议关注 sales 缺失值。" in markdown
    assert "missing_value_analysis" in markdown
