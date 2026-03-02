import sqlite3
import uuid
import os
import sys
from langchain.tools import tool

# ==========================================
# PATH SETUP TO ALLOW ABSOLUTE IMPORTS
# ==========================================
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from multi_agents.config.variable import SQLITE_DB_PATH
from multi_agents.schemas.schemas import CreateTicketSchema, CheckTicketSchema

def get_db_connection():
    """Helper function to establish a database connection."""
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row # Allows column access by name
    return conn

@tool("create_ticket_tool", args_schema=CreateTicketSchema)
def create_ticket_tool(user_id: str, email: str, issue_category: str, description: str) -> str:
    """
    Create a new IT support ticket in the database.
    Returns a success message with the newly generated Ticket ID.
    """
    try:
        # Generate a unique 6-character ticket ID prefixed with 'TKT-'
        ticket_id = f"TKT-{uuid.uuid4().hex[:6].upper()}"
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            '''INSERT INTO tickets (ticket_id, user_id, email, issue_category, description, status)
               VALUES (?, ?, ?, ?, ?, ?)''',
            (ticket_id, user_id, email, issue_category, description, "Open")
        )
        
        conn.commit()
        conn.close()
        
        return f"Successfully created ticket. Ticket ID: {ticket_id}. Status: Open."
    
    except Exception as e:
        return f"Failed to create ticket due to database error: {str(e)}"

@tool("check_ticket_status_tool", args_schema=CheckTicketSchema)
def check_ticket_status_tool(ticket_id: str) -> str:
    """
    Query the database to check the current status and details of a specific ticket.
    Returns the ticket details or an error if not found.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,))
        ticket = cursor.fetchone()
        
        conn.close()
        
        if ticket:
            return (f"Ticket Found:\n"
                    f"- ID: {ticket['ticket_id']}\n"
                    f"- Category: {ticket['issue_category']}\n"
                    f"- Status: {ticket['status']}\n"
                    f"- Description: {ticket['description']}\n"
                    f"- Created At: {ticket['created_at']}")
        else:
            return f"Error: No ticket found with ID '{ticket_id}'."
            
    except Exception as e:
        return f"Failed to retrieve ticket due to database error: {str(e)}"

# Group tools for the agent
TICKET_ALL_TOOLS = [create_ticket_tool, check_ticket_status_tool]

if __name__ == "__main__":
    print("✅ ticket_tool.py loaded successfully. Import paths are correct and tools are ready!")