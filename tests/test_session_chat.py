import asyncio
import tempfile

from fastapi import HTTPException, UploadFile

from app.main import DataChatRequest, chat_with_data, upload_csv_profile
from app.services.session_store import delete_session


def make_upload_file(filename: str, content: bytes) -> UploadFile:
    file = tempfile.SpooledTemporaryFile(max_size=1024 * 1024)
    file.write(content)
    file.seek(0)
    return UploadFile(filename=filename, file=file)


def sample_csv_content() -> bytes:
    return (
        "date,product,region,sales,profit\n"
        "2026-04-01,A,济南,1200,300\n"
        "2026-04-02,B,杭州,1800,450\n"
        "2026-04-03,A,济南,1500,380\n"
        "2026-04-04,C,上海,,500\n"
        "2026-04-05,B,杭州,2100,620\n"
    ).encode("utf-8")


def upload_sample_csv() -> dict:
    return asyncio.run(
        upload_csv_profile(
            make_upload_file("sample_sales.csv", sample_csv_content())
        )
    )


def test_chat_data_with_session_id_uses_cached_profile():
    upload_response = upload_sample_csv()
    session_id = upload_response["session_id"]

    try:
        response = chat_with_data(
            DataChatRequest(
                question="哪些字段有缺失值？",
                session_id=session_id,
            )
        )
    finally:
        delete_session(session_id)

    assert response["tool_name"] == "missing_value_analysis"
    assert "answer" in response
    assert response["tool_trace"][0]["status"] == "success"


def test_chat_data_unknown_session_id_returns_404():
    try:
        chat_with_data(
            DataChatRequest(
                question="哪些字段有缺失值？",
                session_id="not-exist-session-id",
            )
        )
    except HTTPException as exc:
        assert exc.status_code == 404
        assert exc.detail == "Session not found"
    else:
        raise AssertionError("不存在的 session_id 应该返回 404")


def test_chat_data_still_accepts_profile_directly():
    upload_response = upload_sample_csv()
    session_id = upload_response.pop("session_id")

    try:
        response = chat_with_data(
            DataChatRequest(
                question="哪些字段有缺失值？",
                profile=upload_response,
            )
        )
    finally:
        delete_session(session_id)

    assert response["tool_name"] == "missing_value_analysis"
    assert response["tool_trace"][0]["status"] == "success"


def test_chat_data_requires_session_id_or_profile():
    try:
        chat_with_data(DataChatRequest(question="哪些字段有缺失值？"))
    except HTTPException as exc:
        assert exc.status_code == 400
        assert exc.detail == "Either session_id or profile is required"
    else:
        raise AssertionError("缺少 session_id 和 profile 时应该返回 400")
