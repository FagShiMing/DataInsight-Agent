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


def generate_analysis_suggestions(profile: dict | None) -> dict:
    """基于已有数据画像生成规则版分析建议，保证无 API Key 也可演示。"""
    profile = profile or {}
    shape = _shape(profile)
    columns = _column_names(profile)
    missing_values = profile.get("missing_values", {}) or {}
    missing_rate = profile.get("missing_rate", {}) or {}
    numeric_summary = profile.get("numeric_summary", {}) or {}

    suggestions = []
    summary_parts = [
        f"当前数据共有 {shape['rows']} 行、{shape['columns']} 列。"
    ]

    if columns:
        summary_parts.append(f"字段包括：{', '.join(columns)}。")

    missing_columns = [
        {
            "column": column,
            "missing_count": int(count),
            "missing_rate": missing_rate.get(column, 0),
        }
        for column, count in missing_values.items()
        if int(count) > 0
    ]
    missing_columns.sort(
        key=lambda item: (item["missing_rate"], item["missing_count"]),
        reverse=True,
    )

    if missing_columns:
        top_missing = missing_columns[0]
        summary_parts.append(
            f"{len(missing_columns)} 个字段存在缺失值，"
            f"其中 {top_missing['column']} 缺失最明显。"
        )
        suggestions.append(
            f"建议优先检查 {top_missing['column']} 字段的缺失原因，"
            f"当前缺失率为 {top_missing['missing_rate']}。"
        )
    else:
        summary_parts.append("当前未发现缺失值。")
        suggestions.append("当前未发现缺失值，可以继续检查字段类型和关键指标分布。")

    if numeric_summary:
        numeric_columns = list(numeric_summary.keys())
        suggestions.append(
            "建议关注数值列 "
            f"{', '.join(numeric_columns)} 的均值、极值和波动情况。"
        )
    else:
        suggestions.append("当前未识别到数值列，建议确认 CSV 中金额、数量等字段格式是否正确。")

    suggestions.append("建议结合业务目标进一步分析最关键的字段，避免只停留在基础画像。")

    return {
        "success": True,
        "suggestions": suggestions,
        "summary": "".join(summary_parts),
        "source": "rule",
    }
