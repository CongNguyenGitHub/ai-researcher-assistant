"""
Arxiv tool for retrieving academic papers and research.

Retrieves relevant papers from Arxiv API based on query topics.
"""

from typing import List, Optional
from datetime import datetime
import time

from models.query import Query
from models.context import ContextChunk, SourceType
from tools.base import ToolBase, ToolResult, ToolStatus
from logging_config import get_logger

logger = get_logger(__name__)


class ArxivTool(ToolBase):
    """
    Academic paper retrieval tool using Arxiv API.
    
    Retrieves peer-reviewed papers and preprints from Arxiv to provide
    authoritative, citable sources for research queries.
    """
    
    def __init__(
        self,
        timeout_seconds: float = 10.0,
        max_results: int = 3,
        sort_by: str = "relevance",
    ):
        """
        Initialize Arxiv tool.
        
        Args:
            timeout_seconds: API request timeout in seconds
            max_results: Maximum number of papers to retrieve
            sort_by: Sort results by 'relevance', 'date', or 'citation'
        """
        super().__init__(timeout_seconds=timeout_seconds)
        
        self.max_results = max_results
        self.sort_by = sort_by
        
        self._client = None
        
        logger.info(
            f"ArxivTool initialized: max_results={max_results}, "
            f"sort_by={sort_by}, timeout={timeout_seconds}s"
        )
    
    @property
    def source_type(self) -> SourceType:
        """Source type for this tool."""
        return SourceType.ACADEMIC
    
    @property
    def tool_name(self) -> str:
        """Human-readable tool name."""
        return "Arxiv (Academic Papers)"
    
    def _initialize_client(self):
        """Initialize Arxiv client (lazy loading)."""
        if self._client is not None:
            return
        
        try:
            import arxiv
            
            # Create client with timeout
            self._client = arxiv.Client(
                page_size=self.max_results,
                delay_seconds=0.5,
            )
            logger.info("Arxiv client initialized")
            
        except ImportError:
            logger.error("arxiv not installed, cannot initialize ArxivTool")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Arxiv client: {str(e)}")
            raise
    
    def _parse_query_for_arxiv(self, query_text: str) -> str:
        """
        Convert research query to Arxiv search query.
        
        Arxiv queries use specific syntax (AND, OR, ANDNOT operators).
        This converts natural language to Arxiv-compatible format.
        
        Args:
            query_text: Natural language query
            
        Returns:
            Arxiv search query
        """
        # Simple conversion: split on spaces and join with AND
        # In production, use NLP to extract key terms
        terms = [term for term in query_text.split() if len(term) > 3]
        
        if not terms:
            return query_text
        
        # Format for Arxiv (all terms must appear)
        arxiv_query = " AND ".join(f"all:{term}" for term in terms[:5])
        
        logger.debug(f"Converted query '{query_text}' to Arxiv: {arxiv_query}")
        return arxiv_query
    
    def execute(self, query: Query) -> ToolResult:
        """
        Search Arxiv for relevant papers.
        
        Args:
            query: The query to search for papers
            
        Returns:
            ToolResult with paper abstracts as context chunks
        """
        start_time = time.time()
        
        try:
            # Validate query
            if not self.validate_query(query):
                return self.create_error_result(
                    ToolStatus.ERROR,
                    (time.time() - start_time) * 1000,
                    "Invalid query"
                )
            
            # Initialize client
            self._initialize_client()
            
            # Convert query for Arxiv
            arxiv_query = self._parse_query_for_arxiv(query.text)
            
            logger.debug(f"Searching Arxiv with query: {arxiv_query}")
            
            chunks = []
            
            # Execute search
            search = arxiv.Search(
                query=arxiv_query,
                max_results=self.max_results,
                sort_by=arxiv.SortCriterion.Relevance if self.sort_by == "relevance"
                else arxiv.SortCriterion.SubmittedDate,
            )
            
            for paper in self._client.results(search):
                # Extract paper information
                title = paper.title
                authors = ", ".join([author.name for author in paper.authors[:3]])
                published = paper.published
                arxiv_id = paper.arxiv_id
                
                # Create abstract chunk
                abstract = paper.summary
                
                chunk = self.create_chunk(
                    text=abstract,
                    source_id=arxiv_id,
                    source_title=f"{title} ({authors})",
                    source_url=f"https://arxiv.org/abs/{arxiv_id}",
                    source_date=published,
                    semantic_relevance=0.9,  # Arxiv results are typically highly relevant
                    source_reputation=0.95,  # Arxiv papers are peer-reviewed/preprints
                    recency_score=self._calculate_recency(published),
                    metadata={
                        "tool": "arxiv",
                        "arxiv_id": arxiv_id,
                        "authors": authors,
                        "published_date": published.isoformat(),
                        "primary_category": paper.primary_category,
                    }
                )
                chunks.append(chunk)
            
            execution_time_ms = (time.time() - start_time) * 1000
            
            logger.info(
                f"Arxiv search complete: {len(chunks)} papers, "
                f"time={execution_time_ms:.0f}ms"
            )
            
            return self.create_success_result(chunks, execution_time_ms)
            
        except TimeoutError:
            return self.create_error_result(
                ToolStatus.TIMEOUT,
                (time.time() - start_time) * 1000,
                f"Arxiv search timed out after {self.timeout_seconds}s"
            )
        
        except Exception as e:
            logger.error(f"Arxiv tool error: {str(e)}", exc_info=True)
            return self.create_error_result(
                ToolStatus.ERROR,
                (time.time() - start_time) * 1000,
                f"Arxiv search failed: {str(e)}"
            )
    
    @staticmethod
    def _calculate_recency(published_date: datetime) -> float:
        """
        Calculate recency score based on publication date.
        
        Args:
            published_date: When the paper was published
            
        Returns:
            Recency score between 0 and 1
        """
        from datetime import datetime, timedelta
        
        now = datetime.now(published_date.tzinfo) if published_date.tzinfo else datetime.now()
        age_days = (now - published_date).days
        
        # Score: 1.0 if published today, decreases with age
        # After 10 years, score is 0.1
        if age_days <= 0:
            return 1.0
        elif age_days >= 3650:  # ~10 years
            return 0.1
        else:
            return max(0.1, 1.0 - (age_days / 3650) * 0.9)
