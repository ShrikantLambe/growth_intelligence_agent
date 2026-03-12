"""
Phase 3: Build the RAG knowledge base.
Loads company playbook documents, creates embeddings, and stores in FAISS.

Run: python rag/build_vectorstore.py
"""

import os
import glob
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

DOCS_DIR = os.path.join(os.path.dirname(__file__), "docs")
VECTORSTORE_DIR = os.path.join(os.path.dirname(__file__), "vectorstore")
os.makedirs(VECTORSTORE_DIR, exist_ok=True)

_REQUIRED_FILES = ["index.faiss", "index.pkl"]


def vectorstore_exists() -> bool:
    """Return True if the FAISS index files are present on disk."""
    return all(os.path.exists(os.path.join(VECTORSTORE_DIR, f)) for f in _REQUIRED_FILES)


def build_vectorstore():
    """Load markdown docs, embed them, and save a FAISS index."""

    # Lazy imports so the module can be imported without all deps installed
    from langchain_community.document_loaders import TextLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_community.vectorstores import FAISS
    from langchain_community.embeddings import HuggingFaceEmbeddings

    logger.info("Loading company documents from %s", DOCS_DIR)
    print("📚 Loading company documents...")
    doc_paths = glob.glob(os.path.join(DOCS_DIR, "*.md"))
    if not doc_paths:
        raise FileNotFoundError(f"No markdown files found in {DOCS_DIR}")

    docs = []
    for path in sorted(doc_paths):
        loader = TextLoader(path, encoding="utf-8")
        loaded = loader.load()
        for d in loaded:
            d.metadata["source"] = os.path.basename(path)
        docs.extend(loaded)
        print(f"  ✅ Loaded: {os.path.basename(path)}")

    print(f"\n✂️  Splitting {len(docs)} documents into chunks...")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100,
        separators=["\n## ", "\n### ", "\n\n", "\n", " "],
    )
    chunks = splitter.split_documents(docs)
    print(f"   → {len(chunks)} chunks created")

    print("\n🔢 Creating embeddings (HuggingFace all-MiniLM-L6-v2)...")
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
    )

    print("💾 Building FAISS index...")
    vectorstore = FAISS.from_documents(chunks, embeddings)
    vectorstore.save_local(VECTORSTORE_DIR)
    print(f"   → Saved to: {VECTORSTORE_DIR}")

    print("\n✅ RAG knowledge base ready!\n")
    logger.info("Vectorstore built: %d chunks saved to %s", len(chunks), VECTORSTORE_DIR)
    return vectorstore


def load_vectorstore():
    """Load an existing FAISS vectorstore. Raises if not yet built."""
    from langchain_community.vectorstores import FAISS
    from langchain_community.embeddings import HuggingFaceEmbeddings

    if not vectorstore_exists():
        raise FileNotFoundError(
            f"Vectorstore not found at {VECTORSTORE_DIR}. "
            "Run `python rag/build_vectorstore.py` first."
        )

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
    )
    return FAISS.load_local(VECTORSTORE_DIR, embeddings, allow_dangerous_deserialization=True)


def get_retriever(k: int = 4):
    """Return a retriever that fetches top-k relevant chunks."""
    vs = load_vectorstore()
    return vs.as_retriever(search_kwargs={"k": k})


def retrieve_context(query: str, k: int = 4) -> str:
    """Retrieve relevant company context for a given query."""
    retriever = get_retriever(k)
    docs = retriever.invoke(query)
    context_parts = []
    for i, doc in enumerate(docs, 1):
        source = doc.metadata.get("source", "unknown")
        context_parts.append(f"[Source: {source}]\n{doc.page_content}")
    logger.debug("Retrieved %d chunks for query: %s", len(context_parts), query[:80])
    return "\n\n---\n\n".join(context_parts)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    build_vectorstore()
    print("🔍 Test retrieval: 'What is our ICP?'")
    ctx = retrieve_context("What is our ideal customer profile?")
    print(ctx[:500] + "...\n")
