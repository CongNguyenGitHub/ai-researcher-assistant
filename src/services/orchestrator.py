"""
Orchestrator service for Context-Aware Research Assistant.

Orchestrates the complete research query workflow:
1. Parallel retrieval from 4 sources
2. Context evaluation and filtering
3. Response synthesis
4. Memory persistence
"""

from typing import List, Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeoutError
import time

from models.query import Query
from models.context import AggregatedContext, ContextChunk
from models.response import FinalResponse
from models.memory import ConversationHistory, Message, MessageRole
from agents import create_evaluator_agent, create_synthesizer_agent
from tasks import create_evaluate_context_task, create_synthesize_response_task
from logging_config import get_logger, get_orchestrator_logger

logger = get_orchestrator_logger()


class Orchestrator:
    """
    Main orchestration engine for the research assistant workflow.
    
    Coordinates:
    - Parallel tool execution (RAG, web, arxiv, memory)
    - Context aggregation and deduplication
    - Evaluation and filtering
    - Response synthesis
    - Memory updates
    """
    
    def __init__(
        self,
        evaluator=None,
        synthesizer=None,
        tools: Optional[List] = None,
        max_workers: int = 4,
        use_crew: bool = False,
    ):
        """
        Initialize Orchestrator.
        
        Args:
            evaluator: Evaluator service instance
            synthesizer: Synthesizer service instance
            tools: List of retrieval tools (RAG, Web, Arxiv, Memory)
            max_workers: Maximum parallel workers for tool execution
            use_crew: Whether to use CrewAI for agent-based evaluation and synthesis
        """
        self.evaluator = evaluator
        self.synthesizer = synthesizer
        self.tools = tools or []
        self.max_workers = max_workers
        self.use_crew = use_crew
        
        self._crew = None
        self._evaluator_agent = None
        self._synthesizer_agent = None
        
        logger.info(
            f"Orchestrator initialized: {len(self.tools)} tools, "
            f"max_workers={max_workers}, use_crew={use_crew}"
        )
    
    def process_query(
        self,
        query: Query,
        conversation_history: Optional[ConversationHistory] = None,
    ) -> FinalResponse:
        """
        Process a research query through the complete workflow.
        
        Workflow:
        1. Retrieve context from all sources in parallel
        2. Aggregate and deduplicate
        3. Evaluate and filter for quality
        4. Synthesize response
        5. Update conversation memory
        
        Args:
            query: User research query
            conversation_history: Optional conversation context
            
        Returns:
            FinalResponse with answer and citations
        """
        start_time = time.time()
        
        try:
            logger.info(f"Processing query: {query.text[:100]}...")
            
            # Step 1: Parallel retrieval
            logger.debug("Step 1: Parallel retrieval from all sources")
            aggregated_context = self._retrieve_context(query)
            
            # Step 2: Evaluation and filtering
            logger.debug("Step 2: Evaluating and filtering context")
            filtered_context = self.evaluator.filter_context(aggregated_context, query)
            
            # Step 3: Synthesis
            logger.debug("Step 3: Synthesizing response")
            response = self.synthesizer.generate_response(query, filtered_context)
            
            # Step 4: Memory update
            if conversation_history:
                logger.debug("Step 4: Updating conversation memory")
                self._update_memory(query, response, conversation_history)
            
            response.generation_time_ms = (time.time() - start_time) * 1000
            query.mark_completed()
            
            logger.info(
                f"Query processed successfully: {response.generation_time_ms:.0f}ms, "
                f"confidence={response.overall_confidence:.2f}"
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}", exc_info=True)
            query.mark_failed(str(e))
            return self._create_error_response(query, str(e))
    
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
        response = FinalResponse(
            query_id=query.id,
            user_id=query.user_id,
            session_id=query.session_id,
        )
        
        response.answer = (
            f"I encountered an error while processing your query: \"{query.text}\"\n\n"
            f"Error: {error_message}\n\n"
            "Please try:\n"
            "- Refining your question to be more specific\n"
            "- Breaking the question into smaller parts\n"
            "- Checking that your documents are properly indexed (for RAG queries)"
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

