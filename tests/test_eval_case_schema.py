import json
from pathlib import Path

from scripts.evaluate_tool_choice import (
    ALLOWED_CATEGORIES,
    evaluate_tool_choice,
    load_cases,
    sample_profile,
)


EVAL_FILES = [
    Path("eval/tool_choice_cases.jsonl"),
    Path("eval/tool_choice_hard_cases.jsonl"),
    Path("eval/tool_choice_regression_cases.jsonl"),
    Path("eval/tool_choice_blind_cases.jsonl"),
]


def _read_jsonl(path):
    cases = []
    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()
            if not line:
                continue
            case = json.loads(line)
            cases.append((line_number, case))
    return cases


def test_eval_jsonl_files_have_required_schema():
    for path in EVAL_FILES:
        cases = _read_jsonl(path)
        assert cases, f"{path} should not be empty"
        for line_number, case in cases:
            assert case.get("question"), f"{path}:{line_number} missing question"
            assert case.get("expected_tool"), f"{path}:{line_number} missing expected_tool"
            assert case.get("category") in ALLOWED_CATEGORIES
            assert case.get("subcategory"), f"{path}:{line_number} missing subcategory"


def test_base_hard_and_regression_cases_load_with_script_validation():
    for path in EVAL_FILES:
        cases = load_cases(path)
        assert len(cases) == len(_read_jsonl(path))


def test_base_hard_and_regression_cases_can_run_rule_evaluation():
    for path in EVAL_FILES:
        cases = load_cases(path)
        result = evaluate_tool_choice(cases, sample_profile(), mode="rule")
        assert result["total_cases"] == len(cases)
        assert "subcategory_metrics" in result
        assert "failed_by_subcategory" in result["failure_analysis"]


def test_regression_cases_keep_rule_accuracy_at_one():
    cases = load_cases("eval/tool_choice_regression_cases.jsonl")
    result = evaluate_tool_choice(cases, sample_profile(), mode="rule")

    assert result["accuracy"] == 1.0
    assert result["failed_cases"] == []


def test_blind_cases_can_run_rule_evaluation():
    cases = load_cases("eval/tool_choice_blind_cases.jsonl")
    result = evaluate_tool_choice(cases, sample_profile(), mode="rule")

    assert result["total_cases"] == 10
    assert "failure_analysis" in result
