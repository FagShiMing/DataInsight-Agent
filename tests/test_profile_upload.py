import asyncio
import tempfile

from fastapi import HTTPException, UploadFile

from app.main import upload_csv_profile


def make_upload_file(filename: str, content: bytes) -> UploadFile:
    file = tempfile.SpooledTemporaryFile(max_size=1024 * 1024)
    file.write(content)
    file.seek(0)
    return UploadFile(filename=filename, file=file)


def test_upload_csv_success():
    csv_content = (
        "date,product,region,sales,profit\n"
        "2026-04-01,A,济南,1200,300\n"
        "2026-04-02,B,杭州,1800,450\n"
        "2026-04-03,A,济南,1500,380\n"
        "2026-04-04,C,上海,,500\n"
        "2026-04-05,B,杭州,2100,620\n"
    )

    data = asyncio.run(
        upload_csv_profile(
            make_upload_file("sample_sales.csv", csv_content.encode("utf-8"))
        )
    )

    assert data["filename"] == "sample_sales.csv"
    assert data["shape"] == {"rows": 5, "columns": 5}
    assert data["columns"] == ["date", "product", "region", "sales", "profit"]
    assert data["missing_values"]["sales"] == 1
    assert data["missing_rate"]["sales"] == 0.2
    assert data["numeric_summary"]["sales"]["max"] == 2100.0
    assert data["preview"][0]["region"] == "济南"


def test_upload_non_csv_returns_400():
    try:
        asyncio.run(upload_csv_profile(make_upload_file("sample.txt", b"hello")))
    except HTTPException as exc:
        assert exc.status_code == 400
        assert exc.detail == "只支持上传 .csv 文件"
    else:
        raise AssertionError("非 CSV 文件应该返回 400")


def test_upload_empty_csv_returns_400():
    try:
        asyncio.run(upload_csv_profile(make_upload_file("empty.csv", b"")))
    except HTTPException as exc:
        assert exc.status_code == 400
        assert exc.detail == "上传的 CSV 文件为空"
    else:
        raise AssertionError("空 CSV 文件应该返回 400")
