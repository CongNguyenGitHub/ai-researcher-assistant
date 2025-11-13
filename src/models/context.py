"""
Context data models for Context-Aware Research Assistant.

Defines data structures for aggregated context from parallel sources
and filtered high-quality context for response generation.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
import uuid


class SourceType(str, Enum):
    """Valid source types for context chunks."""
    RAG = "rag"              # Retrieved from indexed documents
    WEB = "web"              # From web search via Firecrawl
    ARXIV = "arxiv"          # From academic papers
    MEMORY = "memory"        # From conversation history
    

class FilteringDecision(str, Enum):
    """Why a chunk was kept or removed."""
    KEPT = "kept"
    DEDUPLICATED = "deduplicated"
    LOW_QUALITY = "low_quality"
    CONTRADICTORY = "contradictory"


@dataclass
class ContextChunk:
    """
    Individual piece of information retrieved from any source.
    
    Attributes:
        id: Unique identifier
        query_id: Reference to originating query
        source_type: Where chunk came from (rag, web, arxiv, memory)
        text: The actual content
        semantic_relevance: 0-1 score from embedding similarity
        source_reputation: 0-1 score based on source type
        recency_score: 0-1 score based on document age
        source_id: ID of original document/webpage/paper
        source_title: Title of source
        source_url: URL if applicable
        source_date: When content was published
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    query_id: str = ""
    source_type: SourceType = SourceType.RAG
    text: str = ""
    semantic_relevance: float = 0.0
    source_reputation: float = 0.0
    recency_score: float = 0.0
    source_id: str = ""
    source_title: Optional[str] = None
    source_url: Optional[str] = None
    source_date: Optional[datetime] = None
    position_in_source: Optional[int] = None
    chunk_number: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        """Validate context chunk after initialization."""
        self._validate()
    
    def _validate(self):
        """Validate chunk fields."""
        if not self.text:
            raise ValueError("text must be non-empty")
        
        if len(self.text) > 10000:
            raise ValueError("text must be <= 10000 characters")
        
        if not 0 <= self.semantic_relevance <= 1:
            raise ValueError("semantic_relevance must be 0-1")
        
        if not 0 <= self.source_reputation <= 1:
            raise ValueError("source_reputation must be 0-1")
        
        if not 0 <= self.recency_score <= 1:
            raise ValueError("recency_score must be 0-1")
        
        if self.source_type not in SourceType:
            raise ValueError(f"Invalid source_type: {self.source_type}")
        
        if not self.source_id:
            raise ValueError("source_id must be non-empty")
        
        if self.source_date and self.source_date > datetime.utcnow():
            raise ValueError("source_date cannot be in future")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "query_id": self.query_id,
            "source_type": self.source_type.value,
            "text": self.text,
            "semantic_relevance": self.semantic_relevance,
            "source_reputation": self.source_reputation,
            "recency_score": self.recency_score,
            "source_id": self.source_id,
            "source_title": self.source_title,
            "source_url": self.source_url,
            "source_date": self.source_date.isoformat() if self.source_date else None,
            "position_in_source": self.position_in_source,
            "chunk_number": self.chunk_number,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class AggregatedContext:
    """
    Collection of all context chunks from parallel retrieval.
    
    Before evaluation and filtering, aggregates chunks from all sources.
    
    Attributes:
        id: Unique identifier for this aggregation
        query_id: Reference to the originating query
        chunks: List of retrieved context chunks
        retrieval_time_ms: How long retrieval took
        sources_consulted: Which sources returned results
        sources_failed: Which sources failed
        total_chunks_before_dedup: Count before deduplication
        total_chunks_after_dedup: Count after deduplication
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    query_id: str = ""
    chunks: List[ContextChunk] = field(default_factory=list)
    retrieval_time_ms: float = 0.0
    sources_consulted: List[str] = field(default_factory=list)
    sources_failed: List[str] = field(default_factory=list)
    total_chunks_before_dedup: int = 0
    total_chunks_after_dedup: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def add_chunk(self, chunk: ContextChunk):
        """Add a context chunk to aggregation."""
        self.chunks.append(chunk)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics."""
        return {
            "id": self.id,
            "query_id": self.query_id,
            "total_chunks": len(self.chunks),
            "retrieval_time_ms": self.retrieval_time_ms,
            "sources_consulted": self.sources_consulted,
            "sources_failed": self.sources_failed,
            "dedup_ratio": self.total_chunks_before_dedup / max(self.total_chunks_after_dedup, 1),
        }


@dataclass
class QualityScoring:
    """Quality score components."""
    source_reputation: float = 0.0
    recency_score: float = 0.0
    semantic_relevance: float = 0.0
    redundancy_penalty: float = 0.0
    
    def compute_total(self, weights: Optional[Dict[str, float]] = None) -> float:
        """
        Compute total quality score from components.
        
        Default weights: reputation 0.3, recency 0.2, relevance 0.4, redundancy 0.1
        """
        if weights is None:
            weights = {
                "reputation": 0.3,
                "recency": 0.2,
                "relevance": 0.4,
                "redundancy": -0.1,  # Negative because it's a penalty
            }
        
        score = (
            weights.get("reputation", 0.3) * self.source_reputation +
            weights.get("recency", 0.2) * self.recency_score +
            weights.get("relevance", 0.4) * self.semantic_relevance +
            weights.get("redundancy", -0.1) * self.redundancy_penalty
        )
        return max(0.0, min(1.0, score))  # Clamp to 0-1


@dataclass
class FilteredChunk(ContextChunk):
    """
    Context chunk after filtering and evaluation.
    
    Extends ContextChunk with quality scores and filtering decisions.
    """
    quality_score: float = 0.0
    quality_components: Optional[QualityScoring] = None
    filtering_decision: FilteringDecision = FilteringDecision.KEPT
    
    def __post_init__(self):
        """Validate filtered chunk."""
        super().__post_init__()
        if not 0 <= self.quality_score <= 1:
            raise ValueError("quality_score must be 0-1")


@dataclass
class RemovedChunkRecord:
    """Record of a chunk that was removed during filtering."""
    original_chunk_id: str = ""
    reason: FilteringDecision = FilteringDecision.LOW_QUALITY
    quality_score: float = 0.0
    source: str = ""
    text_preview: str = ""  # First 200 chars of removed text
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "original_chunk_id": self.original_chunk_id,
            "reason": self.reason.value,
            "quality_score": self.quality_score,
            "source": self.source,
            "text_preview": self.text_preview,
        }


@dataclass
class ContradictionRecord:
    """Record of contradictory claims found in sources."""
    claim_1: str = ""
    claim_1_source: str = ""
    claim_2: str = ""
    claim_2_source: str = ""
    severity: str = "moderate"  # minor, moderate, critical
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "claim_1": self.claim_1,
            "claim_1_source": self.claim_1_source,
            "claim_2": self.claim_2,
            "claim_2_source": self.claim_2_source,
            "severity": self.severity,
        }


@dataclass
class FilteredContext:
    """
    High-quality subset of aggregated context after evaluation.
    
    Attributes:
        id: Unique identifier
        query_id: Reference to query
        original_chunk_count: Count before filtering
        filtered_chunk_count: Count after filtering
        chunks: List of kept chunks
        filtering_time_ms: How long filtering took
        average_quality_score: Mean quality of kept chunks
        quality_threshold_used: Minimum score to keep chunk
        removed_chunks: Records of removed chunks
        contradictions_detected: Contradictory claims found
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    query_id: str = ""
    original_chunk_count: int = 0
    filtered_chunk_count: int = 0
    chunks: List[FilteredChunk] = field(default_factory=list)
    filtering_time_ms: float = 0.0
    average_quality_score: float = 0.0
    quality_threshold_used: float = 0.6
    removed_chunks: List[RemovedChunkRecord] = field(default_factory=list)
    contradictions_detected: List[ContradictionRecord] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        """Validate filtered context."""
        if self.filtered_chunk_count > self.original_chunk_count:
            raise ValueError("filtered_chunk_count must be <= original_chunk_count")
        
        if self.filtered_chunk_count > 0:
            quality_sum = sum(c.quality_score for c in self.chunks)
            self.average_quality_score = quality_sum / self.filtered_chunk_count
    
    def add_filtered_chunk(self, chunk: FilteredChunk):
        """Add a filtered chunk."""
        self.chunks.append(chunk)
        self.filtered_chunk_count = len(self.chunks)
    
    def add_removed_chunk(self, record: RemovedChunkRecord):
        """Record a removed chunk."""
        self.removed_chunks.append(record)
    
    def add_contradiction(self, record: ContradictionRecord):
        """Record a contradiction detected."""
        self.contradictions_detected.append(record)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics."""
        return {
            "id": self.id,
            "query_id": self.query_id,
            "original_chunks": self.original_chunk_count,
            "filtered_chunks": self.filtered_chunk_count,
            "removal_rate": (self.original_chunk_count - self.filtered_chunk_count) / max(self.original_chunk_count, 1),
            "average_quality": self.average_quality_score,
            "contradictions_detected": len(self.contradictions_detected),
        }
