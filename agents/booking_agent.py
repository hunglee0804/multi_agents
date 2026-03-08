import os
import sys

# ==========================================
# PATH SETUP TO ALLOW ABSOLUTE IMPORTS
# ==========================================
# Go UP one level ("..") to reach the directory containing 'multi_agents'
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

# Import project configurations and modules
from multi_agents.config.variable import CHATBOT_MODEL, MAX_ITERATIONS
from multi_agents.config.prompt import BOOKING_AGENT_PROMPT
from multi_agents.schemas.schemas import BookingState, CompleteOrEscalate
from multi_agents.tools.booking_tool import BOOKING_ALL_TOOLS
from multi_agents.tools.context_tool import update_context_tool
from multi_agents.context_injection.context_manager import get_conversation_context

# Combine booking tools with the new context tool
ALL_TOOLS = BOOKING_ALL_TOOLS + [update_context_tool]+ [CompleteOrEscalate]

# Initialize the LLM and bind the booking tools
llm = ChatOpenAI(model=CHATBOT_MODEL, temperature=0)
llm_with_tools = llm.bind_tools(ALL_TOOLS )

# ==========================================
# NODE DEFINITIONS
# ==========================================

def reasoner_node(state: BookingState) -> dict:
    messages = list(state["messages"]) # Tạo bản sao để an toàn
    conversation_id = state.get("conversation_id", "default_session")
    
    # Take the memory from Database
    context_data = get_conversation_context(conversation_id)
    context_msg = f"\n\n--- DATABASE CONTEXT (Conversation: {conversation_id}) ---\n"  # ADD THIS LINE
    if context_data:
        context_msg += f"Known User ID / Name: {context_data.get('user_id', 'Unknown')}\n"
        context_msg += f"Known Email: {context_data.get('email', 'Unknown')}\n"
    else:
        context_msg += "No user identity saved yet.\n"
    
    context_msg += (
        "\nCRITICAL INSTRUCTION 1: If the user provides their Name or Email, "
        "you MUST call 'update_context_tool' IMMEDIATELY before answering! "
        f"Use '{conversation_id}' as the conversation_id. "
        "If their name is known, do not ask for it again.\n"
        
        "\nCRITICAL INSTRUCTION 2: If you need to ask the user for missing information, "
        "DO NOT call any tools. Just reply with a normal conversational text message. "
        "ONLY call the 'CompleteOrEscalate' tool AFTER you have successfully executed a database tool (like creating/updating a ticket) "
        "OR if the user explicitly wants to cancel the request. Once finished, put your final success message in the 'reason' parameter of CompleteOrEscalate."
    )

    # Override SystemMessage to always update the latest memory
    full_prompt = BOOKING_AGENT_PROMPT + context_msg
    if messages and isinstance(messages[0], SystemMessage):
        messages[0] = SystemMessage(content=full_prompt)
    else:
        messages.insert(0, SystemMessage(content=full_prompt))

    response = llm_with_tools.invoke(messages)
    
    return {
        "messages": [response],
        "current_iteration": state.get("current_iteration", 0) + 1
    }

def should_continue(state: BookingState) -> str:
    """
    Routing logic to determine the next step in the LangGraph workflow.
    """
    last_message = state["messages"][-1]
    
    # Hard stop to prevent infinite loops
    if state.get("current_iteration", 0) >= state.get("max_iterations", MAX_ITERATIONS):
        # print("\n   [BOOKING SYSTEM] ⚠️ Max iterations reached. Forcing the agent to stop.")
        return "end"

    # If the LLM decided to call a tool, route to the 'tools' node
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        if last_message.tool_calls[0]["name"] == "CompleteOrEscalate":
            return "end"
        return "use_tools"

    # Otherwise, the LLM has generated a final response
    return "end"

# ==========================================
# GRAPH COMPILATION
# ==========================================

def create_booking_agent():
    """
    Builds and compiles the LangGraph workflow for the Booking Agent.
    Returns a compiled, runnable application.
    """
    workflow = StateGraph(BookingState)
    
    # Add nodes
    workflow.add_node("reasoner", reasoner_node)
    workflow.add_node("tools", ToolNode(ALL_TOOLS))

    # Set entry point
    workflow.set_entry_point("reasoner")

    # Add conditional edges from the reasoner
    workflow.add_conditional_edges(
        "reasoner",
        should_continue,
        {
            "use_tools": "tools",
            "end": END
        }
    )

    # Return to reasoner after tool execution
    workflow.add_edge("tools", "reasoner")

    # Compile the graph
    app = workflow.compile()
    
    return app