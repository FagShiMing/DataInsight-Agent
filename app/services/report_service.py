def _shape_text(profile: dict) -> str:
    shape = profile.get("shape", {})
    rows = shape.get("rows", profile.get("rows", 0))
    columns = shape.get("columns", profile.get("columns", 0))
    if isinstance(columns, list):
        columns = len(columns)
    return f"{rows} 行，{columns} 列"


def _column_names(profile: dict) -> list[str]:
    columns = profile.get("columns", [])
    if isinstance(columns, list):
        return columns
    return profile.get("column_names", [])


def generate_markdown_report(
    profile: dict,
    insights: str | None = None,
    tool_trace: list[dict] | None = None,
) -> str:
    """把结构化画像转换成 Markdown 报告，方便直接展示或写入简历项目说明。"""
    columns = _column_names(profile)
    missing_values = profile.get("missing_values", {})
    missing_rate = profile.get("missing_rate", {})
    numeric_summary = profile.get("numeric_summary", {})
    categorical_summary = profile.get("categorical_summary", {})

    lines = [
        "# CSV 数据分析报告",
        "",
        "## 数据概览",
        "",
        f"- 数据规模：{_shape_text(profile)}",
        f"- 字段列表：{', '.join(columns) if columns else '暂无字段'}",
        "",
        "## 缺失值分析",
        "",
    ]

    if missing_values:
        for column, count in missing_values.items():
            rate = missing_rate.get(column, 0)
            lines.append(f"- {column}：缺失 {count} 个，缺失率 {rate}")
    else:
        lines.append("- 暂无缺失值统计。")

    lines.extend(["", "## 数值列摘要", ""])
    if numeric_summary:
        for column, summary in numeric_summary.items():
            lines.append(
                "- "
                f"{column}：count={summary.get('count')}, "
                f"mean={summary.get('mean')}, "
                f"min={summary.get('min')}, "
                f"max={summary.get('max')}, "
                f"median={summary.get('median')}, "
                f"std={summary.get('std')}"
            )
    else:
        lines.append("- 未识别到数值列。")

    lines.extend(["", "## 类别字段摘要", ""])
    if categorical_summary:
        for column, summary in categorical_summary.items():
            top_values = summary.get("top_values", {})
            top_text = ", ".join(
                f"{value}({count})" for value, count in top_values.items()
            )
            lines.append(
                f"- {column}：唯一值 {summary.get('unique_count')} 个；"
                f" 高频值：{top_text or '暂无'}"
            )
    else:
        lines.append("- 未识别到类别字段。")

    lines.extend(["", "## 分析建议", ""])
    lines.append(insights or "当前报告基于规则生成，建议优先关注缺失值较多的字段和关键数值列。")

    if tool_trace is not None:
        lines.extend(["", "## 工具调用轨迹", ""])
        if tool_trace:
            for item in tool_trace:
                lines.append(
                    "- "
                    f"{item.get('tool_name')}：{item.get('status')}；"
                    f"{item.get('result_summary') or item.get('error_message')}"
                )
        else:
            lines.append("- 暂无工具调用记录。")

    return "\n".join(lines)
