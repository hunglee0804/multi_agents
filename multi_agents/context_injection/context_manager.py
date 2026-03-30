import psycopg2
from psycopg2.extras import RealDictCursor
import os
import sys
from dotenv import load_dotenv

# Load biến môi trường từ .env
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:admin123@localhost:5432/fpt_support_db")

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def get_db_connection():
    # Kết nối trực tiếp tới PostgreSQL
    return psycopg2.connect(DATABASE_URL)

def get_conversation_context(conversation_id: str) -> dict:
    try:
        conn = get_db_connection()
        # Sử dụng RealDictCursor để trả về dữ liệu dạng dictionary
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # CHÚ Ý: Đổi ? thành %s
        cursor.execute("SELECT * FROM conversation_context WHERE conversation_id = %s", (conversation_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "conversation_id": row["conversation_id"],
                "user_id": row["user_id"],
                "email": row["email"]
            }
        return {}
    except Exception as e:
        print(f"⚠️ Error retrieving context: {e}")
        return {}

def save_conversation_context(conversation_id: str, user_id: str = None, email: str = None):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # CHÚ Ý: Đổi các dấu ? thành %s
        # PostgreSQL sử dụng từ khóa EXCLUDED (thay vì excluded) trong mệnh đề ON CONFLICT
        cursor.execute('''
            INSERT INTO conversation_context (conversation_id, user_id, email, created_at, updated_at)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT(conversation_id) DO UPDATE SET
                user_id = COALESCE(EXCLUDED.user_id, conversation_context.user_id),
                email = COALESCE(EXCLUDED.email, conversation_context.email),
                updated_at = CURRENT_TIMESTAMP
        ''', (conversation_id, user_id, email))
        
        conn.commit()
        conn.close()
        
        # print(f"\n   [Database] ✅ Context Saved! (Session: {conversation_id} | User: {user_id} | Email: {email})")
    except Exception as e:
        print(f"\n   [Database] ⚠️ Error saving context: {e}")