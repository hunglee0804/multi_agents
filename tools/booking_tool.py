import sqlite3
import uuid
import os
import sys
from langchain.tools import tool

# ==========================================
# PATH SETUP TO ALLOW ABSOLUTE IMPORTS
# ==========================================
# Go UP TWO levels ("../../") to reach the directory containing 'multi_agents'
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from multi_agents.config.variable import SQLITE_DB_PATH
from multi_agents.schemas.schemas import CreateBookingSchema, CheckBookingSchema

def get_db_connection():
    """Helper function to establish a database connection."""
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row # Allows column access by name
    return conn

@tool("create_booking_tool", args_schema=CreateBookingSchema)
def create_booking_tool(user_id: str, email: str, room_name: str, start_time: str, end_time: str) -> str:
    """
    Create a new meeting room booking in the database.
    Returns a success message with the newly generated Booking ID.
    """
    try:
        # Generate a unique 6-character booking ID prefixed with 'BKG-'
        booking_id = f"BKG-{uuid.uuid4().hex[:6].upper()}"
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            '''INSERT INTO bookings (booking_id, user_id, email, room_name, start_time, end_time, status)
               VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (booking_id, user_id, email, room_name, start_time, end_time, "Confirmed")
        )
        
        conn.commit()
        conn.close()
        
        return f"Successfully booked room. Booking ID: {booking_id}. Status: Confirmed."
    
    except Exception as e:
        return f"Failed to create booking due to database error: {str(e)}"

@tool("check_booking_status_tool", args_schema=CheckBookingSchema)
def check_booking_status_tool(booking_id: str) -> str:
    """
    Query the database to check the current status and details of a specific room booking.
    Returns the booking details or an error if not found.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM bookings WHERE booking_id = ?", (booking_id,))
        booking = cursor.fetchone()
        
        conn.close()
        
        if booking:
            return (f"Booking Found:\n"
                    f"- ID: {booking['booking_id']}\n"
                    f"- Room: {booking['room_name']}\n"
                    f"- Start Time: {booking['start_time']}\n"
                    f"- End Time: {booking['end_time']}\n"
                    f"- Status: {booking['status']}\n"
                    f"- Created At: {booking['created_at']}")
        else:
            return f"Error: No booking found with ID '{booking_id}'."
            
    except Exception as e:
        return f"Failed to retrieve booking due to database error: {str(e)}"

# Group tools for the agent
BOOKING_ALL_TOOLS = [create_booking_tool, check_booking_status_tool]

# ==========================================
# QUICK TEST
# ==========================================
if __name__ == "__main__":
    print("✅ booking_tool.py loaded successfully. Import paths are correct and tools are ready!")