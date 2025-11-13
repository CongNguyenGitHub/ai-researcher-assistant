"""
Base tool infrastructure for Context-Aware Research Assistant.

Provides abstract base class and interfaces for all retrieval tools.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

from models.context import ContextChunk, SourceType
from models.query import Query


class ToolStatus(str, Enum):
    """Status of a tool execution."""
    SUCCESS = "success"
    TIMEOUT = "timeout"
    ERROR = "error"
    DEGRADED = "degraded"


@dataclass
class ToolResult:
    """Result of a tool execution."""
    status: ToolStatus
    chunks: List[ContextChunk]
    execution_time_ms: float
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    
    def is_successful(self) -> bool:
        """Check if tool execution was successful."""
        return self.status in [ToolStatus.SUCCESS, ToolStatus.DEGRADED]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "status": self.status.value,
            "chunk_count": len(self.chunks),
            "execution_time_ms": self.execution_time_ms,
            "error_message": self.error_message,
            "error_details": self.error_details,
        }


class ToolBase(ABC):
    """
    Abstract base class for all retrieval tools.
    
    Tools are responsible for retrieving context from a specific source
    and converting results to standardized ContextChunk format.
    """
    
    def __init__(self, timeout_seconds: float = 7.0):
        """
        Initialize tool.
        
        Args:
            timeout_seconds: Maximum execution time
        """
        self.timeout_seconds = timeout_seconds
        self.last_execution_time_ms = 0.0
        self.last_error: Optional[str] = None
    
    @property
    @abstractmethod
    def source_type(self) -> SourceType:
        """Source type for this tool."""
        pass
    
    @property
    @abstractmethod
    def tool_name(self) -> str:
        """Human-readable tool name."""
        pass
    
    @abstractmethod
    def execute(self, query: Query) -> ToolResult:
        """
        Execute the tool to retrieve context for a query.
        
        Args:
            query: The query to retrieve context for
            
        Returns:
            ToolResult with chunks, status, and execution metrics
        """
        pass
    
    def validate_query(self, query: Query) -> bool:
        """
        Validate query is suitable for this tool.
        
        Args:
            query: Query to validate
            
        Returns:
            True if query is valid for this tool
        """
        return bool(query and query.text)
    
    def create_chunk(
        self,
        text: str,
        source_id: str,
        source_title: str,
        source_url: Optional[str] = None,
        source_date: Optional[datetime] = None,
        semantic_relevance: float = 0.8,
        source_reputation: float = 0.7,
        recency_score: float = 0.7,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ContextChunk:
        """
        Create a standardized ContextChunk from tool result.
        
        Args:
            text: Chunk content
            source_id: Unique source identifier
            source_title: Human-readable source title
            source_url: URL if applicable
            source_date: Publication/access date
            semantic_relevance: Relevance score (0-1)
            source_reputation: Reputation score (0-1)
            recency_score: Recency score (0-1)
            metadata: Tool-specific metadata
            
        Returns:
            Standardized ContextChunk
        """
        return ContextChunk(
            query_id="",  # Set by orchestrator
            source_type=self.source_type,
            text=text,
            semantic_relevance=semantic_relevance,
            source_reputation=source_reputation,
            recency_score=recency_score,
            source_id=source_id,
            source_title=source_title,
            source_url=source_url,
            source_date=source_date,
            metadata=metadata or {},
        )
    
    def create_error_result(
        self,
        status: ToolStatus,
        execution_time_ms: float,
        error_message: str,
        error_details: Optional[Dict[str, Any]] = None,
    ) -> ToolResult:
        """
        Create an error result.
        
        Args:
            status: Error status
            execution_time_ms: How long execution took before error
            error_message: User-friendly error message
            error_details: Technical error details
            
        Returns:
            ToolResult with error information
        """
        self.last_error = error_message
        return ToolResult(
            status=status,
            chunks=[],
            execution_time_ms=execution_time_ms,
            error_message=error_message,
            error_details=error_details,
        )
    
    def create_success_result(
        self,
        chunks: List[ContextChunk],
        execution_time_ms: float,
    ) -> ToolResult:
        """
        Create a success result.
        
        Args:
            chunks: Retrieved context chunks
            execution_time_ms: Execution time
            
        Returns:
            ToolResult with chunks
        """
        self.last_execution_time_ms = execution_time_ms
        self.last_error = None
        return ToolResult(
            status=ToolStatus.SUCCESS,
            chunks=chunks,
            execution_time_ms=execution_time_ms,
        )
