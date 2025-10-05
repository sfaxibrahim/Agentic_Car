"""
Pydantic models for API requests and responses
"""
from pydantic import BaseModel, Field
from typing import Optional


class QueryRequest(BaseModel):
    """Request model for chat queries"""
    question: str = Field(..., description="User's question")


class StreamQueryRequest(BaseModel):
    """Request model for streaming chat queries"""
    question: str = Field(..., description="User's question")
    convId: str = Field(..., description="Conversation ID")


class ChatResponse(BaseModel):
    """Response model for chat queries"""
    answer: str = Field(..., description="AI assistant's response")


class ErrorResponse(BaseModel):
    """Error response model"""
    detail: str = Field(..., description="Error message")