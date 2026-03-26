from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from dotenv import load_dotenv
from pathlib import Path
import os
import bs4
import requests
import html2text
import hashlib
import re
import uuid



load_dotenv()

EMBEDDING_MODEL = "text-embedding-3-small"
MARKDOWN_FOLDER = "./data/markdown" 
DATA_FOLDER = "./data"
WEBSITE_LINK = "web_sources.txt"
MULTI_VECTOR_DB = "./database/multi_vector_db"
PARENT_DB = f"{MULTI_VECTOR_DB}/parent_store"
CHILD_DB  = f"{MULTI_VECTOR_DB}/child_store"


def main():
    print("=== TEST DATA LOADING PIPELINE ===\n")

    # # Load data from all source (website, pdf)
    # docs = load_data(DATA_FOLDER)

    # Read all data in markdown file
    md_file = load_markdown_folder(MARKDOWN_FOLDER)

    # Semantic chunk
    semantic_chunk = semantic_chunking(md_file)

    # # Recursive chunk test
    # all_chunk = list()
    # for chunk in semantic_chunk:
    #     recursive_chunk = recursive_chunking(chunk)
    #     all_chunk.extend(recursive_chunk)

    create_multi_vector_database(semantic_chunk)

"""
Loading data process
Convert all file type (HTML, PDF) to markdown file
"""

"""
The loading processing
"""
def load_data(input_folder: str) -> list:
    """
    Load data from PDFs, Websites, Markdown
    Return LangChain Documents
    """

    markdown_dir = MARKDOWN_FOLDER
    ensure_dir(markdown_dir)

    # PDF → Markdown
    pdf_dir = Path(input_folder) / "pdf"
    if pdf_dir.exists():
        for pdf in pdf_dir.glob("*.pdf"):
            md_text = convert_pdf_to_markdown(str(pdf))
            save_markdown_file(md_text, source=str(pdf), output_dir=markdown_dir)

    # Website → Markdown
    web_sources_path = Path(input_folder) / WEBSITE_LINK
    if web_sources_path.exists():
        web_sources = load_web_sources(str(web_sources_path))
        for url in web_sources:
            html = fetch_web_content(url)
            md_text = convert_html_to_markdown(html)
            save_markdown_file(md_text, source=url, output_dir=markdown_dir)

    # Load Markdown → Documents
    docs = load_markdown_folder(markdown_dir)

    return docs


def load_markdown_folder(folder: str | Path) -> list:
    """
    Load markdown files into LangChain Documents
    """
    
    docs = []

    folder = Path(folder)
    if not folder.exists():
        print(f"Folder not found: {folder}")
        return []

    md_files = list_md_files(folder)
    print(f"Found {len(md_files)} markdown files")

    for md_file in list_md_files(folder):
        text = read_file(md_file)
        docs.append(
            Document(
                page_content=text,
                metadata={"source": md_file}
            )
        )

    return docs




def semantic_chunking(documents: list[Document]) -> list[Document]:
    """
    Split document into semantic sections using markdown structure
    or policy-style numbering.
    """

    # Chunking processing
    semantic_chunks = []

    # Chunking through the documents
    for document in documents:
    
        # Take the content and data
        content = document.page_content
        metadata = document.metadata

        # Spilit header
        sections = re.split(r'(?=^#{1,6} )', content, flags = re.MULTILINE)

        # Chunking processing
        for section in sections:
            section = section.strip()

            if not section:
                continue

            semantic_chunks.append(
                Document(
                    page_content = section,
                    metadata = metadata
                )
            )

    return semantic_chunks


def recursive_chunking(
        document: Document,
        chunk_size: int = 2000,
        chunk_overlap: int = 400
    ) -> list[Document]:
    """
    Further split semantic chunk into smaller chunks
    while preserving metadata.
    """    

    # Take the content 
    content = document.page_content
    metadata = document.metadata
    
    # Check the length of content.
    # If it too short, return it.
    if len(content) < chunk_size:
        return [document]
    
    # Call recursive chunk tool and devide the content
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size = chunk_size,
        chunk_overlap = chunk_overlap
    )
    sub_chunks = text_splitter.split_text(content)

    # Chunking processing
    documents = list()

    for idx, chunk in enumerate(sub_chunks):

        # Update metadata
        new_metadata = metadata.copy()
        new_metadata["chunk_index"] = idx
        new_metadata["parent_id"] = metadata.get("source")

        # Add new chunking to the list
        documents.append(
            Document(
                page_content = chunk,
                metadata = new_metadata
            )
        )

    return documents



def create_embeddings(semantic_chunks: list[Document]) -> tuple[list[Document], list[Document]]:
    """
    Create parent and child documents for Multi-Vector indexing.
    Parent = semantic sections
    Child  = recursive chunks
    """

    # Parent child indexing
    parent_docs = list()
    child_docs = list()

    # Index processing
    for parent_doc in semantic_chunks:

        # Update metadata
        parent_id = str(uuid.uuid4())
        parent_meta = parent_doc.metadata.copy()
        parent_meta["doc_type"] = "parent"
        parent_meta["parent_id"] = parent_id

        # Create new documents for parent doc
        parent_document = Document(
            page_content = parent_doc.page_content,
            metadata = parent_meta
        )
        parent_docs.append(parent_document)

        # Recursive chunking → child documents
        sub_chunks = recursive_chunking(parent_doc)

        # Create new documents for child doc
        for idx, child in enumerate(sub_chunks):
            child_meta = child.metadata.copy()
            child_meta["doc_type"] = "child"
            child_meta["parent_id"] = parent_id
            child_meta["chunk_index"] = idx

            child_docs.append(
                Document(
                    page_content = child.page_content,
                    metadata = child_meta
                )
            )

    return parent_docs, child_docs


def build_hnsw_index(documents: list[Document], persist_dir: str):
    """
    Build HNSW indexes
    """

    # Create new folder to save database
    ensure_dir(persist_dir)

    # Embedding model
    embedding = OpenAIEmbeddings(model = EMBEDDING_MODEL)

    # Save to database
    documents = sanitize_documents(documents)
    collection = Path(persist_dir).name
    vector_store = Chroma(
        collection_name=collection,
        embedding_function=embedding,
        persist_directory=persist_dir
    )

    # Use parent_id as Chroma document ID if available
    ids = []
    if collection == "parent_store":
        # Parent: use parent_id as ID
        for doc in documents:
            ids.append(doc.metadata["parent_id"])

    else:
        # Child: generate unique ID for each chunk
        for _ in documents:
            ids.append(str(uuid.uuid4()))

    vector_store.add_documents(documents, ids=ids)

    return vector_store

def create_multi_vector_database(semantic_chunks: list[Document]):
    """
    Create and persist Multi-Vector database.
    """

    if not semantic_chunks:
        print("No semantic chunks found. Stop indexing.")
        return

    print("Creating Multi-Vector embeddings...")

    parent_docs, child_docs = create_embeddings(semantic_chunks)

    print(f"Parent docs: {len(parent_docs)}")
    print(f"Child docs: {len(child_docs)}")

    print("Building Parent Index...")
    build_hnsw_index(parent_docs, PARENT_DB)

    print("Building Child Index...")
    build_hnsw_index(child_docs, CHILD_DB)

    print("Multi-Vector database created successfully!")







"""

Helping function for preprocessing, they include:
- load_web_sources
- fetch_web_content
- convert_pdf_to_markdown
- extract_main_content
- convert_html_to_markdown
- normalize_markdown
- save_markdown_file

"""
def sanitize_documents(documents):
    for doc in documents:
        clean_meta = {}
        for k, v in doc.metadata.items():
            if isinstance(v, Path):
                clean_meta[k] = str(v)
            elif isinstance(v, (str, int, float, bool, list)) or v is None:
                clean_meta[k] = v
            else:
                clean_meta[k] = str(v)
        doc.metadata = clean_meta
    return documents

def hash_source(source: str) -> str:
    return hashlib.md5(source.encode("utf-8")).hexdigest()

def ensure_dir(path: str):
    Path(path).mkdir(parents=True, exist_ok=True)

"""
Loading website content
"""
def load_web_sources(file_path: str) -> list[str]:
    """
    Read list of URLs from file
    """
    with open(file_path, 'r') as f:
        source_web = f.read()
    
    return source_web.split()

def fetch_web_content(url: str) -> str:
    """
    Fetch raw HTML content from website
    """
    respone = requests.get(url, timeout=10)
    return respone.text


"""
Convert all file to markdown
"""

def convert_pdf_to_markdown(pdf_path: str) -> str:
    """
    Convert PDF to markdown text
    """

    loader = PyPDFLoader(pdf_path)
    pages = loader.load()

    markdown = ""
    for page in pages:
        markdown += page.page_content + "\n\n"

    return normalize_markdown(markdown)

def extract_main_content(soup: bs4.BeautifulSoup):
    """
    Remove nav, footer, scripts
    Return main content tag
    """
    # Remove unwanted tags
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()

    # Try to find main content
    main = soup.find("main")
    if main:
        return str(main)

    article = soup.find("article")
    if article:
        return str(article)

    body = soup.find("body")
    if body:
        return str(body)

    # Fallback: entire document
    return str(soup)

def convert_html_to_markdown(html: str) -> str:
    """
    Convert HTML content to markdown
    """

    soup = bs4.BeautifulSoup(html, "html.parser")
    main_content = extract_main_content(soup)

    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = True
    h.body_width = 0

    markdown = h.handle(main_content)

    return normalize_markdown(markdown)

"""
Clean and normalize
"""
def normalize_markdown(text: str) -> str:
    """
    Clean markdown:
    - remove excessive whitespace
    - remove empty lines
    - normalize bullet points
    """

    lines = text.splitlines()

    cleaned = []
    for line in lines:
        line = line.strip()

        if not line:
            continue

        # ALL CAPS short line → treat as top header
        if line.isupper() and len(line.split()) <= 8:
            cleaned.append(f"# {line}")
            continue

        # Match number with dot
        match = re.match(r"^((\d+\.)+\d*)\s+(.+)", line)

        if match:
            section_number = match.group(1).strip(".")
            title = match.group(3)

            # Count the level of number by dot
            level = section_number.count(".")

            # Map level to markdown depth
            # 1.        -> level 0 dot → ##
            # 1.1.      -> 1 dot → ###
            # 1.1.1.    -> 2 dots → ####
            header_prefix = "#" * min(level + 2, 6)
            
            cleaned.append(f"{header_prefix} {section_number} {title}")
            continue

        # Match number without dot
        match_simple_number = re.match(r"^(\d+)\s+(.+)", line)
        if match_simple_number:
            number = match_simple_number.group(1)
            title = match_simple_number.group(2)

            cleaned.append(f"## {number} {title}")
            continue

        # Match letter 
        match_letter = re.match(r"^([a-zA-Z])\.\s+(.+)", line)
        if match_letter:
            letter = match_letter.group(1)
            title = match_letter.group(2)

            cleaned.append(f"### {letter}. {title}")
            continue
        
        cleaned.append(line)

    return "\n".join(cleaned)

"""
Save and load Markdown file
"""
def save_markdown_file(content: str, source: str, output_dir: str):
    """
    Save markdown file with metadata header
    """

    ensure_dir(output_dir)

    filename = hash_source(source) + ".md"
    output_path = Path(output_dir) / filename

    markdown_with_meta = f"""---
source: {source}
---

{content}
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(markdown_with_meta)


def list_md_files(folder: str) -> list:
    return [
        Path(folder) / f
        for f in os.listdir(folder)
        if f.endswith(".md")
    ]
def read_file(path: Path) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()




    
if __name__ == "__main__":
    main()