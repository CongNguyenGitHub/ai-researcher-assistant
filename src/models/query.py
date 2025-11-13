"""
Query data models for Context-Aware Research Assistant.

Defines data structures for user research queries and associated metadata.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum
import uuid


class QueryStatus(str, Enum):
    """Valid query status values."""
    SUBMITTED = "submitted"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class QueryPreferences:
    """Query-specific preferences that override user defaults."""
    response_format: Optional[str] = None  # "concise", "detailed", "technical", "narrative"
    preferred_sources: Optional[list[str]] = None  # Order of preference
    information_depth: Optional[str] = None  # "overview", "comprehensive", "expert"
    max_response_length: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class Query:
    """
    Represents a user's research question with context and metadata.
    
    Attributes:
        id: Unique identifier (UUID or hash of user+timestamp+query)
        user_id: User identifier for memory tracking
        session_id: Conversation session identifier
        text: The actual research question
        timestamp: When query was submitted
        topic_category: Optional user-provided category (e.g., "technology", "science")
        context_window: Optional prior context from conversation
        preferences: Optional query-specific preferences override
        status: Current status (submitted, processing, completed, failed)
        error_message: Error description if status is failed
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    session_id: str = ""
    text: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    topic_category: Optional[str] = None
    context_window: Optional[str] = None
    preferences: Optional[QueryPreferences] = None
    status: QueryStatus = QueryStatus.SUBMITTED
    error_message: Optional[str] = None
    
    def __post_init__(self):
        """Validate query after initialization."""
        self._validate()
    
    def _validate(self):
        """Validate query fields."""
        if not self.text or not isinstance(self.text, str):
            raise ValueError("Query text must be non-empty string")
        
        if len(self.text) > 5000:
            raise ValueError("Query text must be <= 5000 characters")
        
        if not self.user_id:
            raise ValueError("user_id must be non-empty")
        
        if not self.session_id:
            raise ValueError("session_id must be non-empty")
        
        if self.timestamp > datetime.utcnow():
            raise ValueError("Query timestamp cannot be in the future")
        
        if self.status not in QueryStatus:
            raise ValueError(f"Invalid status: {self.status}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "text": self.text,
            "timestamp": self.timestamp.isoformat(),
            "topic_category": self.topic_category,
            "context_window": self.context_window,
            "preferences": self.preferences.to_dict() if self.preferences else None,
            "status": self.status.value,
            "error_message": self.error_message,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Query":
        """Create Query from dictionary."""
        prefs = None
        if data.get("preferences"):
            prefs = QueryPreferences(**data["preferences"])
        
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            user_id=data.get("user_id", ""),
            session_id=data.get("session_id", ""),
            text=data.get("text", ""),
            timestamp=timestamp or datetime.utcnow(),
            topic_category=data.get("topic_category"),
            context_window=data.get("context_window"),
            preferences=prefs,
            status=QueryStatus(data.get("status", "submitted")),
            error_message=data.get("error_message"),
        )
    
    def mark_processing(self):
        """Mark query as currently processing."""
        self.status = QueryStatus.PROCESSING
    
    def mark_completed(self):
        """Mark query as successfully completed."""
        self.status = QueryStatus.COMPLETED
        self.error_message = None
    
    def mark_failed(self, error: str):
        """Mark query as failed with error message."""
        self.status = QueryStatus.FAILED
        self.error_message = error


@dataclass
class Document:
    """
    Represents a user-uploaded file to be indexed in the RAG system.
    
    Attributes:
        id: Unique identifier (UUID)
        user_id: User who uploaded it
        filename: Original filename
        file_type: Type of file (pdf, docx, txt, markdown)
        file_size: Size in bytes
        uploaded_at: When file was uploaded
        upload_status: Current stage (pending, parsing, embedding, storing, complete, failed)
        chunks_created: How many chunks created from this document
        collection_name: Milvus collection where chunks are stored
        title: Document title (if detected)
        pages: Page count (for PDF, DOCX)
        error_message: Error description if failed
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    filename: str = ""
    file_type: str = ""
    file_size: int = 0
    uploaded_at: datetime = field(default_factory=datetime.utcnow)
    upload_status: str = "pending"
    chunks_created: int = 0
    collection_name: str = "documents"
    title: Optional[str] = None
    pages: Optional[int] = None
    error_message: Optional[str] = None
    last_updated: datetime = field(default_factory=datetime.utcnow)
    
    VALID_FILE_TYPES = {"pdf", "docx", "txt", "markdown"}
    VALID_STATUSES = {"pending", "parsing", "embedding", "storing", "complete", "failed"}
    
    def __post_init__(self):
        """Validate document after initialization."""
        self._validate()
    
    def _validate(self):
        """Validate document fields."""
        if not self.filename:
            raise ValueError("filename must be non-empty")
        
        if self.file_type not in self.VALID_FILE_TYPES:
            raise ValueError(f"Invalid file_type: {self.file_type}. Must be one of {self.VALID_FILE_TYPES}")
        
        if self.file_size <= 0:
            raise ValueError("file_size must be > 0")
        
        if self.file_size > 100 * 1024 * 1024:  # 100MB limit
            raise ValueError("file_size must be <= 100MB")
        
        if self.upload_status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid upload_status: {self.upload_status}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "filename": self.filename,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "uploaded_at": self.uploaded_at.isoformat(),
            "upload_status": self.upload_status,
            "chunks_created": self.chunks_created,
            "collection_name": self.collection_name,
            "title": self.title,
            "pages": self.pages,
            "error_message": self.error_message,
            "last_updated": self.last_updated.isoformat(),
        }
    
    def update_status(self, status: str, error_message: Optional[str] = None):
        """Update document status."""
        if status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid status: {status}")
        self.upload_status = status
        self.error_message = error_message
        self.last_updated = datetime.utcnow()
