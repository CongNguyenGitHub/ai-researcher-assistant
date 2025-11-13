"""
Context-Aware Research Assistant
A crewAI-orchestrated system that synthesizes comprehensive research answers
from multiple parallel sources (RAG, web search, academic papers, conversation memory)
"""

from .config import Config, get_config, init_config, ConfigError
from .data_ingestion import (
    TensorLakeDocumentParser,
    ParsedDocument,
    GeminiEmbedder,
    MilvusLoader,
    DataIngestionPipeline,
)

__version__ = "0.1.0-mvp"
__author__ = "AI Research Assistant Team"

# Export main configuration functions
__all__ = [
    "Config",
    "get_config",
    "init_config",
    "ConfigError",
    "TensorLakeDocumentParser",
    "ParsedDocument",
    "GeminiEmbedder",
    "MilvusLoader",
    "DataIngestionPipeline",
]
