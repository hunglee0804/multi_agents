import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))

if project_root not in sys.path:
    sys.path.insert(0, project_root)
from multi_agents.agents.faq_agent import create_retrieval_agent
from multi_agents.config.config import *
def run_chat_loop():

    # Create agent ONCE so it can keep reasoning context
    agent_executor = create_retrieval_agent()

    # Conversation memory (LangChain message format)
    messages = []

    print("RAG system is running. Press CTRL + C to stop.\n")

    try:
        while True:
            user_input = input("You: ").strip()
            if not user_input:
                continue

            # Append user message
            messages.append({
                "role": "user",
                "content": user_input
            })

            # Invoke agent with full conversation history
            result = agent_executor.invoke({
                "messages": messages
            })

            # Extract assistant response
            if "messages" in result:
                assistant_msg = result["messages"][-1]
                print("\nAssistant:", assistant_msg.content, "\n")

                # Append assistant message to memory
                messages.append({
                    "role": "assistant",
                    "content": assistant_msg.content
                })
            else:
                print("\nAssistant:", result, "\n")

    except KeyboardInterrupt:
        sys.exit("\n\nConversation interrupted by user. Exiting gracefully...")

if __name__ == "__main__":
    run_chat_loop()