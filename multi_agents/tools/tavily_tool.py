from langchain.tools import tool
from langchain_openai import ChatOpenAI
from langchain_tavily import TavilySearch
from langchain_core.messages import SystemMessage, HumanMessage

from multi_agents.config.prompt import AI_RESEARCH_PROMPT, FINANCIAL_PROMPT
from multi_agents.config.variable import CHATBOT_MODEL, TAVILY_MAX_RESULTS, TAVILY_SEARCH_DEPTH
from multi_agents.schemas.schemas import AIResearchSchema, FinancialAnalystSchema, WebSearchSchema

# Initialize LLMs and Tools
ai_researcher_llm = ChatOpenAI(model=CHATBOT_MODEL, temperature=0.3)
financial_llm = ChatOpenAI(model=CHATBOT_MODEL, temperature=0.3)
tavily_search_tool = TavilySearch(max_results=TAVILY_MAX_RESULTS, search_depth=TAVILY_SEARCH_DEPTH)

# Define tools with LangChain's @tool decorator
@tool("ai_research_expert", args_schema=AIResearchSchema)
def ai_research_expert(query: str) -> str:
    """Consult AI Research Expert for deep ML/AI theory and architecture questions."""
    message = [SystemMessage(content=AI_RESEARCH_PROMPT), HumanMessage(content=query)]
    return ai_researcher_llm.invoke(message).content

@tool("financial_analyst", args_schema=FinancialAnalystSchema)
def financial_analyst(query: str) -> str:
    """Consult Financial Analyst for market, investment, and valuation questions."""
    message = [SystemMessage(content=FINANCIAL_PROMPT), HumanMessage(content=query)]
    return financial_llm.invoke(message).content

@tool("web_search_expert", args_schema=WebSearchSchema)
def web_search_expert(query: str) -> str:
    """Use Tavily Web Search for real-time factual lookups, recent benchmarks, product specs, or news."""
    try:
        response = tavily_search_tool.invoke(query)
        output = []
        if isinstance(response, list):
            results = response
        elif isinstance(response, dict):
            results = response.get("results", [])
        else:
            results = []

        for r in results:
            content = r.get("content", "")
            url = r.get("url", "")
            output.append(f"Content: {content} | URL: {url}")
            
        return "\n".join(output) if output else "No results found."
    except Exception as e:
        return f"Web search failed: {str(e)}"

# Aggregate all tools for easy import
TAVILY_ALL_TOOLS = [ai_research_expert, financial_analyst, web_search_expert]