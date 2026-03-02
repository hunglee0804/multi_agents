import sys
import os

# 1. Thêm project root vào sys.path để Python nhận diện được package multi_agents
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 2. Import cấu hình và Agent
from multi_agents.config.config import * # Load API Keys
from multi_agents.agents.it_support_agent import create_it_support_agent
from langchain_core.messages import HumanMessage

def run_it_support_test():
    print("="*60)
    print("🚀 START IT SUPPORT AGENT (TAVILY + MULTI-EXPERTS) 🚀")
    print("="*60)
    
    # Compile đồ thị LangGraph
    app = create_it_support_agent()
    
    print("Agent is ready! Type 'quit' or 'exit' for stopping.\n")
    
    while True:
        try:
            user_input = input("\nYou: ").strip()
            
            if user_input.lower() in ['quit', 'exit']:
                print("Quit test!")
                break
            if not user_input:
                continue

            # Khởi tạo State cho LangGraph
            # Khác với FAQ Agent dùng memory, Agent này giải quyết từng query độc lập 
            # với số vòng lặp tối đa (max_iterations) để tránh tốn tiền API.
            initial_state = {
                "messages": [
                    HumanMessage(content=user_input)
                ],
                "max_iterations": 3,
                "current_iteration": 0
            }

            print("\n⏳ Agent is planning and searching...")
            
            # Chạy workflow
            result = app.invoke(initial_state)

            # In câu trả lời cuối cùng
            print("\n🤖 Assistant:")
            print(result["messages"][-1].content)
            print("-" * 60)

        except KeyboardInterrupt:
            sys.exit("\n\nProgram is interrupted. Good bye!")
        except Exception as e:
            print(f"\n❌ Occured error: {e}")

if __name__ == "__main__":
    run_it_support_test()