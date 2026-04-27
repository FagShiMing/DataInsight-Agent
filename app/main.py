from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.services.data_profile import analyze_csv
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


@app.get("/analyze-csv")
def analyze_csv_api(file_path: str):
    # This endpoint analyzes a local CSV file path.
    # Example: /analyze-csv?file_path=data/sample_sales.csv
    try:
        return analyze_csv(file_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
