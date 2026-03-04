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
from multi_agents.config.prompt import TICKET_AGENT_PROMPT
from multi_agents.schemas.schemas import TicketState
from multi_agents.tools.ticket_tool import TICKET_ALL_TOOLS

# NEW IMPORTS FOR CONTEXT
from multi_agents.tools.context_tool import update_context_tool
from multi_agents.context_injection.context_manager import get_conversation_context

# Combine ticket tools with the new context tool
ALL_TOOLS = TICKET_ALL_TOOLS + [update_context_tool]

# Initialize the LLM and bind the combined tools
llm = ChatOpenAI(model=CHATBOT_MODEL, temperature=0)
llm_with_tools = llm.bind_tools(ALL_TOOLS)

# ==========================================
# NODE DEFINITIONS
# ==========================================

def reasoner_node(state: TicketState) -> dict:
    """
    The core reasoning node for the Ticket Support Agent.
    Now injected with Conversation Context Memory.
    """
    messages = list(state["messages"]) # Create a safe copy
    session_id = state.get("session_id", "default_session")
    
    # Retrieve memory from Database
    context_data = get_conversation_context(session_id)
    
    # Build the context injection string
    context_msg = f"\n\n--- DATABASE CONTEXT (Session: {session_id}) ---\n"
    if context_data:
        context_msg += f"Known User ID: {context_data.get('user_id', 'Unknown')}\n"
        context_msg += f"Known Email: {context_data.get('email', 'Unknown')}\n"
        context_msg += f"Saved Params: {context_data.get('extracted_parameters', {})}\n"
    else:
        context_msg += "No prior data saved yet.\n"
    
    context_msg += "\nINSTRUCTION: If you learn new details (like user_id, email, or issue category), use 'update_context_tool' to save them. Use the known data above to avoid asking the user again for information they already provided!"

    # Override/Inject the SystemMessage
    full_prompt = TICKET_AGENT_PROMPT + context_msg
    if messages and isinstance(messages[0], SystemMessage):
        messages[0] = SystemMessage(content=full_prompt)
    else:
        messages.insert(0, SystemMessage(content=full_prompt))

    # Invoke the LLM
    response = llm_with_tools.invoke(messages)
    
    return {
        "messages": [response],
        "current_iteration": state.get("current_iteration", 0) + 1
    }

def should_continue(state: TicketState) -> str:
    """
    Routing logic to determine the next step in the LangGraph workflow.
    """
    last_message = state["messages"][-1]
    
    # Hard stop to prevent infinite loops
    if state.get("current_iteration", 0) >= state.get("max_iterations", MAX_ITERATIONS):
        print("\n   [TICKET SYSTEM] ⚠️ Max iterations reached. Forcing the agent to stop.")
        return "end"

    # If the LLM decided to call a tool, route to the 'tools' node
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "use_tools"

    return "end"

# ==========================================
# GRAPH COMPILATION
# ==========================================

def create_ticket_support_agent():
    """
    Builds and compiles the LangGraph workflow for the Ticket Support Agent.
    """
    workflow = StateGraph(TicketState)
    
    workflow.add_node("reasoner", reasoner_node)
    workflow.add_node("tools", ToolNode(ALL_TOOLS)) # Use ALL_TOOLS here

    workflow.set_entry_point("reasoner")

    workflow.add_conditional_edges(
        "reasoner",
        should_continue,
        {
            "use_tools": "tools",
            "end": END
        }
    )

    workflow.add_edge("tools", "reasoner")

    app = workflow.compile()
    
    return app