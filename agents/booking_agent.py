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
from langgraph.checkpoint.memory import MemorySaver

# Import project configurations and modules
from multi_agents.config.variable import CHATBOT_MODEL, MAX_ITERATIONS
from multi_agents.config.prompt import BOOKING_AGENT_PROMPT
from multi_agents.schemas.schemas import BookingState, CompleteOrEscalate
from multi_agents.tools.booking_tool import BOOKING_ALL_TOOLS
from multi_agents.tools.context_tool import update_context_tool
from multi_agents.context_injection.context_manager import get_conversation_context

# Combine booking tools with the new context tool
safe_tools = [BOOKING_ALL_TOOLS[1], update_context_tool, CompleteOrEscalate] # check_booking
sensitive_tools = [BOOKING_ALL_TOOLS[0], BOOKING_ALL_TOOLS[2]] # create, update
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
        
        "\nCRITICAL INSTRUCTION 2: STRICT TOOL CALLING RULES:\n"
        "- If you need to ask for missing info, confirm details, or say 'I will proceed', just reply with NORMAL TEXT. DO NOT call any tools.\n"
        "- To perform the actual action, you MUST call the specific database tool (e.g., create_booking_tool or create_ticket_tool).\n"
        "- NEVER call 'CompleteOrEscalate' to say you are 'proceeding' or 'attempting' to do something.\n"
        "- ONLY call 'CompleteOrEscalate' AFTER you have actually called the database tool, received the successful DB response, and want to end the task. Put your final summary in the 'reason' parameter."
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
    last_message = state["messages"][-1]
    
    if state.get("current_iteration", 0) >= state.get("max_iterations", MAX_ITERATIONS):
        return "end"

    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        tool_name = last_message.tool_calls[0]["name"]
        if tool_name == "CompleteOrEscalate":
            return "end"
        if tool_name in [t.name for t in sensitive_tools]:
            return "sensitive_tools"
        return "safe_tools"
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
    
    workflow.add_node("reasoner", reasoner_node)
    workflow.add_node("safe_tools", ToolNode(safe_tools))
    workflow.add_node("sensitive_tools", ToolNode(sensitive_tools))

    workflow.set_entry_point("reasoner")
    workflow.add_conditional_edges("reasoner", should_continue, {
        "safe_tools": "safe_tools",
        "sensitive_tools": "sensitive_tools",
        "end": END
    })
    workflow.add_edge("safe_tools", "reasoner")
    workflow.add_edge("sensitive_tools", "reasoner")

    ENABLE_HITL = True
    interrupts = ["sensitive_tools"] if ENABLE_HITL else []
    memory = MemorySaver()
    app = workflow.compile(checkpointer=memory, interrupt_before=interrupts)
    
    return app