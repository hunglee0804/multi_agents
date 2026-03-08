from langchain_core import messages

from multi_agents.tools.react_tool import retrieve_documents_tool
from multi_agents.schemas.schemas import FAQState, CompleteOrEscalate
from multi_agents.config.prompt import REACT_PROMPT
from multi_agents.config.variable import CHATBOT_MODEL, MAX_ITERATIONS
from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver


# Initialize model and bind tôl
llm = ChatOpenAI(model=CHATBOT_MODEL, temperature=0)
faq_tools = [retrieve_documents_tool]  + [CompleteOrEscalate]
llm_with_tools = llm.bind_tools(faq_tools)


# Define node for ReAct graph
def reasoner_node(state: FAQState) -> dict:
    """
    Core node of ReAct: Anaylize question and decide tool or anwser.
    """
    messages = list(state["messages"])
    
   
    instruction = (
        "\n\nCRITICAL INSTRUCTION: When you have successfully answered the user's question, "
        "OR if you cannot proceed and need to escalate, you MUST call the 'CompleteOrEscalate' tool. "
        "You MUST put your ENTIRE detailed final answer (including any links, bullet points, or formatted text) "
        "INSIDE the 'reason' parameter of the tool call. "
        "DO NOT answer using plain text outside the tool call."
    )
    full_prompt = REACT_PROMPT + instruction
    
    # Check SystemMessage. If it is not in, add it
    if messages and isinstance(messages[0], SystemMessage):
        messages[0] = SystemMessage(content=full_prompt)
    else:
        messages.insert(0, SystemMessage(content=full_prompt))

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
        if last_message.tool_calls[0]["name"] == "CompleteOrEscalate":
            return "end"
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

    memory = MemorySaver()
    app = workflow.compile(checkpointer=memory)
    
    return app