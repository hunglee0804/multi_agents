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
from multi_agents.schemas.schemas import AgenticState, CompleteOrEscalate

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
    
    system_prompt = (
        "You are the Primary Routing Assistant at FPT Software. "
        "Your capabilities are STRICTLY limited to exactly 4 domains:\n"
        "1. Booking meeting rooms or checking room status (transfer_to_booking_agent).\n"
        "2. Creating IT support tickets or checking ticket status (transfer_to_ticket_agent).\n"
        "3. Answering internal company policies, HR rules, or guidelines (transfer_to_faq_agent).\n"
        "4. Searching the EXTERNAL web for public tech news or benchmarks (transfer_to_it_agent).\n\n"
        
        "CRITICAL RULES:\n"
        "- OUT-OF-SCOPE & CHIT-CHAT: If the user says hello, or asks to do something OUTSIDE your 4 domains (e.g., ordering food, booking flights, personal advice), answer DIRECTLY. Politely decline and state what you can actually do. DO NOT call any transfer tools.\n"
        "- IN-SCOPE TASKS: If the request matches a domain, IMMEDIATELY call the correct transfer tool. DO NOT ask the user for specific details (like name, time, room, issue description) yourself. The specialized agent will do that.\n"
        "- MULTIPLE TASKS AT ONCE: If the user asks for multiple things in one sentence (e.g., 'book a room and log a ticket'), DO NOT call multiple tools at once. Call the transfer tool for the FIRST task ONLY, and politely tell the user you will handle the first task now and the second task later."
        "- RETURNING FROM AGENT: If the conversation already contains a completed answer from a specialized agent, "
        "DO NOT re-route. Present the result naturally and wait for the user's next request.\n"
        "- CHIT-CHAT AFTER TASK: If the user sends a greeting or off-topic message after a task is completed, "
        "answer it DIRECTLY yourself. Never call a transfer tool for greetings or casual messages."
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
        "max_iterations": 3,
        "conversation_id": state.get("conversation_id", "default")
    }
    
    result = agent_app.invoke(initial_sub_state)
    
    final_message = result["messages"][-1]
    cleanup_messages = []
    
    # 🛟 SAFETY NET: Only intercept NON-CompleteOrEscalate dangling tool calls
    if hasattr(final_message, "tool_calls") and final_message.tool_calls:
        non_escalate_calls = [
            tc for tc in final_message.tool_calls 
            if tc["name"] != "CompleteOrEscalate"  # <-- KEY FIX
        ]
        if non_escalate_calls:
            print(f"\n   [System] ⚠️ Intercepted dangling tool calls from {agent_name}. Applying safety net.")
            for tool_call in non_escalate_calls:
                cleanup_messages.append(
                    ToolMessage(
                        content="Agent stopped to ask for user confirmation or reached max iterations.",
                        name=tool_call["name"],
                        tool_call_id=tool_call["id"]
                    )
                )

    updates = {"messages": tool_messages + [final_message] + cleanup_messages}
    
    current_dialog = state.get("dialog_state", [])
    if not current_dialog or current_dialog[-1] != node_name:
        updates["dialog_state"] = node_name

    # if not (hasattr(final_message, "tool_calls") and final_message.tool_calls):
    #     updates["dialog_state"] = "pop"
        
    return updates

def faq_node(state: AgenticState) -> dict: return execute_sub_agent(faq_agent, state, "FAQ AGENT", "enter_faq")
def it_support_node(state: AgenticState) -> dict: return execute_sub_agent(it_support_agent, state, "IT SUPPORT AGENT", "enter_it")
def ticket_node(state: AgenticState) -> dict: return execute_sub_agent(ticket_agent, state, "TICKET SUPPORT AGENT", "enter_ticket")
def booking_node(state: AgenticState) -> dict: return execute_sub_agent(booking_agent, state, "BOOKING AGENT", "enter_booking")

def leave_skill(state: AgenticState) -> dict:
    """Pop the dialog state, resolve CompleteOrEscalate tool call, and preserve agent's exact answer."""
    print("\n   [System] 🔙 Task completed. Releasing control (leave_skill)...")
    messages = []
    last_message = state["messages"][-1]
    
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        for tool_call in last_message.tool_calls:
            if tool_call["name"] == "CompleteOrEscalate":
                # Lấy câu trả lời gốc của Sub-Agent từ args của tool
                final_answer = tool_call["args"].get("reason", "Task completed.")
                
                # 1. Trả về ToolMessage để thỏa mãn tool_call
                messages.append(
                    ToolMessage(
                        content="Successfully exited sub-agent.",
                        name=tool_call["name"],
                        tool_call_id=tool_call["id"]
                    )
                )
                # 2. Thêm một AIMessage chứa đúng nguyên văn câu trả lời (giữ nguyên link, format)
                from langchain_core.messages import AIMessage
                messages.append(AIMessage(content=final_answer))
                
    return {"dialog_state": "pop", "messages": messages}

def force_leave_skill(state: AgenticState) -> dict:
    # print("\n   [System] 🔙 Context switch detected! Forcefully leaving current skill...")
    return {"dialog_state": "pop"}

# ==========================================
# 4. CONDITIONAL ROUTING LOGIC
# ==========================================

def route_start(state: AgenticState) -> str:
    """Route directly to the active agent. No LLM detector needed here anymore!"""
    if state.get("dialog_state"):
        active_agent = state["dialog_state"][-1]
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
    Evaluates if ANY sub-agent called the CompleteOrEscalate tool to return to Primary.
    Works universally for FAQ, IT, Ticket, and Booking agents!
    """
    last_message = state["messages"][-1]
    active_agent = state.get("dialog_state", [])[-1] if state.get("dialog_state") else "Unknown Agent"
    
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        if last_message.tool_calls[0]["name"] == "CompleteOrEscalate":
            print(f"\n   [Router] ✅ {active_agent} triggered CompleteOrEscalate. Popping state.")
            return "leave_skill"
            
    print(f"\n   [Router] ⏳ {active_agent} needs more info. Waiting for user input.")
    return END

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
    builder.add_node("force_leave_skill", force_leave_skill) 

    builder.add_conditional_edges(START, route_start)

    builder.add_conditional_edges(
        "primary_assistant", 
        route_primary_assistant, 
        ["enter_faq", "enter_it", "enter_ticket", "enter_booking", END]
    )

    sub_agents = ["enter_faq", "enter_it", "enter_ticket", "enter_booking"]
    for agent in sub_agents:
        builder.add_conditional_edges(agent, route_sub_agent, ["leave_skill", END])

    builder.add_edge("leave_skill", END)
    builder.add_edge("force_leave_skill", END)

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