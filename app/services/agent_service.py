import json
from datetime import datetime, timezone
from typing import Any

from app.services.tools import TOOL_REGISTRY, call_tool, get_tool


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
    tool_choice_source: str = "rule",
    fallback_used: bool = False,
    fallback_reason: str | None = None,
    llm_choice_raw: str | None = None,
) -> dict:
    trace = {
        "tool_name": tool_name,
        "arguments": _safe_arguments(arguments),
        "status": status,
        "timestamp": _now(),
        "tool_choice_source": tool_choice_source,
        "fallback_used": fallback_used,
        "fallback_reason": fallback_reason,
        "llm_choice_raw": llm_choice_raw,
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


def _profile_summary(profile: dict | None) -> dict:
    """给 LLM 的画像摘要要短一些，避免把 preview 等大字段都塞进提示词。"""
    if not profile:
        return {}

    return {
        "shape": profile.get("shape"),
        "columns": profile.get("columns", profile.get("column_names")),
        "dtypes": profile.get("dtypes"),
        "missing_values": profile.get("missing_values"),
        "missing_rate": profile.get("missing_rate"),
        "numeric_summary": profile.get("numeric_summary"),
        "categorical_summary": profile.get("categorical_summary"),
    }


def _tools_schema() -> dict:
    """把工具注册表转换成适合 LLM 阅读的工具说明。"""
    return {
        name: {
            "description": tool.description,
            "parameters": tool.parameters,
        }
        for name, tool in TOOL_REGISTRY.items()
    }


def _complete_tool_arguments(
    tool_name: str,
    arguments: dict,
    question: str,
    profile: dict | None,
) -> dict:
    completed_arguments = dict(arguments)
    if tool_name in {
        "missing_value_analysis",
        "numeric_summary",
        "answer_data_question",
        "generate_report",
    }:
        completed_arguments.setdefault("profile", profile)
    if tool_name == "answer_data_question":
        completed_arguments.setdefault("question", question)
    return completed_arguments


def _execute_tool_choice(
    tool_choice: dict,
    question: str,
    profile: dict | None,
) -> tuple[str, dict, Any]:
    tool_name = tool_choice["tool_name"]
    arguments = dict(tool_choice.get("arguments", {}))

    tool = get_tool(tool_name)
    if tool is None:
        raise ValueError(f"工具不存在: {tool_name}")

    arguments = _complete_tool_arguments(
        tool_name=tool_name,
        arguments=arguments,
        question=question,
        profile=profile,
    )
    result = call_tool(tool_name, arguments)
    return tool_name, arguments, result


def _choose_tool_with_llm(question: str, profile: dict | None) -> tuple[dict, str | None]:
    from app.services.llm_service import ask_llm_for_tool_choice

    raw_text = ask_llm_for_tool_choice(
        question=question,
        profile_summary=_profile_summary(profile),
        tools_schema=_tools_schema(),
    )
    try:
        tool_choice = parse_llm_tool_choice(raw_text)
    except ValueError as exc:
        exc.llm_choice_raw = raw_text
        raise
    if get_tool(tool_choice["tool_name"]) is None:
        exc = ValueError(f"工具不存在: {tool_choice['tool_name']}")
        exc.llm_choice_raw = raw_text
        raise exc
    return tool_choice, raw_text


def run_agent(
    question: str,
    profile: dict | None = None,
    llm_tool_choice_json: str | None = None,
    use_llm_tool_choice: bool = False,
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

    tool_choice_source = "rule"
    fallback_used = False
    fallback_reason = None
    llm_choice_raw = None

    if use_llm_tool_choice:
        try:
            tool_choice, llm_choice_raw = _choose_tool_with_llm(question, profile)
            tool_choice_source = "llm"
        except Exception as exc:
            llm_choice_raw = getattr(exc, "llm_choice_raw", None)
            tool_choice = choose_tool_by_rules(question)
            fallback_used = True
            fallback_reason = str(exc)
            tool_choice_source = "rule"
    else:
        tool_choice = None

    try:
        if tool_choice is None:
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
                    tool_choice_source="llm" if llm_tool_choice_json else "rule",
                    llm_choice_raw=llm_tool_choice_json,
                )
            ],
        }

    try:
        tool_name, arguments, result = _execute_tool_choice(
            tool_choice=tool_choice,
            question=question,
            profile=profile,
        )
    except TypeError as exc:
        if use_llm_tool_choice and not fallback_used:
            tool_choice = choose_tool_by_rules(question)
            fallback_used = True
            fallback_reason = f"工具参数错误: {exc}"
            tool_choice_source = "rule"
            try:
                tool_name, arguments, result = _execute_tool_choice(
                    tool_choice=tool_choice,
                    question=question,
                    profile=profile,
                )
            except Exception as fallback_exc:
                error_message = f"工具执行失败: {fallback_exc}"
                return {
                    "answer": error_message,
                    "tool_trace": [
                        build_trace(
                            tool_choice["tool_name"],
                            dict(tool_choice.get("arguments", {})),
                            "failed",
                            error_message=error_message,
                            tool_choice_source=tool_choice_source,
                            fallback_used=fallback_used,
                            fallback_reason=fallback_reason,
                            llm_choice_raw=llm_choice_raw,
                        )
                    ],
                }
        else:
            error_message = f"工具参数错误: {exc}"
            return {
                "answer": error_message,
                "tool_trace": [
                    build_trace(
                        tool_choice["tool_name"],
                        dict(tool_choice.get("arguments", {})),
                        "failed",
                        error_message=error_message,
                        tool_choice_source=tool_choice_source,
                        fallback_used=fallback_used,
                        fallback_reason=fallback_reason,
                        llm_choice_raw=llm_choice_raw,
                    )
                ],
            }
    except Exception as exc:
        if use_llm_tool_choice and not fallback_used:
            tool_choice = choose_tool_by_rules(question)
            fallback_used = True
            fallback_reason = str(exc)
            tool_choice_source = "rule"
            try:
                tool_name, arguments, result = _execute_tool_choice(
                    tool_choice=tool_choice,
                    question=question,
                    profile=profile,
                )
            except Exception as fallback_exc:
                error_message = f"工具执行失败: {fallback_exc}"
                return {
                    "answer": error_message,
                    "tool_trace": [
                        build_trace(
                            tool_choice["tool_name"],
                            dict(tool_choice.get("arguments", {})),
                            "failed",
                            error_message=error_message,
                            tool_choice_source=tool_choice_source,
                            fallback_used=fallback_used,
                            fallback_reason=fallback_reason,
                            llm_choice_raw=llm_choice_raw,
                        )
                    ],
                }
        else:
            error_message = f"工具执行失败: {exc}"
            return {
                "answer": error_message,
                "tool_trace": [
                    build_trace(
                        tool_choice["tool_name"],
                        dict(tool_choice.get("arguments", {})),
                        "failed",
                        error_message=error_message,
                        tool_choice_source=tool_choice_source,
                        fallback_used=fallback_used,
                        fallback_reason=fallback_reason,
                        llm_choice_raw=llm_choice_raw,
                    )
                ],
            }

    answer = result.get("answer") or result.get("summary") or "工具调用完成。"
    return {
        "answer": answer,
        "tool_name": tool_name,
        "result": result,
        "tool_trace": [
            build_trace(
                tool_name,
                arguments,
                "success",
                result=result,
                tool_choice_source=tool_choice_source,
                fallback_used=fallback_used,
                fallback_reason=fallback_reason,
                llm_choice_raw=llm_choice_raw,
            )
        ],
    }
