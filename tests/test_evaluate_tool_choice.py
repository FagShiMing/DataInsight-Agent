import json
from pathlib import Path

from scripts.evaluate_tool_choice import (
    ALLOWED_CATEGORIES,
    DEFAULT_CASES_PATH,
    evaluate_tool_choice,
    load_cases,
    main,
    sample_profile,
)


def test_load_tool_choice_cases_has_required_fields():
    cases = load_cases(DEFAULT_CASES_PATH)

    assert len(cases) >= 12
    for case in cases:
        assert "question" in case
        assert "expected_tool" in case
        assert "category" in case
        assert "subcategory" in case
        assert case["question"]
        assert case["expected_tool"]
        assert case["category"] in ALLOWED_CATEGORIES
        assert case["subcategory"]


def test_evaluate_tool_choice_returns_summary_fields():
    cases = load_cases(DEFAULT_CASES_PATH)
    result = evaluate_tool_choice(cases, sample_profile())

    assert result["mode"] == "rule"
    assert result["total_cases"] == len(cases)
    assert "correct" in result
    assert "accuracy" in result
    assert "failed_cases" in result
    assert "case_results" in result
    assert "category_metrics" in result
    assert "subcategory_metrics" in result
    assert "failure_analysis" in result
    assert isinstance(result["failed_cases"], list)
    assert isinstance(result["case_results"], list)
    assert result["case_results"][0]["id"] == "case_001"
    assert {
        "id",
        "question",
        "category",
        "subcategory",
        "expected_tool",
        "actual_tool",
        "correct",
        "error",
    }.issubset(result["case_results"][0])


def test_evaluate_tool_choice_accuracy_is_between_zero_and_one():
    cases = load_cases(DEFAULT_CASES_PATH)
    result = evaluate_tool_choice(cases, sample_profile())

    assert 0 <= result["accuracy"] <= 1


def test_default_cases_path_exists():
    assert Path(DEFAULT_CASES_PATH).exists()


def test_rule_mode_does_not_call_llm(monkeypatch):
    calls = []

    def fake_run_agent(question, profile=None, use_llm_tool_choice=False):
        calls.append(use_llm_tool_choice)
        return {
            "tool_name": "missing_value_analysis",
            "tool_trace": [
                {
                    "tool_name": "missing_value_analysis",
                    "status": "success",
                    "fallback_used": False,
                    "fallback_reason": None,
                }
            ],
        }

    monkeypatch.setattr("scripts.evaluate_tool_choice.run_agent", fake_run_agent)

    result = evaluate_tool_choice(
        [
            {
                "question": "哪些字段有缺失值？",
                "expected_tool": "missing_value_analysis",
                "category": "missing_value",
                "subcategory": "missing_vs_qa",
            }
        ],
        sample_profile(),
        mode="rule",
    )

    assert result["correct"] == 1
    assert calls == [False]


def test_cli_mode_rule_runs(monkeypatch, capsys):
    monkeypatch.setattr(
        "scripts.evaluate_tool_choice.load_cases",
        lambda path: [
            {
                "question": "哪些字段有缺失值？",
                "expected_tool": "missing_value_analysis",
                "category": "missing_value",
                "subcategory": "missing_vs_qa",
            }
        ],
    )
    monkeypatch.setattr(
        "scripts.evaluate_tool_choice.run_agent",
        lambda question, profile=None, use_llm_tool_choice=False: {
            "tool_name": "missing_value_analysis",
            "tool_trace": [
                {
                    "tool_name": "missing_value_analysis",
                    "status": "success",
                    "fallback_used": False,
                    "fallback_reason": None,
                }
            ],
        },
    )

    result = main(["--mode", "rule"])
    output = capsys.readouterr().out

    assert result["mode"] == "rule"
    assert "mode: rule" in output
    assert "accuracy: 1.0000" in output


def test_llm_mode_uses_mocked_agent_without_real_api(monkeypatch):
    calls = []

    def fake_run_agent(question, profile=None, use_llm_tool_choice=False):
        calls.append(use_llm_tool_choice)
        return {
            "tool_name": "numeric_summary",
            "tool_trace": [
                {
                    "tool_name": "numeric_summary",
                    "status": "success",
                    "tool_choice_source": "llm",
                    "fallback_used": False,
                    "fallback_reason": None,
                }
            ],
        }

    monkeypatch.setattr("scripts.evaluate_tool_choice.run_agent", fake_run_agent)

    result = evaluate_tool_choice(
        [
            {
                "question": "数值字段的平均值是多少？",
                "expected_tool": "numeric_summary",
                "category": "numeric_summary",
                "subcategory": "numeric_vs_business_question",
            }
        ],
        sample_profile(),
        mode="llm",
    )

    assert result["mode"] == "llm"
    assert result["correct"] == 1
    assert calls == [True]


def test_llm_mode_fallback_is_recorded_as_error(monkeypatch):
    def fake_run_agent(question, profile=None, use_llm_tool_choice=False):
        return {
            "tool_name": "missing_value_analysis",
            "tool_trace": [
                {
                    "tool_name": "missing_value_analysis",
                    "status": "success",
                    "tool_choice_source": "rule",
                    "fallback_used": True,
                    "fallback_reason": "API key missing",
                }
            ],
        }

    monkeypatch.setattr("scripts.evaluate_tool_choice.run_agent", fake_run_agent)

    result = evaluate_tool_choice(
        [
            {
                "question": "哪些字段有缺失值？",
                "expected_tool": "missing_value_analysis",
                "category": "missing_value",
                "subcategory": "missing_vs_qa",
            }
        ],
        sample_profile(),
        mode="llm",
    )

    assert result["correct"] == 0
    assert result["failed_cases"][0]["actual_tool"] == "missing_value_analysis"
    assert result["failed_cases"][0]["error"] == "API key missing"


def test_output_writes_json_file(tmp_path, monkeypatch):
    output_path = tmp_path / "tool_choice_result.json"

    monkeypatch.setattr(
        "scripts.evaluate_tool_choice.load_cases",
        lambda path: [
            {
                "question": "哪些字段有缺失值？",
                "expected_tool": "missing_value_analysis",
                "category": "missing_value",
                "subcategory": "missing_vs_qa",
            }
        ],
    )
    monkeypatch.setattr(
        "scripts.evaluate_tool_choice.run_agent",
        lambda question, profile=None, use_llm_tool_choice=False: {
            "tool_name": "missing_value_analysis",
            "tool_trace": [
                {
                    "tool_name": "missing_value_analysis",
                    "status": "success",
                    "fallback_used": False,
                    "fallback_reason": None,
                }
            ],
        },
    )

    main(["--mode", "rule", "--output", str(output_path)])

    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert data["mode"] == "rule"
    assert "category_metrics" in data
    assert "subcategory_metrics" in data
    assert "failure_analysis" in data
    assert data["case_results"][0]["actual_tool"] == "missing_value_analysis"


def test_load_cases_missing_required_field_raises_value_error(tmp_path):
    path = tmp_path / "bad_cases.jsonl"
    path.write_text('{"question": "缺字段"}\n', encoding="utf-8")

    try:
        load_cases(path)
    except ValueError as exc:
        assert "Line 1" in str(exc)
        assert "missing question or expected_tool" in str(exc)
    else:
        raise AssertionError("缺少 expected_tool 时应该抛出 ValueError")


def test_load_cases_skips_empty_lines(tmp_path):
    path = tmp_path / "cases.jsonl"
    path.write_text(
        (
            '\n{"question": "哪些字段有缺失值？", '
            '"expected_tool": "missing_value_analysis", '
            '"category": "missing_value", '
            '"subcategory": "missing_vs_qa"}\n\n'
        ),
        encoding="utf-8",
    )

    cases = load_cases(path)

    assert len(cases) == 1
    assert cases[0]["expected_tool"] == "missing_value_analysis"


def test_load_cases_invalid_json_has_clear_error(tmp_path):
    path = tmp_path / "bad_json.jsonl"
    path.write_text('{"question": "坏 JSON"\n', encoding="utf-8")

    try:
        load_cases(path)
    except ValueError as exc:
        assert "Line 1" in str(exc)
        assert "not valid JSON" in str(exc)
    else:
        raise AssertionError("JSON 格式错误时应该抛出 ValueError")


def test_failed_cases_include_debug_fields(monkeypatch):
    def fake_run_agent(question, profile=None, use_llm_tool_choice=False):
        return {
            "tool_name": "numeric_summary",
            "tool_trace": [
                {
                    "tool_name": "numeric_summary",
                    "status": "success",
                    "fallback_used": False,
                    "fallback_reason": None,
                }
            ],
        }

    monkeypatch.setattr("scripts.evaluate_tool_choice.run_agent", fake_run_agent)

    result = evaluate_tool_choice(
        [
            {
                "question": "哪些字段有缺失值？",
                "expected_tool": "missing_value_analysis",
                "category": "missing_value",
                "subcategory": "missing_vs_qa",
            }
        ],
        sample_profile(),
        mode="rule",
    )
    failed_case = result["failed_cases"][0]

    assert failed_case["question"] == "哪些字段有缺失值？"
    assert failed_case["category"] == "missing_value"
    assert failed_case["subcategory"] == "missing_vs_qa"
    assert failed_case["expected_tool"] == "missing_value_analysis"
    assert failed_case["actual_tool"] == "numeric_summary"
    assert "error" in failed_case


def test_load_cases_missing_category_raises_value_error(tmp_path):
    path = tmp_path / "bad_cases.jsonl"
    path.write_text(
        '{"question": "哪些字段有缺失值？", "expected_tool": "missing_value_analysis"}\n',
        encoding="utf-8",
    )

    try:
        load_cases(path)
    except ValueError as exc:
        assert "Line 1" in str(exc)
        assert "missing category" in str(exc)
    else:
        raise AssertionError("缺少 category 时应该抛出 ValueError")


def test_load_cases_invalid_category_raises_value_error(tmp_path):
    path = tmp_path / "bad_cases.jsonl"
    path.write_text(
        (
            '{"question": "哪些字段有缺失值？", '
            '"expected_tool": "missing_value_analysis", '
            '"category": "missing_values", '
            '"subcategory": "missing_vs_qa"}\n'
        ),
        encoding="utf-8",
    )

    try:
        load_cases(path)
    except ValueError as exc:
        assert "Line 1" in str(exc)
        assert "invalid category: missing_values" in str(exc)
    else:
        raise AssertionError("非法 category 时应该抛出 ValueError")


def test_category_metrics_contains_total_correct_accuracy(monkeypatch):
    def fake_run_agent(question, profile=None, use_llm_tool_choice=False):
        return {
            "tool_name": "missing_value_analysis",
            "tool_trace": [
                {
                    "tool_name": "missing_value_analysis",
                    "status": "success",
                    "fallback_used": False,
                    "fallback_reason": None,
                }
            ],
        }

    monkeypatch.setattr("scripts.evaluate_tool_choice.run_agent", fake_run_agent)

    result = evaluate_tool_choice(
        [
            {
                "question": "哪些字段有缺失值？",
                "expected_tool": "missing_value_analysis",
                "category": "missing_value",
                "subcategory": "missing_vs_qa",
            },
            {
                "question": "生成报告",
                "expected_tool": "generate_report",
                "category": "report_generation",
                "subcategory": "report_vs_summary",
            },
        ],
        sample_profile(),
    )

    assert result["category_metrics"]["missing_value"] == {
        "total": 1,
        "correct": 1,
        "accuracy": 1.0,
    }
    assert result["category_metrics"]["report_generation"] == {
        "total": 1,
        "correct": 0,
        "accuracy": 0.0,
    }
    assert result["failed_cases"][0]["category"] == "report_generation"
    assert result["subcategory_metrics"]["missing_vs_qa"] == {
        "total": 1,
        "correct": 1,
        "accuracy": 1.0,
    }
    assert result["subcategory_metrics"]["report_vs_summary"] == {
        "total": 1,
        "correct": 0,
        "accuracy": 0.0,
    }
    assert result["failed_cases"][0]["subcategory"] == "report_vs_summary"


def test_failure_analysis_counts_category_and_expected_tool(monkeypatch):
    def fake_run_agent(question, profile=None, use_llm_tool_choice=False):
        return {
            "tool_name": "answer_data_question",
            "tool_trace": [
                {
                    "tool_name": "answer_data_question",
                    "status": "success",
                    "fallback_used": False,
                    "fallback_reason": None,
                }
            ],
        }

    monkeypatch.setattr("scripts.evaluate_tool_choice.run_agent", fake_run_agent)

    result = evaluate_tool_choice(
        [
            {
                "question": "生成报告",
                "expected_tool": "generate_report",
                "category": "report_generation",
                "subcategory": "report_vs_summary",
            },
            {
                "question": "数值字段平均值",
                "expected_tool": "numeric_summary",
                "category": "numeric_summary",
                "subcategory": "numeric_vs_business_question",
            },
        ],
        sample_profile(),
    )
    analysis = result["failure_analysis"]

    assert analysis["total_failed"] == 2
    assert analysis["failed_by_category"] == {
        "report_generation": 1,
        "numeric_summary": 1,
    }
    assert analysis["failed_by_subcategory"] == {
        "report_vs_summary": 1,
        "numeric_vs_business_question": 1,
    }
    assert analysis["failed_by_expected_tool"] == {
        "generate_report": 1,
        "numeric_summary": 1,
    }


def test_load_cases_missing_subcategory_raises_value_error(tmp_path):
    path = tmp_path / "bad_cases.jsonl"
    path.write_text(
        (
            '{"question": "哪些字段有缺失值？", '
            '"expected_tool": "missing_value_analysis", '
            '"category": "missing_value"}\n'
        ),
        encoding="utf-8",
    )

    try:
        load_cases(path)
    except ValueError as exc:
        assert "Line 1" in str(exc)
        assert "missing subcategory" in str(exc)
    else:
        raise AssertionError("缺少 subcategory 时应该抛出 ValueError")
