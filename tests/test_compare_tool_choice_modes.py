import json

from scripts.compare_tool_choice_modes import (
    build_category_comparison,
    build_comparison_report,
    compare_results,
    main,
)
from scripts.evaluate_tool_choice import (
    build_category_metrics,
    build_failure_analysis,
    build_subcategory_metrics,
)


def _case_result(
    case_id,
    expected,
    actual,
    correct,
    question=None,
    category="missing_value",
    subcategory="missing_vs_qa",
    error=None,
):
    return {
        "id": case_id,
        "question": question or f"question {case_id}",
        "category": category,
        "subcategory": subcategory,
        "expected_tool": expected,
        "actual_tool": actual,
        "correct": correct,
        "error": error,
    }


def _evaluation_result(mode, case_results):
    return {
        "mode": mode,
        "total_cases": len(case_results),
        "correct": sum(1 for case in case_results if case["correct"]),
        "accuracy": round(
            sum(1 for case in case_results if case["correct"]) / len(case_results),
            4,
        ),
        "category_metrics": build_category_metrics(case_results),
        "subcategory_metrics": build_subcategory_metrics(case_results),
        "failure_analysis": build_failure_analysis(case_results),
        "failed_cases": [case for case in case_results if not case["correct"]],
        "case_results": case_results,
    }


def test_default_compare_runs_rule_only_and_skips_llm(monkeypatch):
    modes = []

    monkeypatch.setattr(
        "scripts.compare_tool_choice_modes.load_cases",
        lambda path: [
            {
                "question": "哪些字段有缺失值？",
                "expected_tool": "missing_value_analysis",
                "category": "missing_value",
            }
        ],
    )

    def fake_evaluate_tool_choice(cases, profile, mode="rule"):
        modes.append(mode)
        return _evaluation_result(
            mode,
            [
                _case_result(
                    "case_001",
                    "missing_value_analysis",
                    "missing_value_analysis",
                    True,
                    question=cases[0]["question"],
                )
            ],
        )

    monkeypatch.setattr(
        "scripts.compare_tool_choice_modes.evaluate_tool_choice",
        fake_evaluate_tool_choice,
    )

    report = build_comparison_report("fake_cases.jsonl", run_llm=False)

    assert modes == ["rule"]
    assert report["llm"]["status"] == "skipped"
    assert report["comparison"]["status"] == "skipped"
    assert report["category_comparison"]["status"] == "skipped"
    assert report["category_comparison"]["reason"] == "llm mode was not run"


def test_compare_report_contains_required_sections(monkeypatch):
    monkeypatch.setattr(
        "scripts.compare_tool_choice_modes.load_cases",
        lambda path: [
            {
                "question": "生成报告",
                "expected_tool": "generate_report",
                "category": "report_generation",
            }
        ],
    )
    monkeypatch.setattr(
        "scripts.compare_tool_choice_modes.evaluate_tool_choice",
        lambda cases, profile, mode="rule": _evaluation_result(
            mode,
            [_case_result("case_001", "generate_report", "generate_report", True)],
        ),
    )

    report = build_comparison_report("fake_cases.jsonl")

    assert "rule" in report
    assert "llm" in report
    assert "comparison" in report
    assert "category_comparison" in report
    assert report["total_cases"] == 1


def test_compare_results_counts_correct_wrong_and_differences():
    rule_result = _evaluation_result(
        "rule",
        [
            _case_result("case_001", "missing_value_analysis", "missing_value_analysis", True),
            _case_result(
                "case_002",
                "generate_report",
                "numeric_summary",
                False,
                category="report_generation",
            ),
            _case_result(
                "case_003",
                "numeric_summary",
                "numeric_summary",
                True,
                category="numeric_summary",
            ),
            _case_result(
                "case_004",
                "answer_data_question",
                "generate_report",
                False,
                category="ambiguous_intent",
            ),
        ],
    )
    llm_result = _evaluation_result(
        "llm",
        [
            _case_result("case_001", "missing_value_analysis", "missing_value_analysis", True),
            _case_result(
                "case_002",
                "generate_report",
                "answer_data_question",
                False,
                category="report_generation",
            ),
            _case_result(
                "case_003",
                "numeric_summary",
                "answer_data_question",
                False,
                category="numeric_summary",
            ),
            _case_result(
                "case_004",
                "answer_data_question",
                "answer_data_question",
                True,
                category="ambiguous_intent",
            ),
        ],
    )
    llm_result["status"] = "completed"

    comparison = compare_results(rule_result, llm_result)

    assert comparison["status"] == "compared"
    assert comparison["both_correct"] == 1
    assert comparison["both_wrong"] == 1
    assert len(comparison["rule_correct_llm_wrong"]) == 1
    assert len(comparison["rule_wrong_llm_correct"]) == 1
    assert len(comparison["different_actual_tool"]) == 3
    assert comparison["different_actual_tool"][0]["category"] == "report_generation"
    assert comparison["different_actual_tool"][0]["subcategory"] == "missing_vs_qa"
    assert comparison["different_actual_tool"][0]["rule_actual_tool"] == "numeric_summary"


def test_run_llm_uses_mocked_llm_result_without_real_api(monkeypatch):
    modes = []

    monkeypatch.setattr(
        "scripts.compare_tool_choice_modes.load_cases",
        lambda path: [
            {
                "question": "数值字段平均值",
                "expected_tool": "numeric_summary",
                "category": "numeric_summary",
            }
        ],
    )

    def fake_evaluate_tool_choice(cases, profile, mode="rule"):
        modes.append(mode)
        actual_tool = "numeric_summary" if mode == "rule" else "answer_data_question"
        return _evaluation_result(
            mode,
            [
                _case_result(
                    "case_001",
                    "numeric_summary",
                    actual_tool,
                    mode == "rule",
                    category="numeric_summary",
                )
            ],
        )

    monkeypatch.setattr(
        "scripts.compare_tool_choice_modes.evaluate_tool_choice",
        fake_evaluate_tool_choice,
    )

    report = build_comparison_report("fake_cases.jsonl", run_llm=True)

    assert modes == ["rule", "llm"]
    assert report["llm"]["status"] == "completed"
    assert len(report["comparison"]["rule_correct_llm_wrong"]) == 1
    assert report["category_comparison"]["numeric_summary"] == {
        "total": 1,
        "rule_correct": 1,
        "rule_accuracy": 1.0,
        "llm_correct": 0,
        "llm_accuracy": 0.0,
    }


def test_run_llm_failure_is_recorded(monkeypatch):
    monkeypatch.setattr(
        "scripts.compare_tool_choice_modes.load_cases",
        lambda path: [
            {
                "question": "生成报告",
                "expected_tool": "generate_report",
                "category": "report_generation",
            }
        ],
    )

    def fake_evaluate_tool_choice(cases, profile, mode="rule"):
        if mode == "llm":
            raise RuntimeError("mock llm failed")
        return _evaluation_result(
            mode,
            [_case_result("case_001", "generate_report", "generate_report", True)],
        )

    monkeypatch.setattr(
        "scripts.compare_tool_choice_modes.evaluate_tool_choice",
        fake_evaluate_tool_choice,
    )

    report = build_comparison_report("fake_cases.jsonl", run_llm=True)

    assert report["llm"]["status"] == "failed"
    assert report["llm"]["error"] == "mock llm failed"
    assert report["comparison"]["status"] == "failed"
    assert report["category_comparison"]["status"] == "failed"


def test_output_writes_json_file(tmp_path, monkeypatch):
    output_path = tmp_path / "compare_result.json"

    monkeypatch.setattr(
        "scripts.compare_tool_choice_modes.load_cases",
        lambda path: [
            {
                "question": "生成报告",
                "expected_tool": "generate_report",
                "category": "report_generation",
            }
        ],
    )
    monkeypatch.setattr(
        "scripts.compare_tool_choice_modes.evaluate_tool_choice",
        lambda cases, profile, mode="rule": _evaluation_result(
            mode,
            [_case_result("case_001", "generate_report", "generate_report", True)],
        ),
    )

    main(["--output", str(output_path)])

    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert data["rule"]["mode"] == "rule"
    assert "category_metrics" in data["rule"]
    assert data["llm"]["status"] == "skipped"
    assert data["comparison"]["status"] == "skipped"
    assert data["category_comparison"]["status"] == "skipped"


def test_cli_default_runs(capsys, monkeypatch):
    monkeypatch.setattr(
        "scripts.compare_tool_choice_modes.load_cases",
        lambda path: [
            {
                "question": "有哪些字段？",
                "expected_tool": "answer_data_question",
                "category": "data_question",
            }
        ],
    )
    monkeypatch.setattr(
        "scripts.compare_tool_choice_modes.evaluate_tool_choice",
        lambda cases, profile, mode="rule": _evaluation_result(
            mode,
            [_case_result("case_001", "answer_data_question", "answer_data_question", True)],
        ),
    )

    report = main([])
    output = capsys.readouterr().out

    assert report["llm"]["status"] == "skipped"
    assert "Tool choice mode comparison" in output
    assert "status: skipped" in output
    assert "Category comparison" in output


def test_cli_verbose_runs(capsys, monkeypatch):
    monkeypatch.setattr(
        "scripts.compare_tool_choice_modes.load_cases",
        lambda path: [
            {
                "question": "生成报告",
                "expected_tool": "generate_report",
                "category": "report_generation",
            }
        ],
    )

    def fake_evaluate_tool_choice(cases, profile, mode="rule"):
        actual_tool = "generate_report" if mode == "rule" else "answer_data_question"
        return _evaluation_result(
            mode,
            [
                _case_result(
                    "case_001",
                    "generate_report",
                    actual_tool,
                    mode == "rule",
                    category="report_generation",
                )
            ],
        )

    monkeypatch.setattr(
        "scripts.compare_tool_choice_modes.evaluate_tool_choice",
        fake_evaluate_tool_choice,
    )

    report = main(["--run-llm", "--verbose"])
    output = capsys.readouterr().out

    assert report["comparison"]["status"] == "compared"
    assert "Different actual tool cases:" in output
    assert "category: report_generation" in output
    assert "subcategory: missing_vs_qa" in output
    assert "llm_actual_tool: answer_data_question" in output


def test_build_category_comparison_counts_rule_and_llm_metrics():
    rule_result = _evaluation_result(
        "rule",
        [
            _case_result(
                "case_001",
                "missing_value_analysis",
                "missing_value_analysis",
                True,
                category="missing_value",
            ),
            _case_result(
                "case_002",
                "numeric_summary",
                "answer_data_question",
                False,
                category="numeric_summary",
            ),
        ],
    )
    llm_result = _evaluation_result(
        "llm",
        [
            _case_result(
                "case_001",
                "missing_value_analysis",
                "answer_data_question",
                False,
                category="missing_value",
            ),
            _case_result(
                "case_002",
                "numeric_summary",
                "numeric_summary",
                True,
                category="numeric_summary",
            ),
        ],
    )
    llm_result["status"] = "completed"

    comparison = build_category_comparison(rule_result, llm_result)

    assert comparison["status"] == "compared"
    assert comparison["missing_value"] == {
        "total": 1,
        "rule_correct": 1,
        "rule_accuracy": 1.0,
        "llm_correct": 0,
        "llm_accuracy": 0.0,
    }
    assert comparison["numeric_summary"] == {
        "total": 1,
        "rule_correct": 0,
        "rule_accuracy": 0.0,
        "llm_correct": 1,
        "llm_accuracy": 1.0,
    }
