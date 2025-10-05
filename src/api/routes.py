"""
FastAPI routes for the automotive assistant
"""
import queue
import threading
from fastapi import APIRouter, HTTPException, Header, Request
from fastapi.responses import StreamingResponse

from api.models import QueryRequest, ChatResponse
from core import (
    setup_memory,
    load_previous_history,
    create_conversational_agent,
    QueueCallback
)
from services.api_service import save_message

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(query: QueryRequest):
    """
    Returns AI response to a user query (non-streaming)
    
    Args:
        query: QueryRequest with user's question
        
    Returns:
        ChatResponse with AI's answer
    """
    memory = setup_memory()
    agent_executor = create_conversational_agent(memory)
    
    try:
        result = agent_executor.invoke({
            "input": query.question,
            "chat_history": memory.chat_memory.messages
        })
        
        if result and "output" in result:
            ai_response = result["output"]
            return ChatResponse(answer=ai_response)
        else:
            return ChatResponse(answer="I'm having trouble processing your request.")
    
    except Exception as e:
        print(f"❌ Error in chat endpoint: {e}")
        return ChatResponse(answer="An error occurred while generating the response.")


@router.post("/chat/stream")
async def chat_stream(request: Request, authorization: str = Header(None)):
    """
    Streams AI response to a user query with conversation persistence
    
    Expects JSON body:
        {
            "question": "user question",
            "convId": "conversation-uuid"
        }
    
    Headers:
        Authorization: Bearer <access_token>
    
    Returns:
        StreamingResponse with text/plain content
    """

        # ADD THIS DEBUG LOGGING:
    
    # Parse request body
    body = await request.json()

    print("=" * 60)
    print("📥 Received request body:")
    print(body)
    print(f"Authorization header: {authorization}")
    print("=" * 60)

    question = body.get("question")
    conv_id = body.get("convId")
    
    if not question or not conv_id:
        raise HTTPException(
            status_code=400,
            detail="question and convId are required"
        )
    
    # Extract access token
    access_token = None
    if authorization:
        if authorization.lower().startswith("bearer "):
            access_token = authorization.split(" ", 1)[1]
        else:
            access_token = authorization
    
    if not access_token:
        raise HTTPException(
            status_code=401,
            detail="Missing Authorization token"
        )
    
    # Save user message to Spring Boot API
    try:
        import requests
        from config.settings import settings
        from services.api_service import api_headers
        
        spring_url = f"{settings.SPRING_API_URL}/api/conversations/{conv_id}/messages"
        resp = requests.post(
            spring_url,
            json={"role": "USER", "content": question},
            headers=api_headers(access_token),
            timeout=5
        )
        
        if resp.status_code >= 400:
            raise HTTPException(
                status_code=resp.status_code,
                detail=f"Spring API error: {resp.text}"
            )
    
    except requests.RequestException as e:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to persist user message: {e}"
        )
    
    # Setup streaming response
    def generate_response():
        """Generator for streaming tokens"""
        q = queue.Queue()
        cb = QueueCallback(q)
        collected = []
        
        # Setup memory and agent
        memory = setup_memory()
        load_previous_history(memory, conv_id, access_token)
        agent_executor = create_conversational_agent(memory, streaming_handler=cb)
        
        def run_agent():
            """Run agent in separate thread"""
            nonlocal collected
            try:
                agent_executor.invoke({
                    "input": question,
                    "chat_history": memory.chat_memory.messages
                })
            except Exception as e:
                q.put(f"[Agent error: {e}]")
            finally:
                q.put(None)
                
                # Save AI response after completion
                full_output = "".join(collected)
                try:
                    save_message(conv_id, "ASSISTANT", full_output, access_token)
                    print(f"✅ Saved AI response to conversation {conv_id}")
                except Exception as e:
                    print(f"❌ Failed to save AI response: {e}")
        
        # Start agent in background thread
        threading.Thread(target=run_agent, daemon=True).start()
        
        # Yield tokens as they arrive
        while True:
            token = q.get()
            if token is None:
                break
            collected.append(token)
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