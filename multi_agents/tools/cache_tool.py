import os
import time
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document

CACHE_DIR = "faiss_cache"
# Cache Invalidation Strategy: Automatically expire after 24 hours (86400 seconds)
TTL_SECONDS = 86400 

def get_faiss_index():
    """Initialize or load the FAISS index from local storage."""
    embeddings = OpenAIEmbeddings()
    if os.path.exists(CACHE_DIR):
        return FAISS.load_local(CACHE_DIR, embeddings, allow_dangerous_deserialization=True)
    return None

def search_cache(query: str, threshold: float = 0.4) -> str | None:
    """
    Search for a similar query in the cache.
    Threshold (L2 Distance): The closer to 0, the more similar. 0.4 is a relatively safe level.
    """
    index = get_faiss_index()
    if not index:
        return None
    
    # Search for the top 1 most similar result
    docs_and_scores = index.similarity_search_with_score(query, k=1)
    if not docs_and_scores:
        return None
        
    doc, score = docs_and_scores[0]
    
    # If the vector distance exceeds the threshold -> Not similar enough
    if score > threshold:
        return None
        
    # PERFORM CACHE INVALIDATION: Check timestamp
    cached_time = doc.metadata.get("timestamp", 0)
    if time.time() - cached_time > TTL_SECONDS:
        print(f"\n   [Cache] ⚠️ Warning: Cache is outdated (expired). Re-querying the Agent.")
        return None
        
    print(f"\n   [Cache] ⚡ HIT! Found the answer in cache (Score: {score:.3f})")
    return doc.metadata.get("response")

def save_to_cache(query: str, response: str, query_type: str):
    """Store the query (for embedding) and the response (in metadata) into FAISS."""
    embeddings = OpenAIEmbeddings()
    
    # Store metadata according to the assignment requirements
    metadata = {
        "timestamp": time.time(),
        "query_type": query_type,
        "source": "FAISS_VectorStore",
        "response": response 
    }
    
    # Embed the user's question and store the agent's response in metadata
    doc = Document(page_content=query, metadata=metadata)
    
    index = get_faiss_index()
    if index:
        index.add_documents([doc])
    else:
        index = FAISS.from_documents([doc], embeddings)
        
    index.save_local(CACHE_DIR)
    print(f"\n   [Cache] 💾 Answer has been saved to the FAISS Vectorstore.")