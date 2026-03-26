import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# 1. Lấy đường dẫn thư mục gốc của project (multi_agents_project)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 2. Trỏ vào thư mục database (tạo mới nếu chưa có)
DB_DIR = os.path.join(BASE_DIR, "database")
os.makedirs(DB_DIR, exist_ok=True)

# 3. Đường dẫn tuyệt đối tới file SQLite
DATABASE_URL = f"sqlite:///{os.path.join(DB_DIR, 'support_system.db')}"

# Khởi tạo engine
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency để sử dụng trong các API Routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()