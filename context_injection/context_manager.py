import sqlite3
import json
import os
import sys

# ==========================================
# PATH SETUP TO ALLOW ABSOLUTE IMPORTS
# ==========================================
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from multi_agents.config.variable import SQLITE_DB_PATH

def get_db_connection():
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_conversation_context(session_id: str) -> dict:
    """
    Retrieve the conversation context for a specific session.
    Returns a dictionary of the context or an empty dict if none exists.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM conversation_context WHERE session_id = ?", (session_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            # Parse the extracted_parameters JSON string back to a dictionary
            extracted_params = {}
            if row["extracted_parameters"]:
                try:
                    extracted_params = json.loads(row["extracted_parameters"])
                except:
                    pass

            return {
                "session_id": row["session_id"],
                "user_id": row["user_id"],
                "email": row["email"],
                "current_intent": row["current_intent"],
                "extracted_parameters": extracted_params
            }
        return {}
    except Exception as e:
        print(f"⚠️ Error retrieving context: {e}")
        return {}

def save_conversation_context(session_id: str, current_intent: str, user_id: str = None, email: str = None, extracted_parameters: dict = None):
    """
    Save or update the conversation context for a specific session.
    Uses UPSERT (INSERT OR REPLACE) to keep the database updated.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Convert dictionary to JSON string for storage
        params_json = json.dumps(extracted_parameters) if extracted_parameters else "{}"
        
        # Upsert logic: Insert if new, Replace if exists based on PRIMARY KEY (session_id)
        cursor.execute('''
            INSERT OR REPLACE INTO conversation_context 
            (session_id, user_id, email, current_intent, extracted_parameters, last_updated)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (session_id, user_id, email, current_intent, params_json))
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"⚠️ Error saving context: {e}")

if __name__ == "__main__":
    # Quick test
    save_conversation_context("test_session_1", "create_ticket", "EMP123", "test@fpt.com", {"issue_category": "Hardware"})
    print("Test Save Context:", get_conversation_context("test_session_1"))