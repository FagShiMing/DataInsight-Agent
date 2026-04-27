from pathlib import Path

import pandas as pd


def _to_json_number(value):
    """Convert a pandas number to a JSON-friendly Python value."""
    if pd.isna(value):
        return None

    return float(value)


def analyze_csv(file_path: str) -> dict:
    """Read a local CSV file and return a simple data overview."""
    # 1. Check whether the path parameter is empty.
    if not file_path or not file_path.strip():
        raise ValueError("file_path cannot be empty.")

    csv_path = Path(file_path)

    # 2. Check whether the file exists and is a normal file.
    if not csv_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if not csv_path.is_file():
        raise ValueError(f"The path is not a file: {file_path}")

    # 3. Only analyze files ending with .csv in this beginner version.
    if csv_path.suffix.lower() != ".csv":
        raise ValueError("Only .csv files are supported.")

    # 4. Read the CSV file with pandas. Convert common read errors into
    #    beginner-friendly error messages.
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

    # 5. Convert pandas results to normal Python types so FastAPI can
    #    return them as JSON.
    row_count = int(df.shape[0])
    column_count = int(df.shape[1])
    column_names = list(df.columns)
    dtypes = {column: str(dtype) for column, dtype in df.dtypes.items()}
    missing_values = {
        column: int(count) for column, count in df.isna().sum().items()
    }

    # 6. Basic statistics for numeric columns only.
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
