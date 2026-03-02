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

# Initialize the LLM and bind the ticket tools
llm = ChatOpenAI(model=CHATBOT_MODEL, temperature=0)
llm_with_tools = llm.bind_tools(TICKET_ALL_TOOLS)

# ==========================================
# NODE DEFINITIONS
# ==========================================

def reasoner_node(state: TicketState) -> dict:
    """
    The core reasoning node for the Ticket Support Agent.
    It evaluates the conversation history and decides whether to call a tool or respond directly.
    """
    messages = state["messages"]
    
    # Ensure the SystemMessage is present to strictly guide the agent's behavior
    if not any(isinstance(m, SystemMessage) for m in messages):
        messages = [SystemMessage(content=TICKET_AGENT_PROMPT)] + messages

    # Invoke the LLM with the bound tools
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
    
    # 1. Hard stop to prevent infinite loops and save API tokens
    if state.get("current_iteration", 0) >= state.get("max_iterations", MAX_ITERATIONS):
        print("\n   [TICKET SYSTEM] ⚠️ Max iterations reached. Forcing the agent to stop.")
        return "end"

    # 2. If the LLM decided to call a tool, route to the 'tools' node
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "use_tools"

    # 3. Otherwise, the LLM has generated a final response for the user
    return "end"

# ==========================================
# GRAPH COMPILATION
# ==========================================

def create_ticket_support_agent():
    """
    Builds and compiles the LangGraph workflow for the Ticket Support Agent.
    Returns a compiled, runnable application.
    """
    workflow = StateGraph(TicketState)
    
    # Add all necessary nodes
    workflow.add_node("reasoner", reasoner_node)
    workflow.add_node("tools", ToolNode(TICKET_ALL_TOOLS))

    # Set the starting point
    workflow.set_entry_point("reasoner")

    # Add conditional edges from the reasoner to evaluate the LLM's decision
    workflow.add_conditional_edges(
        "reasoner",
        should_continue,
        {
            "use_tools": "tools",
            "end": END
        }
    )

    # After a tool executes (e.g., database query), always return to the reasoner to analyze the result
    workflow.add_edge("tools", "reasoner")

    # Compile the graph
    app = workflow.compile()
    
    return app