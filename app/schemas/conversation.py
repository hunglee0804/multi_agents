from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.schemas.message import MessageDTO

class ChatRequest(BaseModel):
    """Schema cho payload Frontend gửi lên khi chat"""
    conversation_id: Optional[str] = None
    message: str

class ChatResponse(BaseModel):
    """Schema cho response trả về sau khi AI xử lý xong"""
    conversation_id: str
    response: str

class ConversationListResponse(BaseModel):
    """Schema cho danh sách hội thoại hiển thị ở Sidebar"""
    id: str
    title: str
    created_at: datetime

class ConversationDetailResponse(BaseModel):
    """Schema cho chi tiết 1 cuộc hội thoại bao gồm lịch sử tin nhắn"""
    id: str
    title: str
    messages: List[MessageDTO]