from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Import settings để lấy chuỗi kết nối PostgreSQL
from app.core.config import settings

# Khởi tạo engine kết nối thẳng tới PostgreSQL thông qua chuỗi DATABASE_URL
# Không cần check_same_thread nữa vì PostgreSQL xử lý đa luồng (multi-thread) mặc định cực tốt
engine = create_engine(settings.DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency để sử dụng trong các API Routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()