# app/services/ai_service.py
from langchain_core.messages import HumanMessage, AIMessage
from multi_agents.runner import create_hierarchical_runner
from app.core.database import SessionLocal
from app.models.message import Message

# Initialize the master chatbot once when the server starts.
app_graph = create_hierarchical_runner()

def process_user_message(conversation_id: str, user_message: str) -> dict:
    config = {"configurable": {"thread_id": conversation_id}}
    
    # 1. Kiểm tra trí nhớ của LangGraph trong RAM
    state = app_graph.get_state(config)
    
    # 2. Nếu rỗng (do server restart hoặc mất kết nối), khôi phục từ Database
    if not state.values or not state.values.get("messages"):
        print(f"\n🔄 [System] RAM wiped. Restoring context from PostgreSQL for session: {conversation_id}")
        db = SessionLocal()
        # Lấy lịch sử chat của session này từ DB
        db_messages = db.query(Message).filter(Message.conversation_id == conversation_id).order_by(Message.created_at.asc()).all()
        db.close()
        
        langchain_messages = []
        for msg in db_messages:
            if msg.role == "user":
                langchain_messages.append(HumanMessage(content=msg.content))
            elif msg.role == "ai":
                langchain_messages.append(AIMessage(content=msg.content))
        
        # Đảm bảo câu hỏi hiện tại luôn nằm ở cuối cùng
        if not langchain_messages or langchain_messages[-1].content != user_message:
            langchain_messages.append(HumanMessage(content=user_message))
            
        input_state = {
            "messages": langchain_messages,
            "conversation_id": conversation_id
        }
    else:
        # Nếu RAM vẫn còn trí nhớ, chỉ cần đưa câu hỏi mới vào
        input_state = {
            "messages": [HumanMessage(content=user_message)],
            "conversation_id": conversation_id
        }
    
    # Run graph
    result = app_graph.invoke(input_state, config=config)
    
    # Get the assistant's last message
    assistant_message = result["messages"][-1]
    
    return {
        "conversation_id": conversation_id,
        "response": assistant_message.content
    }