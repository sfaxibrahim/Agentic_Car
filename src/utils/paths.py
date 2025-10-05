import os
from pathlib import Path

def get_base_dir() -> Path:
    """Get the base directory of the project"""
    return Path(__file__).resolve().parent.parent

def get_data_dir() -> Path:
    """Get the data directory path"""
    return get_base_dir() / "data" / "PDF"

def get_vectorstore_path() -> Path:
    """Get the vectorstore path"""
    return get_base_dir() / "data" / "vector_store_faiss"