import psycopg2
from psycopg2.extras import RealDictCursor
import uuid
import os
import sys
from langchain.tools import tool
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:admin123@localhost:5432/fpt_support_db")

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from multi_agents.schemas.schemas import CreateBookingSchema, CheckBookingSchema, UpdateBookingStatusSchema

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

@tool("create_booking_tool", args_schema=CreateBookingSchema)
def create_booking_tool(customer_name: str, customer_phone: str, reason: str, time: str, email: str = None, note: str = None) -> str:
    """Create a new booking in the database."""
    try:
        booking_id = f"BKG-{uuid.uuid4().hex[:6].upper()}"
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # CHÚ Ý: Đổi ? thành %s
        cursor.execute(
            '''INSERT INTO bookings (booking_id, customer_name, customer_phone, email, reason, time, note, status)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)''',
            (booking_id, customer_name, customer_phone, email, reason, time, note, "Scheduled")
        )
        conn.commit()
        conn.close()
        return f"Successfully created booking. Booking ID: {booking_id}. Status: Scheduled."
    except Exception as e:
        return f"Failed to create booking due to database error: {str(e)}"

@tool("check_booking_status_tool", args_schema=CheckBookingSchema)
def check_booking_status_tool(booking_id: str) -> str:
    """Query the database to check the current status and details of a specific booking."""
    try:
        conn = get_db_connection()
        # Dùng RealDictCursor để truy cập dữ liệu qua key (như dictionary)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM bookings WHERE booking_id = %s", (booking_id,))
        booking = cursor.fetchone()
        conn.close()
        
        if booking:
            return (f"Booking Found:\n"
                    f"- ID: {booking['booking_id']}\n"
                    f"- Customer: {booking['customer_name']} ({booking['customer_phone']})\n"
                    f"- Reason: {booking['reason']}\n"
                    f"- Time: {booking['time']}\n"
                    f"- Status: {booking['status']}\n"
                    f"- Note: {booking['note']}")
        else:
            return f"Error: No booking found with ID '{booking_id}'."
    except Exception as e:
        return f"Failed to retrieve booking due to database error: {str(e)}"

@tool("update_booking_status_tool", args_schema=UpdateBookingStatusSchema)
def update_booking_status_tool(booking_id: str, new_status: str) -> str:
    """Update the status of an existing booking."""
    valid_statuses = ['Scheduled', 'Canceled', 'Finished']
    if new_status not in valid_statuses:
        return f"Error: Invalid status '{new_status}'. Allowed values are: {', '.join(valid_statuses)}"
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT booking_id FROM bookings WHERE booking_id = %s", (booking_id,))
        if not cursor.fetchone():
            conn.close()
            return f"Error: No booking found with ID '{booking_id}'."
            
        cursor.execute("UPDATE bookings SET status = %s WHERE booking_id = %s", (new_status, booking_id))
        conn.commit()
        conn.close()
        return f"Successfully updated booking {booking_id} to status: '{new_status}'."
    except Exception as e:
        return f"Failed to update booking status due to database error: {str(e)}"

BOOKING_ALL_TOOLS = [create_booking_tool, check_booking_status_tool, update_booking_status_tool]