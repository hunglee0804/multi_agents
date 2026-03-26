from pydantic import BaseModel

class MessageBase(BaseModel):
    role: str
    content: str

class MessageDTO(MessageBase):
    """Schema dùng để trả về data tin nhắn cho Frontend"""
    pass 
    # Nếu sau này bạn muốn trả về cả ID tin nhắn hay thời gian tạo, bạn có thể thêm vào đây:
    # id: str
    # created_at: datetime