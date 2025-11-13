"""
Data Ingestion Module
Handles document parsing, embedding generation, and vector database loading
"""

from src.data_ingestion.parser import TensorLakeDocumentParser, ParsedDocument
from src.data_ingestion.embedder import GeminiEmbedder
from src.data_ingestion.milvus_loader import MilvusLoader
from src.data_ingestion.pipeline import DataIngestionPipeline

__all__ = [
    "TensorLakeDocumentParser",
    "ParsedDocument",
    "GeminiEmbedder",
    "MilvusLoader",
    "DataIngestionPipeline",
]
