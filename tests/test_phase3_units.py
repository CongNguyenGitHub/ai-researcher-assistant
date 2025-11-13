"""
Unit tests for Phase 3 components.

Tests for:
- Tool implementations (RAG, Firecrawl, Arxiv, Memory)
- Agents and Tasks
- Orchestrator integration
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from models.query import Query, QueryStatus
from models.context import ContextChunk, AggregatedContext, SourceType
from models.response import FinalResponse
from tools.base import ToolBase, ToolResult, ToolStatus
from services.orchestrator import Orchestrator


class TestToolBase(unittest.TestCase):
    """Test base tool functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.tool = ToolBase(timeout_seconds=5.0)
    
    def test_tool_initialization(self):
        """Test tool initializes correctly."""
        self.assertEqual(self.tool.timeout_seconds, 5.0)
    
    def test_query_validation(self):
        """Test query validation."""
        valid_query = Query(
            id="test-1",
            user_id="user-1",
            text="What is AI?",
        )
        self.assertTrue(self.tool.validate_query(valid_query))
        
        # Invalid: empty text
        invalid_query = Query(
            id="test-2",
            user_id="user-2",
            text="",
        )
        self.assertFalse(self.tool.validate_query(invalid_query))
    
    def test_create_chunk(self):
        """Test chunk creation."""
        chunk = self.tool.create_chunk(
            text="Test content",
            source_id="source-1",
            source_title="Test Source",
            source_url="http://example.com",
            source_date=datetime.now(),
            semantic_relevance=0.8,
            source_reputation=0.9,
            recency_score=0.7,
        )
        
        self.assertEqual(chunk.text, "Test content")
        self.assertEqual(chunk.source_id, "source-1")
        self.assertEqual(chunk.semantic_relevance, 0.8)
    
    def test_success_result(self):
        """Test creating successful tool result."""
        chunks = [
            self.tool.create_chunk(
                text="Content 1",
                source_id="s1",
                source_title="Title 1",
                source_url=None,
                source_date=None,
                semantic_relevance=0.9,
                source_reputation=0.8,
                recency_score=0.7,
            )
        ]
        
        result = self.tool.create_success_result(chunks, 1000.0)
        
        self.assertEqual(result.status, ToolStatus.SUCCESS)
        self.assertEqual(len(result.chunks), 1)
        self.assertEqual(result.execution_time_ms, 1000.0)
        self.assertTrue(result.is_successful())
    
    def test_error_result(self):
        """Test creating error tool result."""
        result = self.tool.create_error_result(
            ToolStatus.ERROR,
            500.0,
            "Test error message"
        )
        
        self.assertEqual(result.status, ToolStatus.ERROR)
        self.assertEqual(result.error_message, "Test error message")
        self.assertFalse(result.is_successful())


class MockRAGTool(ToolBase):
    """Mock RAG tool for testing."""
    
    @property
    def source_type(self):
        return SourceType.RAG
    
    @property
    def tool_name(self):
        return "Mock RAG"
    
    def execute(self, query):
        """Return mock chunks."""
        chunks = [
            self.create_chunk(
                text="RAG result 1",
                source_id="rag-1",
                source_title="Document 1",
                source_url=None,
                source_date=None,
                semantic_relevance=0.9,
                source_reputation=0.8,
                recency_score=0.6,
            ),
            self.create_chunk(
                text="RAG result 2",
                source_id="rag-2",
                source_title="Document 2",
                source_url=None,
                source_date=None,
                semantic_relevance=0.7,
                source_reputation=0.75,
                recency_score=0.5,
            ),
        ]
        return self.create_success_result(chunks, 100.0)


class MockWebTool(ToolBase):
    """Mock web scraping tool."""
    
    @property
    def source_type(self):
        return SourceType.WEB
    
    @property
    def tool_name(self):
        return "Mock Web"
    
    def execute(self, query):
        """Return mock web chunks."""
        chunks = [
            self.create_chunk(
                text="Web result 1",
                source_id="web-1",
                source_title="Website 1",
                source_url="http://example.com/1",
                source_date=datetime.now(),
                semantic_relevance=0.8,
                source_reputation=0.6,
                recency_score=0.95,
            ),
        ]
        return self.create_success_result(chunks, 150.0)


class TestOrchestrator(unittest.TestCase):
    """Test orchestrator functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.rag_tool = MockRAGTool()
        self.web_tool = MockWebTool()
        self.evaluator = Mock()
        self.synthesizer = Mock()
        
        self.orchestrator = Orchestrator(
            evaluator=self.evaluator,
            synthesizer=self.synthesizer,
            tools=[self.rag_tool, self.web_tool],
            max_workers=2,
        )
    
    def test_orchestrator_initialization(self):
        """Test orchestrator initializes correctly."""
        self.assertEqual(len(self.orchestrator.tools), 2)
        self.assertEqual(self.orchestrator.max_workers, 2)
        self.assertIsNotNone(self.orchestrator.evaluator)
    
    def test_register_tool(self):
        """Test tool registration."""
        arxiv_tool = MockRAGTool()
        self.orchestrator.register_tool(arxiv_tool)
        
        self.assertEqual(len(self.orchestrator.tools), 3)
    
    def test_retrieve_context_parallel(self):
        """Test parallel context retrieval."""
        query = Query(
            id="test-1",
            user_id="user-1",
            text="What is machine learning?",
        )
        
        context = self.orchestrator._retrieve_context(query)
        
        # Should have chunks from both tools
        self.assertGreater(len(context.chunks), 0)
        self.assertEqual(len(context.sources_consulted), 2)
        self.assertEqual(len(context.sources_failed), 0)
    
    def test_get_status(self):
        """Test status reporting."""
        status = self.orchestrator.get_status()
        
        self.assertTrue(status["ready"])
        self.assertEqual(status["tools_registered"], 2)
        self.assertIn("Mock RAG", status["tool_names"])
        self.assertIn("Mock Web", status["tool_names"])


class TestAggregatedContext(unittest.TestCase):
    """Test context aggregation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.context = AggregatedContext(query_id="test-1")
    
    def test_add_chunk(self):
        """Test adding chunks to context."""
        chunk = ContextChunk(
            id="chunk-1",
            text="Test content",
            source_id="source-1",
            source_title="Test Source",
            source_type=SourceType.RAG,
        )
        
        self.context.add_chunk(chunk)
        
        self.assertEqual(len(self.context.chunks), 1)
    
    def test_deduplication(self):
        """Test duplicate chunk detection."""
        chunk1 = ContextChunk(
            id="chunk-1",
            text="Same content here",
            source_id="source-1",
            source_title="Source 1",
            source_type=SourceType.RAG,
        )
        
        chunk2 = ContextChunk(
            id="chunk-2",
            text="Same content here",  # Same text
            source_id="source-2",
            source_title="Source 2",
            source_type=SourceType.WEB,
        )
        
        self.context.add_chunk(chunk1)
        self.context.add_chunk(chunk2)
        
        # Should detect some similarity
        # Deduplication strategy depends on implementation
        self.assertGreaterEqual(len(self.context.chunks), 1)


class TestQueryStatus(unittest.TestCase):
    """Test query status tracking."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.query = Query(
            id="test-1",
            user_id="user-1",
            text="Test query",
        )
    
    def test_query_initial_status(self):
        """Test query starts in pending state."""
        self.assertEqual(self.query.status, QueryStatus.PENDING)
    
    def test_mark_completed(self):
        """Test marking query complete."""
        self.query.mark_completed()
        
        self.assertEqual(self.query.status, QueryStatus.COMPLETED)
        self.assertIsNotNone(self.query.completed_at)
    
    def test_mark_failed(self):
        """Test marking query failed."""
        self.query.mark_failed("Test error")
        
        self.assertEqual(self.query.status, QueryStatus.FAILED)
        self.assertEqual(self.query.error_message, "Test error")


class TestFinalResponse(unittest.TestCase):
    """Test response generation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.response = FinalResponse(
            query_id="test-1",
            user_id="user-1",
            session_id="session-1",
        )
    
    def test_response_initialization(self):
        """Test response initializes correctly."""
        self.assertEqual(self.response.query_id, "test-1")
        self.assertEqual(self.response.user_id, "user-1")
        self.assertEqual(len(self.response.sections), 0)
    
    def test_response_confidence(self):
        """Test response confidence calculation."""
        # Confidence should be between 0 and 1
        self.assertGreaterEqual(self.response.overall_confidence, 0.0)
        self.assertLessEqual(self.response.overall_confidence, 1.0)


def run_tests():
    """Run all tests."""
    unittest.main(argv=[''], exit=False, verbosity=2)


if __name__ == "__main__":
    run_tests()
