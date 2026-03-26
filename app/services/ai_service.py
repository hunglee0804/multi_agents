# app/services/ai_service.py
import uuid
from langchain_core.messages import HumanMessage
from multi_agents.runner import create_hierarchical_runner # Hàm bạn đã có

# Initialize the master chatbot once when the server starts.
app_graph = create_hierarchical_runner()

def process_user_message(conversation_id: str, user_message: str) -> dict:
    """
    This function receives a message from the API, passes it to LangGraph, and returns the result.
    """
    config = {"configurable": {"thread_id": conversation_id}}
    
    input_state = {
        "messages": [HumanMessage(content=user_message)],
        "conversation_id": conversation_id
    }
    
    # Run graph
    result = app_graph.invoke(input_state, config=config)
    
    # Get the assistant's last message.
    assistant_message = result["messages"][-1]
    
    return {
        "conversation_id": conversation_id,
        "response": assistant_message.content
    }