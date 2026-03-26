from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.schemas.message import MessageDTO

class ChatRequest(BaseModel):
    """Schema for the payload the frontend sends during chat."""
    conversation_id: Optional[str] = None
    message: str

class ChatResponse(BaseModel):
    """Schema for the response returned after AI processing is complete."""
    conversation_id: str
    response: str

class ConversationListResponse(BaseModel):
    """Schema for the list of conversations displayed in the sidebar."""
    id: str
    title: str
    created_at: datetime

class ConversationDetailResponse(BaseModel):
    """Schema for details of a conversation, including message history."""
    id: str
    title: str
    messages: List[MessageDTO]