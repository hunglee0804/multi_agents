import os
import sys
from pydantic import BaseModel, Field
from langchain.tools import tool

# ==========================================
# PATH SETUP
# ==========================================
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from multi_agents.context_injection.context_manager import save_conversation_context

class UpdateContextSchema(BaseModel):
    """Schema for updating the conversation context in the database."""
    session_id: str = Field(..., description="The current session ID (required).")
    current_intent: str = Field(..., description="The user's current task (e.g., 'book_room', 'create_ticket').")
    user_id: str = Field(default=None, description="The user's ID if known.")
    email: str = Field(default=None, description="The user's email if known.")
    extracted_parameters: dict = Field(default={}, description="Other details like room_name, start_time, etc.")

@tool("update_context_tool", args_schema=UpdateContextSchema)
def update_context_tool(session_id: str, current_intent: str, user_id: str = None, email: str = None, extracted_parameters: dict = None) -> str:
    """
    IMPORTANT: Call this tool to SAVE or UPDATE user information in the database.
    Whenever the user provides new details (like their ID, email, or room preference), 
    use this tool IMMEDIATELY to remember it for future turns.
    """
    save_conversation_context(session_id, current_intent, user_id, email, extracted_parameters)
    return "Memory successfully updated in the database."