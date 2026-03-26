from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime
import uuid

class Message(Base):
    __tablename__ = "api_messages"

    id = Column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    conversation_id = Column(String, ForeignKey("api_conversations.id"))
    role = Column(String) # 'user' hoặc 'assistant'
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")