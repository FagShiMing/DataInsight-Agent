from pathlib import Path

import pandas as pd


def _to_json_number(value):
    """把 pandas 数字转换成适合 JSON 返回的 Python 值。"""
    if pd.isna(value):
        return None

    return float(value)


def _preview_records(df: pd.DataFrame, limit: int = 5) -> list[dict]:
    """返回前几行数据，并把缺失值转换成 JSON 里的 null。"""
    preview_df = df.head(limit).astype(object)
    preview_df = preview_df.where(pd.notna(preview_df), None)
    return preview_df.to_dict(orient="records")


def profile_dataframe(df: pd.DataFrame) -> dict:
    """接收 pandas DataFrame，返回基础数据画像结果。"""
    # 1. 基础行列信息。
    row_count = int(df.shape[0])
    column_count = int(df.shape[1])
    column_names = list(df.columns)

    # 2. 每列的数据类型和缺失值数量。
    dtypes = {column: str(dtype) for column, dtype in df.dtypes.items()}
    missing_values = {
        column: int(count) for column, count in df.isna().sum().items()
    }
    missing_rate = {}
    for column, count in missing_values.items():
        if row_count == 0:
            missing_rate[column] = 0.0
        else:
            missing_rate[column] = round(count / row_count, 4)

    # 3. 只对数值列计算简单统计信息。
    numeric_df = df.select_dtypes(include="number")
    numeric_summary = {}
    for column in numeric_df.columns:
        numeric_summary[column] = {
            "count": int(numeric_df[column].count()),
            "mean": _to_json_number(numeric_df[column].mean()),
            "min": _to_json_number(numeric_df[column].min()),
            "max": _to_json_number(numeric_df[column].max()),
            "median": _to_json_number(numeric_df[column].median()),
            "std": _to_json_number(numeric_df[column].std()),
        }

    # 4. 类别列的高频值对后续 LLM 总结和报告很有用，但不需要复杂建模。
    categorical_df = df.select_dtypes(exclude="number")
    categorical_summary = {}
    for column in categorical_df.columns:
        top_values = categorical_df[column].dropna().value_counts().head(5)
        categorical_summary[column] = {
            "unique_count": int(categorical_df[column].nunique(dropna=True)),
            "top_values": {
                str(value): int(count) for value, count in top_values.items()
            },
        }

    return {
        "rows": row_count,
        "columns": column_count,
        "column_names": column_names,
        "dtypes": dtypes,
        "missing_values": missing_values,
        "missing_rate": missing_rate,
        "numeric_summary": numeric_summary,
        "categorical_summary": categorical_summary,
        "preview": _preview_records(df),
    }


def analyze_csv(file_path: str) -> dict:
    """读取本地 CSV 文件，并返回基础数据画像结果。"""
    # 1. 检查路径参数是否为空。
    if not file_path or not file_path.strip():
        raise ValueError("file_path cannot be empty.")

    csv_path = Path(file_path)

    # 2. 检查文件是否存在。
    if not csv_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if not csv_path.is_file():
        raise ValueError(f"The path is not a file: {file_path}")

    # 3. 当前版本只支持 .csv 文件。
    if csv_path.suffix.lower() != ".csv":
        raise ValueError("Only .csv files are supported.")

    # 4. 使用 pandas 读取 CSV，并把常见异常转换成易理解的错误信息。
    try:
        df = pd.read_csv(csv_path)
    except pd.errors.EmptyDataError as exc:
        raise ValueError("The CSV file is empty.") from exc
    except pd.errors.ParserError as exc:
        raise ValueError("Failed to parse the CSV file. Please check its format.") from exc
    except UnicodeDecodeError as exc:
        raise ValueError("Failed to decode the CSV file. Please check its encoding.") from exc
    except Exception as exc:
        raise ValueError(f"Failed to read the CSV file: {exc}") from exc

    # 5. 复用 DataFrame 画像函数。
    return profile_dataframe(df)
