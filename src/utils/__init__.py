"""
Utilities module for Context-Aware Research Assistant.

Validation and formatting utilities for data models and responses.
"""

from .validators import (
    ValidationError,
    validate_query,
    validate_context_chunk,
    validate_filtered_context,
    validate_response,
    validate_document,
    validate_conversation_history,
    raise_if_invalid,
)

from .formatters import (
    ResponseFormatter,
    CitationFormatter,
    ContradictionFormatter,
    format_response,
)

__all__ = [
    # Validators
    "ValidationError",
    "validate_query",
    "validate_context_chunk",
    "validate_filtered_context",
    "validate_response",
    "validate_document",
    "validate_conversation_history",
    "raise_if_invalid",
    
    # Formatters
    "ResponseFormatter",
    "CitationFormatter",
    "ContradictionFormatter",
    "format_response",
]
