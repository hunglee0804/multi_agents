import os

# Tự động lấy đường dẫn tuyệt đối tới thư mục multi_agents
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
MULTI_AGENTS_DIR = os.path.dirname(CURRENT_DIR)

CHATBOT_MODEL = "gpt-5-nano"
EMBEDDING_MODEL = "text-embedding-3-small"
EXPERT_TEMPERATURE = 0.3
QUERY_TEMPERATURE = 0

# CẬP NHẬT ĐƯỜNG DẪN TUYỆT ĐỐI
MULTI_VECTOR_DB = os.path.join(MULTI_AGENTS_DIR, "database", "multi_vector_db")
PARENT_DB = os.path.join(MULTI_VECTOR_DB, "parent_store")
CHILD_DB = os.path.join(MULTI_VECTOR_DB, "child_store")

# ==========================================
# TAVILY SEARCH & EXPERT VARIABLES
# ==========================================

TAVILY_MAX_RESULTS = 3
TAVILY_SEARCH_DEPTH = "advanced"
MAX_ITERATIONS = 3

# ==========================================
# DATABASE & TICKET VARIABLES
# ==========================================
SQLITE_DB_PATH = os.path.join(MULTI_AGENTS_DIR, "database", "support_system.db")