"""
Search integration service for discovering URLs based on queries.

Provides search functionality to find relevant URLs for web scraping.
"""

from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class SearchService:
    """
    Service for discovering URLs based on search queries.
    
    In production, this would integrate with a search API (Google, DuckDuckGo, etc).
    For MVP, provides a mock search capability that can be replaced with real API.
    """
    
    def __init__(self, use_mock: bool = True, search_api_key: Optional[str] = None):
        """
        Initialize search service.
        
        Args:
            use_mock: Use mock search (for MVP) or real API
            search_api_key: API key for real search service
        """
        self.use_mock = use_mock
        self.search_api_key = search_api_key
        logger.info(f"SearchService initialized: use_mock={use_mock}")
    
    def search(self, query: str, max_results: int = 5) -> List[str]:
        """
        Search for URLs matching the query.
        
        Args:
            query: Search query text
            max_results: Maximum number of URLs to return
            
        Returns:
            List of URLs relevant to the query
        """
        if self.use_mock:
            return self._mock_search(query, max_results)
        else:
            return self._real_search(query, max_results)
    
    def _mock_search(self, query: str, max_results: int) -> List[str]:
        """
        Mock search for MVP testing.
        
        Returns relevant URLs for common query types.
        
        Args:
            query: Search query
            max_results: Number of results
            
        Returns:
            List of mock URLs
        """
        # Map common query topics to relevant domain sources
        query_lower = query.lower()
        
        # Topic detection
        is_ai = any(x in query_lower for x in ["ai", "artificial intelligence", "machine learning"])
        is_health = any(x in query_lower for x in ["health", "medicine", "exercise", "diet"])
        is_tech = any(x in query_lower for x in ["technology", "software", "programming"])
        is_science = any(x in query_lower for x in ["science", "research", "study"])
        
        urls = []
        
        # Return topic-relevant mock URLs
        if is_ai:
            urls = [
                "https://www.deeplearning.ai",
                "https://www.anthropic.com",
                "https://openai.com/research",
                "https://www.stanford.edu/ai",
                "https://www.mit.edu/ai-research"
            ]
        elif is_health:
            urls = [
                "https://www.healthline.com",
                "https://www.mayoclinic.org",
                "https://www.cdc.gov",
                "https://www.who.int",
                "https://www.nih.gov"
            ]
        elif is_tech:
            urls = [
                "https://github.com",
                "https://stackoverflow.com",
                "https://dev.to",
                "https://medium.com/tag/technology",
                "https://www.wired.com/tag/technology"
            ]
        elif is_science:
            urls = [
                "https://www.nature.com",
                "https://www.science.org",
                "https://www.sciencedaily.com",
                "https://phys.org",
                "https://www.researchsquare.com"
            ]
        else:
            # Generic news and reference
            urls = [
                "https://www.wikipedia.org",
                "https://www.bbc.com/news",
                "https://www.reuters.com",
                "https://www.apnews.com",
                "https://www.theguardian.com"
            ]
        
        logger.debug(f"Mock search for '{query}' returned {len(urls)} URLs")
        return urls[:max_results]
    
    def _real_search(self, query: str, max_results: int) -> List[str]:
        """
        Real search using external API.
        
        Implementation placeholder for production.
        In production, integrate with:
        - Google Custom Search API
        - DuckDuckGo API
        - Bing Search API
        - Or similar service
        
        Args:
            query: Search query
            max_results: Number of results
            
        Returns:
            List of URLs from API
        """
        # TODO: Implement real search API integration
        logger.warning("Real search API not yet implemented, falling back to mock")
        return self._mock_search(query, max_results)
    
    @staticmethod
    def extract_domain(url: str) -> str:
        """
        Extract domain from URL.
        
        Args:
            url: Full URL
            
        Returns:
            Domain name
        """
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc or parsed.path
        except Exception:
            return url


# Singleton instance
_search_service: Optional[SearchService] = None


def get_search_service(use_mock: bool = True) -> SearchService:
    """
    Get or create search service singleton.
    
    Args:
        use_mock: Use mock search for MVP
        
    Returns:
        SearchService instance
    """
    global _search_service
    
    if _search_service is None:
        _search_service = SearchService(use_mock=use_mock)
    
    return _search_service
