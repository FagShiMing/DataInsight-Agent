import io
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.services.data_profile import analyze_csv, profile_dataframe

app = FastAPI(
    title="DataInsight Agent",
    description="A RAG and Tool Calling based data insight assistant.",
    version="0.1.0",
)


class ChatRequest(BaseModel):
    message: str


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

    return {
        "filename": filename,
        "shape": {
            "rows": profile["rows"],
            "columns": profile["columns"],
        },
        "columns": profile["column_names"],
        "dtypes": profile["dtypes"],
        "missing_values": profile["missing_values"],
        "numeric_summary": profile["numeric_summary"],
        "preview": profile["preview"],
    }


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
