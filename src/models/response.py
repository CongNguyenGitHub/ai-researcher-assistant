"""
Response data models for Context-Aware Research Assistant.

Defines data structures for synthesized answers and response attribution.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
import uuid


@dataclass
class ResponseSection:
    """
    A section of the final response with specific information.
    
    Attributes:
        heading: Section title/heading
        content: The actual section content
        confidence: Quality score for this section (0-1)
        sources: IDs of sources contributing to this section
        order: Display order
    """
    heading: str = ""
    content: str = ""
    confidence: float = 0.8
    sources: List[str] = field(default_factory=list)
    order: int = 0
    
    def __post_init__(self):
        """Validate section."""
        if not self.content:
            raise ValueError("content must be non-empty")
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be 0-1")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "heading": self.heading,
            "content": self.content,
            "confidence": self.confidence,
            "sources": self.sources,
            "order": self.order,
        }


@dataclass
class Perspective:
    """
    Alternative viewpoint or claim when contradictions exist.
    
    Attributes:
        viewpoint: The actual claim/perspective
        summary: Explanation of perspective
        confidence: How well-supported this viewpoint is (0-1)
        sources: Source IDs supporting this viewpoint
        weight: Ratio of supporting sources vs alternatives
    """
    viewpoint: str = ""
    summary: str = ""
    confidence: float = 0.5
    sources: List[str] = field(default_factory=list)
    weight: float = 0.5
    
    def __post_init__(self):
        """Validate perspective."""
        if not self.viewpoint:
            raise ValueError("viewpoint must be non-empty")
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be 0-1")
        if not 0 <= self.weight <= 1:
            raise ValueError("weight must be 0-1")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "viewpoint": self.viewpoint,
            "summary": self.summary,
            "confidence": self.confidence,
            "sources": self.sources,
            "weight": self.weight,
        }


@dataclass
class SourceAttribution:
    """
    Attribution of a source used in the response.
    
    Attributes:
        id: Source ID
        type: Source type (rag, web, arxiv, memory)
        title: Source title
        url: Source URL (if applicable)
        relevance: How relevant to final answer (0-1)
        contribution: How this source contributed
    """
    id: str = ""
    type: str = "rag"  # rag, web, arxiv, memory
    title: str = ""
    url: Optional[str] = None
    relevance: float = 0.8
    contribution: str = ""
    
    def __post_init__(self):
        """Validate attribution."""
        if not self.id:
            raise ValueError("id must be non-empty")
        if self.type not in ["rag", "web", "arxiv", "memory"]:
            raise ValueError(f"Invalid type: {self.type}")
        if not self.title:
            raise ValueError("title must be non-empty")
        if not 0 <= self.relevance <= 1:
            raise ValueError("relevance must be 0-1")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "type": self.type,
            "title": self.title,
            "url": self.url,
            "relevance": self.relevance,
            "contribution": self.contribution,
        }


@dataclass
class ResponseQuality:
    """
    Quality metrics for the generated response.
    
    Attributes:
        has_contradictions: Whether contradictions were detected
        degraded_mode: Whether generated with limited context
        completeness: How well query was addressed (0-1)
        informativeness: Quality of information provided (0-1)
        confidence: Overall response confidence (0-1)
    """
    has_contradictions: bool = False
    degraded_mode: bool = False
    completeness: float = 0.8
    informativeness: float = 0.8
    confidence: float = 0.8
    
    def __post_init__(self):
        """Validate quality metrics."""
        for attr in ["completeness", "informativeness", "confidence"]:
            value = getattr(self, attr)
            if not 0 <= value <= 1:
                raise ValueError(f"{attr} must be 0-1")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "has_contradictions": self.has_contradictions,
            "degraded_mode": self.degraded_mode,
            "completeness": self.completeness,
            "informativeness": self.informativeness,
            "confidence": self.confidence,
        }


@dataclass
class FinalResponse:
    """
    Synthesized answer to user's research query.
    
    Attributes:
        id: Unique identifier
        query_id: Reference to originating query
        user_id: User who made the query
        session_id: Conversation session
        answer: Main answer/summary
        sections: Detailed breakdown into sections
        perspectives: Alternative viewpoints (if contradictions exist)
        overall_confidence: Overall confidence (0-1)
        generation_time_ms: How long generation took
        sources: List of source attributions
        sources_consulted: Which source types were used
        timestamp: When response was generated
        response_quality: Quality metrics
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    query_id: str = ""
    user_id: str = ""
    session_id: str = ""
    answer: str = ""
    sections: List[ResponseSection] = field(default_factory=list)
    perspectives: Optional[List[Perspective]] = None
    overall_confidence: float = 0.8
    generation_time_ms: float = 0.0
    sources: List[SourceAttribution] = field(default_factory=list)
    sources_consulted: List[str] = field(default_factory=list)
    response_quality: ResponseQuality = field(default_factory=ResponseQuality)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        """Validate response."""
        self._validate()
    
    def _validate(self):
        """Validate response fields."""
        if not self.answer:
            raise ValueError("answer must be non-empty")
        
        if not 0 <= self.overall_confidence <= 1:
            raise ValueError("overall_confidence must be 0-1")
        
        if self.perspectives:
            if len(self.perspectives) < 2:
                raise ValueError("If perspectives provided, must have 2+ items")
        
        for section in self.sections:
            if not 0 <= section.confidence <= 1:
                raise ValueError(f"Section '{section.heading}' confidence must be 0-1")
        
        for source in self.sources:
            if not source.id:
                raise ValueError("Source must have non-empty id")
    
    def add_section(self, section: ResponseSection):
        """Add a section to the response."""
        section.order = len(self.sections)
        self.sections.append(section)
    
    def add_source(self, source: SourceAttribution):
        """Add a source attribution."""
        self.sources.append(source)
        if source.type not in self.sources_consulted:
            self.sources_consulted.append(source.type)
    
    def add_perspective(self, perspective: Perspective):
        """Add an alternative perspective."""
        if self.perspectives is None:
            self.perspectives = []
        self.perspectives.append(perspective)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "query_id": self.query_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "answer": self.answer,
            "sections": [s.to_dict() for s in self.sections],
            "perspectives": [p.to_dict() for p in (self.perspectives or [])],
            "overall_confidence": self.overall_confidence,
            "generation_time_ms": self.generation_time_ms,
            "sources": [s.to_dict() for s in self.sources],
            "sources_consulted": self.sources_consulted,
            "source_count": len(self.sources),
            "response_quality": self.response_quality.to_dict(),
            "timestamp": self.timestamp.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FinalResponse":
        """Create FinalResponse from dictionary."""
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        
        sections = [ResponseSection(**s) for s in data.get("sections", [])]
        perspectives = None
        if data.get("perspectives"):
            perspectives = [Perspective(**p) for p in data["perspectives"]]
        
        sources = [SourceAttribution(**s) for s in data.get("sources", [])]
        
        response_quality_data = data.get("response_quality", {})
        response_quality = ResponseQuality(**response_quality_data)
        
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            query_id=data.get("query_id", ""),
            user_id=data.get("user_id", ""),
            session_id=data.get("session_id", ""),
            answer=data.get("answer", ""),
            sections=sections,
            perspectives=perspectives,
            overall_confidence=data.get("overall_confidence", 0.8),
            generation_time_ms=data.get("generation_time_ms", 0.0),
            sources=sources,
            sources_consulted=data.get("sources_consulted", []),
            response_quality=response_quality,
            timestamp=timestamp or datetime.utcnow(),
        )
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of response."""
        return {
            "id": self.id,
            "query_id": self.query_id,
            "answer_length": len(self.answer),
            "section_count": len(self.sections),
            "source_count": len(self.sources),
            "sources_types": self.sources_consulted,
            "has_perspectives": bool(self.perspectives),
            "overall_confidence": self.overall_confidence,
            "generation_time_ms": self.generation_time_ms,
        }
