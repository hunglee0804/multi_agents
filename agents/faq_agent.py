from multi_agents.tools.react_tool import retrieve_documents_tool
from multi_agents.schemas.schemas import FAQState, CompleteOrEscalate
from multi_agents.config.prompt import REACT_PROMPT
from multi_agents.config.variable import CHATBOT_MODEL, MAX_ITERATIONS
from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode


# Initialize model and bind tôl
llm = ChatOpenAI(model=CHATBOT_MODEL, temperature=0)
faq_tools = [retrieve_documents_tool]
llm_with_tools = llm.bind_tools(faq_tools + [CompleteOrEscalate])


# Define node for ReAct graph
def reasoner_node(state: FAQState) -> dict:
    """
    Core node of ReAct: Anaylize question and decide tool or anwser.
    """
    messages = state["messages"]
    
    # Check SystemMessage. If it is not in, add it
    if not any(isinstance(m, SystemMessage) for m in messages):
        messages = [SystemMessage(content=REACT_PROMPT)] + messages

    response = llm_with_tools.invoke(messages)
    
    return {
        "messages": [response],
        "current_iteration": state.get("current_iteration", 0) + 1
    }

def should_continue(state: FAQState) -> str:
    """
    Conditional: 
    - If LLM call tool and the interation is not larger than max_interation -> go to Node Tools
    - If LLM đã answer or loop to much -> (END)
    """
    last_message = state["messages"][-1]
    
    # If the iteration larger than max iteration, return it
    if state.get("current_iteration", 0) >= state.get("max_iterations", MAX_ITERATIONS):
        return "end"

    # check to decide call tool
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "use_tools"

    return "end"

def create_retrieval_agent():
    """
    Create a ReAct agent with retrieval tools.
    """

    workflow = StateGraph(FAQState)
    
    # Add bide
    workflow.add_node("reasoner", reasoner_node)
    workflow.add_node("tools", ToolNode(faq_tools))

    # Entry node
    workflow.set_entry_point("reasoner")

    # Conditional node
    workflow.add_conditional_edges(
        "reasoner",
        should_continue,
        {
            "use_tools": "tools",
            "end": END
        }
    )

    # Answer after retrieve the document
    workflow.add_edge("tools", "reasoner")

    app = workflow.compile()
    
    return app