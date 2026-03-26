import os
from app.core.config import settings # <-- Nạp biến môi trường đầu tiên
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles # <-- Thêm thư viện này
from app.api.routes import conversation, auth
from app.core.database import engine, Base
from app.core.redis_client import check_redis_connection

Base.metadata.create_all(bind=engine) # Tự động tạo bảng nếu chưa có

check_redis_connection()

app = FastAPI(title="Multi-Agent Chatbot API")

# Setup CORS cho Frontend gọi (Dù giờ chạy chung host nhưng vẫn nên giữ)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. ĐĂNG KÝ CÁC API ROUTES TRƯỚC
app.include_router(auth.router, prefix="/backend-api/auth", tags=["Auth"])
app.include_router(conversation.router)

# 2. CẤU HÌNH PHỤC VỤ FRONTEND (STATIC FILES)
# Lấy đường dẫn tuyệt đối tới thư mục "frontend"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

# Mount toàn bộ thư mục frontend vào root ("/")
# Tham số html=True giúp tự động load file index.html khi truy cập trang chủ
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")