"""
Phase 7 Integration Tests: Orchestration Integration

Tests the complete Phase 4→5→6→7 pipeline:
- Orchestrator.process_query() complete workflow
- Per-step error handling and graceful degradation
- State tracking and logging
- Timeout handling
- Retry logic
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, MagicMock
import uuid

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from services.orchestrator import Orchestrator, WorkflowStep, WorkflowState
from services.evaluator import Evaluator
from services.synthesizer import Synthesizer
from models.query import Query
from models.context import (
    AggregatedContext,
    FilteredContext,
    FilteredChunk,
    SourceType,
    ContextChunk,
)
from models.response import FinalResponse
from models.memory import ConversationHistory


class TestWorkflowStateTracking:
    """Test Phase 7 workflow state tracking (T068)."""
    
    def test_workflow_state_initialization(self):
        """WorkflowState should initialize with query_id."""
        query_id = str(uuid.uuid4())
        state = WorkflowState(query_id)
        
        assert state.query_id == query_id
        assert state.start_time > 0
        assert len(state.completed_steps) == 0
        assert len(state.failed_steps) == 0
    
    def test_workflow_state_records_step_completion(self):
        """WorkflowState should record step completions."""
        state = WorkflowState("test-query")
        
        state.record_step_start(WorkflowStep.RETRIEVAL)
        state.record_step_complete(WorkflowStep.RETRIEVAL)
        
        assert WorkflowStep.RETRIEVAL in state.completed_steps
        assert WorkflowStep.RETRIEVAL not in state.failed_steps
        assert WorkflowStep.RETRIEVAL.value in state.step_times
    
    def test_workflow_state_records_errors(self):
        """WorkflowState should record step errors."""
        state = WorkflowState("test-query")
        error_msg = "Connection timeout"
        
        state.record_step_error(WorkflowStep.RETRIEVAL, error_msg)
        
        assert WorkflowStep.RETRIEVAL in state.failed_steps
        assert state.step_errors[WorkflowStep.RETRIEVAL.value] == error_msg
    
    def test_workflow_state_summary(self):
        """WorkflowState summary should contain all metrics."""
        state = WorkflowState("test-query")
        state.record_step_complete(WorkflowStep.RETRIEVAL)
        state.record_step_error(WorkflowStep.EVALUATION, "Test error")
        
        summary = state.get_summary()
        
        assert "query_id" in summary
        assert "total_time_ms" in summary
        assert "completed_steps" in summary
        assert "failed_steps" in summary
        assert WorkflowStep.RETRIEVAL.value in summary["completed_steps"]
        assert WorkflowStep.EVALUATION.value in summary["failed_steps"]


class TestOrchestratorWorkflow:
    """Test complete orchestrator workflow (T064)."""
    
    @pytest.fixture
    def orchestrator_with_services(self):
        """Create orchestrator with evaluator and synthesizer."""
        evaluator = Evaluator()
        synthesizer = Synthesizer()
        orchestrator = Orchestrator(
            evaluator=evaluator,
            synthesizer=synthesizer,
            tools=[],  # No tools for unit tests
            workflow_timeout_seconds=30,
        )
        return orchestrator
    
    @pytest.fixture
    def test_query(self):
        """Create a test query."""
        return Query(
            id=str(uuid.uuid4()),
            user_id="test-user",
            session_id="test-session",
            text="What is machine learning?",
        )
    
    @pytest.fixture
    def mock_context(self, test_query):
        """Create mock context for testing."""
        chunks = [
            FilteredChunk(
                id="c1",
                text="Machine learning is a subset of AI.",
                source_type=SourceType.ARXIV,
                source_id="arxiv1",
                source_title="ML Paper",
                semantic_relevance=0.95,
                quality_score=0.90,
            ),
            FilteredChunk(
                id="c2",
                text="Deep learning uses neural networks.",
                source_type=SourceType.WEB,
                source_id="web1",
                source_title="Tech Blog",
                semantic_relevance=0.88,
                quality_score=0.85,
            ),
        ]
        
        return FilteredContext(
            query_id=test_query.id,
            chunks=chunks,
            average_quality_score=0.875,
        )
    
    def test_orchestrator_processes_query_successfully(self, orchestrator_with_services, test_query, mock_context):
        """Orchestrator should process query through complete workflow."""
        # Mock the evaluator and synthesizer
        orchestrator_with_services.evaluator = Mock()
        orchestrator_with_services.evaluator.filter_context = Mock(return_value=mock_context)
        
        orchestrator_with_services.synthesizer = Mock()
        orchestrator_with_services.synthesizer.generate_response = Mock(
            return_value=FinalResponse(
                query_id=test_query.id,
                user_id=test_query.user_id,
                session_id=test_query.session_id,
                answer="Machine learning is a method of teaching computers to learn from data.",
            )
        )
        
        response = orchestrator_with_services.process_query(test_query)
        
        assert response is not None
        assert response.answer is not None
        assert response.overall_confidence > 0
        assert test_query.id in orchestrator_with_services._workflow_states
    
    def test_orchestrator_handles_empty_context(self, orchestrator_with_services, test_query):
        """Orchestrator should handle empty context gracefully."""
        empty_context = FilteredContext(
            query_id=test_query.id,
            chunks=[],
            average_quality_score=0.0,
        )
        
        orchestrator_with_services.evaluator = Mock()
        orchestrator_with_services.evaluator.filter_context = Mock(return_value=empty_context)
        
        orchestrator_with_services.synthesizer = Mock()
        orchestrator_with_services.synthesizer.generate_response = Mock(
            return_value=FinalResponse(
                query_id=test_query.id,
                user_id=test_query.user_id,
                session_id=test_query.session_id,
                answer="No relevant information found.",
            )
        )
        
        response = orchestrator_with_services.process_query(test_query)
        
        assert response is not None
        assert "No relevant information found" in response.answer or "couldn't find" in response.answer.lower()


class TestErrorHandling:
    """Test Phase 7 error handling per step (T065)."""
    
    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator with mocked services."""
        evaluator = Mock()
        synthesizer = Mock()
        return Orchestrator(
            evaluator=evaluator,
            synthesizer=synthesizer,
            tools=[],
            workflow_timeout_seconds=30,
        )
    
    @pytest.fixture
    def test_query(self):
        """Create test query."""
        return Query(
            id=str(uuid.uuid4()),
            user_id="test-user",
            session_id="test-session",
            text="Test query",
        )
    
    def test_evaluator_failure_returns_unfiltered_context(self, orchestrator, test_query):
        """If evaluator fails, should use unfiltered context (T065)."""
        # Mock retrieval to return context
        aggregated = AggregatedContext(query_id=test_query.id)
        chunk = ContextChunk(
            id="c1",
            text="Test content",
            source_type=SourceType.WEB,
            source_id="web1",
            source_title="Source",
            semantic_relevance=0.8,
        )
        aggregated.add_chunk(chunk)
        
        orchestrator.evaluator = Mock()
        orchestrator.evaluator.filter_context = Mock(side_effect=Exception("Evaluation error"))
        
        orchestrator.synthesizer = Mock()
        orchestrator.synthesizer.generate_response = Mock(
            return_value=FinalResponse(
                query_id=test_query.id,
                user_id=test_query.user_id,
                session_id=test_query.session_id,
                answer="Response despite evaluation failure",
            )
        )
        
        # Mock the retrieval method
        orchestrator._retrieve_context_with_timeout = Mock(return_value=aggregated)
        
        response = orchestrator.process_query(test_query)
        
        # Should get response even though evaluator failed
        assert response is not None
        # Synthesizer should have been called with some context
        orchestrator.synthesizer.generate_response.assert_called()
    
    def test_synthesis_failure_returns_error_response(self, orchestrator, test_query):
        """If synthesis fails, should return transparent error response (T065)."""
        context = FilteredContext(
            query_id=test_query.id,
            chunks=[],
            average_quality_score=0.5,
        )
        
        orchestrator.evaluator = Mock()
        orchestrator.evaluator.filter_context = Mock(return_value=context)
        
        orchestrator.synthesizer = Mock()
        orchestrator.synthesizer.generate_response = Mock(
            side_effect=Exception("Synthesis error")
        )
        
        orchestrator._retrieve_context_with_timeout = Mock(
            return_value=AggregatedContext(query_id=test_query.id)
        )
        
        response = orchestrator.process_query(test_query)
        
        # Should get error response
        assert response is not None
        assert "error" in response.answer.lower() or "encountered" in response.answer.lower()
        assert response.overall_confidence == 0.0
    
    def test_memory_failure_continues_processing(self, orchestrator, test_query):
        """If memory update fails, should continue without persistence (T065)."""
        context = FilteredContext(
            query_id=test_query.id,
            chunks=[],
            average_quality_score=0.5,
        )
        
        orchestrator.evaluator = Mock()
        orchestrator.evaluator.filter_context = Mock(return_value=context)
        
        orchestrator.synthesizer = Mock()
        final_response = FinalResponse(
            query_id=test_query.id,
            user_id=test_query.user_id,
            session_id=test_query.session_id,
            answer="Test response",
        )
        orchestrator.synthesizer.generate_response = Mock(return_value=final_response)
        
        orchestrator._retrieve_context_with_timeout = Mock(
            return_value=AggregatedContext(query_id=test_query.id)
        )
        
        orchestrator._update_memory = Mock(side_effect=Exception("Memory error"))
        
        # Should not raise error
        response = orchestrator.process_query(test_query, conversation_history=Mock())
        
        assert response is not None
        assert response.answer == "Test response"


class TestStateManagement:
    """Test workflow state management and tracking (T068)."""
    
    def test_orchestrator_stores_workflow_state(self):
        """Orchestrator should store workflow state for each query."""
        orchestrator = Orchestrator(
            evaluator=Mock(),
            synthesizer=Mock(),
            tools=[],
        )
        
        query = Query(
            id=str(uuid.uuid4()),
            user_id="user1",
            session_id="session1",
            text="Test",
        )
        
        # Mock services
        orchestrator.evaluator.filter_context = Mock(
            return_value=FilteredContext(
                query_id=query.id,
                chunks=[],
                average_quality_score=0.5,
            )
        )
        
        orchestrator.synthesizer.generate_response = Mock(
            return_value=FinalResponse(
                query_id=query.id,
                user_id=query.user_id,
                session_id=query.session_id,
                answer="Response",
            )
        )
        
        orchestrator._retrieve_context_with_timeout = Mock(
            return_value=AggregatedContext(query_id=query.id)
        )
        
        response = orchestrator.process_query(query)
        
        # Workflow state should be stored
        assert query.id in orchestrator._workflow_states
        state = orchestrator._workflow_states[query.id]
        assert state.query_id == query.id


class TestTimeoutHandling:
    """Test timeout handling per step (T069)."""
    
    def test_orchestrator_has_configurable_timeouts(self):
        """Orchestrator should have configurable timeouts."""
        orchestrator = Orchestrator(
            evaluator=Mock(),
            synthesizer=Mock(),
            tools=[],
            workflow_timeout_seconds=20,
        )
        
        assert orchestrator.workflow_timeout_seconds == 20
        assert orchestrator.DEFAULT_RETRIEVAL_TIMEOUT == 15
        assert orchestrator.DEFAULT_EVALUATION_TIMEOUT == 5
        assert orchestrator.DEFAULT_SYNTHESIS_TIMEOUT == 8


class TestPhase7AcceptanceCriteria:
    """Test Phase 7 acceptance criteria."""
    
    def test_ac_p7_001_complete_workflow_execution(self):
        """AC-P7-001: Complete workflow should execute all steps."""
        query = Query(
            id=str(uuid.uuid4()),
            user_id="user1",
            session_id="session1",
            text="Test query",
        )
        
        orchestrator = Orchestrator(
            evaluator=Mock(),
            synthesizer=Mock(),
            tools=[],
        )
        
        # Mock all services
        aggregated = AggregatedContext(query_id=query.id)
        context = FilteredContext(
            query_id=query.id,
            chunks=[FilteredChunk(
                id="c1",
                text="Context",
                source_type=SourceType.WEB,
                source_id="web1",
                source_title="Web",
                semantic_relevance=0.8,
                quality_score=0.8,
            )],
            average_quality_score=0.8,
        )
        
        orchestrator.evaluator.filter_context = Mock(return_value=context)
        orchestrator.synthesizer.generate_response = Mock(
            return_value=FinalResponse(
                query_id=query.id,
                user_id=query.user_id,
                session_id=query.session_id,
                answer="Complete response",
            )
        )
        orchestrator._retrieve_context_with_timeout = Mock(return_value=aggregated)
        
        response = orchestrator.process_query(query)
        
        # All services should be called
        assert response is not None
        assert len(response.answer) > 0
        # Should have called retrieval
        orchestrator._retrieve_context_with_timeout.assert_called()
        # Synthesis should have been called
        orchestrator.synthesizer.generate_response.assert_called()
    
    def test_ac_p7_002_error_handling_per_step(self):
        """AC-P7-002: Errors should be handled per step with graceful degradation."""
        query = Query(
            id=str(uuid.uuid4()),
            user_id="user1",
            session_id="session1",
            text="Test",
        )
        
        orchestrator = Orchestrator(
            evaluator=Mock(),
            synthesizer=Mock(),
            tools=[],
        )
        
        # Mock with failures
        orchestrator.evaluator.filter_context = Mock(side_effect=Exception("Filter error"))
        orchestrator.synthesizer.generate_response = Mock(
            return_value=FinalResponse(
                query_id=query.id,
                user_id=query.user_id,
                session_id=query.session_id,
                answer="Response despite evaluation failure",
            )
        )
        orchestrator._retrieve_context_with_timeout = Mock(
            return_value=AggregatedContext(query_id=query.id)
        )
        
        # Should not raise, should return response
        response = orchestrator.process_query(query)
        assert response is not None
    
    def test_ac_p7_003_workflow_logging(self):
        """AC-P7-003: Workflow should log each step completion."""
        query = Query(
            id=str(uuid.uuid4()),
            user_id="user1",
            session_id="session1",
            text="Test",
        )
        
        orchestrator = Orchestrator(
            evaluator=Mock(),
            synthesizer=Mock(),
            tools=[],
        )
        
        context = FilteredContext(
            query_id=query.id,
            chunks=[],
            average_quality_score=0.5,
        )
        
        orchestrator.evaluator.filter_context = Mock(return_value=context)
        orchestrator.synthesizer.generate_response = Mock(
            return_value=FinalResponse(
                query_id=query.id,
                user_id=query.user_id,
                session_id=query.session_id,
                answer="Response",
            )
        )
        orchestrator._retrieve_context_with_timeout = Mock(
            return_value=AggregatedContext(query_id=query.id)
        )
        
        response = orchestrator.process_query(query)
        
        # Workflow state should track all steps
        state = orchestrator._workflow_states[query.id]
        assert WorkflowStep.RETRIEVAL in state.completed_steps or WorkflowStep.RETRIEVAL in state.failed_steps
        assert WorkflowStep.EVALUATION in state.completed_steps or WorkflowStep.EVALUATION in state.failed_steps
        assert WorkflowStep.SYNTHESIS in state.completed_steps or WorkflowStep.SYNTHESIS in state.failed_steps


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
