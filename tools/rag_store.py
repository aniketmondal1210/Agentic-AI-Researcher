"""
RAG Vector Store — stores and retrieves paper chunks using ChromaDB.
Uses Google's embedding model for vectorization.
"""

import os
import hashlib
from langchain_core.tools import tool

# Lazy-init globals
_collection = None
_embed_fn = None


def _get_collection():
    """Get or create the ChromaDB collection (lazy init)."""
    global _collection, _embed_fn
    if _collection is not None:
        return _collection, _embed_fn

    import chromadb
    from chromadb.utils import embedding_functions

    # Use local DefaultEmbeddingFunction (no API key needed, works everywhere)
    # GoogleGenerativeAiEmbeddingFunction uses v1beta which doesn't support text-embedding-004
    _embed_fn = embedding_functions.DefaultEmbeddingFunction()

    client = chromadb.Client()  # In-memory for simplicity
    _collection = client.get_or_create_collection(
        name="research_papers",
        embedding_function=_embed_fn,
    )
    return _collection, _embed_fn


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        start += chunk_size - overlap
    return chunks


@tool
def store_paper_in_rag(paper_text: str, paper_title: str, paper_url: str = "") -> str:
    """Store a research paper's content in the RAG vector store for later retrieval.

    Args:
        paper_text: The full text content of the paper
        paper_title: The title of the paper
        paper_url: Optional URL/source of the paper

    Returns:
        Confirmation message with number of chunks stored
    """
    print(f"RAG STORE: Indexing paper '{paper_title}'")
    collection, _ = _get_collection()

    chunks = chunk_text(paper_text)
    if not chunks:
        return "No content to store."

    # Create unique IDs based on content hash
    ids = []
    documents = []
    metadatas = []

    for i, chunk in enumerate(chunks):
        chunk_id = hashlib.md5(f"{paper_title}_{i}_{chunk[:50]}".encode()).hexdigest()
        ids.append(chunk_id)
        documents.append(chunk)
        metadatas.append({
            "paper_title": paper_title,
            "paper_url": paper_url,
            "chunk_index": i,
            "total_chunks": len(chunks),
        })

    # Upsert (add or update)
    collection.upsert(ids=ids, documents=documents, metadatas=metadatas)

    print(f"RAG STORE: Stored {len(chunks)} chunks for '{paper_title}'")
    return f"✅ Stored {len(chunks)} chunks from '{paper_title}' in the knowledge base."


@tool
def query_rag_store(query: str, n_results: int = 5) -> str:
    """Search the RAG knowledge base for relevant content from previously read papers.

    Args:
        query: The search query to find relevant paper excerpts
        n_results: Number of results to return (default 5)

    Returns:
        Relevant excerpts from stored papers with source attribution
    """
    print(f"RAG QUERY: '{query}'")
    collection, _ = _get_collection()

    if collection.count() == 0:
        return "The knowledge base is empty. Please read some papers first using read_pdf and store_paper_in_rag."

    results = collection.query(query_texts=[query], n_results=min(n_results, collection.count()))

    if not results["documents"] or not results["documents"][0]:
        return "No relevant content found in the knowledge base."

    formatted = []
    for i, (doc, meta) in enumerate(
        zip(results["documents"][0], results["metadatas"][0])
    ):
        source = meta.get("paper_title", "Unknown paper")
        url = meta.get("paper_url", "")
        source_info = f"{source}"
        if url:
            source_info += f" ({url})"

        formatted.append(
            f"**[Source {i+1}: {source_info}]**\n"
            f"{doc}\n"
        )

    header = f"Found {len(formatted)} relevant excerpts for: '{query}'\n\n"
    return header + "\n---\n".join(formatted)


def get_rag_stats() -> dict:
    """Get statistics about the RAG store."""
    try:
        collection, _ = _get_collection()
        count = collection.count()

        # Get unique papers
        if count > 0:
            all_meta = collection.get()["metadatas"]
            unique_papers = set(m.get("paper_title", "") for m in all_meta)
            return {
                "total_chunks": count,
                "total_papers": len(unique_papers),
                "paper_titles": list(unique_papers),
            }
        return {"total_chunks": 0, "total_papers": 0, "paper_titles": []}
    except Exception:
        return {"total_chunks": 0, "total_papers": 0, "paper_titles": []}
