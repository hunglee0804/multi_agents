import psycopg2
import os
import sys
from dotenv import load_dotenv

# Load biến môi trường từ .env
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:admin123@localhost:5432/fpt_support_db")

def init_database():
    """
    Initialize the PostgreSQL database and create all 6 necessary tables for the Support System.
    """
    try:
        # Kết nối thẳng tới PostgreSQL
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # 1. Tạo bảng api_users
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL,
                full_name TEXT,
                employee_id TEXT
            )
        ''')

        # 2. Tạo bảng api_conversations
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_conversations (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES api_users(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 3. Tạo bảng api_messages
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_messages (
                id TEXT PRIMARY KEY, 
                conversation_id TEXT NOT NULL REFERENCES api_conversations(id) ON DELETE CASCADE,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 4. Tạo bảng Tickets 
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tickets (
                ticket_id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                description TEXT NOT NULL,
                customer_name TEXT NOT NULL,
                customer_phone TEXT NOT NULL,
                email TEXT,
                status TEXT DEFAULT 'Pending' CHECK(status IN ('Pending', 'Resolving', 'Canceled', 'Finished')),
                time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 5. Tạo bảng Bookings 
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bookings (
                booking_id TEXT PRIMARY KEY,
                customer_name TEXT NOT NULL,
                customer_phone TEXT NOT NULL,
                email TEXT,
                reason TEXT NOT NULL,
                time TIMESTAMP NOT NULL,
                note TEXT,
                status TEXT DEFAULT 'Scheduled' CHECK(status IN ('Scheduled', 'Canceled', 'Finished')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 6. Tạo bảng Conversation Context 
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversation_context (
                conversation_id TEXT PRIMARY KEY,
                user_id TEXT,
                email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        conn.close()
        print(f"✅ Đã tạo thành công toàn bộ 6 bảng tại PostgreSQL!")
    except Exception as e:
        print(f"❌ Failed to initialize database: {e}")

if __name__ == "__main__":
    init_database()