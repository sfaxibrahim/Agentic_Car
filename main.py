from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import asyncio
from fastapi.responses import StreamingResponse
import json

from src.search import setup_fast_rag, get_bot_response  ,get_bot_response_stream

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

# @app.on_event("startup")
# async def startup_event():
#     setup_fast_rag()

@app.post("/chat")
async def chat(query: Query):
    """Returns AI response to a user query"""
    response = get_bot_response(query.question)
    return {"answer": response}



@app.post("/chat/stream")
async def chat_stream(query: Query):
    def generate_response():
        for token in get_bot_response_stream(query.question):
            yield token
    
    return StreamingResponse(
        generate_response(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive", 
            "X-Accel-Buffering": "no",
        }
    )