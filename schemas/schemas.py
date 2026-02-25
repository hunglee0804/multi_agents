from tkinter.dialog import Dialog
from typing import Annotated, Optional, List
from typing_extensions import TypedDict, Literal
from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages
from pydantic import EmailStr
from chatbot_instance.app.models import conversation
from dialog.dialog import *

DIALOG_ROLE = Literal[
    "primary_assistant",
    "ticket_agent",
    "it_agent",
    "booking_agent",
]
class AgenticState(TypedDict):
    """Shared state for all agents"""

    # Messages - automatically merged
    messages: Annotated[list[AnyMessage], add_messages]

    # Dialog stack - track agent hierarchy
    dialog_state: Annotated[
        list[DIALOG_ROLE],
        update_dialog_stack,
    ]

    # Context information
    conversation_id: Annotated[str, ["Conversation ID"]]
    user_id: Annotated[str, "User ID"]
    email: Annotated[Optional[EmailStr], " Email from context (optional)"]
