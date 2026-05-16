from dataclasses import dataclass
from typing import Any, Callable

from app.services.data_profile import analyze_csv
from app.services.report_service import generate_markdown_report


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict
    callable: Callable[..., Any]


def _shape(profile: dict) -> dict:
    shape = profile.get("shape", {})
    columns = shape.get("columns", profile.get("columns", 0))
    if isinstance(columns, list):
        columns = len(columns)
    return {
        "rows": shape.get("rows", profile.get("rows", 0)),
        "columns": columns,
    }


def _column_names(profile: dict) -> list[str]:
    columns = profile.get("columns", [])
    if isinstance(columns, list):
        return columns
    return profile.get("column_names", [])


def _require_profile(profile: dict | None) -> dict:
    if not profile:
        raise ValueError("profile 参数不能为空，请先上传或传入 CSV 数据画像。")
    return profile


def profile_csv(file_path: str) -> dict:
    """工具：读取本地 CSV 文件并生成基础画像。"""
    return analyze_csv(file_path)


def missing_value_analysis(profile: dict) -> dict:
    """工具：从画像结果中提取缺失值信息。"""
    profile = _require_profile(profile)
    missing_values = profile.get("missing_values", {})
    missing_rate = profile.get("missing_rate", {})
    total_missing = sum(int(count) for count in missing_values.values())
    columns_with_missing = [
        {
            "column": column,
            "missing_count": int(count),
            "missing_rate": missing_rate.get(column, 0),
        }
        for column, count in missing_values.items()
        if int(count) > 0
    ]

    if columns_with_missing:
        summary = f"共有 {len(columns_with_missing)} 个字段存在缺失值，缺失单元格总数为 {total_missing}。"
    else:
        summary = "未发现缺失值。"

    return {
        "summary": summary,
        "total_missing": total_missing,
        "columns_with_missing": columns_with_missing,
        "missing_values": missing_values,
        "missing_rate": missing_rate,
    }


def numeric_summary(profile: dict) -> dict:
    """工具：返回数值列统计摘要。"""
    profile = _require_profile(profile)
    summary = profile.get("numeric_summary", {})
    if not summary:
        return {
            "summary": "未识别到数值列，无法生成数值摘要。",
            "numeric_summary": {},
        }

    return {
        "summary": f"识别到 {len(summary)} 个数值列，已生成 count、mean、min、max、median、std 摘要。",
        "numeric_summary": summary,
    }


def answer_data_question(profile: dict, question: str) -> dict:
    """工具：用规则回答常见数据问题，保证没有 LLM 时也能稳定演示。"""
    profile = _require_profile(profile)
    question = question.strip()
    if not question:
        raise ValueError("question 参数不能为空。")

    if any(keyword in question for keyword in ["缺失", "空值", "null", "NULL"]):
        result = missing_value_analysis(profile)
        return {
            "answer": result["summary"],
            "source": "missing_value_analysis",
            "details": result,
        }

    if any(keyword in question for keyword in ["数值", "平均", "最大", "最小", "中位", "标准差", "摘要"]):
        result = numeric_summary(profile)
        return {
            "answer": result["summary"],
            "source": "numeric_summary",
            "details": result,
        }

    shape = _shape(profile)
    columns = _column_names(profile)
    return {
        "answer": (
            f"这份数据共有 {shape['rows']} 行、{shape['columns']} 列。"
            f"字段包括：{', '.join(columns) if columns else '暂无字段'}。"
        ),
        "source": "profile",
        "details": {
            "shape": shape,
            "columns": columns,
            "dtypes": profile.get("dtypes", {}),
        },
    }


def generate_report(
    profile: dict,
    insights: str | None = None,
    tool_trace: list[dict] | None = None,
) -> dict:
    """工具：生成 Markdown 数据分析报告。"""
    profile = _require_profile(profile)
    report = generate_markdown_report(
        profile=profile,
        insights=insights,
        tool_trace=tool_trace,
    )
    return {
        "summary": "Markdown 数据分析报告已生成。",
        "markdown": report,
    }


TOOL_REGISTRY = {
    "profile_csv": Tool(
        name="profile_csv",
        description="读取本地 CSV 文件并生成基础数据画像。",
        parameters={"file_path": "CSV 文件路径"},
        callable=profile_csv,
    ),
    "missing_value_analysis": Tool(
        name="missing_value_analysis",
        description="分析数据画像中的缺失值数量和缺失率。",
        parameters={"profile": "CSV 数据画像结果"},
        callable=missing_value_analysis,
    ),
    "numeric_summary": Tool(
        name="numeric_summary",
        description="生成数值列的基础统计摘要。",
        parameters={"profile": "CSV 数据画像结果"},
        callable=numeric_summary,
    ),
    "answer_data_question": Tool(
        name="answer_data_question",
        description="回答用户关于当前 CSV 数据的常见问题。",
        parameters={"profile": "CSV 数据画像结果", "question": "用户问题"},
        callable=answer_data_question,
    ),
    "generate_report": Tool(
        name="generate_report",
        description="基于数据画像、分析建议和工具轨迹生成 Markdown 报告。",
        parameters={
            "profile": "CSV 数据画像结果",
            "insights": "可选分析建议",
            "tool_trace": "可选工具调用轨迹",
        },
        callable=generate_report,
    ),
}


def get_tool(tool_name: str) -> Tool | None:
    return TOOL_REGISTRY.get(tool_name)


def call_tool(tool_name: str, arguments: dict) -> Any:
    tool = get_tool(tool_name)
    if tool is None:
        raise ValueError(f"工具不存在: {tool_name}")
    return tool.callable(**arguments)
