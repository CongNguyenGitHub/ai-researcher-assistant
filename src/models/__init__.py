"""
Data models for Context-Aware Research Assistant.

Core domain models for queries, context, responses, and conversation memory.
"""

from .query import (
    Query,
    QueryPreferences,
    QueryStatus,
    Document,
)

from .context import (
    ContextChunk,
    AggregatedContext,
    FilteredContext,
    FilteredChunk,
    RemovedChunkRecord,
    ContradictionRecord,
    QualityScoring,
    SourceType,
    FilteringDecision,
)

from .response import (
    FinalResponse,
    ResponseSection,
    Perspective,
    SourceAttribution,
    ResponseQuality,
)

from .memory import (
    ConversationHistory,
    Message,
    UserPreferences,
    MessageRole,
)

__all__ = [
    # Query models
    "Query",
    "QueryPreferences",
    "QueryStatus",
    "Document",
    
    # Context models
    "ContextChunk",
    "AggregatedContext",
    "FilteredContext",
    "FilteredChunk",
    "RemovedChunkRecord",
    "ContradictionRecord",
    "QualityScoring",
    "SourceType",
    "FilteringDecision",
    
    # Response models
    "FinalResponse",
    "ResponseSection",
    "Perspective",
    "SourceAttribution",
    "ResponseQuality",
    
    # Memory models
    "ConversationHistory",
    "Message",
    "UserPreferences",
    "MessageRole",
]
