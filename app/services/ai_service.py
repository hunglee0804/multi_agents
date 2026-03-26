# app/services/ai_service.py
import uuid
from langchain_core.messages import HumanMessage
from multi_agents.runner import create_hierarchical_runner # Hàm bạn đã có

# Khởi tạo master chatbot 1 lần khi start server
app_graph = create_hierarchical_runner()

def process_user_message(conversation_id: str, user_message: str) -> dict:
    """
    Hàm này nhận message từ API, đưa vào LangGraph và trả về kết quả
    """
    config = {"configurable": {"thread_id": conversation_id}}
    
    input_state = {
        "messages": [HumanMessage(content=user_message)],
        "conversation_id": conversation_id
    }
    
    # Chạy graph
    result = app_graph.invoke(input_state, config=config)
    
    # Lấy tin nhắn cuối cùng của assistant
    assistant_message = result["messages"][-1]
    
    return {
        "conversation_id": conversation_id,
        "response": assistant_message.content
    }