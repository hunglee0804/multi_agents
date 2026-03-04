import os
import sys
from pydantic import BaseModel, Field
from langchain.tools import tool

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from multi_agents.context_injection.context_manager import save_conversation_context
from multi_agents.schemas.schemas import UpdateContextSchema

@tool("update_context_tool", args_schema=UpdateContextSchema)
def update_context_tool(conversation_id: str, user_id: str = None, email: str = None) -> str:
    """
    IMPORTANT: Call this tool to SAVE or UPDATE user identity (user_id, email) in the database.
    Use this IMMEDIATELY when the user provides their ID or Email.
    """
    save_conversation_context(conversation_id, user_id, email)
    return "User identity successfully updated in the database."