from sqlalchemy import Column, String
from sqlalchemy.orm import relationship
from app.core.database import Base
import uuid

class User(Base):
    __tablename__ = "api_users"

    id = Column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    email = Column(String, unique=True, index=True, nullable=False) # Dùng email thay cho username
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    employee_id = Column(String, nullable=True)
    
    conversations = relationship("Conversation", back_populates="owner", cascade="all, delete-orphan")