import json
from datetime import datetime, timezone
from typing import Any

from app.services.tools import call_tool, get_tool


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _short_text(value: Any, limit: int = 120) -> str:
    text = str(value)
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def _safe_arguments(arguments: dict) -> dict:
    """工具轨迹需要可读，profile 这种大对象只保留摘要，避免接口返回过长。"""
    safe = {}
    for key, value in arguments.items():
        if key == "profile" and isinstance(value, dict):
            shape = value.get("shape", {})
            columns = value.get("columns", [])
            if not isinstance(columns, list):
                columns = value.get("column_names", [])
            safe[key] = {
                "shape": shape or {
                    "rows": value.get("rows", 0),
                    "columns": value.get("columns", 0),
                },
                "columns": columns,
            }
        else:
            safe[key] = value
    return safe


def build_trace(
    tool_name: str,
    arguments: dict,
    status: str,
    result: Any | None = None,
    error_message: str | None = None,
) -> dict:
    trace = {
        "tool_name": tool_name,
        "arguments": _safe_arguments(arguments),
        "status": status,
        "timestamp": _now(),
    }
    if status == "success":
        trace["result_summary"] = _short_text(
            result.get("summary", result) if isinstance(result, dict) else result
        )
    else:
        trace["error_message"] = error_message or "工具调用失败"
    return trace


def parse_llm_tool_choice(raw_text: str) -> dict:
    """解析 LLM 输出的工具选择 JSON；失败时抛出清晰错误，方便接口统一处理。"""
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError("LLM 未返回合法 JSON。") from exc

    if not isinstance(data, dict):
        raise ValueError("LLM 工具选择结果必须是 JSON 对象。")

    tool_name = data.get("tool_name")
    arguments = data.get("arguments", {})
    if not tool_name:
        raise ValueError("LLM 工具选择结果缺少 tool_name。")
    if not isinstance(arguments, dict):
        raise ValueError("LLM 工具选择结果中的 arguments 必须是对象。")

    return {"tool_name": tool_name, "arguments": arguments}


def choose_tool_by_rules(question: str) -> dict:
    """MVP 先使用规则选工具，保证离线环境也能稳定测试和演示。"""
    question = question.strip()
    if any(keyword in question for keyword in ["报告", "markdown", "Markdown"]):
        return {"tool_name": "generate_report", "arguments": {}}
    if any(keyword in question for keyword in ["缺失", "空值", "null", "NULL"]):
        return {"tool_name": "missing_value_analysis", "arguments": {}}
    if any(keyword in question for keyword in ["数值", "平均", "最大", "最小", "中位", "标准差", "摘要"]):
        return {"tool_name": "numeric_summary", "arguments": {}}
    return {
        "tool_name": "answer_data_question",
        "arguments": {"question": question},
    }


def run_agent(
    question: str,
    profile: dict | None = None,
    llm_tool_choice_json: str | None = None,
) -> dict:
    """执行一次轻量 Agent 调用：选择工具、补齐参数、调用工具、记录轨迹。"""
    if not question or not question.strip():
        return {
            "answer": "问题不能为空。",
            "tool_trace": [
                build_trace(
                    tool_name="unknown",
                    arguments={},
                    status="failed",
                    error_message="question 参数不能为空。",
                )
            ],
        }

    try:
        tool_choice = (
            parse_llm_tool_choice(llm_tool_choice_json)
            if llm_tool_choice_json
            else choose_tool_by_rules(question)
        )
    except ValueError as exc:
        return {
            "answer": str(exc),
            "tool_trace": [
                build_trace(
                    tool_name="unknown",
                    arguments={"raw_text": llm_tool_choice_json},
                    status="failed",
                    error_message=str(exc),
                )
            ],
        }

    tool_name = tool_choice["tool_name"]
    arguments = dict(tool_choice.get("arguments", {}))

    tool = get_tool(tool_name)
    if tool is None:
        error_message = f"工具不存在: {tool_name}"
        return {
            "answer": error_message,
            "tool_trace": [
                build_trace(tool_name, arguments, "failed", error_message=error_message)
            ],
        }

    if tool_name in {
        "missing_value_analysis",
        "numeric_summary",
        "answer_data_question",
        "generate_report",
    }:
        arguments.setdefault("profile", profile)
    if tool_name == "answer_data_question":
        arguments.setdefault("question", question)

    try:
        result = call_tool(tool_name, arguments)
    except TypeError as exc:
        error_message = f"工具参数错误: {exc}"
        return {
            "answer": error_message,
            "tool_trace": [
                build_trace(tool_name, arguments, "failed", error_message=error_message)
            ],
        }
    except Exception as exc:
        error_message = f"工具执行失败: {exc}"
        return {
            "answer": error_message,
            "tool_trace": [
                build_trace(tool_name, arguments, "failed", error_message=error_message)
            ],
        }

    answer = result.get("answer") or result.get("summary") or "工具调用完成。"
    return {
        "answer": answer,
        "tool_name": tool_name,
        "result": result,
        "tool_trace": [
            build_trace(tool_name, arguments, "success", result=result)
        ],
    }
