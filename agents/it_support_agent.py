from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from multi_agents.config.variable import CHATBOT_MODEL, MAX_ITERATIONS
from multi_agents.config.prompt import PLANNER_PROMPT, COORDINATOR_PROMPT
from multi_agents.schemas.schemas import ResearcherState
from multi_agents.tools.tavily_tool import TAVILY_ALL_TOOLS

# Initialize LLM for Nodes (Planner & Coordinator)
llm = ChatOpenAI(model=CHATBOT_MODEL, temperature=0)

# ==========================================
# DEFINE NODES CHO WORKFLOW
# ==========================================

def planner_node(state: ResearcherState) -> dict:
    """
    Planner Node: plan the workflow by analyzing the conversation and deciding which tools to call.
    """
    response = llm.invoke([SystemMessage(content=PLANNER_PROMPT), *state["messages"]])
    return {"messages": [response]}


# Bind tools into LLM for Coordinator
coordinator_with_tools = llm.bind_tools(TAVILY_ALL_TOOLS)

def coordinator_node(state: ResearcherState) -> dict:
    """
    Coordinator Node: Execute the plan from Planner, call tools when needed, and produce final answer when sufficient info is gathered.
    """
    # Formart prompt with iteration info for better context
    formatted_prompt = COORDINATOR_PROMPT.format(
        iteration=state["current_iteration"] + 1,
        max_iterations=state.get("max_iterations", MAX_ITERATIONS),
    )
    
    response = coordinator_with_tools.invoke([
        SystemMessage(content=formatted_prompt),
        *state["messages"]
    ])

    return {
        "messages": [response], 
        "current_iteration": state["current_iteration"] + 1
    }


def should_continue(state: ResearcherState) -> str:
    """
    Conditional function to determine if we should continue calling tools or end the workflow.
    """
    last_message = state["messages"][-1]

    # If the iteration larger than max iteration, return it
    if state.get("current_iteration", 0) >= state.get("max_iterations", 3):
        return "end"

    # If LLM calls a tool, we need to continue to execute that tool
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "use_tools"

    # If no tool calls and we've reached max iterations, end the workflow
    return "end"


# ==========================================
# INITIALIZE WORKFLOW LANGGRAPH
# ==========================================

def create_it_support_agent():
    """
    Build the IT Support Agent workflow using LangGraph
    """
    workflow = StateGraph(ResearcherState)
    
    # Add nodes: Planner, Coordinator, Tools
    workflow.add_node("planner", planner_node)
    workflow.add_node("coordinator", coordinator_node)
    workflow.add_node("tools", ToolNode(TAVILY_ALL_TOOLS))

    # Set Planner as entry point
    workflow.set_entry_point("planner")

    # Connect nodes: Planner -> Coordinator -> (Tools or END)
    workflow.add_edge("planner", "coordinator")
    
    # Turn coordinator into a conditional node based on whether it calls tools or not
    workflow.add_conditional_edges(
        "coordinator",
        should_continue,
        {
            "use_tools": "tools",
            "end": END
        }
    )

    # Evaluate tools and then return to coordinator for next iteration or final answer
    workflow.add_edge("tools", "coordinator")

    # Compile workflow to get the final agent app
    app = workflow.compile()
    
    return app