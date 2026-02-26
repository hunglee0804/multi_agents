from tkinter.dialog import Dialog
from typing import Annotated, Optional, List
from typing_extensions import TypedDict, Literal
from langchain_core.messages import AnyMessage, ToolMessage
from langgraph.graph import add_messages
from pydantic import EmailStr

from pydantic import BaseModel, Field

DIALOG_ROLE = Literal[
    "primary_assistant",
    "ticket_agent",
    "it_agent",
    "booking_agent",
]
def update_dialog_stack(left: list[str], right: Optional[str]) -> list[str]:
    """Push or pop dialog stack"""

    if right is None:
        return left
    if right == "pop":
        return left[:-1] # Pop: return to previous agent
    
    return left + [right] # Push: add new agent to stack

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

    
def pop_dialog_state(state: AgenticState):
    """Pop diaglog stack and return to primary assistant."""

    messages = list()

    if state["messages"][-1].tool_calls:
        messages.append(
            ToolMessage(
                content="Resuming dialog with the host assistant."
                        "Please reflect on the past conversation and assist the user as needed",
                tool_call_id = state["messages"][-1].tool_calls[0]["id"],
            )
        )
    
    return {
        "dialog_state" : "pop",  # Trigger pop operation
        "messages" : messages,
    }



class RetrieveDocumentsSchema(BaseModel):
    question: str = Field(
        ..., 
        description="Detailed user query that requires searching internal documents for an answer."
    )