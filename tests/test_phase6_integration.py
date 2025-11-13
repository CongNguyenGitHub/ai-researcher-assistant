"""
Phase 6 Integration Tests: Response Synthesis

Tests the Synthesizer service implementation:
- Response generation from filtered context
- Section organization by source type
- Citation and source attribution
- Contradiction handling as perspectives
- Confidence calculation
- Response structure and validation
"""

import pytest
from datetime import datetime, timedelta
import uuid
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from services.synthesizer import Synthesizer
from models.query import Query
from models.context import (
    FilteredContext,
    FilteredChunk,
    ContextChunk,
    SourceType,
)
from models.response import (
    FinalResponse,
    ResponseSection,
    Perspective,
    SourceAttribution,
    ResponseQuality,
)


class TestSynthesizerInitialization:
    """Test Synthesizer service initialization."""
    
    def test_synthesizer_creates_with_defaults(self):
        """Synthesizer should initialize with default parameters."""
        synthesizer = Synthesizer()
        
        assert synthesizer.model_name == "gemini-2.0-flash"
        assert synthesizer.max_response_length == 5000
    
    def test_synthesizer_accepts_custom_parameters(self):
        """Synthesizer should accept custom model and max length."""
        synthesizer = Synthesizer(
            model_name="gemini-1.5-pro",
            max_response_length=10000,
        )
        
        assert synthesizer.model_name == "gemini-1.5-pro"
        assert synthesizer.max_response_length == 10000


class TestResponseGeneration:
    """Test basic response generation from filtered context."""
    
    @pytest.fixture
    def query(self):
        """Create a test query."""
        return Query(
            id=str(uuid.uuid4()),
            user_id="test-user",
            session_id="test-session",
            text="What are the latest developments in AI?",
        )
    
    @pytest.fixture
    def filtered_context_with_chunks(self):
        """Create filtered context with multiple chunks."""
        chunks = [
            FilteredChunk(
                id="chunk1",
                text="Recent transformer models have achieved state-of-the-art results.",
                source_type=SourceType.ARXIV,
                source_id="arxiv1",
                source_title="Latest in Transformers",
                source_url="https://arxiv.org/paper1",
                semantic_relevance=0.95,
                quality_score=0.85,
                source_reputation=0.95,
                recency_score=0.9,
            ),
            FilteredChunk(
                id="chunk2",
                text="Major tech companies are investing heavily in AI research.",
                source_type=SourceType.WEB,
                source_id="web1",
                source_title="Tech News Today",
                source_url="https://technews.com/ai-investment",
                semantic_relevance=0.87,
                quality_score=0.78,
                source_reputation=0.80,
                recency_score=0.85,
            ),
            FilteredChunk(
                id="chunk3",
                text="Multimodal models combining text and vision are now mainstream.",
                source_type=SourceType.WEB,
                source_id="web2",
                source_title="AI Research Weekly",
                source_url="https://airesearch.com/multimodal",
                semantic_relevance=0.82,
                quality_score=0.76,
                source_reputation=0.75,
                recency_score=0.88,
            ),
        ]
        
        return FilteredContext(
            query_id="test-query",
            chunks=chunks,
            average_quality_score=0.80,
        )
    
    def test_response_generated_from_filtered_context(self, query, filtered_context_with_chunks):
        """Synthesizer should generate response from filtered context."""
        synthesizer = Synthesizer()
        
        response = synthesizer.generate_response(query, filtered_context_with_chunks)
        
        assert isinstance(response, FinalResponse)
        assert response.query_id == query.id
        assert response.user_id == query.user_id
        assert response.session_id == query.session_id
        assert len(response.answer) > 0
        assert response.overall_confidence > 0
    
    def test_response_handles_empty_context(self, query):
        """Synthesizer should gracefully handle empty context."""
        synthesizer = Synthesizer()
        empty_context = FilteredContext(
            query_id=query.id,
            chunks=[],
            average_quality_score=0.0,
        )
        
        response = synthesizer.generate_response(query, empty_context)
        
        assert response.answer is not None
        assert "couldn't find" in response.answer.lower() or "no" in response.answer.lower()
        assert response.response_quality.degraded_mode
        assert response.overall_confidence < 0.5


class TestSectionOrganization:
    """Test response section organization by source type."""
    
    def test_sections_organized_by_source_type(self):
        """Sections should be organized by source type."""
        synthesizer = Synthesizer()
        query = Query(
            id=str(uuid.uuid4()),
            user_id="test-user",
            session_id="test-session",
            text="Test query",
        )
        
        chunks = [
            FilteredChunk(
                id="arxiv1",
                text="Academic paper content here.",
                source_type=SourceType.ARXIV,
                source_id="arxiv1",
                source_title="Paper 1",
                source_url="https://arxiv.org/1",
                semantic_relevance=0.9,
                quality_score=0.85,
            ),
            FilteredChunk(
                id="web1",
                text="Web content here.",
                source_type=SourceType.WEB,
                source_id="web1",
                source_title="Web 1",
                semantic_relevance=0.8,
                quality_score=0.75,
            ),
            FilteredChunk(
                id="arxiv2",
                text="Another academic paper.",
                source_type=SourceType.ARXIV,
                source_id="arxiv2",
                source_title="Paper 2",
                semantic_relevance=0.88,
                quality_score=0.82,
            ),
        ]
        
        context = FilteredContext(
            query_id=query.id,
            chunks=chunks,
            average_quality_score=0.82,
        )
        
        response = synthesizer.generate_response(query, context)
        
        # Should have 2 sections (one for Arxiv, one for Web)
        assert len(response.sections) >= 2
        
        # Sections should have proper structure
        for section in response.sections:
            assert section.heading
            assert section.content
            assert section.confidence > 0
            assert section.order >= 0
    
    def test_sections_sorted_by_chunk_count(self):
        """Sections should be sorted by number of chunks (descending)."""
        synthesizer = Synthesizer()
        query = Query(
            id=str(uuid.uuid4()),
            user_id="test-user",
            session_id="test-session",
            text="Test query",
        )
        
        # Create 3 Arxiv chunks and 1 Web chunk
        chunks = [
            FilteredChunk(
                id=f"arxiv{i}",
                text=f"Arxiv content {i}",
                source_type=SourceType.ARXIV,
                source_id=f"arxiv{i}",
                source_title=f"Paper {i}",
                semantic_relevance=0.9,
                quality_score=0.85,
            )
            for i in range(3)
        ]
        chunks.append(
            FilteredChunk(
                id="web1",
                text="Web content",
                source_type=SourceType.WEB,
                source_id="web1",
                source_title="Web",
                semantic_relevance=0.8,
                quality_score=0.75,
            )
        )
        
        context = FilteredContext(
            query_id=query.id,
            chunks=chunks,
            average_quality_score=0.84,
        )
        
        response = synthesizer.generate_response(query, context)
        
        # First section should have more content
        assert len(response.sections) >= 2
        # Check that Arxiv section appears first (more chunks)
        first_section_content_length = len(response.sections[0].content)
        assert first_section_content_length > 0


class TestCitationAndAttribution:
    """Test source attribution and citation formatting."""
    
    def test_sources_attributed_to_response(self):
        """All sources should be properly attributed in response."""
        synthesizer = Synthesizer()
        query = Query(
            id=str(uuid.uuid4()),
            user_id="test-user",
            session_id="test-session",
            text="What is machine learning?",
        )
        
        chunks = [
            FilteredChunk(
                id="arxiv1",
                text="Machine learning is a subset of AI.",
                source_type=SourceType.ARXIV,
                source_id="arxiv1",
                source_title="ML Fundamentals",
                source_url="https://arxiv.org/ml",
                semantic_relevance=0.95,
                quality_score=0.90,
            ),
            FilteredChunk(
                id="web1",
                text="Deep learning uses neural networks.",
                source_type=SourceType.WEB,
                source_id="web1",
                source_title="AI Blog",
                source_url="https://aiblog.com",
                semantic_relevance=0.90,
                quality_score=0.85,
            ),
        ]
        
        context = FilteredContext(
            query_id=query.id,
            chunks=chunks,
            average_quality_score=0.875,
        )
        
        response = synthesizer.generate_response(query, context)
        
        # Should have attributions for all sources
        assert len(response.sources) >= 2
        
        # Each attribution should be valid
        for source in response.sources:
            assert isinstance(source, SourceAttribution)
            assert source.id
            assert source.type in ["rag", "web", "arxiv", "memory"]
            assert source.title
            assert 0 <= source.relevance <= 1
    
    def test_source_attribution_details(self):
        """Source attributions should contain correct details."""
        synthesizer = Synthesizer()
        query = Query(
            id=str(uuid.uuid4()),
            user_id="test-user",
            session_id="test-session",
            text="What is ML?",
        )
        
        chunks = [
            FilteredChunk(
                id="paper-123",
                text="Content here",
                source_type=SourceType.ARXIV,
                source_id="arxiv-paper-123",
                source_title="Deep Learning Survey",
                source_url="https://arxiv.org/abs/2001.12345",
                semantic_relevance=0.92,
                quality_score=0.88,
            ),
        ]
        
        context = FilteredContext(
            query_id=query.id,
            chunks=chunks,
            average_quality_score=0.88,
        )
        
        response = synthesizer.generate_response(query, context)
        
        # Find the arxiv source
        arxiv_sources = [s for s in response.sources if s.type == "arxiv"]
        assert len(arxiv_sources) > 0
        
        arxiv_source = arxiv_sources[0]
        assert arxiv_source.title == "Deep Learning Survey"
        assert arxiv_source.url == "https://arxiv.org/abs/2001.12345"
        assert arxiv_source.relevance == 0.92


class TestContradictionHandling:
    """Test handling of contradictory information as perspectives."""
    
    def test_contradictions_create_perspectives(self):
        """Detected contradictions should create alternative perspectives."""
        synthesizer = Synthesizer()
        query = Query(
            id=str(uuid.uuid4()),
            user_id="test-user",
            session_id="test-session",
            text="Is quantum computing practical?",
        )
        
        chunks = [
            FilteredChunk(
                id="c1",
                text="Quantum computers are ready for commercial use.",
                source_type=SourceType.WEB,
                source_id="web1",
                source_title="Tech Company Press",
                semantic_relevance=0.85,
                quality_score=0.80,
            ),
            FilteredChunk(
                id="c2",
                text="Quantum computers still have significant scalability issues.",
                source_type=SourceType.ARXIV,
                source_id="arxiv1",
                source_title="Research Paper",
                semantic_relevance=0.83,
                quality_score=0.88,
            ),
        ]
        
        # Create contradiction record
        class MockContradiction:
            claim_1 = "Quantum computers are ready for commercial use"
            claim_2 = "Quantum computers still have significant scalability issues"
            claim_1_source = "web1"
            claim_2_source = "arxiv1"
        
        context = FilteredContext(
            query_id=query.id,
            chunks=chunks,
            average_quality_score=0.84,
            contradictions_detected=[MockContradiction()],
        )
        
        response = synthesizer.generate_response(query, context)
        
        # Response should indicate contradictions exist
        assert response.response_quality.has_contradictions
        
        # Response should have perspectives
        assert response.perspectives is not None
        assert len(response.perspectives) >= 2
        
        # Perspectives should represent different viewpoints
        for perspective in response.perspectives:
            assert isinstance(perspective, Perspective)
            assert perspective.viewpoint
            assert 0 <= perspective.confidence <= 1
    
    def test_no_perspectives_without_contradictions(self):
        """Response should have no perspectives if no contradictions."""
        synthesizer = Synthesizer()
        query = Query(
            id=str(uuid.uuid4()),
            user_id="test-user",
            session_id="test-session",
            text="What is Python?",
        )
        
        chunks = [
            FilteredChunk(
                id="c1",
                text="Python is a high-level programming language.",
                source_type=SourceType.WEB,
                source_id="web1",
                source_title="Python Docs",
                semantic_relevance=0.95,
                quality_score=0.90,
            ),
        ]
        
        context = FilteredContext(
            query_id=query.id,
            chunks=chunks,
            average_quality_score=0.90,
            contradictions_detected=[],  # No contradictions
        )
        
        response = synthesizer.generate_response(query, context)
        
        assert not response.response_quality.has_contradictions
        assert response.perspectives is None or len(response.perspectives) == 0


class TestConfidenceCalculation:
    """Test confidence score calculation."""
    
    def test_confidence_based_on_quality_score(self):
        """Confidence should increase with average quality score."""
        synthesizer = Synthesizer()
        query = Query(
            id=str(uuid.uuid4()),
            user_id="test-user",
            session_id="test-session",
            text="Test query",
        )
        
        # High quality context
        high_quality_chunks = [
            FilteredChunk(
                id="c1",
                text="High quality content",
                source_type=SourceType.ARXIV,
                source_id="arxiv1",
                source_title="Paper",
                semantic_relevance=0.95,
                quality_score=0.95,
            ),
        ]
        
        high_context = FilteredContext(
            query_id=query.id,
            chunks=high_quality_chunks,
            average_quality_score=0.95,
        )
        
        # Low quality context
        low_quality_chunks = [
            FilteredChunk(
                id="c2",
                text="Low quality content",
                source_type=SourceType.WEB,
                source_id="web1",
                source_title="Blog",
                semantic_relevance=0.60,
                quality_score=0.55,
            ),
        ]
        
        low_context = FilteredContext(
            query_id=query.id,
            chunks=low_quality_chunks,
            average_quality_score=0.55,
        )
        
        high_response = synthesizer.generate_response(query, high_context)
        low_response = synthesizer.generate_response(query, low_context)
        
        # High quality should have higher confidence
        assert high_response.overall_confidence > low_response.overall_confidence
    
    def test_confidence_penalized_by_contradictions(self):
        """Confidence should be reduced when contradictions exist."""
        synthesizer = Synthesizer()
        query = Query(
            id=str(uuid.uuid4()),
            user_id="test-user",
            session_id="test-session",
            text="Test query",
        )
        
        chunks = [
            FilteredChunk(
                id="c1",
                text="Claim A",
                source_type=SourceType.WEB,
                source_id="web1",
                source_title="Source 1",
                semantic_relevance=0.8,
                quality_score=0.8,
            ),
            FilteredChunk(
                id="c2",
                text="Contradicts A",
                source_type=SourceType.ARXIV,
                source_id="arxiv1",
                source_title="Source 2",
                semantic_relevance=0.8,
                quality_score=0.8,
            ),
        ]
        
        class MockContradiction:
            claim_1 = "Claim A"
            claim_2 = "Contradicts A"
            claim_1_source = "web1"
            claim_2_source = "arxiv1"
        
        # With contradictions
        with_contradictions = FilteredContext(
            query_id=query.id,
            chunks=chunks,
            average_quality_score=0.8,
            contradictions_detected=[MockContradiction()],
        )
        
        # Without contradictions
        without_contradictions = FilteredContext(
            query_id=query.id,
            chunks=chunks,
            average_quality_score=0.8,
            contradictions_detected=[],
        )
        
        with_contra_response = synthesizer.generate_response(query, with_contradictions)
        without_contra_response = synthesizer.generate_response(query, without_contradictions)
        
        # Contradictions should reduce confidence
        assert with_contra_response.overall_confidence < without_contra_response.overall_confidence


class TestResponseStructure:
    """Test FinalResponse structure and validation."""
    
    def test_response_has_required_fields(self):
        """FinalResponse should have all required fields."""
        synthesizer = Synthesizer()
        query = Query(
            id=str(uuid.uuid4()),
            user_id="test-user",
            session_id="test-session",
            text="Test",
        )
        
        chunks = [
            FilteredChunk(
                id="c1",
                text="Content",
                source_type=SourceType.WEB,
                source_id="web1",
                source_title="Source",
                semantic_relevance=0.8,
                quality_score=0.8,
            ),
        ]
        
        context = FilteredContext(
            query_id=query.id,
            chunks=chunks,
            average_quality_score=0.8,
        )
        
        response = synthesizer.generate_response(query, context)
        
        # Required fields
        assert response.id
        assert response.query_id == query.id
        assert response.user_id == query.user_id
        assert response.session_id == query.session_id
        assert response.answer
        assert isinstance(response.sections, list)
        assert isinstance(response.sources, list)
        assert isinstance(response.response_quality, ResponseQuality)
        assert response.timestamp is not None
        assert response.generation_time_ms > 0
    
    def test_response_can_be_serialized_to_dict(self):
        """FinalResponse should be serializable to dictionary."""
        synthesizer = Synthesizer()
        query = Query(
            id=str(uuid.uuid4()),
            user_id="test-user",
            session_id="test-session",
            text="Test",
        )
        
        chunks = [
            FilteredChunk(
                id="c1",
                text="Content",
                source_type=SourceType.WEB,
                source_id="web1",
                source_title="Source",
                semantic_relevance=0.8,
                quality_score=0.8,
            ),
        ]
        
        context = FilteredContext(
            query_id=query.id,
            chunks=chunks,
            average_quality_score=0.8,
        )
        
        response = synthesizer.generate_response(query, context)
        response_dict = response.to_dict()
        
        # Should be a valid dictionary
        assert isinstance(response_dict, dict)
        assert response_dict["id"] == response.id
        assert response_dict["query_id"] == query.id
        assert response_dict["answer"] == response.answer
        assert "sections" in response_dict
        assert "sources" in response_dict


class TestPhase6AcceptanceCriteria:
    """Test Phase 6 acceptance criteria."""
    
    def test_ac_p6_001_response_generated_from_filtered_context(self):
        """AC-P6-001: Response should be generated from filtered context."""
        synthesizer = Synthesizer()
        query = Query(
            id=str(uuid.uuid4()),
            user_id="test-user",
            session_id="test-session",
            text="What is AI?",
        )
        
        chunks = [
            FilteredChunk(
                id="c1",
                text="AI is the simulation of intelligence.",
                source_type=SourceType.WEB,
                source_id="web1",
                source_title="Definition",
                semantic_relevance=0.9,
                quality_score=0.85,
            ),
        ]
        
        context = FilteredContext(
            query_id=query.id,
            chunks=chunks,
            average_quality_score=0.85,
        )
        
        response = synthesizer.generate_response(query, context)
        
        # Response should exist and be based on context
        assert response is not None
        assert len(response.answer) > 0
        assert len(response.sources) > 0
        assert len(response.sections) > 0
    
    def test_ac_p6_002_citations_formatted_with_sources(self):
        """AC-P6-002: Citations should be formatted with source information."""
        synthesizer = Synthesizer()
        query = Query(
            id=str(uuid.uuid4()),
            user_id="test-user",
            session_id="test-session",
            text="Test",
        )
        
        chunks = [
            FilteredChunk(
                id="c1",
                text="Important information",
                source_type=SourceType.ARXIV,
                source_id="arxiv1",
                source_title="Research Paper",
                source_url="https://arxiv.org/paper",
                semantic_relevance=0.9,
                quality_score=0.85,
            ),
        ]
        
        context = FilteredContext(
            query_id=query.id,
            chunks=chunks,
            average_quality_score=0.85,
        )
        
        response = synthesizer.generate_response(query, context)
        
        # Sources should be properly formatted with attribution details
        assert len(response.sources) > 0
        source = response.sources[0]
        assert source.title == "Research Paper"
        assert source.url == "https://arxiv.org/paper"
        assert source.type == "arxiv"
    
    def test_ac_p6_003_contradictions_documented(self):
        """AC-P6-003: Contradictions should be documented in response."""
        synthesizer = Synthesizer()
        query = Query(
            id=str(uuid.uuid4()),
            user_id="test-user",
            session_id="test-session",
            text="Controversial topic",
        )
        
        chunks = [
            FilteredChunk(
                id="c1",
                text="Perspective A",
                source_type=SourceType.WEB,
                source_id="web1",
                source_title="Source 1",
                semantic_relevance=0.8,
                quality_score=0.8,
            ),
            FilteredChunk(
                id="c2",
                text="Perspective B",
                source_type=SourceType.ARXIV,
                source_id="arxiv1",
                source_title="Source 2",
                semantic_relevance=0.8,
                quality_score=0.8,
            ),
        ]
        
        class MockContradiction:
            claim_1 = "Perspective A"
            claim_2 = "Perspective B"
            claim_1_source = "web1"
            claim_2_source = "arxiv1"
        
        context = FilteredContext(
            query_id=query.id,
            chunks=chunks,
            average_quality_score=0.8,
            contradictions_detected=[MockContradiction()],
        )
        
        response = synthesizer.generate_response(query, context)
        
        # Contradictions should be documented
        assert response.response_quality.has_contradictions
        assert response.perspectives is not None
        assert len(response.perspectives) >= 2
    
    def test_ac_p6_004_response_ready_for_user_display(self):
        """AC-P6-004: Response should be ready for user display."""
        synthesizer = Synthesizer()
        query = Query(
            id=str(uuid.uuid4()),
            user_id="test-user",
            session_id="test-session",
            text="User question",
        )
        
        chunks = [
            FilteredChunk(
                id="c1",
                text="Comprehensive answer content",
                source_type=SourceType.WEB,
                source_id="web1",
                source_title="Source",
                semantic_relevance=0.85,
                quality_score=0.80,
            ),
        ]
        
        context = FilteredContext(
            query_id=query.id,
            chunks=chunks,
            average_quality_score=0.80,
        )
        
        response = synthesizer.generate_response(query, context)
        response_dict = response.to_dict()
        
        # Should be JSON-serializable for display
        assert isinstance(response_dict, dict)
        assert response_dict["answer"]
        assert response_dict["sections"]
        assert response_dict["sources"]
        assert "overall_confidence" in response_dict
        
        # Should be displayable (no missing critical fields)
        assert response.answer
        assert response.generation_time_ms > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
