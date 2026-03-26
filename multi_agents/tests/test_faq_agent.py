import sys
import os

# 1. Thêm project root vào sys.path để Python nhận diện được package multi_agents
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 2. Import cấu hình và Agent
from multi_agents.config.config import * # Load API Keys
from multi_agents.agents.faq_agent import create_retrieval_agent
from langchain_core.messages import HumanMessage

def run_faq_agent_test():
    print("="*60)
    print("🚀 KHỞI ĐỘNG FAQ AGENT (RAG + LANGGRAPH) 🚀")
    print("="*60)
    
    # Compile đồ thị LangGraph
    app = create_retrieval_agent()
    
    print("Agent đã sẵn sàng! Gõ 'quit' hoặc 'exit' để dừng chương trình.\n")
    
    # Khởi tạo danh sách chứa lịch sử hội thoại
    chat_history = []

    while True:
        try:
            user_input = input("\nYou: ").strip()
            
            if user_input.lower() in ['quit', 'exit']:
                print("Đã thoát chương trình test.")
                break
            if not user_input:
                continue

            # Thêm tin nhắn của user vào lịch sử
            chat_history.append(HumanMessage(content=user_input))

            # Khởi tạo State cho FAQ Agent
            initial_state = {
                "messages": chat_history,
                "max_iterations": 3,
                "current_iteration": 0
            }

            print("\n⏳ Agent đang suy luận và tìm kiếm tài liệu...")
            
            # Chạy workflow LangGraph
            result = app.invoke(initial_state)

            # Lấy tin nhắn cuối cùng (câu trả lời của Assistant)
            assistant_message = result["messages"][-1]
            
            print("\n🤖 Assistant:")
            print(assistant_message.content)
            print("-" * 60)

            # Thêm câu trả lời của hệ thống vào lịch sử để giữ luồng hội thoại
            chat_history.append(assistant_message)

        except KeyboardInterrupt:
            sys.exit("\n\nChương trình bị ngắt bởi người dùng. Tạm biệt!")
        except Exception as e:
            print(f"\n❌ Đã xảy ra lỗi: {e}")

if __name__ == "__main__":
    run_faq_agent_test()