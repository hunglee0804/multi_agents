import os
from dotenv import load_dotenv

# 1. Lấy đường dẫn gốc của project (multi_agents_project)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 2. Trỏ tới file .env đang nằm trong thư mục multi_agents
ENV_PATH = os.path.join(BASE_DIR, "multi_agents", ".env")

# 3. Nạp tất cả các biến môi trường vào hệ thống
load_dotenv(ENV_PATH)

# Tạo một class Settings để gom nhóm các config (chuẩn FastAPI)
class Settings:
    # Các key của Chatbot
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
    LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY")
    
    # Các key cho FastAPI (Auth, Redis, Database)
    SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key-change-it-in-production")
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:admin123@localhost:5432/fpt_support_db")

settings = Settings()