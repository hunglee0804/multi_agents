import sqlite3
import uuid
import os
import sys
from langchain.tools import tool

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from multi_agents.config.variable import SQLITE_DB_PATH
from multi_agents.schemas.schemas import CreateTicketSchema, CheckTicketSchema, UpdateTicketStatusSchema

def get_db_connection():
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@tool("create_ticket_tool", args_schema=CreateTicketSchema)
def create_ticket_tool(content: str, description: str, customer_name: str, customer_phone: str, email: str = None) -> str:
    """Create a new IT support ticket in the database."""
    try:
        ticket_id = f"TKT-{uuid.uuid4().hex[:6].upper()}"
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            '''INSERT INTO tickets (ticket_id, content, description, customer_name, customer_phone, email, status)
               VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (ticket_id, content, description, customer_name, customer_phone, email, "Pending")
        )
        conn.commit()
        conn.close()
        return f"Successfully created ticket. Ticket ID: {ticket_id}. Status: Pending."
    except Exception as e:
        return f"Failed to create ticket due to database error: {str(e)}"

@tool("check_ticket_status_tool", args_schema=CheckTicketSchema)
def check_ticket_status_tool(ticket_id: str) -> str:
    """Query the database to check the current status and details of a specific ticket."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,))
        ticket = cursor.fetchone()
        conn.close()
        
        if ticket:
            return (f"Ticket Found:\n"
                    f"- ID: {ticket['ticket_id']}\n"
                    f"- Customer: {ticket['customer_name']} ({ticket['customer_phone']})\n"
                    f"- Content: {ticket['content']}\n"
                    f"- Status: {ticket['status']}\n"
                    f"- Description: {ticket['description']}\n"
                    f"- Created At: {ticket['time']}")
        else:
            return f"Error: No ticket found with ID '{ticket_id}'."
    except Exception as e:
        return f"Failed to retrieve ticket due to database error: {str(e)}"

@tool("update_ticket_status_tool", args_schema=UpdateTicketStatusSchema)
def update_ticket_status_tool(ticket_id: str, new_status: str) -> str:
    """Update the status of an existing IT support ticket."""
    valid_statuses = ['Pending', 'Resolving', 'Canceled', 'Finished']
    if new_status not in valid_statuses:
        return f"Error: Invalid status '{new_status}'. Allowed values are: {', '.join(valid_statuses)}"
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT ticket_id FROM tickets WHERE ticket_id = ?", (ticket_id,))
        if not cursor.fetchone():
            conn.close()
            return f"Error: No ticket found with ID '{ticket_id}'."
            
        cursor.execute("UPDATE tickets SET status = ? WHERE ticket_id = ?", (new_status, ticket_id))
        conn.commit()
        conn.close()
        return f"Successfully updated ticket {ticket_id} to status: '{new_status}'."
    except Exception as e:
        return f"Failed to update ticket status due to database error: {str(e)}"

# IMPORTANT: Add the new tool to the list
TICKET_ALL_TOOLS = [create_ticket_tool, check_ticket_status_tool, update_ticket_status_tool]

if __name__ == "__main__":
    print("✅ ticket_tool.py loaded successfully. Import paths are correct and tools are ready!")