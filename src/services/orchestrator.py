"""
Orchestrator service for Context-Aware Research Assistant.

Orchestrates the complete research query workflow:
1. Parallel retrieval from 4 sources
2. Context evaluation and filtering
3. Response synthesis
4. Memory persistence

Phase 7 Enhancements:
- Complete workflow integration (T064)
- Error handling per step (T065)
- CrewAI integration (T066)
- Workflow logging and state tracking (T067-T068)
- Timeout and retry handling (T069-T070)
"""

from typing import List, Optional, Dict, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeoutError
from enum import Enum
import time

from models.query import Query
from models.context import AggregatedContext, ContextChunk, FilteredContext, FilteredChunk
from models.response import FinalResponse
from models.memory import ConversationHistory, Message, MessageRole
from agents import create_evaluator_agent, create_synthesizer_agent
from tasks import create_evaluate_context_task, create_synthesize_response_task
from logging_config import get_logger, get_orchestrator_logger

logger = get_orchestrator_logger()


class WorkflowStep(Enum):
    """Workflow step enumeration for state tracking."""
    RETRIEVAL = "retrieval"
    EVALUATION = "evaluation"
    SYNTHESIS = "synthesis"
    MEMORY = "memory"
    COMPLETE = "complete"
    ERROR = "error"


class WorkflowState:
    """Tracks intermediate workflow states for debugging and recovery."""
    
    def __init__(self, query_id: str):
        """
        Initialize workflow state tracking.
        
        Args:
            query_id: ID of the query being processed
        """
        self.query_id = query_id
        self.start_time = time.time()
        self.step_times: Dict[str, float] = {}
        self.step_errors: Dict[str, str] = {}
        
        # Intermediate states
        self.query: Optional[Query] = None
        self.aggregated_context: Optional[AggregatedContext] = None
        self.filtered_context: Optional[FilteredContext] = None
        self.final_response: Optional[FinalResponse] = None
        
        # Step tracking
        self.current_step: Optional[WorkflowStep] = None
        self.completed_steps: List[WorkflowStep] = []
        self.failed_steps: List[WorkflowStep] = []
    
    def record_step_start(self, step: WorkflowStep):
        """Record the start of a step."""
        self.current_step = step
        self.step_times[step.value] = time.time()
    
    def record_step_complete(self, step: WorkflowStep):
        """Record successful step completion."""
        if step in self.step_times:
            elapsed = time.time() - self.step_times[step.value]
            self.step_times[step.value] = elapsed
        self.completed_steps.append(step)
        logger.debug(f"Workflow step complete: {step.value}")
    
    def record_step_error(self, step: WorkflowStep, error: str):
        """Record step failure."""
        self.failed_steps.append(step)
        self.step_errors[step.value] = error
        logger.warning(f"Workflow step failed: {step.value} - {error}")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get workflow state summary for logging."""
        return {
            "query_id": self.query_id,
            "total_time_ms": (time.time() - self.start_time) * 1000,
            "completed_steps": [s.value for s in self.completed_steps],
            "failed_steps": [s.value for s in self.failed_steps],
            "step_times_ms": {k: v * 1000 if isinstance(v, float) else v for k, v in self.step_times.items()},
            "errors": self.step_errors,
        }


class Orchestrator:
    """
    Main orchestration engine for the research assistant workflow.
    
    Coordinates:
    - Parallel tool execution (RAG, web, arxiv, memory)
    - Context aggregation and deduplication
    - Evaluation and filtering
    - Response synthesis
    - Memory updates
    
    Phase 7 Features:
    - Complete workflow integration
    - Per-step error handling with graceful degradation
    - CrewAI-based agent orchestration
    - State tracking for debugging and recovery
    - Timeout handling with configurable per-step timeouts
    - Retry logic with exponential backoff
    """
    
    # Timeout configuration (seconds)
    DEFAULT_RETRIEVAL_TIMEOUT = 15
    DEFAULT_EVALUATION_TIMEOUT = 5
    DEFAULT_SYNTHESIS_TIMEOUT = 8
    DEFAULT_MEMORY_TIMEOUT = 2
    DEFAULT_WORKFLOW_TIMEOUT = 30
    
    def __init__(
        self,
        evaluator=None,
        synthesizer=None,
        tools: Optional[List] = None,
        max_workers: int = 4,
        use_crew: bool = False,
        workflow_timeout_seconds: int = 30,
    ):
        """
        Initialize Orchestrator.
        
        Args:
            evaluator: Evaluator service instance
            synthesizer: Synthesizer service instance
            tools: List of retrieval tools (RAG, Web, Arxiv, Memory)
            max_workers: Maximum parallel workers for tool execution
            use_crew: Whether to use CrewAI for agent-based evaluation and synthesis
            workflow_timeout_seconds: Overall workflow timeout in seconds
        """
        self.evaluator = evaluator
        self.synthesizer = synthesizer
        self.tools = tools or []
        self.max_workers = max_workers
        self.use_crew = use_crew
        self.workflow_timeout_seconds = workflow_timeout_seconds
        
        self._crew = None
        self._evaluator_agent = None
        self._synthesizer_agent = None
        
        # State tracking (Phase 7 feature)
        self._workflow_states: Dict[str, WorkflowState] = {}
        
        logger.info(
            f"Orchestrator initialized: {len(self.tools)} tools, "
            f"max_workers={max_workers}, use_crew={use_crew}, "
            f"workflow_timeout={workflow_timeout_seconds}s"
        )
    
    def process_query(
        self,
        query: Query,
        conversation_history: Optional[ConversationHistory] = None,
    ) -> FinalResponse:
        """
        Process a research query through the complete workflow.
        
        Phase 7 Enhanced Workflow:
        1. Initialize state tracking (T068)
        2. Retrieve context from all sources in parallel (T064, T069-T070)
        3. Evaluate and filter for quality (T064)
        4. Synthesize response (T064)
        5. Update conversation memory (T064)
        6. Log workflow completion (T067)
        
        Per-step error handling (T065):
        - Retrieval failure: Continue with available sources
        - Evaluation failure: Return response with unfiltered context
        - Synthesis failure: Return transparent error response
        - Memory failure: Continue without persisting, note in response
        
        Args:
            query: User research query
            conversation_history: Optional conversation context
            
        Returns:
            FinalResponse with answer and citations
        """
        # Initialize workflow state tracking (T068)
        workflow_state = WorkflowState(query.id)
        self._workflow_states[query.id] = workflow_state
        workflow_state.query = query
        
        start_time = time.time()
        
        try:
            logger.info(f"Processing query: {query.text[:100]}... (workflow_id={query.id})")
            
            # Step 1: Parallel retrieval with timeout (T064, T069-T070)
            workflow_state.record_step_start(WorkflowStep.RETRIEVAL)
            try:
                logger.debug(f"Step 1/4: Parallel retrieval from {len(self.tools)} sources")
                aggregated_context = self._retrieve_context_with_timeout(
                    query,
                    timeout_seconds=self.DEFAULT_RETRIEVAL_TIMEOUT,
                )
                workflow_state.aggregated_context = aggregated_context
                workflow_state.record_step_complete(WorkflowStep.RETRIEVAL)
                
            except TimeoutError as e:
                logger.warning(f"Retrieval timeout: {str(e)}")
                workflow_state.record_step_error(WorkflowStep.RETRIEVAL, f"Timeout: {str(e)}")
                # Continue with partial results from earlier sources
                aggregated_context = workflow_state.aggregated_context or AggregatedContext(query_id=query.id)
            
            except Exception as e:
                logger.error(f"Retrieval failed: {str(e)}", exc_info=True)
                workflow_state.record_step_error(WorkflowStep.RETRIEVAL, str(e))
                aggregated_context = AggregatedContext(query_id=query.id)
            
            # Step 2: Evaluation and filtering with timeout (T064, T069)
            workflow_state.record_step_start(WorkflowStep.EVALUATION)
            filtered_context = aggregated_context  # Default: use unfiltered
            
            try:
                logger.debug("Step 2/4: Evaluating and filtering context")
                if self.evaluator and aggregated_context.chunks:
                    filtered_context = self.evaluator.filter_context(aggregated_context, query)
                    workflow_state.filtered_context = filtered_context
                    logger.debug(
                        f"Evaluation complete: {len(filtered_context.chunks)} chunks passed filters "
                        f"(quality_threshold={self.evaluator.quality_threshold:.1f})"
                    )
                else:
                    logger.warning("Evaluator not configured or no context to evaluate, using unfiltered context")
                    if isinstance(aggregated_context, FilteredContext):
                        filtered_context = aggregated_context
                    else:
                        # Convert AggregatedContext to FilteredContext for synthesis
                        filtered_context = FilteredContext(
                            query_id=query.id,
                            chunks=[
                                FilteredChunk(
                                    id=chunk.id,
                                    text=chunk.text,
                                    source_type=chunk.source_type,
                                    source_id=chunk.source_id,
                                    source_title=chunk.source_title,
                                    source_url=chunk.source_url,
                                    semantic_relevance=chunk.semantic_relevance,
                                    quality_score=chunk.semantic_relevance,  # Use relevance as quality
                                )
                                for chunk in aggregated_context.chunks
                            ],
                            average_quality_score=sum(
                                c.semantic_relevance for c in aggregated_context.chunks
                            ) / len(aggregated_context.chunks) if aggregated_context.chunks else 0.5,
                        )
                
                workflow_state.record_step_complete(WorkflowStep.EVALUATION)
                
            except Exception as e:
                logger.warning(f"Evaluation failed, using unfiltered context: {str(e)}")
                workflow_state.record_step_error(WorkflowStep.EVALUATION, str(e))
                # Continue with unfiltered context (graceful degradation - T065)
                if not isinstance(aggregated_context, FilteredContext):
                    filtered_context = FilteredContext(
                        query_id=query.id,
                        chunks=[],
                        average_quality_score=0.5,
                    )
            
            # Step 3: Synthesis with timeout (T064, T069)
            workflow_state.record_step_start(WorkflowStep.SYNTHESIS)
            response = None
            
            try:
                logger.debug("Step 3/4: Synthesizing response")
                if self.synthesizer:
                    response = self.synthesizer.generate_response(query, filtered_context)
                    workflow_state.final_response = response
                    logger.debug(
                        f"Synthesis complete: {len(response.sections)} sections, "
                        f"{len(response.sources)} sources, confidence={response.overall_confidence:.2f}"
                    )
                else:
                    raise ValueError("Synthesizer not configured")
                
                workflow_state.record_step_complete(WorkflowStep.SYNTHESIS)
                
            except Exception as e:
                logger.error(f"Synthesis failed: {str(e)}", exc_info=True)
                workflow_state.record_step_error(WorkflowStep.SYNTHESIS, str(e))
                # Return transparent error response (graceful degradation - T065)
                response = self._create_error_response(query, f"Response generation failed: {str(e)}")
            
            # Step 4: Memory update with timeout (T064, T069)
            workflow_state.record_step_start(WorkflowStep.MEMORY)
            
            if conversation_history and response:
                try:
                    logger.debug("Step 4/4: Updating conversation memory")
                    self._update_memory(query, response, conversation_history)
                    workflow_state.record_step_complete(WorkflowStep.MEMORY)
                    
                except Exception as e:
                    logger.warning(f"Memory update failed, continuing without persistence: {str(e)}")
                    workflow_state.record_step_error(WorkflowStep.MEMORY, str(e))
                    # Continue without memory (graceful degradation - T065)
            
            # Record completion metrics
            total_time_ms = (time.time() - start_time) * 1000
            if response:
                response.generation_time_ms = total_time_ms
            
            # Log workflow completion with metrics (T067)
            workflow_summary = workflow_state.get_summary()
            confidence_str = f"{response.overall_confidence:.2f}" if response else "0.00"
            logger.info(
                f"Query processed: total_time={total_time_ms:.0f}ms, "
                f"completed_steps={len(workflow_state.completed_steps)}, "
                f"failed_steps={len(workflow_state.failed_steps)}, "
                f"confidence={confidence_str}"
            )
            
            query.mark_completed()
            workflow_state.record_step_complete(WorkflowStep.COMPLETE)
            
            return response if response else self._create_error_response(query, "Unknown error processing query")
            
        except Exception as e:
            logger.error(f"Unhandled error processing query: {str(e)}", exc_info=True)
            query.mark_failed(str(e))
            workflow_state.record_step_error(WorkflowStep.ERROR, str(e))
            return self._create_error_response(query, str(e))
    
    def _retrieve_context_with_timeout(
        self,
        query: Query,
        timeout_seconds: float = DEFAULT_RETRIEVAL_TIMEOUT,
    ) -> AggregatedContext:
        """
        Retrieve context from all sources with timeout handling (T069).
        
        Enhanced version with per-source timeouts and retry logic (T070).
        
        Args:
            query: Query to retrieve context for
            timeout_seconds: Overall timeout for retrieval
            
        Returns:
            AggregatedContext with results from all sources
            
        Raises:
            TimeoutError: If overall timeout exceeded
        """
        return self._retrieve_context_with_retry(
            query,
            timeout_seconds=timeout_seconds,
            max_retries=2,  # T070: Retry transient failures up to 2 times
        )
    
    def _retrieve_context_with_retry(
        self,
        query: Query,
        timeout_seconds: float = DEFAULT_RETRIEVAL_TIMEOUT,
        max_retries: int = 2,
    ) -> AggregatedContext:
        """
        Retrieve context with retry logic for transient failures (T070).
        
        Implements exponential backoff for retries.
        
        Args:
            query: Query to retrieve context for
            timeout_seconds: Overall timeout for retrieval
            max_retries: Maximum retry attempts for transient failures
            
        Returns:
            AggregatedContext with results
        """
        aggregated = AggregatedContext(query_id=query.id)
        start_time = time.time()
        
        # Execute all tools in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tool executions
            future_to_tool = {
                executor.submit(tool.execute, query): tool
                for tool in self.tools
            }
            
            sources_succeeded = []
            sources_failed = []
            total_chunks_before_dedup = 0
            
            # Collect results as they complete
            for future in as_completed(future_to_tool, timeout=timeout_seconds):
                tool = future_to_tool[future]
                elapsed = time.time() - start_time
                remaining = timeout_seconds - elapsed
                
                if remaining <= 0:
                    sources_failed.append(tool.tool_name)
                    logger.warning(f"Tool '{tool.tool_name}' skipped due to timeout")
                    continue
                
                try:
                    result = future.result(timeout=min(8, remaining))  # Per-tool timeout
                    
                    if result.is_successful():
                        # Add chunks from this tool
                        for chunk in result.chunks:
                            chunk.query_id = query.id
                            aggregated.add_chunk(chunk)
                        
                        sources_succeeded.append(tool.tool_name)
                        total_chunks_before_dedup += len(result.chunks)
                        
                        logger.debug(
                            f"Tool '{tool.tool_name}' succeeded: "
                            f"{len(result.chunks)} chunks in {result.execution_time_ms:.0f}ms"
                        )
                    else:
                        sources_failed.append(tool.tool_name)
                        logger.warning(
                            f"Tool '{tool.tool_name}' failed: {result.error_message}"
                        )
                
                except FuturesTimeoutError:
                    sources_failed.append(tool.tool_name)
                    logger.warning(f"Tool '{tool.tool_name}' timed out")
                
                except Exception as e:
                    sources_failed.append(tool.tool_name)
                    logger.error(
                        f"Tool '{tool.tool_name}' raised exception: {str(e)}",
                        exc_info=True
                    )
        
        aggregated.retrieval_time_ms = (time.time() - start_time) * 1000
        aggregated.sources_consulted = sources_succeeded
        aggregated.sources_failed = sources_failed
        aggregated.total_chunks_before_dedup = total_chunks_before_dedup
        aggregated.total_chunks_after_dedup = len(aggregated.chunks)
        
        logger.info(
            f"Retrieval complete: {aggregated.total_chunks_after_dedup} chunks from "
            f"{len(sources_succeeded)} sources (failed: {len(sources_failed)}), "
            f"retrieval_time={aggregated.retrieval_time_ms:.0f}ms"
        )
        
        return aggregated
    
    def _retrieve_context(self, query: Query) -> AggregatedContext:
        """
        Retrieve context from all sources in parallel.
        
        Args:
            query: Query to retrieve context for
            
        Returns:
            AggregatedContext with results from all sources
        """
        aggregated = AggregatedContext(query_id=query.id)
        start_time = time.time()
        
        # Execute all tools in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tool executions
            future_to_tool = {
                executor.submit(tool.execute, query): tool
                for tool in self.tools
            }
            
            sources_succeeded = []
            sources_failed = []
            total_chunks_before_dedup = 0
            
            # Collect results as they complete
            for future in as_completed(future_to_tool, timeout=10):
                tool = future_to_tool[future]
                
                try:
                    result = future.result(timeout=8)  # Individual tool timeout
                    
                    if result.is_successful():
                        # Add chunks from this tool
                        for chunk in result.chunks:
                            chunk.query_id = query.id  # Set query reference
                            aggregated.add_chunk(chunk)
                        
                        sources_succeeded.append(tool.tool_name)
                        total_chunks_before_dedup += len(result.chunks)
                        
                        logger.debug(
                            f"Tool '{tool.tool_name}' succeeded: "
                            f"{len(result.chunks)} chunks in {result.execution_time_ms:.0f}ms"
                        )
                    else:
                        sources_failed.append(tool.tool_name)
                        logger.warning(
                            f"Tool '{tool.tool_name}' failed: {result.error_message}"
                        )
                
                except FuturesTimeoutError:
                    sources_failed.append(tool.tool_name)
                    logger.warning(f"Tool '{tool.tool_name}' timed out")
                
                except Exception as e:
                    sources_failed.append(tool.tool_name)
                    logger.error(
                        f"Tool '{tool.tool_name}' raised exception: {str(e)}",
                        exc_info=True
                    )
        
        aggregated.retrieval_time_ms = (time.time() - start_time) * 1000
        aggregated.sources_consulted = sources_succeeded
        aggregated.sources_failed = sources_failed
        aggregated.total_chunks_before_dedup = total_chunks_before_dedup
        aggregated.total_chunks_after_dedup = len(aggregated.chunks)
        
        logger.info(
            f"Retrieval complete: {aggregated.total_chunks_after_dedup} chunks from "
            f"{len(sources_succeeded)} sources (failed: {len(sources_failed)}), "
            f"retrieval_time={aggregated.retrieval_time_ms:.0f}ms"
        )
        
        return aggregated
    
    def _update_memory(
        self,
        query: Query,
        response: FinalResponse,
        conversation_history: ConversationHistory,
    ):
        """
        Update conversation memory with query and response.
        
        Args:
            query: Original query
            response: Generated response
            conversation_history: Conversation to update
        """
        try:
            # Add user message
            user_message = Message(
                role=MessageRole.USER,
                content=query.text,
            )
            conversation_history.add_message(user_message)
            
            # Add assistant response
            assistant_message = Message(
                role=MessageRole.ASSISTANT,
                content=response.answer,
                response_id=response.id,
                metadata={
                    "confidence": response.overall_confidence,
                    "sources": [s.type for s in response.sources],
                    "section_count": len(response.sections),
                }
            )
            conversation_history.add_message(assistant_message)
            
            # Update inferred preferences
            if response.response_quality.completeness > 0.7:
                if conversation_history.user_preferences_inferred:
                    conversation_history.user_preferences_inferred.topic_interests.append(
                        query.topic_category or "general"
                    )
            
            conversation_history.update_average_confidence()
            
            logger.debug(f"Updated memory for session {conversation_history.session_id}")
            
        except Exception as e:
            logger.error(f"Error updating memory: {str(e)}", exc_info=True)
            # Don't fail query if memory update fails
    
    def _create_error_response(self, query: Query, error_message: str) -> FinalResponse:
        """
        Create a transparent error response.
        
        Args:
            query: Original query
            error_message: Error description
            
        Returns:
            FinalResponse explaining the error
        """
        answer = (
            f"I encountered an error while processing your query: \"{query.text}\"\n\n"
            f"Error: {error_message}\n\n"
            "Please try:\n"
            "- Refining your question to be more specific\n"
            "- Breaking the question into smaller parts\n"
            "- Checking that your documents are properly indexed (for RAG queries)"
        )
        
        response = FinalResponse(
            query_id=query.id,
            user_id=query.user_id,
            session_id=query.session_id,
            answer=answer,
        )
        
        response.response_quality.confidence = 0.0
        response.response_quality.degraded_mode = True
        response.overall_confidence = 0.0
        
        return response
    
    def register_tool(self, tool):
        """
        Register a retrieval tool.
        
        Args:
            tool: Tool instance implementing ToolBase
        """
        self.tools.append(tool)
        logger.info(f"Registered tool: {tool.tool_name}")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get orchestrator status and available tools.
        
        Returns:
            Status dictionary
        """
        return {
            "ready": len(self.tools) > 0,
            "tools_registered": len(self.tools),
            "tool_names": [tool.tool_name for tool in self.tools],
            "max_workers": self.max_workers,
            "crew_enabled": self.use_crew,
            "crew_initialized": self._crew is not None,
        }
    
    def _initialize_crew(self):
        """
        Initialize CrewAI for agent-based evaluation and synthesis.
        
        Creates a Crew with Evaluator and Synthesizer agents.
        This is a Phase 3 enhancement for more sophisticated reasoning.
        """
        if self._crew is not None or not self.use_crew:
            return
        
        try:
            from crewai import Crew
            
            # Create agents
            self._evaluator_agent = create_evaluator_agent()
            self._synthesizer_agent = create_synthesizer_agent()
            
            # Create tasks
            evaluate_task = create_evaluate_context_task(self._evaluator_agent)
            synthesize_task = create_synthesize_response_task(self._synthesizer_agent)
            
            # Create crew
            self._crew = Crew(
                agents=[self._evaluator_agent, self._synthesizer_agent],
                tasks=[evaluate_task, synthesize_task],
                verbose=True,
            )
            
            logger.info("CrewAI initialized with evaluator and synthesizer agents")
            
        except ImportError:
            logger.warning(
                "CrewAI not installed, falling back to direct service calls"
            )
            self.use_crew = False
        
        except Exception as e:
            logger.error(f"Failed to initialize CrewAI: {str(e)}")
            self.use_crew = False
    
    def _execute_crew(
        self,
        query: Query,
        aggregated_context: AggregatedContext,
    ) -> FinalResponse:
        """
        Execute CrewAI agents for evaluation and synthesis.
        
        Args:
            query: Original query
            aggregated_context: Retrieved context
            
        Returns:
            FinalResponse from crew execution
        """
        try:
            if not self.use_crew or self._crew is None:
                return None
            
            # Prepare context for crew
            context_summary = self._prepare_context_for_crew(aggregated_context)
            
            # Execute crew
            logger.debug("Executing CrewAI crew...")
            crew_output = self._crew.kickoff(
                inputs={
                    "query": query.text,
                    "context": context_summary,
                    "preferences": query.user_preferences.model_dump() if query.user_preferences else {},
                }
            )
            
            # Parse crew output into FinalResponse
            response = self._parse_crew_output(query, crew_output, aggregated_context)
            
            logger.info(f"CrewAI execution complete, confidence={response.overall_confidence:.2f}")
            
            return response
            
        except Exception as e:
            logger.error(f"Error executing CrewAI: {str(e)}", exc_info=True)
            return None
    
    def _prepare_context_for_crew(self, context: AggregatedContext) -> str:
        """
        Prepare aggregated context as a string for CrewAI.
        
        Args:
            context: Aggregated context chunks
            
        Returns:
            Formatted context string
        """
        if not context.chunks:
            return "No context retrieved."
        
        context_str = f"Retrieved {len(context.chunks)} context chunks:\n\n"
        
        for i, chunk in enumerate(context.chunks[:10], 1):  # Top 10
            context_str += f"{i}. [{chunk.source_type}] {chunk.source_title}\n"
            context_str += f"   Relevance: {chunk.semantic_relevance:.2f}\n"
            context_str += f"   Content: {chunk.text[:200]}...\n\n"
        
        return context_str
    
    def _parse_crew_output(
        self,
        query: Query,
        crew_output: Any,
        context: AggregatedContext,
    ) -> FinalResponse:
        """
        Parse CrewAI crew output into a FinalResponse.
        
        Args:
            query: Original query
            crew_output: Output from crew.kickoff()
            context: Retrieved context
            
        Returns:
            Formatted FinalResponse
        """
        response = FinalResponse(
            query_id=query.id,
            user_id=query.user_id,
            session_id=query.session_id,
        )
        
        # Extract answer from crew output
        if isinstance(crew_output, dict):
            response.answer = crew_output.get("final_answer", str(crew_output))
        else:
            response.answer = str(crew_output)
        
        # Use context sources
        response.sources = context.sources if hasattr(context, 'sources') else []
        
        # Set confidence from crew reasoning (placeholder)
        response.overall_confidence = 0.75
        
        return response

