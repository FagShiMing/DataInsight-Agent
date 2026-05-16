import pandas as pd
import pytest

from app.services.data_profile import analyze_csv, profile_dataframe


def test_profile_dataframe_returns_core_profile_fields():
    df = pd.DataFrame(
        {
            "product": ["A", "B", "A"],
            "sales": [100, None, 300],
            "profit": [20, 30, 50],
        }
    )

    profile = profile_dataframe(df)

    assert profile["rows"] == 3
    assert profile["columns"] == 3
    assert profile["column_names"] == ["product", "sales", "profit"]
    assert profile["missing_values"]["sales"] == 1
    assert profile["missing_rate"]["sales"] == 0.3333
    assert profile["numeric_summary"]["sales"]["max"] == 300.0
    assert profile["numeric_summary"]["profit"]["median"] == 30.0
    assert profile["categorical_summary"]["product"]["top_values"]["A"] == 2
    assert profile["preview"][0]["product"] == "A"


def test_analyze_csv_rejects_non_csv_file():
    with pytest.raises(ValueError, match="Only .csv files are supported"):
        analyze_csv("README.md")
