from pathlib import Path

from scripts.evaluate_tool_choice import (
    DEFAULT_CASES_PATH,
    evaluate_tool_choice,
    load_cases,
    sample_profile,
)


def test_load_tool_choice_cases_has_required_fields():
    cases = load_cases(DEFAULT_CASES_PATH)

    assert len(cases) >= 12
    for case in cases:
        assert "question" in case
        assert "expected_tool" in case
        assert case["question"]
        assert case["expected_tool"]


def test_evaluate_tool_choice_returns_summary_fields():
    cases = load_cases(DEFAULT_CASES_PATH)
    result = evaluate_tool_choice(cases, sample_profile())

    assert result["total_cases"] == len(cases)
    assert "correct" in result
    assert "accuracy" in result
    assert "failed_cases" in result
    assert isinstance(result["failed_cases"], list)


def test_evaluate_tool_choice_accuracy_is_between_zero_and_one():
    cases = load_cases(DEFAULT_CASES_PATH)
    result = evaluate_tool_choice(cases, sample_profile())

    assert 0 <= result["accuracy"] <= 1


def test_default_cases_path_exists():
    assert Path(DEFAULT_CASES_PATH).exists()
