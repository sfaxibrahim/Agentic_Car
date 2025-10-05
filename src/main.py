"""
FastAPI application entry point for Automotive Assistant AI
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import router
from config.settings import settings

# Create FastAPI application
app = FastAPI(
    title="Automotive Assistant API",
    description="AI-powered automotive assistant with RAG, YouTube, and Google search capabilities",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="", tags=["chat"])


@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    print("=" * 60)
    print("🚗 Automotive Assistant API Starting...")
    print("=" * 60)
    print(f"📁 Base directory: {settings.BASE_DIR}")
    print(f"📁 Data directory: {settings.DATA_DIR}")
    print(f"📁 Vectorstore path: {settings.VECTORSTORE_PATH}")
    print(f"🤖 Model: {settings.OLLAMA_MODEL}")
    print(f"🔗 Spring API: {settings.SPRING_API_URL}")
    print("=" * 60)
    
    # Pre-load vectorstore for faster first query
    try:
        from services.rag_service import load_vectorstore, load_bm25
        load_vectorstore()
        load_bm25()
        print("✅ RAG system initialized")
    except Exception as e:
        print(f"⚠️ RAG system initialization warning: {e}")
    
    print("✅ Application ready!")
    print("=" * 60)


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Automotive Assistant API",
        "version": "1.0.0",
        "endpoints": {
            "chat": "/chat (POST)",
            "stream_chat": "/chat/stream (POST)"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )