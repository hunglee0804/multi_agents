from tkinter.dialog import Dialog
from typing import Annotated, Optional, List, TypedDict
from typing_extensions import TypedDict, Literal
from langchain_core.messages import AnyMessage, ToolMessage
from langgraph.graph import add_messages
from pydantic import EmailStr, BaseModel, Field

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
    conversation_id: str

    
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
# CONTEXT MANAGER SCHEMAS
# ==========================================
class UpdateContextSchema(BaseModel):
    """Schema for updating the conversation context (user identity)."""
    conversation_id: str = Field(..., description="The current conversation ID.")
    user_id: Optional[str]= Field(default=None, description="The user's ID if known.")
    email: Optional[str] = Field(default=None, description="The user's email if known.")

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
    conversation_id: str

class CreateTicketSchema(BaseModel):
    """Schema for creating a new IT support ticket."""
    content: str = Field(..., description="A short summary or title of the ticket content.")
    description: str = Field(..., description="A detailed description of the issue.")
    customer_name: str = Field(..., description="The full name of the customer.")
    customer_phone: str = Field(..., description="The phone number of the customer.")
    email: Optional[str] = Field(default=None, description="The email of the customer (optional).")

class CheckTicketSchema(BaseModel):
    """Schema for checking the status of an existing ticket."""
    ticket_id: str = Field(..., description="The unique ticket identifier (e.g., 'TKT-XXXXXX').")

class UpdateTicketStatusSchema(BaseModel):
    """Schema for updating the status of an existing ticket."""
    ticket_id: str = Field(..., description="The unique ticket identifier (e.g., 'TKT-XXXXXX').")
    new_status: str = Field(..., description="The new status. MUST be exactly one of: 'Pending', 'Resolving', 'Canceled', 'Finished'.")


# ==========================================
# BOOKING AGENT SCHEMAS
# ==========================================

class BookingState(TypedDict):
    """State exclusively for the Booking Agent."""
    messages: Annotated[List[AnyMessage], add_messages]
    current_iteration: int
    max_iterations: int
    conversation_id: str # ĐÃ SỬA SESSION_ID THÀNH CONVERSATION_ID Ở ĐÂY

class CreateBookingSchema(BaseModel):
    """Schema for creating a new booking."""
    customer_name: str = Field(..., description="The full name of the customer.")
    customer_phone: str = Field(..., description="The phone number of the customer.")
    email: Optional[str] = Field(default=None, description="The email of the customer (optional).")
    reason: str = Field(..., description="The reason or purpose for the booking.")
    time: str = Field(..., description="The requested booking time (format: YYYY-MM-DD HH:MM).")
    note: Optional[str] = Field(default=None, description="Any additional notes or special requests (optional).")

class CheckBookingSchema(BaseModel):
    """Schema for checking the status of an existing booking."""
    booking_id: str = Field(..., description="The unique booking identifier (e.g., 'BKG-XXXXXX').")

class UpdateBookingStatusSchema(BaseModel):
    """Schema for updating the status of an existing booking."""
    booking_id: str = Field(..., description="The unique booking identifier (e.g., 'BKG-XXXXXX').")
    new_status: str = Field(..., description="The new status. MUST be exactly one of: 'Scheduled', 'Canceled', 'Finished'.")

# Add CompleteOrEscalate Schema
class CompleteOrEscalate(BaseModel):
    """A tool to mark the current task as completed and/or to escalate control of the dialog to the main assistant."""
    cancel: bool = Field(False, description="Set to True if canceled or escalated, False if successfully completed.")
    reason: str = Field(
        ..., 
        description="The FULL, DETAILED, and FRIENDLY final answer to display to the user. Put your entire conversational response here, NOT just a short summary!"
    )