from pathlib import Path

import pandas as pd


def _to_json_number(value):
    """把 pandas 数字转换成适合 JSON 返回的 Python 值。"""
    if pd.isna(value):
        return None

    return float(value)


def profile_dataframe(df: pd.DataFrame) -> dict:
    """接收 pandas DataFrame，返回基础数据画像结果。"""
    # 1. 基础行列信息
    row_count = int(df.shape[0])
    column_count = int(df.shape[1])
    column_names = list(df.columns)

    # 2. 每列的数据类型和缺失值数量
    dtypes = {column: str(dtype) for column, dtype in df.dtypes.items()}
    missing_values = {
        column: int(count) for column, count in df.isna().sum().items()
    }

    # 3. 只对数值列计算简单统计信息
    numeric_df = df.select_dtypes(include="number")
    numeric_summary = {}
    for column in numeric_df.columns:
        numeric_summary[column] = {
            "mean": _to_json_number(numeric_df[column].mean()),
            "min": _to_json_number(numeric_df[column].min()),
            "max": _to_json_number(numeric_df[column].max()),
        }

    return {
        "rows": row_count,
        "columns": column_count,
        "column_names": column_names,
        "dtypes": dtypes,
        "missing_values": missing_values,
        "numeric_summary": numeric_summary,
    }


def analyze_csv(file_path: str) -> dict:
    """读取本地 CSV 文件，并返回基础数据画像结果。"""
    # 1. 检查路径参数是否为空
    if not file_path or not file_path.strip():
        raise ValueError("file_path cannot be empty.")

    csv_path = Path(file_path)

    # 2. 检查文件是否存在
    if not csv_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if not csv_path.is_file():
        raise ValueError(f"The path is not a file: {file_path}")

    # 3. 当前版本只支持 .csv 文件
    if csv_path.suffix.lower() != ".csv":
        raise ValueError("Only .csv files are supported.")

    # 4. 使用 pandas 读取 CSV，并把常见异常转换成易理解的错误信息
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

    # 5. 复用 DataFrame 画像函数
    return profile_dataframe(df)
