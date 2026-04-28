from io import BytesIO
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.services.data_profile import analyze_csv, profile_dataframe
from app.services.llm_service import ask_llm

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
    answer = ask_llm(request.message)
    return {"answer": answer}


@app.post("/profile/upload")
async def upload_csv_profile(file: UploadFile = File(...)):
    # 1. 先用文件名后缀做基础校验，当前只支持 CSV 文件
    filename = file.filename or ""
    if Path(filename).suffix.lower() != ".csv":
        raise HTTPException(status_code=400, detail="Only .csv files are supported.")

    # 2. 读取上传文件内容，空文件直接返回错误
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="The CSV file is empty.")

    # 3. 使用 pandas 从内存中读取 CSV
    try:
        df = pd.read_csv(BytesIO(contents))
    except pd.errors.EmptyDataError as exc:
        raise HTTPException(status_code=400, detail="The CSV file is empty.") from exc
    except pd.errors.ParserError as exc:
        raise HTTPException(
            status_code=400,
            detail="Failed to parse the CSV file. Please check its format.",
        ) from exc
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=400,
            detail="Failed to decode the CSV file. Please check its encoding.",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to read the CSV file: {exc}",
        ) from exc

    # 4. 调用可复用的数据画像函数
    return {
        "filename": filename,
        "profile": profile_dataframe(df),
    }


@app.get("/analyze-csv")
def analyze_csv_api(file_path: str):
    # 这个接口用于分析本地 CSV 文件路径
    # 示例：/analyze-csv?file_path=data/sample_sales.csv
    try:
        return analyze_csv(file_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
