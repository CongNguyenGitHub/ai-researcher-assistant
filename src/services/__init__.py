"""
Services module for Context-Aware Research Assistant.

Core business logic for orchestration, evaluation, and response synthesis.
"""

from .orchestrator import Orchestrator
from .evaluator import Evaluator
from .synthesizer import Synthesizer
from .search_service import SearchService, get_search_service

__all__ = [
    "Orchestrator",
    "Evaluator",
    "Synthesizer",
    "SearchService",
    "get_search_service",
]
