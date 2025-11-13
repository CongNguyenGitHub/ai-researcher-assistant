"""
Memory and conversation data models for Context-Aware Research Assistant.

Defines data structures for conversation history and user memory management.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
import uuid


class MessageRole(str, Enum):
    """Message sender role."""
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class Message:
    """
    Single message in conversation history.
    
    Attributes:
        id: Unique message identifier
        role: Who sent it (user or assistant)
        content: Full message text
        timestamp: When message was sent
        metadata: Additional data (sources, confidence, etc.)
        response_id: Link to FinalResponse (for assistant messages)
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    role: MessageRole = MessageRole.USER
    content: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = None
    response_id: Optional[str] = None
    
    def __post_init__(self):
        """Validate message."""
        if not self.content:
            raise ValueError("content must be non-empty")
        
        if self.role not in MessageRole:
            raise ValueError(f"Invalid role: {self.role}")
        
        if self.timestamp > datetime.utcnow():
            raise ValueError("timestamp cannot be in future")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "response_id": self.response_id,
        }


@dataclass
class UserPreferences:
    """
    User settings that affect response generation.
    
    Attributes:
        user_id: User identifier
        response_format: Preferred format (concise, detailed, technical, narrative)
        max_response_length: Character limit for responses
        include_citations: Whether to include source citations
        preferred_sources: Ordered list of source preferences
        exclude_sources: Sources to never use
        information_depth: Desired depth (overview, comprehensive, expert)
        explanation_style: How to explain (academic, casual, instructional)
        topic_interests: Topics the user cares about
        last_updated: When preferences were last updated
    """
    user_id: str = ""
    response_format: str = "detailed"  # concise, detailed, technical, narrative
    max_response_length: int = 5000
    include_citations: bool = True
    preferred_sources: List[str] = field(default_factory=lambda: ["rag", "arxiv", "web", "memory"])
    exclude_sources: List[str] = field(default_factory=list)
    preferred_domains: Optional[List[str]] = None
    information_depth: str = "comprehensive"  # overview, comprehensive, expert
    explanation_style: str = "academic"  # academic, casual, instructional
    topic_interests: List[str] = field(default_factory=list)
    date_preference: str = "recent"  # recent, any, historical
    last_updated: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        """Validate preferences."""
        if not self.user_id:
            raise ValueError("user_id must be non-empty")
        
        valid_formats = {"concise", "detailed", "technical", "narrative"}
        if self.response_format not in valid_formats:
            raise ValueError(f"Invalid response_format: {self.response_format}")
        
        valid_depths = {"overview", "comprehensive", "expert"}
        if self.information_depth not in valid_depths:
            raise ValueError(f"Invalid information_depth: {self.information_depth}")
        
        valid_styles = {"academic", "casual", "instructional"}
        if self.explanation_style not in valid_styles:
            raise ValueError(f"Invalid explanation_style: {self.explanation_style}")
        
        if self.max_response_length <= 0:
            raise ValueError("max_response_length must be > 0")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "user_id": self.user_id,
            "response_format": self.response_format,
            "max_response_length": self.max_response_length,
            "include_citations": self.include_citations,
            "preferred_sources": self.preferred_sources,
            "exclude_sources": self.exclude_sources,
            "preferred_domains": self.preferred_domains,
            "information_depth": self.information_depth,
            "explanation_style": self.explanation_style,
            "topic_interests": self.topic_interests,
            "date_preference": self.date_preference,
            "last_updated": self.last_updated.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserPreferences":
        """Create UserPreferences from dictionary."""
        last_updated = data.get("last_updated")
        if isinstance(last_updated, str):
            last_updated = datetime.fromisoformat(last_updated)
        
        return cls(
            user_id=data.get("user_id", ""),
            response_format=data.get("response_format", "detailed"),
            max_response_length=data.get("max_response_length", 5000),
            include_citations=data.get("include_citations", True),
            preferred_sources=data.get("preferred_sources", ["rag", "arxiv", "web", "memory"]),
            exclude_sources=data.get("exclude_sources", []),
            preferred_domains=data.get("preferred_domains"),
            information_depth=data.get("information_depth", "comprehensive"),
            explanation_style=data.get("explanation_style", "academic"),
            topic_interests=data.get("topic_interests", []),
            date_preference=data.get("date_preference", "recent"),
            last_updated=last_updated or datetime.utcnow(),
        )


@dataclass
class ConversationHistory:
    """
    Persistent record of user interactions across sessions.
    
    Attributes:
        session_id: Unique session identifier
        user_id: User who owns this session
        created_at: When session started
        last_updated: When last activity occurred
        messages: Ordered conversation messages
        topics_discussed: Topics mentioned in this session
        user_preferences_inferred: User preferences learned from this session
        query_count: Total queries in session
        average_confidence: Mean confidence of responses
    """
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)
    messages: List[Message] = field(default_factory=list)
    topics_discussed: List[str] = field(default_factory=list)
    user_preferences_inferred: Optional[UserPreferences] = None
    query_count: int = 0
    average_confidence: float = 0.8
    
    def __post_init__(self):
        """Validate history."""
        if not self.user_id:
            raise ValueError("user_id must be non-empty")
        
        if self.created_at > datetime.utcnow():
            raise ValueError("created_at cannot be in future")
    
    def add_message(self, message: Message):
        """Add a message to history."""
        self.messages.append(message)
        self.last_updated = datetime.utcnow()
        
        # Update statistics
        if message.role == MessageRole.USER:
            self.query_count += 1
        
        # Update topic list if metadata contains topics
        if message.metadata and "topics" in message.metadata:
            for topic in message.metadata["topics"]:
                if topic not in self.topics_discussed:
                    self.topics_discussed.append(topic)
    
    def get_last_user_message(self) -> Optional[Message]:
        """Get the last user message in history."""
        for message in reversed(self.messages):
            if message.role == MessageRole.USER:
                return message
        return None
    
    def get_last_assistant_message(self) -> Optional[Message]:
        """Get the last assistant message in history."""
        for message in reversed(self.messages):
            if message.role == MessageRole.ASSISTANT:
                return message
        return None
    
    def get_recent_context(self, message_count: int = 5) -> List[Message]:
        """
        Get recent messages for context (last N messages).
        
        Args:
            message_count: Number of messages to return
            
        Returns:
            Last N messages in chronological order
        """
        return self.messages[-message_count:]
    
    def update_average_confidence(self):
        """Recalculate average confidence from assistant messages."""
        assistant_messages = [m for m in self.messages if m.role == MessageRole.ASSISTANT]
        if assistant_messages:
            confidences = []
            for msg in assistant_messages:
                if msg.metadata and "confidence" in msg.metadata:
                    confidences.append(msg.metadata["confidence"])
            
            if confidences:
                self.average_confidence = sum(confidences) / len(confidences)
    
    def to_dict(self, include_messages: bool = True) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "topics_discussed": self.topics_discussed,
            "query_count": self.query_count,
            "average_confidence": self.average_confidence,
        }
        
        if include_messages:
            data["messages"] = [m.to_dict() for m in self.messages]
        
        if self.user_preferences_inferred:
            data["user_preferences_inferred"] = self.user_preferences_inferred.to_dict()
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationHistory":
        """Create ConversationHistory from dictionary."""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        
        last_updated = data.get("last_updated")
        if isinstance(last_updated, str):
            last_updated = datetime.fromisoformat(last_updated)
        
        messages = [Message(**m) if isinstance(m, dict) else m for m in data.get("messages", [])]
        
        prefs = None
        if data.get("user_preferences_inferred"):
            prefs = UserPreferences.from_dict(data["user_preferences_inferred"])
        
        return cls(
            session_id=data.get("session_id", str(uuid.uuid4())),
            user_id=data.get("user_id", ""),
            created_at=created_at or datetime.utcnow(),
            last_updated=last_updated or datetime.utcnow(),
            messages=messages,
            topics_discussed=data.get("topics_discussed", []),
            user_preferences_inferred=prefs,
            query_count=data.get("query_count", 0),
            average_confidence=data.get("average_confidence", 0.8),
        )
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of conversation."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "message_count": len(self.messages),
            "query_count": self.query_count,
            "topics_discussed": self.topics_discussed,
            "average_confidence": self.average_confidence,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
        }
