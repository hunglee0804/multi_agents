import sqlite3
import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from multi_agents.config.variable import SQLITE_DB_PATH

def get_db_connection():
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_conversation_context(conversation_id: str) -> dict:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM conversation_context WHERE conversation_id = ?", (conversation_id,))
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
        
        
        cursor.execute('''
            INSERT INTO conversation_context (conversation_id, user_id, email, created_at, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT(conversation_id) DO UPDATE SET
                user_id = COALESCE(excluded.user_id, conversation_context.user_id),
                email = COALESCE(excluded.email, conversation_context.email),
                updated_at = CURRENT_TIMESTAMP
        ''', (conversation_id, user_id, email))
        
        conn.commit()
        conn.close()
        
       
        # print(f"\n   [Database] ✅ Context Saved! (Session: {conversation_id} | User: {user_id} | Email: {email})")
    except Exception as e:
        print(f"\n   [Database] ⚠️ Error saving context: {e}")