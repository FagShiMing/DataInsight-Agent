from fastapi import FastAPI
from pydantic import BaseModel

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