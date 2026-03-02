import sys
import os
import operator
from typing import Annotated, Sequence, TypedDict, Literal
import uuid

# ==========================================
# 1. PATH SETUP & IMPORTS
# ==========================================

# Add project root to sys.path to allow absolute imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel

# Import environment configurations
from multi_agents.config.config import * 
from multi_agents.config.variable import CHATBOT_MODEL

# Import compiled sub-agents
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
# 2. SUPERVISOR STATE & SCHEMAS
# ==========================================

class SupervisorState(TypedDict):
    """Shared state for the master routing graph."""
    # The history of all conversation messages
    messages: Annotated[Sequence[BaseMessage], operator.add]
    # The identifier of the next agent to be called
    next: str
    session_id: str

class RouterSchema(BaseModel):
    """Schema to strictly enforce the LLM's routing decisions."""
    # FUTURE: Add "ticket_agent" and "booking_agent" to this Literal list
    next: Literal["FINISH", "faq_agent", "it_support_agent", "ticket_agent", "booking_agent"]

# ==========================================
# 3. NODE DEFINITIONS
# ==========================================

def supervisor_node(state: SupervisorState) -> dict:
    """
    The Supervisor analyzes the conversation and decides which agent to call next.
    It uses structured output to guarantee a valid routing decision.
    """
    llm = ChatOpenAI(model=CHATBOT_MODEL, temperature=0)
    
    # System prompt ĐÃ ĐƯỢC TỐI ƯU HÓA RẤT MẠNH ĐỂ CHỐNG XUNG ĐỘT NGỮ NGHĨA
    system_prompt = (
        "You are a Master Supervisor managing a team of specialized AI agents.\n"
        "Your team members are:\n"
        "- faq_agent: Specialized in reading internal company documents, policies, HR rules, and guidelines.\n"
        "- it_support_agent: Specialized ONLY in searching the EXTERNAL WEB for public information, market data, news, or product benchmarks using Tavily search. DO NOT use this for internal company IT issues.\n"
        "- ticket_agent: Specialized in Internal IT Helpdesk. Route here IMMEDIATELY if the user wants to 'create a ticket', report a broken device (hardware/software), request IT support, or check ticket status in the database.\n"
        "- booking_agent: Specialized in Booking Management. Route here if the user wants to book a meeting room, schedule a workspace, or check room booking status.\n"
        "\n"
        "CRITICAL ROUTING RULES:\n"
        "1. If the user mentions 'ticket' (e.g., create, submit, check ticket) or reports a technical issue needing repair, YOU MUST ROUTE TO 'ticket_agent'.\n"
        "2. If the user asks to compare products or find news, ROUTE TO 'it_support_agent'.\n"
        "3. If the user's request has been fully answered in the conversation history, or if it is just a greeting/farewell, you MUST route to FINISH. Do NOT route back to an agent."
        "4. If the user's request has been fully answered in the conversation history, or if it is just a greeting/farewell, you MUST route to FINISH. Do NOT route back to an agent."
    )

    messages = [SystemMessage(content=system_prompt)] + state["messages"]
    
    # Enforce structured output based on RouterSchema
    response = llm.with_structured_output(RouterSchema).invoke(messages)
    
    return {"next": response.next}

def faq_node(state: SupervisorState) -> dict:
    """Wrapper node to execute the FAQ Agent subgraph."""
    print("\n   [Supervisor] 🔀 Routing to -> FAQ AGENT")
    initial_sub_state = {
        "messages": state["messages"],
        "current_iteration": 0,
        "max_iterations": 3
    }
    # Invoke the RAG sub-graph
    result = faq_agent.invoke(initial_sub_state)
    # Extract only the final response message to append to the master state
    return {"messages": [result["messages"][-1]]}

def it_support_node(state: SupervisorState) -> dict:
    """Wrapper node to execute the IT Support Agent subgraph."""
    print("\n   [Supervisor] 🔀 Routing to -> IT SUPPORT AGENT")
    initial_sub_state = {
        "messages": state["messages"],
        "current_iteration": 0,
        "max_iterations": 3
    }
    # Invoke the Tavily Search sub-graph
    result = it_support_agent.invoke(initial_sub_state)
    # Extract only the final response message to append to the master state
    return {"messages": [result["messages"][-1]]}

def ticket_node(state: SupervisorState) -> dict:
    """Wrapper node to execute the Ticket Support Agent subgraph."""
    print("\n   [Supervisor] 🔀 Routing to -> TICKET SUPPORT AGENT")
    initial_sub_state = {
        "messages": state["messages"],
        "current_iteration": 0,
        "max_iterations": 3
    }
    # Invoke the Ticket Database sub-graph
    result = ticket_agent.invoke(initial_sub_state)
    return {"messages": [result["messages"][-1]]}

def booking_node(state: SupervisorState) -> dict:
    """Wrapper node to execute the Booking Agent subgraph."""
    print("\n   [Supervisor] 🔀 Routing to -> BOOKING AGENT")
    initial_sub_state = {
        "messages": state["messages"],
        "current_iteration": 0,
        "max_iterations": 3,
        "session_id": state["session_id"]
    }
    result = booking_agent.invoke(initial_sub_state)
    return {"messages": [result["messages"][-1]]}

# ==========================================
# 4. GRAPH COMPILATION
# ==========================================

def create_master_runner():
    """Builds and compiles the master Supervisor workflow."""
    workflow = StateGraph(SupervisorState)

    # Add all nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("faq_agent", faq_node)
    workflow.add_node("it_support_agent", it_support_node)
    workflow.add_node("ticket_agent", ticket_node)
    workflow.add_node("booking_agent", booking_node)

    # Set the starting point
    workflow.add_edge(START, "supervisor")

    # Add conditional routing from the supervisor
    workflow.add_conditional_edges(
        "supervisor",
        lambda state: state["next"], # Extract the 'next' routing string
        {
            "faq_agent": "faq_agent",
            "it_support_agent": "it_support_agent",
            "ticket_agent": "ticket_agent",
            "booking_agent": "booking_agent",
            "FINISH": END
        }
    )

    # Route back to the supervisor after a sub-agent finishes its task
    workflow.add_edge("faq_agent", END)
    workflow.add_edge("it_support_agent", END)
    workflow.add_edge("ticket_agent", END)
    workflow.add_edge("booking_agent", END)

    return workflow.compile()

# ==========================================
# 5. INTERACTIVE TESTING LOOP
# ==========================================

if __name__ == "__main__":
    app = create_master_runner()
    current_session = f"SESSION_{uuid.uuid4().hex[:6].upper()}"
    print("="*60)
    print("🚀 MASTER CHATBOT RUNNER INITIALIZED 🚀")
    print("="*60)
    print("Type 'quit' or 'exit' to stop.\n")
    
    chat_history = []
    
    while True:
        try:
            user_input = input("\nYou: ").strip()
            
            if user_input.lower() in ['quit', 'exit']:
                print("Exiting Master Chatbot. Goodbye!")
                break
            if not user_input:
                continue

            # Append user input to history
            chat_history.append(HumanMessage(content=user_input))
            initial_state = {
                "messages": chat_history,
                "session_id": current_session
                }
            
            print("\n⏳ Supervisor is analyzing and routing...")
            
            # Execute the workflow
            result = app.invoke(initial_state)
            
            # The final response is the last message generated by the agents
            assistant_message = result["messages"][-1]
            print(f"\n🤖 Assistant:\n{assistant_message.content}")
            print("-" * 60)
            
            # Save assistant message to maintain conversational context
            chat_history.append(assistant_message)

        except KeyboardInterrupt:
            sys.exit("\n\nProcess interrupted by user. Goodbye!")
        except Exception as e:
            print(f"\n❌ Error occurred: {e}")