import langchain

from multi_agents.schemas.schemas import AgenticState
from langchain_core.messages import AIMessage

def inject_user_info(state: AgenticState, result: AIMessage):
    """Automatically inject user_id and email into tool calls"""

    if hasattr(result, "tool_calls") and result.tool_calls:
        for tool_call in result.tool_calls:
            
            # Inject into tool calls that need user context
            if tool_call["name"] in [
                "ToTicketAssistant",
                "ToITAssistant",
                "ToBookingAssistant"
            ]:
                # Automatically add user_id and email from state
                tool_call["args"]["user_id"] = state["user_id"]

                if state.get("email"):
                    tool_call["args"]["email"] = state["email"]

    return result

def assistant_runable_with_user_infor(state: AgenticState):
    """Primary assistant with context injection"""

    # Bind tools for primary assistant
    
