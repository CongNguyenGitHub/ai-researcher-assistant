"""
CrewAI tasks for Context-Aware Research Assistant.

Defines specific tasks for evaluation and synthesis agents.
"""

try:
    from crewai import Task
except ImportError:
    Task = None

from logging_config import get_logger

logger = get_logger(__name__)


def create_evaluate_context_task(evaluator_agent):
    """
    Create the Evaluate Context task.
    
    Description: Evaluate aggregated context chunks for quality
    Expected Output: Filtered context with quality scores
    
    Args:
        evaluator_agent: The evaluator agent that will execute this task
        
    Returns:
        CrewAI Task instance (or dict if crewai not available)
    """
    if not Task:
        logger.warning("CrewAI not installed, returning task configuration dict")
        return {
            "description": (
                "Evaluate the retrieved context chunks from all sources for quality, relevance, "
                "and reliability. Score each chunk based on: source reputation (30%), recency (20%), "
                "semantic relevance (40%), and redundancy penalty (10%). "
                "Filter out chunks scoring below the quality threshold. Identify contradictions. "
                "Provide a ranked list of high-quality chunks ready for synthesis."
            ),
            "expected_output": (
                "A FilteredContext object containing: scored chunks ranked by quality, "
                "list of removed chunks with reasons, detected contradictions, "
                "average quality score, and filtering statistics."
            ),
        }
    
    return Task(
        description=(
            "Evaluate the retrieved context chunks from all sources for quality, relevance, "
            "and reliability. Score each chunk based on: source reputation (30%), recency (20%), "
            "semantic relevance (40%), and redundancy penalty (10%). "
            "Filter out chunks scoring below the quality threshold. Identify contradictions. "
            "Provide a ranked list of high-quality chunks ready for synthesis."
        ),
        expected_output=(
            "A FilteredContext object containing: scored chunks ranked by quality, "
            "list of removed chunks with reasons, detected contradictions, "
            "average quality score, and filtering statistics."
        ),
        agent=evaluator_agent,
        async_execution=False,
    )


def create_synthesize_response_task(synthesizer_agent):
    """
    Create the Synthesize Response task.
    
    Description: Synthesize comprehensive answer from filtered context
    Expected Output: FinalResponse with sections, citations, and confidence
    
    Args:
        synthesizer_agent: The synthesizer agent that will execute this task
        
    Returns:
        CrewAI Task instance (or dict if crewai not available)
    """
    if not Task:
        logger.warning("CrewAI not installed, returning task configuration dict")
        return {
            "description": (
                "Synthesize a comprehensive research answer from the filtered context chunks. "
                "Organize information into logical sections by theme. "
                "Include proper 3-level citations: main answer attribution, section-level sources, "
                "and per-claim confidence scores. "
                "Explicitly document any contradictions from different sources. "
                "Calculate overall response confidence based on source quality and context completeness. "
                "Format answer for clarity and academic rigor."
            ),
            "expected_output": (
                "A FinalResponse object containing: main answer, organized sections with content, "
                "source attributions with URLs and relevance scores, detected perspectives/contradictions, "
                "3-level citation information, quality metrics (completeness/informativeness/confidence), "
                "and generation metadata."
            ),
        }
    
    return Task(
        description=(
            "Synthesize a comprehensive research answer from the filtered context chunks. "
            "Organize information into logical sections by theme. "
            "Include proper 3-level citations: main answer attribution, section-level sources, "
            "and per-claim confidence scores. "
            "Explicitly document any contradictions from different sources. "
            "Calculate overall response confidence based on source quality and context completeness. "
            "Format answer for clarity and academic rigor."
        ),
        expected_output=(
            "A FinalResponse object containing: main answer, organized sections with content, "
            "source attributions with URLs and relevance scores, detected perspectives/contradictions, "
            "3-level citation information, quality metrics (completeness/informativeness/confidence), "
            "and generation metadata."
        ),
        agent=synthesizer_agent,
        async_execution=False,
    )


class TaskFactory:
    """Factory for creating and managing tasks."""
    
    _tasks = {}
    
    @classmethod
    def get_evaluate_context_task(cls, agent):
        """Get or create evaluate context task."""
        if "evaluate_context" not in cls._tasks:
            cls._tasks["evaluate_context"] = create_evaluate_context_task(agent)
        return cls._tasks["evaluate_context"]
    
    @classmethod
    def get_synthesize_response_task(cls, agent):
        """Get or create synthesize response task."""
        if "synthesize_response" not in cls._tasks:
            cls._tasks["synthesize_response"] = create_synthesize_response_task(agent)
        return cls._tasks["synthesize_response"]
    
    @classmethod
    def reset(cls):
        """Reset task cache."""
        cls._tasks = {}
        logger.info("Task cache reset")
