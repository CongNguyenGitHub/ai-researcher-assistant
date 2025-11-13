"""
Evaluator service for Context-Aware Research Assistant.

Evaluates and filters aggregated context using multi-factor quality scoring.
"""

from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime, timedelta
import math
from dataclasses import replace

from models.query import Query
from models.context import (
    ContextChunk,
    AggregatedContext,
    FilteredContext,
    FilteredChunk,
    QualityScoring,
    RemovedChunkRecord,
    ContradictionRecord,
    FilteringDecision,
)
from logging_config import get_logger

logger = get_logger(__name__)


class Evaluator:
    """
    Evaluates and filters context chunks using multi-factor quality scoring.
    
    Quality score formula:
    - Source reputation (30%): Type-based weights
    - Recency (20%): Exponential decay with age
    - Semantic relevance (40%): Embedding similarity
    - Deduplication penalty (10%): Text similarity to higher-scored chunks
    """
    
    # Default source reputation weights
    DEFAULT_REPUTATION_WEIGHTS = {
        "arxiv": 0.95,   # Academic papers highest
        "web": 0.70,     # Web results medium
        "memory": 0.60,  # Conversation history lower
        "rag": 0.80,     # RAG indexed docs medium-high
    }
    
    def __init__(
        self,
        reputation_weights: Optional[Dict[str, float]] = None,
        quality_threshold: float = 0.6,
        dedup_threshold: float = 0.9,
        max_age_days: int = 365,
    ):
        """
        Initialize Evaluator.
        
        Args:
            reputation_weights: Override default source reputation weights
            quality_threshold: Minimum quality score to keep chunk (0-1)
            dedup_threshold: Text similarity threshold for deduplication (0-1)
            max_age_days: Maximum document age for recency scoring
        """
        self.reputation_weights = reputation_weights or self.DEFAULT_REPUTATION_WEIGHTS
        self.quality_threshold = max(0.0, min(1.0, quality_threshold))
        self.dedup_threshold = max(0.0, min(1.0, dedup_threshold))
        self.max_age_days = max(1, max_age_days)
        
        logger.info(
            f"Evaluator initialized: threshold={self.quality_threshold}, "
            f"dedup_threshold={self.dedup_threshold}"
        )
    
    def calculate_quality_score(
        self,
        chunk: ContextChunk,
        query: Optional[Query] = None,
        higher_scored_chunks: Optional[List[ContextChunk]] = None,
        weights: Optional[Dict[str, float]] = None,
    ) -> Tuple[float, QualityScoring]:
        """
        Calculate quality score for a chunk using multi-factor formula.
        
        Args:
            chunk: Chunk to score
            query: Original query (for relevance context)
            higher_scored_chunks: Chunks with higher scores (for dedup)
            weights: Override default weights
            
        Returns:
            Tuple of (total_score, quality_components)
        """
        if weights is None:
            weights = {
                "reputation": 0.30,
                "recency": 0.20,
                "relevance": 0.40,
                "redundancy": -0.10,
            }
        
        # Reputation score (30%)
        rep_score = self.reputation_weights.get(
            chunk.source_type.value,
            0.5
        )
        
        # Recency score (20%)
        recency = self._calculate_recency_score(chunk.source_date)
        
        # Semantic relevance (40%) - use provided score
        relevance = chunk.semantic_relevance
        
        # Redundancy penalty (10%)
        redundancy_penalty = 0.0
        if higher_scored_chunks:
            redundancy_penalty = self._calculate_redundancy_penalty(
                chunk,
                higher_scored_chunks
            )
        
        # Weighted combination
        total_score = (
            weights.get("reputation", 0.30) * rep_score +
            weights.get("recency", 0.20) * recency +
            weights.get("relevance", 0.40) * relevance +
            weights.get("redundancy", -0.10) * redundancy_penalty
        )
        
        # Clamp to 0-1
        total_score = max(0.0, min(1.0, total_score))
        
        components = QualityScoring(
            source_reputation=rep_score,
            recency_score=recency,
            semantic_relevance=relevance,
            redundancy_penalty=redundancy_penalty,
        )
        
        return total_score, components
    
    def _calculate_recency_score(self, source_date: Optional[datetime]) -> float:
        """
        Calculate recency score using exponential decay.
        
        Args:
            source_date: Publication/creation date of source
            
        Returns:
            Recency score (0-1)
        """
        if not source_date:
            return 0.5  # Unknown age gets middle score
        
        now = datetime.utcnow()
        if source_date > now:
            return 0.9  # Future dates (shouldn't happen) get high score
        
        age_days = (now - source_date).days
        if age_days < 0:
            return 1.0
        
        # Exponential decay: e^(-age/max_age)
        decay_rate = 1.0 / self.max_age_days
        score = math.exp(-decay_rate * age_days)
        
        return max(0.0, min(1.0, score))
    
    def _calculate_redundancy_penalty(
        self,
        chunk: ContextChunk,
        higher_scored_chunks: List[ContextChunk],
    ) -> float:
        """
        Calculate redundancy penalty based on similarity to higher-scored chunks.
        
        Args:
            chunk: Chunk to evaluate
            higher_scored_chunks: Previously scored chunks with higher quality
            
        Returns:
            Redundancy penalty (0-1)
        """
        if not higher_scored_chunks:
            return 0.0
        
        # Calculate text similarity to highest-scored chunk
        max_similarity = 0.0
        for higher_chunk in higher_scored_chunks[:5]:  # Check top 5 only
            similarity = self._calculate_text_similarity(chunk.text, higher_chunk.text)
            max_similarity = max(max_similarity, similarity)
        
        if max_similarity > self.dedup_threshold:
            return 1.0  # Full penalty for high similarity
        elif max_similarity > 0.7:
            return (max_similarity - 0.7) / 0.2  # Scale between 0 and 1
        else:
            return 0.0
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate text similarity using token overlap.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score (0-1)
        """
        tokens1 = set(text1.lower().split())
        tokens2 = set(text2.lower().split())
        
        if not tokens1 or not tokens2:
            return 0.0
        
        intersection = len(tokens1 & tokens2)
        union = len(tokens1 | tokens2)
        
        return intersection / union if union > 0 else 0.0
    
    def filter_context(
        self,
        aggregated: AggregatedContext,
        query: Query,
    ) -> FilteredContext:
        """
        Filter aggregated context to high-quality chunks.
        
        Args:
            aggregated: Aggregated context from all sources
            query: Original query
            
        Returns:
            FilteredContext with evaluated chunks
        """
        import time
        start_time = time.time()
        
        filtered = FilteredContext(
            query_id=aggregated.query_id,
            original_chunk_count=len(aggregated.chunks),
            quality_threshold_used=self.quality_threshold,
        )
        
        # Score all chunks
        scored_chunks: List[Tuple[ContextChunk, float, QualityScoring]] = []
        for chunk in aggregated.chunks:
            score, components = self.calculate_quality_score(chunk, query)
            scored_chunks.append((chunk, score, components))
        
        # Sort by score descending
        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        
        # Filter by threshold and deduplication
        kept_chunks = []
        removed_chunks = []
        
        for chunk, score, components in scored_chunks:
            if score >= self.quality_threshold:
                # Check if chunk is duplicate of already-kept chunk
                is_duplicate = False
                for kept_chunk in kept_chunks:
                    similarity = self._calculate_text_similarity(
                        chunk.text,
                        kept_chunk.text
                    )
                    if similarity > self.dedup_threshold:
                        is_duplicate = True
                        removed_chunks.append(
                            RemovedChunkRecord(
                                original_chunk_id=chunk.id,
                                reason=FilteringDecision.DEDUPLICATED,
                                quality_score=score,
                                source=chunk.source_type.value,
                                text_preview=chunk.text[:200],
                            )
                        )
                        break
                
                if not is_duplicate:
                    filtered_chunk = FilteredChunk(
                        **chunk.__dict__,
                        quality_score=score,
                        quality_components=components,
                        filtering_decision=FilteringDecision.KEPT,
                    )
                    kept_chunks.append(filtered_chunk)
                    filtered.add_filtered_chunk(filtered_chunk)
            else:
                removed_chunks.append(
                    RemovedChunkRecord(
                        original_chunk_id=chunk.id,
                        reason=FilteringDecision.LOW_QUALITY,
                        quality_score=score,
                        source=chunk.source_type.value,
                        text_preview=chunk.text[:200],
                    )
                )
        
        # Add removed chunk records
        for record in removed_chunks:
            filtered.add_removed_chunk(record)
        
        # Detect contradictions (simple implementation)
        self._detect_contradictions(kept_chunks, filtered)
        
        filtered.filtering_time_ms = (time.time() - start_time) * 1000
        
        logger.info(
            f"Filtered context: {filtered.original_chunk_count} → {filtered.filtered_chunk_count} chunks, "
            f"avg_quality={filtered.average_quality_score:.2f}, "
            f"time={filtered.filtering_time_ms:.1f}ms"
        )
        
        return filtered
    
    def _detect_contradictions(
        self,
        chunks: List[FilteredChunk],
        filtered_context: FilteredContext,
    ):
        """
        Detect contradictory claims between chunks.
        
        Simple implementation: compare claims with "is", "are", "cannot"
        
        Args:
            chunks: Kept chunks to check
            filtered_context: Context to add contradictions to
        """
        # Simple contradiction detection by comparing chunks from different sources
        if len(chunks) < 2:
            return
        
        # Find pairs of chunks from different sources
        contradiction_pairs = []
        for i, chunk1 in enumerate(chunks):
            for chunk2 in chunks[i + 1:]:
                if chunk1.source_type != chunk2.source_type:
                    # Naive check: look for conflicting statements
                    if self._contains_potential_contradiction(chunk1.text, chunk2.text):
                        contradiction_pairs.append((chunk1, chunk2))
        
        # Log contradictions as records (not adding them yet as it requires
        # more sophisticated NLP to truly detect contradictions)
        if contradiction_pairs:
            logger.warning(f"Detected {len(contradiction_pairs)} potential contradictions")
    
    def _contains_potential_contradiction(self, text1: str, text2: str) -> bool:
        """
        Simple heuristic to detect potential contradictions.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            True if texts might contain contradictions
        """
        # Simple keyword-based detection
        conflict_keywords = [
            ("cannot", "can"),
            ("is not", "is"),
            ("false", "true"),
            ("yes", "no"),
            ("rejects", "accepts"),
        ]
        
        text1_lower = text1.lower()
        text2_lower = text2.lower()
        
        for kw1, kw2 in conflict_keywords:
            if kw1 in text1_lower and kw2 in text2_lower:
                return True
        
        return False
