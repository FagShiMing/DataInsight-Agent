import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def load_eval_result(path: str | Path) -> dict:
    """读取 evaluate_tool_choice.py 输出的 JSON 结果。"""
    result_path = Path(path)
    try:
        result = json.loads(result_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{result_path} is not valid JSON: {exc.msg}") from exc

    required_fields = {"total_cases", "correct", "accuracy", "case_results"}
    missing_fields = required_fields - set(result)
    if missing_fields:
        missing_text = ", ".join(sorted(missing_fields))
        raise ValueError(f"{result_path} missing required fields: {missing_text}")

    return result


def index_case_results(result: dict) -> dict:
    """按 case id 建立索引，并检查重复 id。"""
    indexed = {}
    for case_result in result["case_results"]:
        case_id = case_result["id"]
        if case_id in indexed:
            raise ValueError(f"Duplicate case id: {case_id}")
        indexed[case_id] = case_result
    return indexed


def _summary(path: str | Path, result: dict) -> dict:
    return {
        "path": str(path),
        "accuracy": result["accuracy"],
        "correct": result["correct"],
        "total_cases": result["total_cases"],
    }


def _category_delta(before: dict, after: dict) -> dict:
    before_metrics = before.get("category_metrics", {})
    after_metrics = after.get("category_metrics", {})
    categories = sorted(set(before_metrics) | set(after_metrics))
    delta = {}

    for category in categories:
        before_metric = before_metrics.get(
            category,
            {"total": 0, "correct": 0, "accuracy": 0.0},
        )
        after_metric = after_metrics.get(
            category,
            {"total": 0, "correct": 0, "accuracy": 0.0},
        )
        delta[category] = {
            "before_total": before_metric["total"],
            "after_total": after_metric["total"],
            "before_correct": before_metric["correct"],
            "after_correct": after_metric["correct"],
            "before_accuracy": before_metric["accuracy"],
            "after_accuracy": after_metric["accuracy"],
            "delta": round(after_metric["accuracy"] - before_metric["accuracy"], 4),
        }

    return delta


def _case_delta(before_case: dict, after_case: dict) -> dict:
    return {
        "id": before_case["id"],
        "question": before_case["question"],
        "category": before_case["category"],
        "expected_tool": before_case["expected_tool"],
        "before_actual_tool": before_case.get("actual_tool"),
        "after_actual_tool": after_case.get("actual_tool"),
    }


def compare_eval_results(
    before: dict,
    after: dict,
    before_path: str | Path,
    after_path: str | Path,
) -> dict:
    """比较两个 evaluate_tool_choice.py JSON 结果。"""
    before_cases = index_case_results(before)
    after_cases = index_case_results(after)

    before_ids = set(before_cases)
    after_ids = set(after_cases)
    if before_ids != after_ids:
        missing_in_after = sorted(before_ids - after_ids)
        missing_in_before = sorted(after_ids - before_ids)
        raise ValueError(
            "before and after case ids do not match. "
            f"missing_in_after={missing_in_after}, "
            f"missing_in_before={missing_in_before}"
        )

    improved_cases = []
    regressed_cases = []
    for case_id in sorted(before_cases):
        before_case = before_cases[case_id]
        after_case = after_cases[case_id]
        if before_case["correct"] is False and after_case["correct"] is True:
            improved_cases.append(_case_delta(before_case, after_case))
        elif before_case["correct"] is True and after_case["correct"] is False:
            regressed_cases.append(_case_delta(before_case, after_case))

    return {
        "before": _summary(before_path, before),
        "after": _summary(after_path, after),
        "delta": {
            "accuracy": round(after["accuracy"] - before["accuracy"], 4),
            "correct": after["correct"] - before["correct"],
        },
        "category_delta": _category_delta(before, after),
        "improved_cases": improved_cases,
        "regressed_cases": regressed_cases,
    }


def _print_summary(report: dict, verbose: bool = False) -> None:
    print("Evaluation version comparison")
    print(f"before: {report['before']['path']}")
    print(
        f"  correct: {report['before']['correct']}/"
        f"{report['before']['total_cases']}"
    )
    print(f"  accuracy: {report['before']['accuracy']:.4f}")
    print(f"after: {report['after']['path']}")
    print(
        f"  correct: {report['after']['correct']}/"
        f"{report['after']['total_cases']}"
    )
    print(f"  accuracy: {report['after']['accuracy']:.4f}")
    print("delta:")
    print(f"  correct: {report['delta']['correct']}")
    print(f"  accuracy: {report['delta']['accuracy']:.4f}")

    print()
    print("Category delta:")
    for category, metric in report["category_delta"].items():
        print(
            f"- {category}: "
            f"{metric['before_accuracy']:.4f} -> "
            f"{metric['after_accuracy']:.4f} "
            f"(delta={metric['delta']:.4f})"
        )

    print()
    print(f"improved_cases: {len(report['improved_cases'])}")
    print(f"regressed_cases: {len(report['regressed_cases'])}")

    if verbose:
        print()
        print("Improved cases:")
        if not report["improved_cases"]:
            print("- none")
        for case in report["improved_cases"]:
            print(f"- id: {case['id']}")
            print(f"  question: {case['question']}")
            print(f"  category: {case['category']}")
            print(f"  expected_tool: {case['expected_tool']}")
            print(f"  before_actual_tool: {case['before_actual_tool']}")
            print(f"  after_actual_tool: {case['after_actual_tool']}")

        print()
        print("Regressed cases:")
        if not report["regressed_cases"]:
            print("- none")
        for case in report["regressed_cases"]:
            print(f"- id: {case['id']}")
            print(f"  question: {case['question']}")
            print(f"  category: {case['category']}")
            print(f"  expected_tool: {case['expected_tool']}")
            print(f"  before_actual_tool: {case['before_actual_tool']}")
            print(f"  after_actual_tool: {case['after_actual_tool']}")


def main(argv: list[str] | None = None) -> dict:
    parser = argparse.ArgumentParser(description="Compare two tool choice eval results.")
    parser.add_argument("--before", required=True, help="Before JSON result path.")
    parser.add_argument("--after", required=True, help="After JSON result path.")
    parser.add_argument("--output", help="Optional JSON output path.")
    parser.add_argument("--verbose", action="store_true", help="Print changed cases.")
    args = parser.parse_args(argv)

    before = load_eval_result(args.before)
    after = load_eval_result(args.after)
    report = compare_eval_results(before, after, args.before, args.after)
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
