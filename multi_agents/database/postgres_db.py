import psycopg2
import os
import sys
from dotenv import load_dotenv

# Load biến môi trường từ .env
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:admin123@localhost:5432/fpt_support_db")

def init_database():
    """
    Initialize the PostgreSQL database and create necessary tables for the Support System.
    """
    try:
        # Kết nối thẳng tới PostgreSQL
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Create the Tickets table
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
        # Create the Bookings Table
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

        # Create the Conversation Context Table
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
        print(f"✅ Database initialized successfully at PostgreSQL!")
    except Exception as e:
        print(f"❌ Failed to initialize database: {e}")

if __name__ == "__main__":
    init_database()