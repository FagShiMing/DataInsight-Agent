import json
import re
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


def _extract_csv_path(question: str) -> str | None:
    match = re.search(r"[\w./\\-]+\.csv", question, flags=re.IGNORECASE)
    if match:
        return match.group(0)
    return None


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


REPORT_NEGATION_KEYWORDS = [
    "不要写报告",
    "先别写报告",
    "不用生成报告",
    "不要生成报告",
    "暂时不要报告",
    "不要报告",
    "不要汇报材料",
    "不是要报告",
    "不是要正式报告",
]

REPORT_KEYWORDS = [
    "报告",
    "markdown",
    "Markdown",
    "发给老板",
    "给老板看",
    "汇报",
    "汇报稿",
    "汇报材料",
    "文档",
    "结论报告",
    "分析总结",
    "数据分析总结",
    "复盘",
    "周报",
    "生成一份",
    "分析材料",
    "发出去",
    "正式分析",
    "正式点的分析结论",
    "交付材料",
    "组织成报告",
    "输出成文档",
]

MISSING_KEYWORDS = [
    "缺失",
    "空值",
    "null",
    "NULL",
    "NaN",
    "nan",
    "没填",
    "没有填",
    "没填全",
    "未填",
    "不完整",
    "完整性",
    "完整率",
    "空白",
    "空的",
    "补数据",
    "字段质量",
    "缺得多",
    "缺得厉害",
    "缺得严重",
    "数据缺口",
    "漏了很多信息",
]

NUMERIC_KEYWORDS = [
    "数值",
    "数值列",
    "平均",
    "均值",
    "最大",
    "最小",
    "中位",
    "标准差",
    "摘要",
    "销售额",
    "利润",
    "年龄",
    "金额",
    "收入",
    "范围",
    "连续型",
    "统计一下",
    "波动",
    "指标",
    "大概什么水平",
    "大概情况",
    "分布怎么样",
    "整体分布",
    "特别大",
    "特别小",
    "极值",
    "高低水平",
    "量化",
]

STRONG_NUMERIC_KEYWORDS = [
    "数值",
    "数值列",
    "平均",
    "均值",
    "最大",
    "最小",
    "中位",
    "标准差",
    "范围",
    "统计一下",
    "波动",
    "大概什么水平",
    "大概情况",
    "分布怎么样",
    "整体分布",
    "特别大",
    "特别小",
    "极值",
    "高低水平",
    "量化",
]

PROFILE_KEYWORDS = [
    "读取",
    "分析",
    "画像",
    "加载",
    "导入",
    "整体",
    "概览",
    "结构",
    "摸一下",
    "扫一眼",
    "看一眼",
    "大概什么情况",
    "大概是个什么情况",
    "整体情况",
    "表结构",
    "先看一下",
    "初步看看",
    "数据概况",
    "数据概览",
    "整体质量",
    "有哪些列",
    "质量怎么样",
    "这份表的底",
]

BUSINESS_QUESTION_KEYWORDS = [
    "业务问题",
    "业务信号",
    "业务风险",
    "异常趋势",
    "哪个因素",
    "影响结果",
    "值得优先关注",
    "有什么问题",
    "哪里有问题",
    "能说明什么",
    "能看出什么结论",
    "判断一下",
    "展开分析",
]


def has_report_negation(question: str) -> bool:
    """识别“不要报告”类表达，避免报告关键词误触发。"""
    return _contains_any(question, REPORT_NEGATION_KEYWORDS)


def has_report_intent(question: str) -> bool:
    return not has_report_negation(question) and _contains_any(question, REPORT_KEYWORDS)


def has_missing_intent(question: str) -> bool:
    return _contains_any(question, MISSING_KEYWORDS)


def has_numeric_intent(question: str) -> bool:
    return _contains_any(question, NUMERIC_KEYWORDS)


def has_strong_numeric_intent(question: str) -> bool:
    return _contains_any(question, STRONG_NUMERIC_KEYWORDS)


def has_profile_intent(question: str) -> bool:
    return _contains_any(question, PROFILE_KEYWORDS)


def has_business_question_intent(question: str) -> bool:
    return _contains_any(question, BUSINESS_QUESTION_KEYWORDS)


def choose_tool_by_rules(question: str) -> dict:
    """MVP 先使用规则选工具，保证离线环境也能稳定测试和演示。"""
    question = question.strip()
    csv_path = _extract_csv_path(question)
    if csv_path and has_profile_intent(question):
        return {"tool_name": "profile_csv", "arguments": {"file_path": csv_path}}

    if has_missing_intent(question):
        return {"tool_name": "missing_value_analysis", "arguments": {}}

    if has_business_question_intent(question) and not has_strong_numeric_intent(question):
        return {
            "tool_name": "answer_data_question",
            "arguments": {"question": question},
        }

    if has_numeric_intent(question):
        return {"tool_name": "numeric_summary", "arguments": {}}

    if has_report_intent(question):
        return {"tool_name": "generate_report", "arguments": {}}

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
