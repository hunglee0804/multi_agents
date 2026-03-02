import sys
import os
import operator
from typing import Annotated, Sequence, TypedDict, Literal

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

# FUTURE: Import new agents here when they are ready
# from multi_agents.agents.ticket_support_agent import create_ticket_support_agent
# from multi_agents.agents.booking_agent import create_booking_agent

# Initialize sub-agents
faq_agent = create_retrieval_agent()
it_support_agent = create_it_support_agent()
# FUTURE: ticket_support_agent = create_ticket_support_agent()
# FUTURE: booking_agent = create_booking_agent()

# ==========================================
# 2. SUPERVISOR STATE & SCHEMAS
# ==========================================

class SupervisorState(TypedDict):
    """Shared state for the master routing graph."""
    # The history of all conversation messages
    messages: Annotated[Sequence[BaseMessage], operator.add]
    # The identifier of the next agent to be called
    next: str

class RouterSchema(BaseModel):
    """Schema to strictly enforce the LLM's routing decisions."""
    # FUTURE: Add "ticket_agent" and "booking_agent" to this Literal list
    next: Literal["FINISH", "faq_agent", "it_support_agent"]

# ==========================================
# 3. NODE DEFINITIONS
# ==========================================

def supervisor_node(state: SupervisorState) -> dict:
    """
    The Supervisor analyzes the conversation and decides which agent to call next.
    It uses structured output to guarantee a valid routing decision.
    """
    llm = ChatOpenAI(model=CHATBOT_MODEL, temperature=0)
    
    # System prompt defining the exact roles of each sub-agent
    system_prompt = (
        "You are a master supervisor managing a team of specialized AI agents.\n"
        "Your team members are:\n"
        "- faq_agent: Specialized in searching internal company policies, rules, and local documents.\n"
        "- it_support_agent: Specialized in searching the web for real-time data, technical specs, and financial info.\n"
        # FUTURE: Add short descriptions for ticket_agent and booking_agent here
        "\n"
        "Analyze the user's latest message and route the request to the most appropriate agent.\n"
        "If the user's request has been fully answered, or if it is just a simple greeting/farewell, route to FINISH."
    )

    messages = [SystemMessage(content=system_prompt)] + state["messages"]
    
    # Enforce structured output based on RouterSchema
    response = llm.with_structured_output(RouterSchema).invoke(messages)
    
    return {"next": response.next}

def faq_node(state: SupervisorState) -> dict:
    """Wrapper node to execute the FAQ Agent subgraph."""
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
    initial_sub_state = {
        "messages": state["messages"],
        "current_iteration": 0,
        "max_iterations": 3
    }
    # Invoke the Tavily Search sub-graph
    result = it_support_agent.invoke(initial_sub_state)
    # Extract only the final response message to append to the master state
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
    # FUTURE: workflow.add_node("ticket_agent", ticket_node)
    # FUTURE: workflow.add_node("booking_agent", booking_node)

    # Set the starting point
    workflow.add_edge(START, "supervisor")

    # Add conditional routing from the supervisor
    workflow.add_conditional_edges(
        "supervisor",
        lambda state: state["next"], # Extract the 'next' routing string
        {
            "faq_agent": "faq_agent",
            "it_support_agent": "it_support_agent",
            # FUTURE: "ticket_agent": "ticket_agent",
            # FUTURE: "booking_agent": "booking_agent",
            "FINISH": END
        }
    )

    # Route back to the supervisor after a sub-agent finishes its task
    workflow.add_edge("faq_agent", END)
    workflow.add_edge("it_support_agent", END)
    # FUTURE: workflow.add_edge("ticket_agent", "supervisor")
    # FUTURE: workflow.add_edge("booking_agent", "supervisor")

    return workflow.compile()

# ==========================================
# 5. INTERACTIVE TESTING LOOP
# ==========================================

if __name__ == "__main__":
    app = create_master_runner()
    
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
            initial_state = {"messages": chat_history}
            
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