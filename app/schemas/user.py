from pydantic import BaseModel, EmailStr
from typing import Optional

# 1. User's basic information
class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    employee_id: Optional[str] = None # Rất hữu ích cho hệ thống nội bộ

# 2. Schema used during registration (inherits UserBase and adds password)
class UserCreate(UserBase):
    password: str 

# 3. Schema is used to return user data to the frontend (it does not return passwords).
class UserResponse(UserBase):
    id: str

    class Config:
        from_attributes = True # Important: This helps Pydantic automatically convert SQLAlchemy objects to JSON.

# 4. Schema for JWT Token
class Token(BaseModel):
    access_token: str
    token_type: str