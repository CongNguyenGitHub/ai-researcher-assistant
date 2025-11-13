"""
Synthesizer service for Context-Aware Research Assistant.

Generates comprehensive, well-sourced responses from filtered context.
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime
import time

from models.query import Query
from models.context import FilteredContext, FilteredChunk
from models.response import (
    FinalResponse,
    ResponseSection,
    Perspective,
    SourceAttribution,
    ResponseQuality,
)
from logging_config import get_logger

logger = get_logger(__name__)


class Synthesizer:
    """
    Generates comprehensive responses from filtered context.
    
    Handles:
    - Response generation from context chunks
    - Section organization and summarization
    - Citation tracking (3-level: summary, section, chunk)
    - Contradiction documentation as perspectives
    - Confidence calculation
    """
    
    def __init__(
        self,
        model_name: str = "gemini-2.0-flash",
        max_response_length: int = 5000,
    ):
        """
        Initialize Synthesizer.
        
        Args:
            model_name: LLM to use for generation
            max_response_length: Maximum response character length
        """
        self.model_name = model_name
        self.max_response_length = max_response_length
        logger.info(f"Synthesizer initialized with model={model_name}")
    
    def generate_response(
        self,
        query: Query,
        filtered_context: FilteredContext,
    ) -> FinalResponse:
        """
        Generate a comprehensive response from filtered context.
        
        Args:
            query: Original user query
            filtered_context: Filtered and evaluated context
            
        Returns:
            FinalResponse with answer, sections, and citations
        """
        start_time = time.time()
        
        # Handle empty context
        if not filtered_context.chunks:
            logger.warning(f"No context available for query {query.id}")
            answer = (
                f"I couldn't find relevant information to answer your query: \"{query.text}\"\n\n"
                "Please try:\n"
                "- Rephrasing your question\n"
                "- Breaking it into smaller questions\n"
                "- Providing source documents if using RAG"
            )
            response = FinalResponse(
                query_id=query.id,
                user_id=query.user_id,
                session_id=query.session_id,
                answer=answer,
            )
            response.response_quality.completeness = 0.0
            response.response_quality.degraded_mode = True
            response.overall_confidence = 0.2
            return response
        
        # Group chunks by topic/section
        sections_data = self._organize_into_sections(query, filtered_context.chunks)
        
        # Generate answer summary
        answer = self._generate_summary(query, filtered_context.chunks)
        
        response = FinalResponse(
            query_id=query.id,
            user_id=query.user_id,
            session_id=query.session_id,
            answer=answer,
        )
        
        # Create sections with citations
        for section_idx, (title, chunks) in enumerate(sections_data):
            section = self._create_response_section(title, chunks, section_idx)
            response.add_section(section)
        
        # Add source attributions
        self._add_source_attributions(response, filtered_context.chunks)
        
        # Handle contradictions as perspectives
        if filtered_context.contradictions_detected:
            self._add_perspectives_from_contradictions(
                response,
                filtered_context.contradictions_detected
            )
            response.response_quality.has_contradictions = True
        
        # Calculate confidence
        response.overall_confidence = self._calculate_confidence(
            filtered_context,
            len(response.sections)
        )
        response.response_quality.confidence = response.overall_confidence
        
        # Calculate quality metrics
        response.response_quality.completeness = min(
            1.0,
            len(filtered_context.chunks) / 10  # More chunks = more complete
        )
        response.response_quality.informativeness = filtered_context.average_quality_score
        
        response.generation_time_ms = (time.time() - start_time) * 1000
        
        logger.info(
            f"Generated response for query {query.id}: "
            f"{len(response.sections)} sections, "
            f"{len(response.sources)} sources, "
            f"confidence={response.overall_confidence:.2f}"
        )
        
        return response
    
    def _organize_into_sections(
        self,
        query: Query,
        chunks: List[FilteredChunk],
    ) -> List[Tuple[str, List[FilteredChunk]]]:
        """
        Organize chunks into logical sections.
        
        Simple implementation: group by source type.
        
        Args:
            query: Original query
            chunks: Chunks to organize
            
        Returns:
            List of (section_title, chunks) tuples
        """
        sections: Dict[str, List[FilteredChunk]] = {}
        
        # Group by source type
        source_section_names = {
            "rag": "From Your Documents",
            "web": "From Web Search",
            "arxiv": "From Academic Papers",
            "memory": "From Conversation History",
        }
        
        for chunk in chunks:
            source_type = chunk.source_type.value
            section_name = source_section_names.get(source_type, source_type.title())
            
            if section_name not in sections:
                sections[section_name] = []
            sections[section_name].append(chunk)
        
        # Sort sections by number of chunks (descending)
        sorted_sections = sorted(
            sections.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )
        
        return sorted_sections
    
    def _generate_summary(
        self,
        query: Query,
        chunks: List[FilteredChunk],
    ) -> str:
        """
        Generate summary answer from top chunks.
        
        Args:
            query: Original query
            chunks: Context chunks (sorted by quality)
            
        Returns:
            Summary answer text
        """
        if not chunks:
            return "No relevant information found."
        
        # For MVP: concatenate top 3 chunks with introductory phrase
        top_chunks = chunks[:3]
        
        # Build summary
        summary_parts = []
        
        # Intro
        summary_parts.append(f"Based on available sources, here's what I found:\n")
        
        # Key information from top chunks
        for i, chunk in enumerate(top_chunks, 1):
            # Extract first sentence or first 100 chars
            text = chunk.text.strip()
            first_sentence = text.split('.')[0] + '.' if '.' in text else text[:100]
            summary_parts.append(f"• {first_sentence}")
        
        summary = "\n".join(summary_parts)
        
        # Truncate if needed
        if len(summary) > self.max_response_length:
            summary = summary[:self.max_response_length - 3] + "..."
        
        return summary
    
    def _create_response_section(
        self,
        title: str,
        chunks: List[FilteredChunk],
        order: int = 0,
    ) -> ResponseSection:
        """
        Create a response section from chunks.
        
        Args:
            title: Section title
            chunks: Chunks for this section
            order: Display order
            
        Returns:
            ResponseSection object
        """
        # Combine chunk texts
        section_content = "\n\n".join([chunk.text for chunk in chunks[:5]])  # Max 5 chunks per section
        
        # Calculate section confidence as average of chunk qualities
        confidence = (
            sum(chunk.quality_score for chunk in chunks) / len(chunks)
            if chunks else 0.5
        )
        
        # Collect source IDs
        source_ids = list(set(chunk.source_id for chunk in chunks))
        
        section = ResponseSection(
            heading=title,
            content=section_content,
            confidence=confidence,
            sources=source_ids,
            order=order,
        )
        
        return section
    
    def _add_source_attributions(
        self,
        response: FinalResponse,
        chunks: List[FilteredChunk],
    ):
        """
        Add source attributions for all sources in response.
        
        Args:
            response: Response to add attributions to
            chunks: Context chunks used in response
        """
        seen_sources: Dict[str, SourceAttribution] = {}
        
        for chunk in chunks:
            if chunk.source_id not in seen_sources:
                attribution = SourceAttribution(
                    id=chunk.source_id,
                    type=chunk.source_type.value,
                    title=chunk.source_title or "Untitled",
                    url=chunk.source_url,
                    relevance=chunk.semantic_relevance,
                    contribution=f"Contributed to {chunk.source_type.value} section",
                )
                response.add_source(attribution)
                seen_sources[chunk.source_id] = attribution
        
        logger.info(f"Added {len(seen_sources)} unique sources to response")
    
    def _add_perspectives_from_contradictions(
        self,
        response: FinalResponse,
        contradictions: List,
    ):
        """
        Create perspectives from detected contradictions.
        
        Args:
            response: Response to add perspectives to
            contradictions: Contradiction records
        """
        for contradiction in contradictions[:2]:  # Max 2 perspectives for MVP
            perspective = Perspective(
                viewpoint=contradiction.claim_1,
                summary=f"Supported by {contradiction.claim_1_source}",
                confidence=0.7,
                sources=[contradiction.claim_1_source],
                weight=0.5,
            )
            response.add_perspective(perspective)
            
            perspective2 = Perspective(
                viewpoint=contradiction.claim_2,
                summary=f"Supported by {contradiction.claim_2_source}",
                confidence=0.7,
                sources=[contradiction.claim_2_source],
                weight=0.5,
            )
            response.add_perspective(perspective2)
    
    def _calculate_confidence(
        self,
        filtered_context: FilteredContext,
        section_count: int,
    ) -> float:
        """
        Calculate overall response confidence.
        
        Args:
            filtered_context: Filtered context used
            section_count: Number of sections in response
            
        Returns:
            Confidence score (0-1)
        """
        # Base confidence from average chunk quality
        base_confidence = filtered_context.average_quality_score
        
        # Boost with section count
        section_boost = min(0.1, section_count * 0.05)
        
        # Penalty for contradictions
        contradiction_penalty = (
            0.2 if filtered_context.contradictions_detected else 0.0
        )
        
        confidence = base_confidence + section_boost - contradiction_penalty
        
        return max(0.0, min(1.0, confidence))
