from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime

class Conversation(Base):
    __tablename__ = "api_conversations"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, default="New Conversation")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # KHÓA NGOẠI: Liên kết tới bảng api_users
    user_id = Column(String, ForeignKey("api_users.id"), nullable=False)

    owner = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")