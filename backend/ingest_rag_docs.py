#!/usr/bin/env python3
"""
Ingest RAG documents from backend/data/rag_docs into FAISS vector store.
Run this script to populate the RAG knowledge base with emotional wellness PDFs.

Usage:
    python ingest_rag_docs.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from utils.model_loader import ModelLoader
from logger.custom_logger import CustomLogger

load_dotenv()

log = CustomLogger().get_logger(__name__)


def ingest_documents(
    docs_dir: str = "data/rag_docs",
    vectorstore_dir: str = "rag/vectorstore",
    chunk_size: int = 800,
    chunk_overlap: int = 200
):
    """
    Load all PDFs from docs_dir, chunk them, and create/update FAISS index.
    
    Args:
        docs_dir: Directory containing PDF files
        vectorstore_dir: Directory to save FAISS index
        chunk_size: Size of text chunks
        chunk_overlap: Overlap between chunks
    """
    
    # Check for API keys
    if not os.getenv("GOOGLE_API_KEY") and not os.getenv("GEMINI_API_KEY"):
        log.error("No GOOGLE_API_KEY or GEMINI_API_KEY found in environment")
        print("\n❌ Error: GOOGLE_API_KEY or GEMINI_API_KEY is required for embeddings.")
        print("Please set it in your .env file:")
        print("  GEMINI_API_KEY=your_api_key_here")
        print("\nOr export it:")
        print("  export GEMINI_API_KEY=your_api_key_here\n")
        sys.exit(1)
    
    docs_path = Path(docs_dir)
    vectorstore_path = Path(vectorstore_dir)
    
    if not docs_path.exists():
        log.error("RAG docs directory not found", path=str(docs_path))
        print(f"\n❌ Error: Directory not found: {docs_path}")
        print("Please create it and add PDF files:\n")
        print(f"  mkdir -p {docs_path}")
        print(f"  # Then add your wellness PDFs to {docs_path}/\n")
        sys.exit(1)
    
    # Find all PDF files
    pdf_files = list(docs_path.glob("*.pdf"))
    
    if not pdf_files:
        log.warning("No PDF files found in RAG docs directory", path=str(docs_path))
        print(f"\n⚠️  No PDF files found in {docs_path}")
        print("Please add emotional wellness PDFs to ingest.\n")
        sys.exit(1)
    
    log.info("Found PDF files for ingestion", count=len(pdf_files), files=[f.name for f in pdf_files])
    print(f"\n📚 Found {len(pdf_files)} PDF files to ingest:\n")
    for pdf in pdf_files:
        print(f"  - {pdf.name}")
    print()
    
    # Load model loader
    try:
        log.info("Loading embeddings model...")
        print("🔧 Loading Google embeddings model...")
        model_loader = ModelLoader()
        embeddings = model_loader.load_embeddings()
        log.info("Embeddings model loaded successfully")
        print("✅ Embeddings model loaded\n")
    except Exception as e:
        log.error("Failed to load embeddings model", error=str(e))
        print(f"\n❌ Failed to load embeddings model: {e}\n")
        sys.exit(1)
    
    # Load and process documents
    all_documents = []
    
    print("📖 Loading PDFs...")
    for pdf_file in pdf_files:
        try:
            log.info("Loading PDF", file=pdf_file.name)
            print(f"  Loading {pdf_file.name}...", end=" ")
            
            loader = PyPDFLoader(str(pdf_file))
            docs = loader.load()
            
            # Add source metadata
            for doc in docs:
                doc.metadata["source_file"] = pdf_file.name
                doc.metadata["source_path"] = str(pdf_file)
            
            all_documents.extend(docs)
            print(f"✓ ({len(docs)} pages)")
            log.info("PDF loaded", file=pdf_file.name, pages=len(docs))
            
        except Exception as e:
            log.error("Failed to load PDF", file=pdf_file.name, error=str(e))
            print(f"✗ Error: {e}")
            continue
    
    if not all_documents:
        log.error("No documents loaded successfully")
        print("\n❌ No documents were loaded successfully.\n")
        sys.exit(1)
    
    total_pages = len(all_documents)
    log.info("All PDFs loaded", total_pages=total_pages)
    print(f"\n✅ Loaded {total_pages} total pages\n")
    
    # Split into chunks
    print(f"✂️  Splitting into chunks (size={chunk_size}, overlap={chunk_overlap})...")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
    )
    chunks = splitter.split_documents(all_documents)
    log.info("Documents split into chunks", count=len(chunks))
    print(f"✅ Created {len(chunks)} chunks\n")
    
    # Create or update FAISS index
    print("🔨 Building FAISS vector index (this may take a while)...")
    vectorstore_path.mkdir(parents=True, exist_ok=True)
    
    try:
        # Check if existing index exists
        index_file = vectorstore_path / "index.faiss"
        
        if index_file.exists():
            log.info("Existing FAISS index found, loading...")
            print("  Found existing index, loading...")
            vectorstore = FAISS.load_local(
                str(vectorstore_path),
                embeddings,
                allow_dangerous_deserialization=True
            )
            log.info("Adding new documents to existing index")
            print("  Adding new documents to existing index...")
            vectorstore.add_documents(chunks)
        else:
            log.info("Creating new FAISS index")
            print("  Creating new FAISS index...")
            vectorstore = FAISS.from_documents(chunks, embeddings)
        
        # Save the index
        vectorstore.save_local(str(vectorstore_path))
        log.info("FAISS index saved", path=str(vectorstore_path))
        print(f"✅ FAISS index saved to: {vectorstore_path}\n")
        
    except Exception as e:
        log.error("Failed to create FAISS index", error=str(e))
        print(f"\n❌ Failed to create FAISS index: {e}\n")
        sys.exit(1)
    
    # Summary
    print("=" * 60)
    print("✨ RAG Ingestion Complete!")
    print("=" * 60)
    print(f"📁 Source directory:  {docs_path}")
    print(f"📄 PDFs processed:    {len(pdf_files)}")
    print(f"📃 Total pages:       {total_pages}")
    print(f"🧩 Chunks created:    {len(chunks)}")
    print(f"💾 Index saved to:    {vectorstore_path}")
    print("=" * 60)
    print("\n🚀 Your RAG system is ready!")
    print("Start the backend server: python app.py\n")


if __name__ == "__main__":
    ingest_documents()
