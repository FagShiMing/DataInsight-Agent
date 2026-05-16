import json

from scripts.compare_eval_versions import (
    compare_eval_results,
    load_eval_result,
    main,
)


def _case_result(case_id, expected, before_or_after_actual, correct, category):
    return {
        "id": case_id,
        "question": f"question {case_id}",
        "category": category,
        "subcategory": "regression_core",
        "expected_tool": expected,
        "actual_tool": before_or_after_actual,
        "correct": correct,
        "error": None,
    }


def _result(case_results):
    correct = sum(1 for case in case_results if case["correct"])
    total = len(case_results)
    category_metrics = {}
    for case in case_results:
        category = case["category"]
        category_metrics.setdefault(category, {"total": 0, "correct": 0, "accuracy": 0.0})
        category_metrics[category]["total"] += 1
        if case["correct"]:
            category_metrics[category]["correct"] += 1
    for metric in category_metrics.values():
        metric["accuracy"] = round(metric["correct"] / metric["total"], 4)

    return {
        "mode": "rule",
        "total_cases": total,
        "correct": correct,
        "accuracy": round(correct / total, 4),
        "category_metrics": category_metrics,
        "failure_analysis": {},
        "failed_cases": [case for case in case_results if not case["correct"]],
        "case_results": case_results,
    }


def test_load_eval_result_reads_json_file(tmp_path):
    path = tmp_path / "result.json"
    path.write_text(
        json.dumps(
            _result([
                _case_result(
                    "case_001",
                    "generate_report",
                    "generate_report",
                    True,
                    "report_generation",
                )
            ]),
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = load_eval_result(path)

    assert result["total_cases"] == 1
    assert result["case_results"][0]["id"] == "case_001"


def test_compare_eval_results_calculates_delta_and_changed_cases():
    before = _result(
        [
            _case_result(
                "case_001",
                "generate_report",
                "answer_data_question",
                False,
                "report_generation",
            ),
            _case_result(
                "case_002",
                "numeric_summary",
                "numeric_summary",
                True,
                "numeric_summary",
            ),
            _case_result(
                "case_003",
                "missing_value_analysis",
                "missing_value_analysis",
                True,
                "missing_value",
            ),
        ]
    )
    after = _result(
        [
            _case_result(
                "case_001",
                "generate_report",
                "generate_report",
                True,
                "report_generation",
            ),
            _case_result(
                "case_002",
                "numeric_summary",
                "answer_data_question",
                False,
                "numeric_summary",
            ),
            _case_result(
                "case_003",
                "missing_value_analysis",
                "missing_value_analysis",
                True,
                "missing_value",
            ),
        ]
    )

    report = compare_eval_results(before, after, "before.json", "after.json")

    assert report["delta"]["correct"] == 0
    assert report["delta"]["accuracy"] == 0.0
    assert report["category_delta"]["report_generation"]["delta"] == 1.0
    assert report["category_delta"]["numeric_summary"]["delta"] == -1.0
    assert len(report["improved_cases"]) == 1
    assert report["improved_cases"][0]["id"] == "case_001"
    assert len(report["regressed_cases"]) == 1
    assert report["regressed_cases"][0]["id"] == "case_002"


def test_compare_eval_results_rejects_mismatched_case_ids():
    before = _result(
        [_case_result("case_001", "generate_report", "generate_report", True, "report_generation")]
    )
    after = _result(
        [_case_result("case_002", "generate_report", "generate_report", True, "report_generation")]
    )

    try:
        compare_eval_results(before, after, "before.json", "after.json")
    except ValueError as exc:
        assert "case ids do not match" in str(exc)
        assert "missing_in_after=['case_001']" in str(exc)
    else:
        raise AssertionError("case id 不一致时应该抛出 ValueError")


def test_output_writes_json_file(tmp_path, capsys):
    before_path = tmp_path / "before.json"
    after_path = tmp_path / "after.json"
    output_path = tmp_path / "compare.json"

    before_path.write_text(
        json.dumps(
            _result([
                _case_result(
                    "case_001",
                    "generate_report",
                    "answer_data_question",
                    False,
                    "report_generation",
                )
            ]),
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    after_path.write_text(
        json.dumps(
            _result([
                _case_result(
                    "case_001",
                    "generate_report",
                    "generate_report",
                    True,
                    "report_generation",
                )
            ]),
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    report = main([
        "--before",
        str(before_path),
        "--after",
        str(after_path),
        "--output",
        str(output_path),
    ])
    output = capsys.readouterr().out

    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert report["delta"]["correct"] == 1
    assert data["improved_cases"][0]["id"] == "case_001"
    assert "Evaluation version comparison" in output


def test_cli_verbose_runs(tmp_path, capsys):
    before_path = tmp_path / "before.json"
    after_path = tmp_path / "after.json"

    before_path.write_text(
        json.dumps(
            _result([
                _case_result(
                    "case_001",
                    "numeric_summary",
                    "answer_data_question",
                    False,
                    "numeric_summary",
                )
            ]),
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    after_path.write_text(
        json.dumps(
            _result([
                _case_result(
                    "case_001",
                    "numeric_summary",
                    "numeric_summary",
                    True,
                    "numeric_summary",
                )
            ]),
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    report = main(["--before", str(before_path), "--after", str(after_path), "--verbose"])
    output = capsys.readouterr().out

    assert len(report["improved_cases"]) == 1
    assert "Improved cases:" in output
    assert "after_actual_tool: numeric_summary" in output
