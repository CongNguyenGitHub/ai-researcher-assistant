"""
Validators for Context-Aware Research Assistant.

Functions for validating data models and input across the system.
"""

from typing import Tuple, List, Optional
from datetime import datetime

from models.query import Query, QueryStatus, Document
from models.context import ContextChunk, FilteredContext, AggregatedContext
from models.response import FinalResponse, ResponseSection
from models.memory import ConversationHistory, Message, MessageRole


class ValidationError(Exception):
    """Raised when validation fails."""
    pass


def validate_query(query: Query) -> Tuple[bool, Optional[str]]:
    """
    Validate a Query object.
    
    Args:
        query: Query to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not query:
        return False, "Query object is None"
    
    if not query.text:
        return False, "Query text is required"
    
    if len(query.text) > 5000:
        return False, f"Query text too long: {len(query.text)} > 5000 chars"
    
    if len(query.text) < 3:
        return False, "Query text too short (minimum 3 characters)"
    
    if not query.user_id:
        return False, "user_id is required"
    
    if not query.session_id:
        return False, "session_id is required"
    
    if query.timestamp > datetime.utcnow():
        return False, "Query timestamp cannot be in the future"
    
    try:
        if query.status not in [QueryStatus.SUBMITTED, QueryStatus.PROCESSING, 
                                QueryStatus.COMPLETED, QueryStatus.FAILED]:
            return False, f"Invalid query status: {query.status}"
    except (AttributeError, ValueError):
        return False, "Invalid status value"
    
    return True, None


def validate_context_chunk(chunk: ContextChunk) -> Tuple[bool, Optional[str]]:
    """
    Validate a ContextChunk object.
    
    Args:
        chunk: ContextChunk to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not chunk:
        return False, "ContextChunk object is None"
    
    if not chunk.text:
        return False, "Chunk text is required"
    
    if len(chunk.text) > 10000:
        return False, f"Chunk text too long: {len(chunk.text)} > 10000 chars"
    
    if not 0 <= chunk.semantic_relevance <= 1:
        return False, f"semantic_relevance out of range: {chunk.semantic_relevance}"
    
    if not 0 <= chunk.source_reputation <= 1:
        return False, f"source_reputation out of range: {chunk.source_reputation}"
    
    if not 0 <= chunk.recency_score <= 1:
        return False, f"recency_score out of range: {chunk.recency_score}"
    
    if not chunk.source_id:
        return False, "source_id is required"
    
    if chunk.source_date and chunk.source_date > datetime.utcnow():
        return False, "source_date cannot be in the future"
    
    return True, None


def validate_aggregated_context(context: AggregatedContext) -> Tuple[bool, Optional[str]]:
    """
    Validate an AggregatedContext object.
    
    Args:
        context: AggregatedContext to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not context:
        return False, "AggregatedContext object is None"
    
    if not context.query_id:
        return False, "query_id is required"
    
    if context.retrieval_time_ms < 0:
        return False, "retrieval_time_ms cannot be negative"
    
    for chunk in context.chunks:
        is_valid, error = validate_context_chunk(chunk)
        if not is_valid:
            return False, f"Invalid chunk in context: {error}"
    
    if context.total_chunks_after_dedup > context.total_chunks_before_dedup:
        return False, "After-dedup count cannot exceed before-dedup count"
    
    return True, None


def validate_filtered_context(context: FilteredContext) -> Tuple[bool, Optional[str]]:
    """
    Validate a FilteredContext object.
    
    Args:
        context: FilteredContext to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not context:
        return False, "FilteredContext object is None"
    
    if not context.query_id:
        return False, "query_id is required"
    
    if context.filtered_chunk_count > context.original_chunk_count:
        return False, "filtered_chunk_count cannot exceed original_chunk_count"
    
    if not 0 <= context.average_quality_score <= 1:
        return False, f"average_quality_score out of range: {context.average_quality_score}"
    
    if not 0 <= context.quality_threshold_used <= 1:
        return False, f"quality_threshold_used out of range: {context.quality_threshold_used}"
    
    for chunk in context.chunks:
        is_valid, error = validate_context_chunk(chunk)
        if not is_valid:
            return False, f"Invalid chunk in filtered context: {error}"
    
    if context.filtering_time_ms < 0:
        return False, "filtering_time_ms cannot be negative"
    
    return True, None


def validate_response(response: FinalResponse) -> Tuple[bool, Optional[str]]:
    """
    Validate a FinalResponse object.
    
    Args:
        response: FinalResponse to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not response:
        return False, "FinalResponse object is None"
    
    if not response.query_id:
        return False, "query_id is required"
    
    if not response.user_id:
        return False, "user_id is required"
    
    if not response.answer:
        return False, "answer is required"
    
    if len(response.answer) > 50000:
        return False, f"answer too long: {len(response.answer)} > 50000 chars"
    
    if not 0 <= response.overall_confidence <= 1:
        return False, f"overall_confidence out of range: {response.overall_confidence}"
    
    if response.generation_time_ms < 0:
        return False, "generation_time_ms cannot be negative"
    
    # Validate sections
    for section in response.sections:
        if not section.heading:
            return False, "Section heading is required"
        
        if not section.content:
            return False, "Section content is required"
        
        if not 0 <= section.confidence <= 1:
            return False, f"Section confidence out of range: {section.confidence}"
    
    # Validate perspectives if present
    if response.perspectives:
        if len(response.perspectives) < 2:
            return False, "If perspectives provided, must have 2+ items"
        
        for perspective in response.perspectives:
            if not perspective.viewpoint:
                return False, "Perspective viewpoint is required"
    
    # Validate response quality
    if not 0 <= response.response_quality.completeness <= 1:
        return False, "quality.completeness out of range"
    
    if not 0 <= response.response_quality.informativeness <= 1:
        return False, "quality.informativeness out of range"
    
    return True, None


def validate_document(document: Document) -> Tuple[bool, Optional[str]]:
    """
    Validate a Document object.
    
    Args:
        document: Document to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not document:
        return False, "Document object is None"
    
    if not document.filename:
        return False, "filename is required"
    
    if not document.file_type:
        return False, "file_type is required"
    
    valid_types = {"pdf", "docx", "txt", "markdown"}
    if document.file_type not in valid_types:
        return False, f"Invalid file_type: {document.file_type}"
    
    if document.file_size <= 0:
        return False, "file_size must be > 0"
    
    if document.file_size > 100 * 1024 * 1024:
        return False, "file_size must be <= 100MB"
    
    if not document.user_id:
        return False, "user_id is required"
    
    valid_statuses = {"pending", "parsing", "embedding", "storing", "complete", "failed"}
    if document.upload_status not in valid_statuses:
        return False, f"Invalid upload_status: {document.upload_status}"
    
    return True, None


def validate_conversation_history(history: ConversationHistory) -> Tuple[bool, Optional[str]]:
    """
    Validate a ConversationHistory object.
    
    Args:
        history: ConversationHistory to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not history:
        return False, "ConversationHistory object is None"
    
    if not history.user_id:
        return False, "user_id is required"
    
    if history.created_at > datetime.utcnow():
        return False, "created_at cannot be in the future"
    
    if history.query_count < 0:
        return False, "query_count cannot be negative"
    
    if not 0 <= history.average_confidence <= 1:
        return False, f"average_confidence out of range: {history.average_confidence}"
    
    for message in history.messages:
        if message.role not in [MessageRole.USER, MessageRole.ASSISTANT]:
            return False, f"Invalid message role: {message.role}"
        
        if not message.content:
            return False, "Message content is required"
    
    return True, None


def raise_if_invalid(obj, validator_func, object_name: str = "object"):
    """
    Validate an object and raise ValidationError if invalid.
    
    Args:
        obj: Object to validate
        validator_func: Validator function that returns (is_valid, error_message)
        object_name: Name for error message
        
    Raises:
        ValidationError if validation fails
    """
    is_valid, error_message = validator_func(obj)
    if not is_valid:
        raise ValidationError(f"Invalid {object_name}: {error_message}")
