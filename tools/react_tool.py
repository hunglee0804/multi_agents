from multi_agents.schemas.schemas import *
from langchain.tools import tool
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain_core.documents import Document
from rank_bm25 import BM25Okapi
from pathlib import Path
from multi_agents.config.config import *
from multi_agents.config.variable import *
from multi_agents.config.prompt import HYDE_PROMPT, QUERY_PROMPT, REACT_PROMPT
import ast

"""
Retrieval tool
"""

def load_vector_store(persist_dir: str):
    """
    Load vector from database
    """

    embedding = OpenAIEmbeddings(model = EMBEDDING_MODEL)

    collection = Path(persist_dir).name

    vector_store = Chroma(
        collection_name= collection,
        persist_directory = str(persist_dir),
        embedding_function = embedding
    )
    
    return vector_store

def deduplicate_docs(docs: list) -> list:
    """Remove duplicate documents based on page_content."""

    seen = set()
    unique_docs = list()

    for doc in docs:
        content_hash = doc.page_content[:100]
        if content_hash not in seen:
            seen.add(content_hash)
            unique_docs.append(doc)
    
    return unique_docs


def query_processing(user_question: str) -> list:
    """
    Generate multiple search queries from a single user question.
    Uses LLM to expand the question into 3 different variations.
    
    Args:
        user_question: The original question from user
    
    Returns:
        List of 3 refined queries
    """


    # Create ChatOpenAI instance
    llm = ChatOpenAI(
        model = CHATBOT_MODEL,
        temperature = 0
    )

    # Format prompt with user question
    formatted_prompt = QUERY_PROMPT.replace("{user_question}", user_question)

    # Call LLM to generate queries
    response = llm.invoke(formatted_prompt)

    # Parse LLM output (string) to python list
    queries = ast.literal_eval(response.content)

    # Return list of queries
    return queries


def generate_hyde_document(question: str) -> str:
    """
    Generate a hypothetical answer to the question.
    This answer will be embedded and used for retrieval.
    """

    llm = ChatOpenAI(
        model=CHATBOT_MODEL,
        temperature=0
    )

    hyde_prompt = HYDE_PROMPT.replace("{question}", question)

    response = llm.invoke(hyde_prompt)

    return response.content



def multi_vector_search(queries: list[str]) -> list:
    """
    Perform multi vector search for multiple queries.

    Args:
        queries: List of search queries
    
    Returns:
        All parent documents
    """

    # Access to the database
    child_store = load_vector_store(CHILD_DB)
    parent_store = load_vector_store(PARENT_DB)

    # Create child results list
    all_child_results = list()

    # Similarity search for child blocks
    for query in queries:
        child_doc = child_store.similarity_search(query, k = 10)
        all_child_results.extend(child_doc)

    # Take the unique documents
    unique_child = deduplicate_docs(all_child_results)

    # Extract parent_ids from child metadata
    
    parent_ids = list({
        doc.metadata.get("parent_id")
        for doc in unique_child 
        if "parent_id" in doc.metadata
    })

    if not parent_ids:
        return []

    # Fetch parent documents by parent_ids
    
    raw = parent_store.get(ids=parent_ids)
    if not raw or not raw.get("documents"):
        print("Parent fetch returned empty result.")
        print("Requested parent_ids:", parent_ids)
        return []

    parents = []
    for text, meta in zip(raw["documents"], raw["metadatas"]):
        parents.append(Document(page_content=text, metadata=meta))

    return parents


def load_bm25_corpus() -> list[Document]:
    return load_all_docs_from_chroma(PARENT_DB)

def bm25_search(queries: list, docs: list, top_k: int =5) -> list[Document]:
    """
    Perform BM25 search over given documents
    """

    # Take corpus from documents
    corpus = [doc.page_content for doc in docs]
    tokenize_corpus = [c.split() for c in corpus]

    # Define BM25 search
    bm25 = BM25Okapi(tokenize_corpus)

    # Create a dictionary of all results
    results = dict()

    # Score the document and add it to the result
    for query in queries:

        tokenize_query = query.split()
        scores = bm25.get_scores(tokenize_query)

        for i, score in enumerate(scores):
            results[i] = max(results.get(i, 0), score)
    
    ranked_indices = sorted(results, key = results.get, reverse=True)

    # Return the result
    return [docs[i] for i in ranked_indices[:top_k]]


def load_all_docs_from_chroma(persist_dir: str) -> list[Document]:
    """
    Load data from databse
    """

    vector = load_vector_store(persist_dir)
    raw = vector.get()

    docs = []
    for text, meta in zip(raw["documents"], raw["metadatas"]):
        docs.append(
            Document(
                page_content=text,
                metadata=meta
            )
        )

    return docs


def rrf(similarity_docs: list, bm25_docs: list, top_k: int = 5) -> list:
    """
    Reciprocal Rank Fusion algorithm
    """

    # Create score dictionary and document dictionary
    scores = dict()
    doc_map = dict()

    k = 60

    # RRF processing
    for rank, doc in enumerate(bm25_docs):
        doc_id = id(doc)
        scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank)
        doc_map[doc_id] = doc

    for rank, doc in enumerate(similarity_docs):
        doc_id = id(doc)
        scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank)
        doc_map[doc_id] = doc

    # Sort, filter, and return top k
    ranked = sorted(scores.items(), key=lambda x : x[1], reverse = True)

    return [doc_map[doc_id] for doc_id, _ in ranked[:top_k]]


def retrive_documents(question : str, top_k: int = 3):
    """
    Retrieve and rerank relevant documents for answering the question.
    """

    # Query processing
    queries = query_processing(question)

    # If question have not enough information, call HyDE
    if len(question.split()) < 8:
        # HyDE generation
        hyde_doc = generate_hyde_document(question)

        # Enrich query list
        queries.append(hyde_doc)

    # Multi vector search
    multi_docs = multi_vector_search(queries)

    # BM25 retrieval
    bm25_corpus = load_bm25_corpus()
    bm25_docs = bm25_search(
        queries=queries,
        docs=bm25_corpus,
        top_k=top_k
    )

    # Reranking
    rerank_docs = rrf(
        similarity_docs=multi_docs,
        bm25_docs=bm25_docs,
        top_k=top_k
    )

    return rerank_docs
@tool("retrieval_documents_tools", args_schema=RetrieveDocumentsSchema)
def retrieve_documents_tool(question: str) -> str:
    """
    Retrieve and rerank relevant documents for answering the question.
    Returns the combined text of top documents.
    """

    docs = retrive_documents(question)

    context = "\n\n".join(
        f"[Doc {i+1}]\n{doc.page_content}"
        for i, doc in enumerate(docs)
    )

    return context