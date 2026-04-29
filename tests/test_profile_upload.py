from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_upload_csv_success():
    csv_content = (
        "date,product,region,sales,profit\n"
        "2026-04-01,A,济南,1200,300\n"
        "2026-04-02,B,杭州,1800,450\n"
        "2026-04-03,A,济南,1500,380\n"
        "2026-04-04,C,上海,,500\n"
        "2026-04-05,B,杭州,2100,620\n"
    )

    response = client.post(
        "/profile/upload",
        files={
            "file": (
                "sample_sales.csv",
                csv_content.encode("utf-8"),
                "text/csv",
            )
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "sample_sales.csv"
    assert data["shape"] == {"rows": 5, "columns": 5}
    assert data["columns"] == ["date", "product", "region", "sales", "profit"]
    assert data["missing_values"]["sales"] == 1
    assert data["numeric_summary"]["sales"]["max"] == 2100.0
    assert data["preview"][0]["region"] == "济南"


def test_upload_non_csv_returns_400():
    response = client.post(
        "/profile/upload",
        files={"file": ("sample.txt", b"hello", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "只支持上传 .csv 文件"


def test_upload_empty_csv_returns_400():
    response = client.post(
        "/profile/upload",
        files={"file": ("empty.csv", b"", "text/csv")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "上传的 CSV 文件为空"
