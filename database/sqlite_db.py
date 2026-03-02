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
            user_id TEXT NOT NULL,
            email TEXT NOT NULL,
            issue_category TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT DEFAULT 'Open',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"✅ Database initialized successfully at: {SQLITE_DB_PATH}")

# Run initialization when the script is executed directly
if __name__ == "__main__":
    init_database()