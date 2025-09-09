from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os

from src.search import setup_fast_rag, get_bot_response  

Base_dir = os.path.dirname(os.path.abspath(__file__))

app = FastAPI(title="Automotive Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Query(BaseModel):
    question: str

# Load PDFs once at startup
@app.on_event("startup")
async def startup_event():
    setup_fast_rag()


@app.post("/chat")
async def chat(query: Query):
    """Returns AI response to a user query"""
    response = get_bot_response(query.question)
    return {"answer": response}


@app.get("/health")
async def health():
    """Health check"""
    return {"status": "ok"}

