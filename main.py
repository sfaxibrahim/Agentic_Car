from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import requests
from fastapi.responses import StreamingResponse

from src.search import  get_bot_response  ,get_bot_response_stream

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
async def chat_stream(request: Request, authorization: str = Header(None)):
    """
    Expects JSON body: { "question": "...", "convId": "<uuid>" }
    Authorization header: Bearer <accessToken>
    """
    body = await request.json()
    question = body.get("question")
    conv_id = body.get("convId")
    if not question or not conv_id:
        raise HTTPException(status_code=400, detail="question and convId required")
    access_token=None

    if authorization:
        if authorization.lower().startswith("bearer "):
            access_token=authorization.split(" ",1)[1]
        else:
            access_token=authorization
    if not access_token:
        # if you want to allow unauthenticated usage, remove this check, but we require token for DB write
        raise HTTPException(status_code=401, detail="Missing Authorization token")
    try:
        import requests
        spring_url = f"http://localhost:8080/api/conversations/{conv_id}/messages"
        resp = requests.post(
            spring_url,
            json={"role": "USER", "content": question},
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
            timeout=5
        )
        if resp.status_code >= 400:
            # If Spring rejects (403/401), bubble up to client
            raise HTTPException(status_code=resp.status_code, detail=f"Spring API error: {resp.text}")
    except requests.RequestException as e:
        # network problem - reject
        raise HTTPException(status_code=502, detail=f"Failed to persist user message: {e}")
     
    def generate_response():
        for token in get_bot_response_stream(question, conv_id, access_token):
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