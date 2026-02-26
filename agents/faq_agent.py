from multi_agents.tools.react_tool import retrieve_documents_tool
from langchain.agents import create_agent
from multi_agents.config.prompt import REACT_PROMPT
from langchain_openai import ChatOpenAI
from multi_agents.config.variable import CHATBOT_MODEL


def create_retrieval_agent():
    """
    Create a ReAct agent with retrieval tools.
    """

    # Define tool
    tools = [retrieve_documents_tool]

    # Create Chat model for agent reasoning
    model = ChatOpenAI(
        model  = CHATBOT_MODEL,
        temperature= 0
    )

    # Create agent 
    reac_instructor = REACT_PROMPT
    agent = create_agent(
        model=model,
        tools= tools,
        system_prompt=reac_instructor
    )

    return agent
