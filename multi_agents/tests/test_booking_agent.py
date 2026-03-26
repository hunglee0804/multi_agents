import sys
import os

# ==========================================
# 1. PATH SETUP TO ALLOW ABSOLUTE IMPORTS
# ==========================================
# Go UP TWO levels ("../../") to reach the directory containing 'multi_agents'
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 2. Import configurations and the compiled agent
from multi_agents.config.config import * 
from multi_agents.agents.booking_agent import create_booking_agent
from langchain_core.messages import HumanMessage



def run_booking_agent_test():
    """
    Interactive terminal interface to test the Booking Agent.
    """
    print("=" * 60)
    print("🚀 BOOKING AGENT TEST INITIALIZED 🚀")
    print("=" * 60)
    
    # Compile the LangGraph application
    app = create_booking_agent()
    
    print("Agent is ready! Type 'quit' or 'exit' to stop the program.\n")
    print("Hint: Try saying 'I want to book Room A tomorrow morning' and see if it asks for missing details.\n")
    
    # Initialize chat history
    chat_history = []

    while True:
        try:
            user_input = input("\nYou: ").strip()
            
            if user_input.lower() in ['quit', 'exit']:
                print("Exiting test program. Goodbye!")
                break
            if not user_input:
                continue

            # Append user message
            chat_history.append(HumanMessage(content=user_input))

            # Initialize state
            initial_state = {
                "messages": chat_history,
                "max_iterations": 3,
                "current_iteration": 0
            }

            print("\n⏳ Agent is reasoning and accessing the database...")
            
            # Execute workflow
            result = app.invoke(initial_state)

            # Retrieve final message
            assistant_message = result["messages"][-1]
            
            print(f"\n🤖 Assistant:\n{assistant_message.content}")
            print("-" * 60)

            # Append response to history
            chat_history.append(assistant_message)

        except KeyboardInterrupt:
            sys.exit("\n\nProcess interrupted by user. Goodbye!")
        except Exception as e:
            print(f"\n❌ Error occurred: {e}")

if __name__ == "__main__":
    run_booking_agent_test()