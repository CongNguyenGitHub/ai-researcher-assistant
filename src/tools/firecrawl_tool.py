"""
Firecrawl tool for web scraping and content extraction.

Retrieves and processes content from web URLs using Firecrawl API.
"""

from typing import List, Optional
from datetime import datetime
import time

from models.query import Query
from models.context import ContextChunk, SourceType
from tools.base import ToolBase, ToolResult, ToolStatus
from logging_config import get_logger

logger = get_logger(__name__)


class FirecrawlTool(ToolBase):
    """
    Web scraping and content extraction tool using Firecrawl API.
    
    Fetches and processes web content to provide recent, up-to-date
    information for research queries.
    """
    
    def __init__(
        self,
        api_key: str,
        timeout_seconds: float = 10.0,
        max_urls: int = 3,
        chunk_size: int = 1024,
    ):
        """
        Initialize Firecrawl tool.
        
        Args:
            api_key: Firecrawl API key
            timeout_seconds: Request timeout in seconds
            max_urls: Maximum number of URLs to fetch
            chunk_size: Size of text chunks to create from content
        """
        super().__init__(timeout_seconds=timeout_seconds)
        
        self.api_key = api_key
        self.max_urls = max_urls
        self.chunk_size = chunk_size
        
        self._client = None
        
        logger.info(
            f"FirecrawlTool initialized: max_urls={max_urls}, "
            f"chunk_size={chunk_size}, timeout={timeout_seconds}s"
        )
    
    @property
    def source_type(self) -> SourceType:
        """Source type for this tool."""
        return SourceType.WEB
    
    @property
    def tool_name(self) -> str:
        """Human-readable tool name."""
        return "Firecrawl (Web Scraping)"
    
    def _initialize_client(self):
        """Initialize Firecrawl client (lazy loading)."""
        if self._client is not None:
            return
        
        try:
            from firecrawl import FirecrawlApp
            
            self._client = FirecrawlApp(api_key=self.api_key)
            logger.info("Firecrawl client initialized")
            
        except ImportError:
            logger.error("firecrawl-python not installed, cannot initialize FirecrawlTool")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Firecrawl client: {str(e)}")
            raise
    
    def _extract_search_urls(self, query_text: str) -> List[str]:
        """
        Generate search URLs for the query.
        
        In a real implementation, this would use Google Search API or similar.
        For now, returns a placeholder format that could be filled by a search service.
        
        Args:
            query_text: The search query
            
        Returns:
            List of URLs to fetch
        """
        # Placeholder: In production, use a search API
        # For now, return empty list (would be populated by search service)
        logger.debug(f"URL extraction requested for: {query_text}")
        return []
    
    def execute(self, query: Query) -> ToolResult:
        """
        Fetch and process web content for the query.
        
        Args:
            query: The query to retrieve web content for
            
        Returns:
            ToolResult with web-sourced context chunks
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
            
            # Get URLs to fetch (from search service)
            urls = self._extract_search_urls(query.text)
            
            if not urls:
                logger.warning("No URLs found for query, returning empty result")
                return self.create_success_result([], (time.time() - start_time) * 1000)
            
            # Limit to max_urls
            urls = urls[:self.max_urls]
            
            chunks = []
            
            for url in urls:
                try:
                    logger.debug(f"Fetching content from: {url}")
                    
                    # Fetch and scrape the URL
                    response = self._client.scrape_url(
                        url,
                        params={
                            "pageOptions": {
                                "onlyMainContent": True,
                            }
                        }
                    )
                    
                    if not response or response.get("success") is False:
                        logger.warning(f"Failed to fetch {url}")
                        continue
                    
                    content = response.get("markdown", "")
                    title = response.get("metadata", {}).get("title", url)
                    
                    if not content:
                        logger.warning(f"No content extracted from {url}")
                        continue
                    
                    # Create chunk from web content
                    chunk = self.create_chunk(
                        text=content[:self.chunk_size],
                        source_id=url,
                        source_title=title,
                        source_url=url,
                        source_date=datetime.now(),
                        semantic_relevance=0.7,  # Web results have moderate relevance
                        source_reputation=0.6,  # Variable web source reputation
                        recency_score=0.9,  # Web results are typically recent
                        metadata={
                            "tool": "firecrawl",
                            "full_content_length": len(content),
                            "scraped_at": datetime.now().isoformat(),
                        }
                    )
                    chunks.append(chunk)
                    
                except Exception as e:
                    logger.warning(f"Error processing {url}: {str(e)}")
                    continue
            
            execution_time_ms = (time.time() - start_time) * 1000
            
            logger.info(
                f"Firecrawl retrieval complete: {len(chunks)} chunks from {len(urls)} URLs, "
                f"time={execution_time_ms:.0f}ms"
            )
            
            return self.create_success_result(chunks, execution_time_ms)
            
        except TimeoutError:
            return self.create_error_result(
                ToolStatus.TIMEOUT,
                (time.time() - start_time) * 1000,
                f"Web scraping timed out after {self.timeout_seconds}s"
            )
        
        except Exception as e:
            logger.error(f"Firecrawl tool error: {str(e)}", exc_info=True)
            return self.create_error_result(
                ToolStatus.ERROR,
                (time.time() - start_time) * 1000,
                f"Web scraping failed: {str(e)}"
            )
