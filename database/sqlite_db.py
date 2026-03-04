import sqlite3
import os
import sys

# ==========================================
# PATH SETUP TO ALLOW ABSOLUTE IMPORTS
# ==========================================
# Go UP one level to the parent directory of 'multi_agents'
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from multi_agents.config.variable import SQLITE_DB_PATH

def init_database():
    """
    Initialize the SQLite database and create necessary tables for the Support System.
    Currently includes the 'tickets' table.
    """
    # Ensure the database directory exists
    os.makedirs(os.path.dirname(SQLITE_DB_PATH), exist_ok=True)
    
    # Connect to SQLite (this creates the file if it doesn't exist)
    conn = sqlite3.connect(SQLITE_DB_PATH)
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
    print(f"✅ Database initialized successfully at: {SQLITE_DB_PATH}")

# Run initialization when the script is executed directly
if __name__ == "__main__":
    init_database()