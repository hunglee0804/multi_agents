CHATBOT_MODEL = "gpt-5-nano"
EMBEDDING_MODEL = "text-embedding-3-small"
EXPERT_TEMPERATURE = 0.3
QUERY_TEMPERATURE = 0
MULTI_VECTOR_DB = "./database/multi_vector_db"
PARENT_DB = f"{MULTI_VECTOR_DB}/parent_store"
CHILD_DB = f"{MULTI_VECTOR_DB}/child_store"

# ==========================================
# TAVILY SEARCH & EXPERT VARIABLES
# ==========================================

# Tavily Search Tool configuration
TAVILY_MAX_RESULTS = 3
TAVILY_SEARCH_DEPTH = "advanced"

# Workflow Graph
MAX_ITERATIONS = 3

# ==========================================
# DATABASE & TICKET VARIABLES
# ==========================================
SQLITE_DB_PATH = "./database/support_system.db"