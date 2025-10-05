"""
RAG (Retrieval-Augmented Generation) service for PDF knowledge base
"""
import os
from typing import Optional
from langchain_community.vectorstores import FAISS
from langchain.retrievers import BM25Retriever, EnsembleRetriever
from langchain_huggingface import HuggingFaceEmbeddings
from config.settings import settings


# Global variables for singleton pattern
vector_store: Optional[FAISS] = None
bm25_retriever: Optional[BM25Retriever] = None


def load_vectorstore() -> Optional[FAISS]:
    """
    Load FAISS vectorstore from disk if not already in memory
    
    Returns:
        FAISS vectorstore instance or None if not found
    """
    global vector_store
    
    if vector_store is None:
        if os.path.exists(settings.VECTORSTORE_PATH):
            print(f"📂 Loading FAISS vectorstore from: {settings.VECTORSTORE_PATH}")
            
            embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2"
            )
            
            vector_store = FAISS.load_local(
                str(settings.VECTORSTORE_PATH),
                embeddings,
                allow_dangerous_deserialization=True
            )
            print("✅ FAISS vectorstore loaded successfully")
        else:
            print(f"❌ No saved FAISS vectorstore found at: {settings.VECTORSTORE_PATH}")
    
    return vector_store


def load_bm25() -> Optional[BM25Retriever]:
    """
    Rebuild BM25 retriever from FAISS stored documents if needed
    
    Returns:
        BM25Retriever instance or None if vectorstore not available
    """
    global bm25_retriever, vector_store
    
    if bm25_retriever is None and vector_store is not None:
        print("🔄 Rebuilding BM25 retriever from FAISS docs...")
        
        # FAISS stores docs internally
        docs = list(vector_store.docstore._dict.values())
        bm25_retriever = BM25Retriever.from_documents(docs)
        bm25_retriever.k = 15
        
        print("✅ BM25 retriever ready")
    
    return bm25_retriever


def search_pdf_knowledge(query: str) -> str:
    """
    Hybrid RAG search with semantic + keyword results
    
    Args:
        query: Search query
        
    Returns:
        Formatted search results or error message
    """
    global vector_store, bm25_retriever
    
    print(f"🔍 Searching PDF knowledge base for: '{query}'")
    
    # Load vectorstore and BM25 if needed
    vector_store = load_vectorstore()
    bm25_retriever = load_bm25()
    
    if vector_store is None or bm25_retriever is None:
        return "❌ RAG system not initialized. Please ensure FAISS vectorstore exists."
    
    try:
        # Create FAISS retriever
        faiss_retriever = vector_store.as_retriever(search_kwargs={"k": 15})
        
        # Create ensemble retriever combining BM25 and FAISS
        ensemble = EnsembleRetriever(
            retrievers=[bm25_retriever, faiss_retriever],
            weights=[0.4, 0.6]  # Favor semantic search slightly
        )
        
        # Retrieve relevant documents
        docs = ensemble.get_relevant_documents(query)
        
        if not docs:
            print("❌ No relevant information found in PDFs")
            return "The PDF documents do not contain specific information about this topic."
        
        print(f"✅ Found {len(docs)} relevant chunks, selecting top 3")
        
        # Format top 3 results
        final_docs = docs[:3]
        snippets = []
        
        for i, doc in enumerate(final_docs, 1):
            source = os.path.basename(doc.metadata.get('source', 'unknown.pdf'))
            page = doc.metadata.get('page', 'N/A')
            content = doc.page_content.strip()
            snippets.append(f"📄 [{source} - page {page}]\n{content}")
        
        return "\n\n".join(snippets)
    
    except Exception as e:
        print(f"❌ Error searching documents: {e}")
        return f"❌ Error searching documents: {str(e)}"