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
from .models import (
    Query,
    QueryPreferences,
    QueryStatus,
    Document,
    ContextChunk,
    AggregatedContext,
    FilteredContext,
    FilteredChunk,
    FinalResponse,
    ResponseSection,
    Perspective,
    SourceAttribution,
    ResponseQuality,
    ConversationHistory,
    Message,
    UserPreferences,
)
from .services import (
    Orchestrator,
    Evaluator,
    Synthesizer,
)
from .tools import (
    ToolBase,
    ToolResult,
    ToolStatus,
)
from .utils import (
    ValidationError,
    validate_query,
    validate_response,
    ResponseFormatter,
    format_response,
)

__version__ = "0.1.0-mvp"
__author__ = "AI Research Assistant Team"

# Export main configuration functions
__all__ = [
    "Config",
    "get_config",
    "init_config",
    "ConfigError",
    # Data ingestion
    "TensorLakeDocumentParser",
    "ParsedDocument",
    "GeminiEmbedder",
    "MilvusLoader",
    "DataIngestionPipeline",
    # Models
    "Query",
    "QueryPreferences",
    "QueryStatus",
    "Document",
    "ContextChunk",
    "AggregatedContext",
    "FilteredContext",
    "FilteredChunk",
    "FinalResponse",
    "ResponseSection",
    "Perspective",
    "SourceAttribution",
    "ResponseQuality",
    "ConversationHistory",
    "Message",
    "UserPreferences",
    # Services
    "Orchestrator",
    "Evaluator",
    "Synthesizer",
    # Tools
    "ToolBase",
    "ToolResult",
    "ToolStatus",
    # Utils
    "ValidationError",
    "validate_query",
    "validate_response",
    "ResponseFormatter",
    "format_response",
]
