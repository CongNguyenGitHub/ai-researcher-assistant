"""
Tools module for Context-Aware Research Assistant.

Retrieval tools for accessing context from multiple sources:
- RAGTool: Document retrieval from Milvus
- FirecrawlTool: Web scraping with Firecrawl
- ArxivTool: Academic paper retrieval
- MemoryTool: Conversation history from Zep
"""

from .base import ToolBase, ToolResult, ToolStatus
from .rag_tool import RAGTool
from .firecrawl_tool import FirecrawlTool
from .arxiv_tool import ArxivTool
from .memory_tool import MemoryTool

__all__ = [
    # Base classes
    "ToolBase",
    "ToolResult",
    "ToolStatus",
    # Concrete tools
    "RAGTool",
    "FirecrawlTool",
    "ArxivTool",
    "MemoryTool",
]
