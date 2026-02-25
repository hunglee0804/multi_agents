from typing import Annotated, Optional
from langchain_core.messages import ToolMessage
from schemas.schemas import AgenticState

def update_dialog_stack(left: list[str], right: Optional[str]) -> list[str]:
    """Push or pop dialog stack"""

    if right is None:
        return left
    if right == "pop":
        return left[:-1] # Pop: return to previous agent
    
    return left + [right] # Push: add new agent to stack


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


