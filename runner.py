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
from langgraph.checkpoint.memory import MemorySaver

from multi_agents.config.config import *
from multi_agents.config.variable import CHATBOT_MODEL
from multi_agents.schemas.schemas import AgenticState

from multi_agents.agents.faq_agent import create_retrieval_agent
from multi_agents.agents.it_support_agent import create_it_support_agent
from multi_agents.agents.ticket_support_agent import create_ticket_support_agent
from multi_agents.agents.booking_agent import create_booking_agent

faq_agent = create_retrieval_agent()
it_support_agent = create_it_support_agent()
ticket_agent = create_ticket_support_agent()
booking_agent = create_booking_agent()

# ==========================================
# 2. TRANSFER TOOLS FOR PRIMARY ASSISTANT
# ==========================================

@tool
def transfer_to_faq_agent() -> str:
    """Transfer to FAQ Agent for internal company policies, rules, and HR documents."""
    return "Transferred to FAQ Agent"

@tool
def transfer_to_it_agent() -> str:
    """Transfer to IT Support Agent for EXTERNAL web search, tech news, or benchmarks."""
    return "Transferred to IT Support Agent"

@tool
def transfer_to_ticket_agent() -> str:
    """Transfer to Ticket Support Agent to create IT tickets or check ticket status."""
    return "Transferred to Ticket Support Agent"

@tool
def transfer_to_booking_agent() -> str:
    """Transfer to Booking Agent to book a meeting room or check booking status."""
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
    llm = ChatOpenAI(model=CHATBOT_MODEL, temperature=0).bind_tools(primary_tools)
    
    # PROMPT ĐƯỢC SIẾT CHẶT ĐỂ CHỮA BỆNH "LANH CHANH"
    system_prompt = (
        "You are the Primary Routing Assistant at FPT Software.\n"
        "Your ONLY jobs are:\n"
        "1. Greet the user or answer basic chit-chat directly.\n"
        "2. If the user wants to do ANY specific task (e.g., book a room, create a ticket, ask about policies, search the web, check status), YOU MUST IMMEDIATELY CALL THE CORRECT TRANSFER TOOL.\n"
        "CRITICAL WARNING: DO NOT ask the user for details (like their name, room name, issue description, or date) before transferring. Just call the transfer tool immediately and let the specialized agent handle the data collection!"
    )
    
    messages = [SystemMessage(content=system_prompt)] + state["messages"]
    response = llm.invoke(messages)
    return {"messages": [response]}

def execute_sub_agent(agent_app, state: AgenticState, agent_name: str, node_name: str) -> dict:
    print(f"\n   [System] 🔄 Executing {agent_name}...")
    
    last_message = state["messages"][-1]
    tool_messages = []
    
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        for tool_call in last_message.tool_calls:
            tool_messages.append(
                ToolMessage(
                    content=f"Successfully transferred to {agent_name}.",
                    name=tool_call["name"],
                    tool_call_id=tool_call["id"]
                )
            )

    initial_sub_state = {
        "messages": list(state["messages"]) + tool_messages,
        "current_iteration": 0,
        "max_iterations": 7, # ⬆️ INCREASED: Give the agent more loops for complex update/delete tasks
        "conversation_id": state.get("conversation_id", "default")
    }
    
    result = agent_app.invoke(initial_sub_state)
    
    final_message = result["messages"][-1]
    cleanup_messages = []
    
    # 🛟 SAFETY NET: Catch dangling tool calls if the agent gets forced to stop
    # This prevents the OpenAI Error 400 crash on the next turn
    if hasattr(final_message, "tool_calls") and final_message.tool_calls:
        print(f"\n   [System] ⚠️ Intercepted dangling tool calls from {agent_name}. Applying safety net.")
        for tool_call in final_message.tool_calls:
            cleanup_messages.append(
                ToolMessage(
                    content="Agent stopped to ask for user confirmation or reached max iterations.",
                    name=tool_call["name"],
                    tool_call_id=tool_call["id"]
                )
            )

    # Append the final message AND any safety net cleanups
    updates = {"messages": tool_messages + [final_message] + cleanup_messages}
    
    current_dialog = state.get("dialog_state", [])
    if not current_dialog or current_dialog[-1] != node_name:
        updates["dialog_state"] = node_name
        
    return updates

def faq_node(state: AgenticState) -> dict: return execute_sub_agent(faq_agent, state, "FAQ AGENT", "enter_faq")
def it_support_node(state: AgenticState) -> dict: return execute_sub_agent(it_support_agent, state, "IT SUPPORT AGENT", "enter_it")
def ticket_node(state: AgenticState) -> dict: return execute_sub_agent(ticket_agent, state, "TICKET SUPPORT AGENT", "enter_ticket")
def booking_node(state: AgenticState) -> dict: return execute_sub_agent(booking_agent, state, "BOOKING AGENT", "enter_booking")

def leave_skill(state: AgenticState) -> dict:
    print("\n   [System] 🔙 Task completed. Returning to Primary Assistant (leave_skill)...")
    return {"dialog_state": "pop"}

# NODE MỚI ĐỂ CHỮA BỆNH MẮC KẸT
def force_leave_skill(state: AgenticState) -> dict:
    print("\n   [System] 🔙 Context switch detected! Forcefully leaving current skill...")
    return {"dialog_state": "pop"}

# ==========================================
# 4. CONDITIONAL ROUTING LOGIC
# ==========================================

def route_start(state: AgenticState) -> str:
    """Route directly to the active agent or intercept context switches."""
    if state.get("dialog_state"):
        active_agent = state["dialog_state"][-1]
        user_msg = state["messages"][-1].content
        
        # --- SUPER CONTEXT SWITCH DETECTOR ---
        # Máy dò đã được nâng cấp: Định nghĩa rõ ràng "lãnh thổ" của từng Agent
        llm = ChatOpenAI(model=CHATBOT_MODEL, temperature=0)
        switch_prompt = (
            f"CURRENT AGENT: {active_agent}\n"
            f"USER MESSAGE: '{user_msg}'\n\n"
            "SYSTEM DOMAINS:\n"
            "- enter_booking: Booking meeting rooms, changing room schedules.\n"
            "- enter_ticket: Creating IT helpdesk tickets, hardware issues, PC problems.\n"
            "- enter_faq: Company policies, HR rules, overtime.\n"
            "- enter_it: External web search, tech news.\n\n"
            "TASK: Does the user's message explicitly request a task that belongs to a DIFFERENT domain than the CURRENT AGENT?\n"
            "If YES (context switch), reply ONLY with 'YES'.\n"
            "If NO (stay in current context), reply ONLY with 'NO'."
        )
        response = llm.invoke([SystemMessage(content=switch_prompt)]).content.strip().upper()
        
        if "YES" in response:
            print(f"\n   [Router] 🔄 Context switch detected! Interrupting {active_agent}.")
            return "force_leave_skill"
        # -------------------------------------
            
        print(f"\n   [Router] 📍 Resuming conversation with: {active_agent}")
        return active_agent
        
    print("\n   [Router] 📍 Routing to Primary Assistant")
    return "primary_assistant"

def route_primary_assistant(state: AgenticState) -> str:
    """Route to the specific sub-agent node if a tool was called."""
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        tool_name = last_message.tool_calls[0]["name"]
        if tool_name == "transfer_to_faq_agent": return "enter_faq"
        elif tool_name == "transfer_to_it_agent": return "enter_it"
        elif tool_name == "transfer_to_ticket_agent": return "enter_ticket"
        elif tool_name == "transfer_to_booking_agent": return "enter_booking"
    return END

def route_sub_agent(state: AgenticState) -> str:
    """
    Evaluates if the sub-agent should stay active or return to Primary.
    """
    last_message = state["messages"][-1].content
    
    # Mở rộng bộ từ khóa để bao trùm mọi câu thông báo hoàn thành của Agent
    completion_keywords = [
        "Successfully created", "Successfully booked", "Successfully updated", 
        "has been created", "has been canceled", "has been updated", "canceled", "confirmed"
    ]
    
    if any(keyword in last_message for keyword in completion_keywords):
        return "leave_skill"
        
    if "?" in last_message:
        return END
        
    return "leave_skill"

# ==========================================
# 5. GRAPH COMPILATION WITH CHECKPOINTER
# ==========================================

def create_hierarchical_runner():
    builder = StateGraph(AgenticState)

    builder.add_node("primary_assistant", primary_assistant_node)
    builder.add_node("enter_faq", faq_node)
    builder.add_node("enter_it", it_support_node)
    builder.add_node("enter_ticket", ticket_node)
    builder.add_node("enter_booking", booking_node)
    builder.add_node("leave_skill", leave_skill)
    builder.add_node("force_leave_skill", force_leave_skill) # THÊM NODE MỚI

    builder.add_conditional_edges(START, route_start)

    builder.add_conditional_edges(
        "primary_assistant", 
        route_primary_assistant, 
        ["enter_faq", "enter_it", "enter_ticket", "enter_booking", END]
    )

    sub_agents = ["enter_faq", "enter_it", "enter_ticket", "enter_booking"]
    for agent in sub_agents:
        builder.add_conditional_edges(agent, route_sub_agent, ["leave_skill", END])

    builder.add_edge("leave_skill", "primary_assistant")
    builder.add_edge("force_leave_skill", "primary_assistant") # KẾT NỐI NODE MỚI

    memory = MemorySaver()
    return builder.compile(checkpointer=memory)

# ==========================================
# 6. INTERACTIVE TESTING LOOP
# ==========================================

if __name__ == "__main__":
    app = create_hierarchical_runner()
    current_conversation_id = f"SESSION_{uuid.uuid4().hex[:6].upper()}"
    
    config = {"configurable": {"thread_id": current_conversation_id}}
    
    print("="*60)
    print("🚀 HIERARCHICAL MASTER CHATBOT INITIALIZED (WITH MEMORY) 🚀")
    print(f"🔑 Conversation ID: {current_conversation_id}")
    print("="*60)
    
    while True:
        try:
            user_input = input("\nYou: ").strip()
            if user_input.lower() in ['quit', 'exit']:
                break
            if not user_input:
                continue

            input_state = {
                "messages": [HumanMessage(content=user_input)],
                "conversation_id": current_conversation_id
            }
            
            result = app.invoke(input_state, config=config)
            
            assistant_message = result["messages"][-1]
            print(f"\n🤖 Assistant:\n{assistant_message.content}")
            print("-" * 60)

        except KeyboardInterrupt:
            sys.exit("\n\nProcess interrupted by user.")
        except Exception as e:
            print(f"\n❌ Error occurred: {e}")