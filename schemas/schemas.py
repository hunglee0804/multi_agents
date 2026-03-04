from tkinter.dialog import Dialog
from typing import Annotated, Optional, List, TypedDict
from typing_extensions import TypedDict, Literal
from langchain_core.messages import AnyMessage, ToolMessage
from langgraph.graph import add_messages
from pydantic import EmailStr, BaseModel, Field

from pydantic import BaseModel, Field

DIALOG_ROLE = Literal[
    "primary_assistant",
    "ticket_agent",
    "it_agent",
    "booking_agent",
]
def update_dialog_stack(left: list[str], right: Optional[str]) -> list[str]:
    """
    Manage the dialog stack to track which agent is currently active.
    Push to stack when entering an agent, 'pop' to leave and return to Primary.
    """
    if right is None:
        return left
    if right == "pop":
        return left[:-1] if left else []
    return left + [right]

class AgenticState(TypedDict):
    """Shared master state for the hierarchical multi-agent system."""
    messages: Annotated[List[AnyMessage], add_messages]
    dialog_state: Annotated[List[str], update_dialog_stack]
    session_id: str

    
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


# ==========================================
# FAQ AGENT (REACT) SCHEMAS
# ==========================================

class FAQState(TypedDict):
    """State riêng biệt dành cho FAQ Agent (ReAct)"""
    messages: Annotated[List[AnyMessage], add_messages]
    current_iteration: int
    max_iterations: int


class RetrieveDocumentsSchema(BaseModel):
    question: str = Field(
        ..., 
        description="Detailed user query that requires searching internal documents for an answer."
    )

# ==========================================
# TAVILY SEARCH & EXPERT SCHEMAS
# ==========================================

# State cho Agent Tavily Search
class ResearcherState(TypedDict):
    messages: Annotated[List[AnyMessage], add_messages]
    current_iteration: int
    max_iterations: int
    

# Schema Tool 1
class AIResearchSchema(BaseModel):
    query: str = Field(
        ...,
        description="Detailed question regarding ML/AI theory, model architectures, or training methods."
    )

# Schema Tool 2
class FinancialAnalystSchema(BaseModel):
    query: str = Field(
        ...,
        description="Detailed question regarding the stock market, valuations, or investment strategies."
    )

# Schema Tool 3
class WebSearchSchema(BaseModel):
    query: str = Field(
        ...,
        description="Search query to look up factual information, the latest news, benchmarks, or product specifications on the internet."
    )


# ==========================================
# TICKET SUPPORT AGENT SCHEMAS
# ==========================================

class TicketState(TypedDict):
    """State exclusively for the Ticket Support Agent."""
    messages: Annotated[List[AnyMessage], add_messages]
    current_iteration: int
    max_iterations: int
    session_id: str

class CreateTicketSchema(BaseModel):
    """Schema for creating a new IT support ticket."""
    user_id: str = Field(
        default="unknown_user", 
        description="The ID of the user. Can be default if not explicitly provided."
    )
    email: str = Field(
        default="unknown@fpt.com", 
        description="The email of the user. Can be default if not explicitly provided."
    )
    issue_category: str = Field(
        ..., 
        description="The category of the issue (e.g., 'Hardware', 'Software', 'Network', 'Access')."
    )
    description: str = Field(
        ..., 
        description="A detailed description of the user's technical issue."
    )

class CheckTicketSchema(BaseModel):
    """Schema for checking the status of an existing ticket."""
    ticket_id: str = Field(
        ..., 
        description="The unique ticket identifier (e.g., 'TKT-XXXXXX')."
    )


# ==========================================
# BOOKING AGENT SCHEMAS
# ==========================================

class BookingState(TypedDict):
    """State exclusively for the Booking Agent."""
    messages: Annotated[List[AnyMessage], add_messages]
    current_iteration: int
    max_iterations: int
    session_id: str

class CreateBookingSchema(BaseModel):
    """Schema for creating a new room booking."""
    user_id: str = Field(
        default="unknown_user",
        description="The ID of the user. Can be default if not explicitly provided."
    )
    email: str = Field(
        default="unknown@fpt.com",
        description="The email of the user. Can be default if not explicitly provided."
    )
    room_name: str = Field(
        ..., 
        description="The name of the meeting room to book (e.g., 'Room A', 'Conference Room 1')."
    )
    start_time: str = Field(
        ..., 
        description="The start time of the booking (format: YYYY-MM-DD HH:MM)."
    )
    end_time: str = Field(
        ..., 
        description="The end time of the booking (format: YYYY-MM-DD HH:MM)."
    )

class CheckBookingSchema(BaseModel):
    """Schema for checking the status of an existing room booking."""
    booking_id: str = Field(
        ..., 
        description="The unique booking identifier (e.g., 'BKG-XXXXXX')."
    )