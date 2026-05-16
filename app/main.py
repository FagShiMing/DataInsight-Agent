import io
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.services.agent_service import run_agent
from app.services.data_profile import analyze_csv, profile_dataframe
from app.services.report_service import generate_markdown_report
from app.services.session_store import create_session, get_profile

app = FastAPI(
    title="DataInsight Agent",
    description="A lightweight CSV data analysis Agent.",
    version="0.1.0",
)


class ChatRequest(BaseModel):
    message: str


class DataChatRequest(BaseModel):
    question: str
    profile: dict | None = None
    session_id: str | None = None
    llm_tool_choice_json: str | None = None


class ReportGenerateRequest(BaseModel):
    profile: dict
    insights: str | None = None
    tool_trace: list[dict] | None = None


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/chat")
def chat(request: ChatRequest):
    # LLM 只在调用 /chat 时才加载，避免影响 CSV 上传接口和测试。
    from app.services.llm_service import ask_llm

    answer = ask_llm(request.message)
    return {"answer": answer}


@app.post("/profile/upload")
async def upload_csv_profile(file: UploadFile = File(...)):
    # 1. 先用文件名后缀做基础校验，当前只支持 CSV 文件。
    filename = file.filename or ""
    if Path(filename).suffix.lower() != ".csv":
        raise HTTPException(status_code=400, detail="只支持上传 .csv 文件")

    # 2. 读取上传文件内容，空文件直接返回 400。
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="上传的 CSV 文件为空")

    # 3. 用 BytesIO 把上传的二进制内容转换成 pandas 可读取的对象。
    try:
        df = pd.read_csv(io.BytesIO(contents))
    except pd.errors.EmptyDataError as exc:
        raise HTTPException(status_code=400, detail="上传的 CSV 文件为空") from exc
    except (pd.errors.ParserError, UnicodeDecodeError, ValueError) as exc:
        raise HTTPException(
            status_code=400,
            detail="CSV 文件读取失败，请检查文件格式",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail="CSV 文件读取失败，请检查文件格式",
        ) from exc

    # 4. 调用数据画像函数，并把结果整理成适合展示的 JSON。
    try:
        profile = profile_dataframe(df)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="服务器处理 CSV 时发生未知错误",
        ) from exc

    response_data = {
        "filename": filename,
        "shape": {
            "rows": profile["rows"],
            "columns": profile["columns"],
        },
        "columns": profile["column_names"],
        "dtypes": profile["dtypes"],
        "missing_values": profile["missing_values"],
        "missing_rate": profile["missing_rate"],
        "numeric_summary": profile["numeric_summary"],
        "categorical_summary": profile["categorical_summary"],
        "preview": profile["preview"],
    }
    session_id = create_session(dict(response_data))
    response_data["session_id"] = session_id

    return response_data


@app.post("/chat/data")
def chat_with_data(request: DataChatRequest):
    # 新方式优先使用 session_id，调用方不需要每次把完整 profile 传回来。
    if request.session_id:
        profile = get_profile(request.session_id)
        if profile is None:
            raise HTTPException(status_code=404, detail="Session not found")
    elif request.profile:
        profile = request.profile
    else:
        raise HTTPException(
            status_code=400,
            detail="Either session_id or profile is required",
        )

    return run_agent(
        question=request.question,
        profile=profile,
        llm_tool_choice_json=request.llm_tool_choice_json,
    )


@app.post("/report/generate")
def generate_report_api(request: ReportGenerateRequest):
    markdown = generate_markdown_report(
        profile=request.profile,
        insights=request.insights,
        tool_trace=request.tool_trace,
    )
    return {"markdown": markdown}


@app.get("/analyze-csv")
def analyze_csv_api(file_path: str):
    # 这个接口用于分析本地 CSV 文件路径。
    # 示例：/analyze-csv?file_path=data/sample_sales.csv
    try:
        return analyze_csv(file_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
