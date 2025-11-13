"""
CrewAI agents for Context-Aware Research Assistant.

Defines specialized agents for context evaluation and response synthesis.
"""

try:
    from crewai import Agent
except ImportError:
    # Fallback for when crewai is not yet installed
    Agent = None

from logging_config import get_logger

logger = get_logger(__name__)


def create_evaluator_agent():
    """
    Create the Context Evaluator agent.
    
    Role: Evaluates retrieved context chunks and scores them by quality
    Goal: Filter out low-quality information to improve answer accuracy
    
    Returns:
        CrewAI Agent instance (or dict if crewai not available)
    """
    if not Agent:
        logger.warning("CrewAI not installed, returning agent configuration dict")
        return {
            "role": "Context Evaluator",
            "goal": "Filter low-quality context and identify high-value information",
            "backstory": (
                "You are an expert information curator with deep knowledge of research methodology. "
                "Your role is to evaluate retrieved context chunks for quality, relevance, and reliability. "
                "You assess information based on source credibility, recency, and semantic relevance to the query. "
                "You identify contradictions and redundancy, removing low-value duplicates while preserving diverse perspectives."
            ),
        }
    
    return Agent(
        role="Context Evaluator",
        goal="Filter low-quality context and identify high-value information",
        backstory=(
            "You are an expert information curator with deep knowledge of research methodology. "
            "Your role is to evaluate retrieved context chunks for quality, relevance, and reliability. "
            "You assess information based on source credibility, recency, and semantic relevance to the query. "
            "You identify contradictions and redundancy, removing low-value duplicates while preserving diverse perspectives."
        ),
        verbose=True,
        allow_delegation=False,
    )


def create_synthesizer_agent():
    """
    Create the Answer Synthesizer agent.
    
    Role: Synthesizes comprehensive answers from filtered context
    Goal: Generate well-structured, highly accurate responses with proper citations
    
    Returns:
        CrewAI Agent instance (or dict if crewai not available)
    """
    if not Agent:
        logger.warning("CrewAI not installed, returning agent configuration dict")
        return {
            "role": "Answer Synthesizer",
            "goal": "Generate comprehensive, well-sourced research answers",
            "backstory": (
                "You are a master synthesizer and academic writer with expertise in translating "
                "complex research findings into clear, coherent narratives. "
                "Your role is to craft high-quality responses that accurately represent the context, "
                "properly attribute sources, and explicitly highlight any contradictions. "
                "You excel at organizing information hierarchically, building logical arguments, "
                "and explaining nuanced perspectives with appropriate confidence levels."
            ),
        }
    
    return Agent(
        role="Answer Synthesizer",
        goal="Generate comprehensive, well-sourced research answers",
        backstory=(
            "You are a master synthesizer and academic writer with expertise in translating "
            "complex research findings into clear, coherent narratives. "
            "Your role is to craft high-quality responses that accurately represent the context, "
            "properly attribute sources, and explicitly highlight any contradictions. "
            "You excel at organizing information hierarchically, building logical arguments, "
            "and explaining nuanced perspectives with appropriate confidence levels."
        ),
        verbose=True,
        allow_delegation=False,
    )


class AgentFactory:
    """Factory for creating and managing agents."""
    
    _agents = {}
    
    @classmethod
    def get_evaluator(cls):
        """Get or create evaluator agent."""
        if "evaluator" not in cls._agents:
            cls._agents["evaluator"] = create_evaluator_agent()
        return cls._agents["evaluator"]
    
    @classmethod
    def get_synthesizer(cls):
        """Get or create synthesizer agent."""
        if "synthesizer" not in cls._agents:
            cls._agents["synthesizer"] = create_synthesizer_agent()
        return cls._agents["synthesizer"]
    
    @classmethod
    def reset(cls):
        """Reset agent cache."""
        cls._agents = {}
        logger.info("Agent cache reset")
