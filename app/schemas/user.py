from pydantic import BaseModel, EmailStr
from typing import Optional

# 1. Thông tin cơ bản của User
class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    employee_id: Optional[str] = None # Rất hữu ích cho hệ thống nội bộ

# 2. Schema dùng khi Đăng ký (Kế thừa UserBase và thêm password)
class UserCreate(UserBase):
    password: str 

# 3. Schema dùng để trả dữ liệu User về cho Frontend (Không trả về password)
class UserResponse(UserBase):
    id: str

    class Config:
        from_attributes = True # Quan trọng: Giúp Pydantic tự động chuyển đổi từ object SQLAlchemy sang JSON

# 4. Schema cho JWT Token
class Token(BaseModel):
    access_token: str
    token_type: str