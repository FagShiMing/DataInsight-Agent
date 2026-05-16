import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.agent_service import run_agent


DEFAULT_CASES_PATH = PROJECT_ROOT / "eval" / "tool_choice_cases.jsonl"
VALID_MODES = {"rule", "llm"}


def load_cases(path: str | Path = DEFAULT_CASES_PATH) -> list[dict]:
    """读取 JSONL 格式的工具选择评估样例。"""
    cases = []
    with Path(path).open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()
            if not line:
                continue

            try:
                case = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Line {line_number} is not valid JSON: {exc.msg}") from exc

            if not isinstance(case, dict):
                raise ValueError(f"Line {line_number} must be a JSON object")
            if "question" not in case or "expected_tool" not in case:
                raise ValueError(f"Line {line_number} missing question or expected_tool")
            if not case["question"] or not case["expected_tool"]:
                raise ValueError(f"Line {line_number} question and expected_tool cannot be empty")
            cases.append(case)

    return cases


def sample_profile() -> dict:
    """构造固定画像，避免评估依赖真实上传流程或外部服务。"""
    return {
        "shape": {"rows": 5, "columns": 5},
        "columns": ["date", "product", "region", "sales", "profit"],
        "dtypes": {
            "date": "object",
            "product": "object",
            "region": "object",
            "sales": "float64",
            "profit": "int64",
        },
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
            "sales": {
                "count": 4,
                "mean": 1650.0,
                "min": 1200.0,
                "max": 2100.0,
                "median": 1650.0,
                "std": 387.2983346207417,
            },
            "profit": {
                "count": 5,
                "mean": 450.0,
                "min": 300.0,
                "max": 620.0,
                "median": 450.0,
                "std": 124.89995996796796,
            },
        },
        "categorical_summary": {
            "product": {"unique_count": 3, "top_values": {"A": 2, "B": 2, "C": 1}},
            "region": {"unique_count": 3, "top_values": {"济南": 2, "杭州": 2, "上海": 1}},
        },
        "preview": [],
    }


def _actual_tool_name(agent_response: dict) -> str | None:
    if agent_response.get("tool_name"):
        return agent_response["tool_name"]

    tool_trace = agent_response.get("tool_trace", [])
    if tool_trace:
        return tool_trace[-1].get("tool_name")

    return None


def _case_id(case: dict, index: int) -> str:
    return case.get("id") or f"case_{index:03d}"


def _trace_error(agent_response: dict, mode: str) -> str | None:
    tool_trace = agent_response.get("tool_trace", [])
    if not tool_trace:
        return "Agent response missing tool_trace"

    trace = tool_trace[-1]
    if trace.get("status") != "success":
        return trace.get("error_message") or agent_response.get("answer") or "工具调用失败"

    if mode == "llm" and trace.get("fallback_used"):
        return trace.get("fallback_reason") or "LLM 工具选择失败，已 fallback 到规则版"

    return None


def evaluate_tool_choice(
    cases: list[dict],
    profile: dict,
    mode: str = "rule",
) -> dict:
    """评估 rule 或 llm 模式下的 Agent 工具选择准确率。"""
    if mode not in VALID_MODES:
        raise ValueError("mode must be rule or llm")

    failed_cases = []
    case_results = []
    correct = 0
    use_llm_tool_choice = mode == "llm"

    for index, case in enumerate(cases, start=1):
        expected_tool = case["expected_tool"]
        actual_tool = None
        error = None

        try:
            response = run_agent(
                question=case["question"],
                profile=profile,
                use_llm_tool_choice=use_llm_tool_choice,
            )
            actual_tool = _actual_tool_name(response)
            error = _trace_error(response, mode)
        except Exception as exc:
            error = str(exc)

        is_correct = actual_tool == expected_tool and error is None
        if is_correct:
            correct += 1

        case_result = {
            "id": _case_id(case, index),
            "question": case["question"],
            "expected_tool": expected_tool,
            "actual_tool": actual_tool,
            "correct": is_correct,
            "error": error,
        }
        case_results.append(case_result)

        if not is_correct:
            failed_cases.append(case_result)

    total_cases = len(cases)
    accuracy = correct / total_cases if total_cases else 0.0

    return {
        "mode": mode,
        "total_cases": total_cases,
        "correct": correct,
        "accuracy": round(accuracy, 4),
        "failed_cases": failed_cases,
        "case_results": case_results,
    }


def _print_result(result: dict, verbose: bool = False) -> None:
    print("Tool choice evaluation")
    print(f"mode: {result['mode']}")
    print(f"total_cases: {result['total_cases']}")
    print(f"correct: {result['correct']}")
    print(f"accuracy: {result['accuracy']:.4f}")

    if verbose:
        print()
        print("Case results:")
        for case_result in result["case_results"]:
            print(
                f"- {case_result['id']} "
                f"expected={case_result['expected_tool']} "
                f"actual={case_result['actual_tool']} "
                f"correct={case_result['correct']}"
            )
            if case_result["error"]:
                print(f"  error: {case_result['error']}")

    print()
    print("Failed cases:")
    if not result["failed_cases"]:
        print("- none")
        return

    for failed_case in result["failed_cases"]:
        print(f"- id: {failed_case['id']}")
        print(f"  question: {failed_case['question']}")
        print(f"  expected_tool: {failed_case['expected_tool']}")
        print(f"  actual_tool: {failed_case['actual_tool']}")
        print(f"  error: {failed_case['error']}")


def main(argv: list[str] | None = None) -> dict:
    parser = argparse.ArgumentParser(description="Evaluate DataInsight Agent tool choice.")
    parser.add_argument(
        "--cases",
        default=str(DEFAULT_CASES_PATH),
        help="JSONL evaluation cases path. Default: eval/tool_choice_cases.jsonl",
    )
    parser.add_argument(
        "--mode",
        choices=sorted(VALID_MODES),
        default="rule",
        help="Tool choice mode: rule or llm. Default: rule",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print every case result.",
    )
    parser.add_argument(
        "--output",
        help="Optional JSON output path.",
    )
    args = parser.parse_args(argv)

    cases = load_cases(args.cases)
    result = evaluate_tool_choice(cases, sample_profile(), mode=args.mode)

    _print_result(result, verbose=args.verbose)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    return result


if __name__ == "__main__":
    main()
