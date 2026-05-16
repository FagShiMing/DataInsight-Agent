import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.evaluate_tool_choice import (
    DEFAULT_CASES_PATH,
    build_category_metrics,
    evaluate_tool_choice,
    load_cases,
    sample_profile,
)


def _empty_llm_result(status: str = "skipped", error: str | None = None) -> dict:
    result = {
        "mode": "llm",
        "status": status,
        "correct": None,
        "accuracy": None,
        "category_metrics": {},
        "failure_analysis": {
            "total_failed": 0,
            "failed_by_category": {},
            "failed_by_expected_tool": {},
        },
        "failed_cases": [],
        "case_results": [],
    }
    if error:
        result["error"] = error
    return result


def _comparison_case(rule_case: dict, llm_case: dict) -> dict:
    return {
        "id": rule_case["id"],
        "question": rule_case["question"],
        "category": rule_case["category"],
        "expected_tool": rule_case["expected_tool"],
        "rule_actual_tool": rule_case.get("actual_tool"),
        "llm_actual_tool": llm_case.get("actual_tool"),
        "rule_correct": rule_case.get("correct"),
        "llm_correct": llm_case.get("correct"),
        "rule_error": rule_case.get("error"),
        "llm_error": llm_case.get("error"),
    }


def _metrics_from_result(result: dict) -> dict:
    if result.get("category_metrics"):
        return result["category_metrics"]
    return build_category_metrics(result.get("case_results", []))


def compare_results(rule_result: dict, llm_result: dict) -> dict:
    """比较 rule 和 llm 两组逐 case 评估结果。"""
    if llm_result.get("status") in {"skipped", "failed"}:
        return {
            "status": llm_result["status"],
            "both_correct": 0,
            "both_wrong": 0,
            "rule_correct_llm_wrong": [],
            "rule_wrong_llm_correct": [],
            "different_actual_tool": [],
        }

    llm_cases_by_id = {case["id"]: case for case in llm_result["case_results"]}
    both_correct = 0
    both_wrong = 0
    rule_correct_llm_wrong = []
    rule_wrong_llm_correct = []
    different_actual_tool = []

    for rule_case in rule_result["case_results"]:
        llm_case = llm_cases_by_id.get(rule_case["id"])
        if llm_case is None:
            continue

        comparison_case = _comparison_case(rule_case, llm_case)
        rule_correct = bool(rule_case.get("correct"))
        llm_correct = bool(llm_case.get("correct"))

        if rule_correct and llm_correct:
            both_correct += 1
        elif not rule_correct and not llm_correct:
            both_wrong += 1
        elif rule_correct and not llm_correct:
            rule_correct_llm_wrong.append(comparison_case)
        elif not rule_correct and llm_correct:
            rule_wrong_llm_correct.append(comparison_case)

        if rule_case.get("actual_tool") != llm_case.get("actual_tool"):
            different_actual_tool.append(comparison_case)

    return {
        "status": "compared",
        "both_correct": both_correct,
        "both_wrong": both_wrong,
        "rule_correct_llm_wrong": rule_correct_llm_wrong,
        "rule_wrong_llm_correct": rule_wrong_llm_correct,
        "different_actual_tool": different_actual_tool,
    }


def build_category_comparison(rule_result: dict, llm_result: dict) -> dict:
    """按 category 对比 rule 和 llm 的工具选择准确率。"""
    if llm_result.get("status") == "skipped":
        return {"status": "skipped", "reason": "llm mode was not run"}
    if llm_result.get("status") == "failed":
        return {
            "status": "failed",
            "reason": llm_result.get("error", "llm mode failed"),
        }

    rule_metrics = _metrics_from_result(rule_result)
    llm_metrics = _metrics_from_result(llm_result)
    categories = sorted(set(rule_metrics) | set(llm_metrics))
    comparison = {"status": "compared"}

    for category in categories:
        rule_metric = rule_metrics.get(category, {"total": 0, "correct": 0, "accuracy": 0.0})
        llm_metric = llm_metrics.get(category, {"total": 0, "correct": 0, "accuracy": 0.0})
        comparison[category] = {
            "total": rule_metric["total"],
            "rule_correct": rule_metric["correct"],
            "rule_accuracy": rule_metric["accuracy"],
            "llm_correct": llm_metric["correct"],
            "llm_accuracy": llm_metric["accuracy"],
        }

    return comparison


def build_comparison_report(cases_path: str | Path, run_llm: bool = False) -> dict:
    """读取同一批 cases，分别生成 rule 和可选 llm 的工具选择对比报告。"""
    cases = load_cases(cases_path)
    profile = sample_profile()

    rule_result = evaluate_tool_choice(cases, profile, mode="rule")

    if not run_llm:
        llm_result = _empty_llm_result(status="skipped")
    else:
        try:
            llm_result = evaluate_tool_choice(cases, profile, mode="llm")
            llm_result["status"] = "completed"
        except Exception as exc:
            llm_result = _empty_llm_result(status="failed", error=str(exc))

    return {
        "cases_path": str(cases_path),
        "total_cases": len(cases),
        "rule": rule_result,
        "llm": llm_result,
        "comparison": compare_results(rule_result, llm_result),
        "category_comparison": build_category_comparison(rule_result, llm_result),
    }


def _print_summary(report: dict, verbose: bool = False) -> None:
    rule_result = report["rule"]
    llm_result = report["llm"]
    comparison = report["comparison"]
    category_comparison = report["category_comparison"]

    print("Tool choice mode comparison")
    print(f"cases_path: {report['cases_path']}")
    print(f"total_cases: {report['total_cases']}")
    print()
    print("Rule mode")
    print(f"correct: {rule_result['correct']}")
    print(f"accuracy: {rule_result['accuracy']:.4f}")
    print()
    print("LLM mode")
    print(f"status: {llm_result['status']}")
    if llm_result["status"] == "completed":
        print(f"correct: {llm_result['correct']}")
        print(f"accuracy: {llm_result['accuracy']:.4f}")
    elif llm_result.get("error"):
        print(f"error: {llm_result['error']}")

    print()
    print("Comparison")
    print(f"status: {comparison['status']}")
    print(f"both_correct: {comparison['both_correct']}")
    print(f"both_wrong: {comparison['both_wrong']}")
    print(f"rule_correct_llm_wrong: {len(comparison['rule_correct_llm_wrong'])}")
    print(f"rule_wrong_llm_correct: {len(comparison['rule_wrong_llm_correct'])}")
    print(f"different_actual_tool: {len(comparison['different_actual_tool'])}")

    print()
    print("Category comparison")
    print(f"status: {category_comparison['status']}")
    if category_comparison["status"] != "compared":
        print(f"reason: {category_comparison['reason']}")
    else:
        for category, metric in category_comparison.items():
            if category == "status":
                continue
            print(
                f"- {category}: total={metric['total']} "
                f"rule_accuracy={metric['rule_accuracy']:.4f} "
                f"llm_accuracy={metric['llm_accuracy']:.4f}"
            )

    if verbose and comparison["status"] == "compared":
        print()
        print("Different actual tool cases:")
        if not comparison["different_actual_tool"]:
            print("- none")
        for case in comparison["different_actual_tool"]:
            print(f"- id: {case['id']}")
            print(f"  question: {case['question']}")
            print(f"  category: {case['category']}")
            print(f"  expected_tool: {case['expected_tool']}")
            print(f"  rule_actual_tool: {case['rule_actual_tool']}")
            print(f"  llm_actual_tool: {case['llm_actual_tool']}")


def main(argv: list[str] | None = None) -> dict:
    parser = argparse.ArgumentParser(description="Compare DataInsight Agent tool choice modes.")
    parser.add_argument(
        "--cases",
        default=str(DEFAULT_CASES_PATH),
        help="JSONL evaluation cases path. Default: eval/tool_choice_cases.jsonl",
    )
    parser.add_argument(
        "--run-llm",
        action="store_true",
        help="Also run llm mode. Default: false, so no real LLM API is called.",
    )
    parser.add_argument(
        "--output",
        help="Optional JSON output path.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print comparison details.",
    )
    args = parser.parse_args(argv)

    report = build_comparison_report(cases_path=args.cases, run_llm=args.run_llm)
    _print_summary(report, verbose=args.verbose)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    return report


if __name__ == "__main__":
    main()
