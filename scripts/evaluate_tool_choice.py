import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.agent_service import run_agent


DEFAULT_CASES_PATH = PROJECT_ROOT / "eval" / "tool_choice_cases.jsonl"


def load_cases(path: str | Path = DEFAULT_CASES_PATH) -> list[dict]:
    """读取 JSONL 格式的工具选择评估样例。"""
    cases = []
    with Path(path).open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()
            if not line:
                continue

            case = json.loads(line)
            if "question" not in case or "expected_tool" not in case:
                raise ValueError(f"Line {line_number} missing question or expected_tool")
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


def evaluate_tool_choice(cases: list[dict], profile: dict) -> dict:
    """评估规则版 Agent 工具选择准确率。"""
    failed_cases = []
    correct = 0

    for case in cases:
        response = run_agent(
            question=case["question"],
            profile=profile,
            use_llm_tool_choice=False,
        )
        actual_tool = _actual_tool_name(response)
        expected_tool = case["expected_tool"]

        if actual_tool == expected_tool:
            correct += 1
        else:
            failed_cases.append(
                {
                    "question": case["question"],
                    "expected_tool": expected_tool,
                    "actual_tool": actual_tool,
                }
            )

    total_cases = len(cases)
    accuracy = correct / total_cases if total_cases else 0.0

    return {
        "total_cases": total_cases,
        "correct": correct,
        "accuracy": round(accuracy, 4),
        "failed_cases": failed_cases,
    }


def main() -> None:
    cases = load_cases()
    result = evaluate_tool_choice(cases, sample_profile())

    print("Tool choice evaluation")
    print(f"total_cases: {result['total_cases']}")
    print(f"correct: {result['correct']}")
    print(f"accuracy: {result['accuracy']:.4f}")
    print()
    print("Failed cases:")
    if not result["failed_cases"]:
        print("- none")
        return

    for failed_case in result["failed_cases"]:
        print(f"- question: {failed_case['question']}")
        print(f"  expected_tool: {failed_case['expected_tool']}")
        print(f"  actual_tool: {failed_case['actual_tool']}")


if __name__ == "__main__":
    main()
