import sys
import os
import uuid
from typing import Literal

# ==========================================
# 1. PATH SETUP & IMPORTS
# ==========================================
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END

# Import configurations
from multi_agents.config.config import *
from multi_agents.config.variable import CHATBOT_MODEL
from multi_agents.schemas.schemas import AgenticState

# Import sub-agents
from multi_agents.agents.faq_agent import create_retrieval_agent
from multi_agents.agents.it_support_agent import create_it_support_agent
from multi_agents.agents.ticket_support_agent import create_ticket_support_agent
from multi_agents.agents.booking_agent import create_booking_agent

# Initialize sub-agents
faq_agent = create_retrieval_agent()
it_support_agent = create_it_support_agent()
ticket_agent = create_ticket_support_agent()
booking_agent = create_booking_agent()

# ==========================================
# 2. TRANSFER TOOLS FOR PRIMARY ASSISTANT
# ==========================================
# These tools allow the Primary Assistant to delegate tasks.

@tool
def transfer_to_faq_agent() -> str:
    """Use this to answer questions about internal company policies, rules, and HR documents."""
    return "Transferred to FAQ Agent"

@tool
def transfer_to_it_agent() -> str:
    """Use this to search the EXTERNAL web for public tech news, product specs, or market benchmarks."""
    return "Transferred to IT Support Agent"

@tool
def transfer_to_ticket_agent() -> str:
    """Use this to help the user create an IT support ticket or check ticket status."""
    return "Transferred to Ticket Support Agent"

@tool
def transfer_to_booking_agent() -> str:
    """Use this to help the user book a meeting room or check booking status."""
    return "Transferred to Booking Agent"

primary_tools = [
    transfer_to_faq_agent, 
    transfer_to_it_agent, 
    transfer_to_ticket_agent, 
    transfer_to_booking_agent
]

# ==========================================
# 3. NODE DEFINITIONS
# ==========================================

def primary_assistant_node(state: AgenticState) -> dict:
    """
    The Primary Assistant handles general chit-chat directly.
    If it needs specialized help, it calls a transfer tool.
    """
    llm = ChatOpenAI(model=CHATBOT_MODEL, temperature=0).bind_tools(primary_tools)
    
    system_prompt = (
        "You are a helpful and friendly Primary Assistant at FPT Software.\n"
        "Your job is to greet users, answer simple questions directly, and route complex tasks to your specialized team members using the provided transfer tools.\n"
        "If the user says 'Hello' or asks 'Who are you?', answer them directly and warmly WITHOUT calling any tools."
    )
    
    messages = [SystemMessage(content=system_prompt)] + state["messages"]
    response = llm.invoke(messages)
    
    return {"messages": [response]}

# Wrapper nodes for sub-agents
def execute_sub_agent(agent_app, state: AgenticState, agent_name: str) -> dict:
    """Helper to execute a sub-agent and manage state properly."""
    print(f"\n   [Primary] 🔀 Delegating to -> {agent_name}")
    
    last_message = state["messages"][-1]
    tool_messages = []

    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        for tool_call in last_message.tool_calls:
            tool_messages.append(
                ToolMessage(
                    content=f"Successfully transferred to {agent_name}",
                    name=tool_call["name"],
                    tool_call_id=tool_call["id"]
                )
            )

    # Pass the resolved history (including the ToolMessage) to the sub-agent
    initial_sub_state = {
        "messages": list(state["messages"]) + tool_messages,
        "current_iteration": 0,
        "max_iterations": 3,
        "session_id": state["session_id"]
    }
    
    result = agent_app.invoke(initial_sub_state)
    
    # Return the ToolMessages AND the sub-agent's final answer to the master state
    return {
        "messages": tool_messages + [result["messages"][-1]],
        "dialog_state": "pop"
    }

def faq_node(state: AgenticState) -> dict:
    return execute_sub_agent(faq_agent, state, "FAQ AGENT")

def it_support_node(state: AgenticState) -> dict:
    return execute_sub_agent(it_support_agent, state, "IT SUPPORT AGENT")

def ticket_node(state: AgenticState) -> dict:
    return execute_sub_agent(ticket_agent, state, "TICKET SUPPORT AGENT")

def booking_node(state: AgenticState) -> dict:
    return execute_sub_agent(booking_agent, state, "BOOKING AGENT")

# ==========================================
# 4. ROUTING LOGIC
# ==========================================

def route_primary_assistant(state: AgenticState) -> str:
    """
    Determines where to go after the Primary Assistant responds.
    """
    last_message = state["messages"][-1]
    
    # If the Primary Assistant called a transfer tool, route to that specific agent
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        tool_name = last_message.tool_calls[0]["name"]
        if tool_name == "transfer_to_faq_agent":
            return "enter_faq"
        elif tool_name == "transfer_to_it_agent":
            return "enter_it"
        elif tool_name == "transfer_to_ticket_agent":
            return "enter_ticket"
        elif tool_name == "transfer_to_booking_agent":
            return "enter_booking"
            
    # If no tools were called, it's a direct conversation (e.g., greeting). We end the turn.
    return END

# ==========================================
# 5. GRAPH COMPILATION
# ==========================================

def create_hierarchical_runner():
    """Builds and compiles the hierarchical master workflow."""
    builder = StateGraph(AgenticState)

    # Add Primary Assistant
    builder.add_node("primary_assistant", primary_assistant_node)

    # Add Sub-Agent Nodes
    builder.add_node("enter_faq", faq_node)
    builder.add_node("enter_it", it_support_node)
    builder.add_node("enter_ticket", ticket_node)
    builder.add_node("enter_booking", booking_node)

    # Set Entry Point
    builder.add_edge(START, "primary_assistant")

    # Primary routing conditional edges
    builder.add_conditional_edges(
        "primary_assistant",
        route_primary_assistant,
        {
            "enter_faq": "enter_faq",
            "enter_it": "enter_it",
            "enter_ticket": "enter_ticket",
            "enter_booking": "enter_booking",
            END: END
        }
    )

    # Sub-agents always return control back to the Primary Assistant
    builder.add_edge("enter_faq", "primary_assistant")
    builder.add_edge("enter_it", "primary_assistant")
    builder.add_edge("enter_ticket", "primary_assistant")
    builder.add_edge("enter_booking", "primary_assistant")

    return builder.compile()

# ==========================================
# 6. INTERACTIVE TESTING LOOP
# ==========================================

if __name__ == "__main__":
    app = create_hierarchical_runner()
    current_session = f"SESSION_{uuid.uuid4().hex[:6].upper()}"
    
    print("="*60)
    print("🚀 HIERARCHICAL MASTER CHATBOT INITIALIZED 🚀")
    print(f"🔑 Session ID: {current_session}")
    print("="*60)
    
    chat_history = []
    
while True:
        try:
            user_input = input("\nYou: ").strip()
            if user_input.lower() in ['quit', 'exit']:
                break
            if not user_input:
                continue

            chat_history.append(HumanMessage(content=user_input))
            initial_state = {
                "messages": chat_history,
                "dialog_state": [],
                "session_id": current_session
            }
            
            print("\n⏳ Primary Assistant is processing...")
            
            result = app.invoke(initial_state)
            
            # Extract the final answer and print
            assistant_message = result["messages"][-1]
            print(f"\n🤖 Assistant:\n{assistant_message.content}")
            print("-" * 60)
            
            # Cleanly append only the final text response to the chat history
            chat_history.append(assistant_message)

        except KeyboardInterrupt:
            sys.exit("\n\nProcess interrupted by user.")
        except Exception as e:
            print(f"\n❌ Error occurred: {e}")