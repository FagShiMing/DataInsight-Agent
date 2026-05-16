import json

from scripts.compare_tool_choice_modes import (
    build_comparison_report,
    compare_results,
    main,
)


def _case_result(case_id, expected, actual, correct, question=None, error=None):
    return {
        "id": case_id,
        "question": question or f"question {case_id}",
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
        "failed_cases": [case for case in case_results if not case["correct"]],
        "case_results": case_results,
    }


def test_default_compare_runs_rule_only_and_skips_llm(monkeypatch):
    modes = []

    monkeypatch.setattr(
        "scripts.compare_tool_choice_modes.load_cases",
        lambda path: [{"question": "哪些字段有缺失值？", "expected_tool": "missing_value_analysis"}],
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


def test_compare_report_contains_required_sections(monkeypatch):
    monkeypatch.setattr(
        "scripts.compare_tool_choice_modes.load_cases",
        lambda path: [{"question": "生成报告", "expected_tool": "generate_report"}],
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
    assert report["total_cases"] == 1


def test_compare_results_counts_correct_wrong_and_differences():
    rule_result = _evaluation_result(
        "rule",
        [
            _case_result("case_001", "missing_value_analysis", "missing_value_analysis", True),
            _case_result("case_002", "generate_report", "numeric_summary", False),
            _case_result("case_003", "numeric_summary", "numeric_summary", True),
            _case_result("case_004", "answer_data_question", "generate_report", False),
        ],
    )
    llm_result = _evaluation_result(
        "llm",
        [
            _case_result("case_001", "missing_value_analysis", "missing_value_analysis", True),
            _case_result("case_002", "generate_report", "answer_data_question", False),
            _case_result("case_003", "numeric_summary", "answer_data_question", False),
            _case_result("case_004", "answer_data_question", "answer_data_question", True),
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
    assert comparison["different_actual_tool"][0]["rule_actual_tool"] == "numeric_summary"


def test_run_llm_uses_mocked_llm_result_without_real_api(monkeypatch):
    modes = []

    monkeypatch.setattr(
        "scripts.compare_tool_choice_modes.load_cases",
        lambda path: [{"question": "数值字段平均值", "expected_tool": "numeric_summary"}],
    )

    def fake_evaluate_tool_choice(cases, profile, mode="rule"):
        modes.append(mode)
        actual_tool = "numeric_summary" if mode == "rule" else "answer_data_question"
        return _evaluation_result(
            mode,
            [_case_result("case_001", "numeric_summary", actual_tool, mode == "rule")],
        )

    monkeypatch.setattr(
        "scripts.compare_tool_choice_modes.evaluate_tool_choice",
        fake_evaluate_tool_choice,
    )

    report = build_comparison_report("fake_cases.jsonl", run_llm=True)

    assert modes == ["rule", "llm"]
    assert report["llm"]["status"] == "completed"
    assert len(report["comparison"]["rule_correct_llm_wrong"]) == 1


def test_run_llm_failure_is_recorded(monkeypatch):
    monkeypatch.setattr(
        "scripts.compare_tool_choice_modes.load_cases",
        lambda path: [{"question": "生成报告", "expected_tool": "generate_report"}],
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


def test_output_writes_json_file(tmp_path, monkeypatch):
    output_path = tmp_path / "compare_result.json"

    monkeypatch.setattr(
        "scripts.compare_tool_choice_modes.load_cases",
        lambda path: [{"question": "生成报告", "expected_tool": "generate_report"}],
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
    assert data["llm"]["status"] == "skipped"
    assert data["comparison"]["status"] == "skipped"


def test_cli_default_runs(capsys, monkeypatch):
    monkeypatch.setattr(
        "scripts.compare_tool_choice_modes.load_cases",
        lambda path: [{"question": "有哪些字段？", "expected_tool": "answer_data_question"}],
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


def test_cli_verbose_runs(capsys, monkeypatch):
    monkeypatch.setattr(
        "scripts.compare_tool_choice_modes.load_cases",
        lambda path: [{"question": "生成报告", "expected_tool": "generate_report"}],
    )

    def fake_evaluate_tool_choice(cases, profile, mode="rule"):
        actual_tool = "generate_report" if mode == "rule" else "answer_data_question"
        return _evaluation_result(
            mode,
            [_case_result("case_001", "generate_report", actual_tool, mode == "rule")],
        )

    monkeypatch.setattr(
        "scripts.compare_tool_choice_modes.evaluate_tool_choice",
        fake_evaluate_tool_choice,
    )

    report = main(["--run-llm", "--verbose"])
    output = capsys.readouterr().out

    assert report["comparison"]["status"] == "compared"
    assert "Different actual tool cases:" in output
    assert "llm_actual_tool: answer_data_question" in output
