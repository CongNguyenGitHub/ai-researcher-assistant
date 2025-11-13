# Tool Contracts: Context-Aware Research Assistant

**Version**: 1.0  
**Date**: November 13, 2025  
**Purpose**: Define interfaces and contracts for all retrieval tools

---

## Tool Base Interface

```python
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime

class ToolError(Exception):
    """Base exception for tool errors - never raised, logged instead"""
    pass

class ContextChunk(BaseModel):
    """Standardized output for all tools"""
    id: str
    source_type: str  # "rag", "web", "arxiv", "memory"
    text: str
    semantic_relevance: float  # 0-1, tool provides raw score
    source_id: str
    source_title: Optional[str]
    source_url: Optional[str]
    source_date: Optional[datetime]
    metadata: Dict[str, Any]

class Tool(ABC):
    """All tools implement this contract"""
    
    name: str
    description: str
    timeout_seconds: float = 7.0
    
    @abstractmethod
    async def execute(
        self,
        query: str,
        **kwargs
    ) -> List[ContextChunk]:
        """
        Execute the tool and return context chunks.
        
        Contract:
        - MUST complete within timeout_seconds
        - MUST return empty list on ANY error (no exceptions)
        - MUST log errors for debugging
        - MUST return List[ContextChunk] objects
        - MUST NOT hallucinate data
        - MUST include source attribution
        - MUST NOT include internal implementation details
        
        Args:
            query: User's research question
            **kwargs: Tool-specific parameters
            
        Returns:
            List of ContextChunk objects (may be empty)
        """
        raise NotImplementedError
    
    async def _safe_execute(self, *args, **kwargs) -> List[ContextChunk]:
        """Wrapper that enforces error handling"""
        try:
            return await asyncio.wait_for(
                self.execute(*args, **kwargs),
                timeout=self.timeout_seconds
            )
        except asyncio.TimeoutError:
            logger.warning(f"{self.name}: timeout after {self.timeout_seconds}s")
            return []
        except Exception as e:
            logger.error(f"{self.name}: {e}")
            return []
```

---

## 1. RAG Tool (Milvus Vector Search)

**Purpose**: Query internal document knowledge base

**Implementation**: `src/tools/rag_tool.py`

### Input Contract

```python
class RAGToolInput(BaseModel):
    query: str  # User query (required)
    top_k: int = 5  # Number of chunks to return
    min_relevance: float = 0.5  # Minimum similarity threshold
    filter_source_type: Optional[List[str]] = None  # Restrict to certain document types
    filter_date_range: Optional[Tuple[datetime, datetime]] = None  # Date filter
```

### Output Contract

```python
class RAGToolOutput(BaseModel):
    chunks: List[ContextChunk]
    total_found: int  # Total matches before top-k
    execution_time_ms: float
    milvus_status: str  # "success", "partial", "timeout", "error"
    
class RAGContextChunk(ContextChunk):
    # RAG-specific metadata
    metadata: RAGMetadata

class RAGMetadata(BaseModel):
    document_id: str
    document_title: str
    collection_name: str
    chunk_index: int  # Position in document
    embedding_model: str  # Model used for embedding
    similarity_score: float  # Raw cosine similarity
    document_total_chunks: int
```

### API Specification

**Endpoint**: Internal async function (not HTTP)

```python
async def rag_search(
    query: str,
    top_k: int = 5,
    min_relevance: float = 0.5,
    user_id: Optional[str] = None,
    **kwargs
) -> RAGToolOutput:
    """
    Search Milvus vector database for relevant document chunks.
    
    Process:
    1. Embed query using configured embedding model
    2. Search Milvus collection for nearest vectors
    3. Filter by min_relevance threshold
    4. Format results as ContextChunk objects
    5. Return top_k results
    
    Error Handling:
    - Connection error: Log and return empty list
    - Timeout: Log and return partial results if available
    - Invalid query: Log and return empty list
    - Index not found: Log and return empty list
    """
```

### Milvus Configuration

```python
MILVUS_CONFIG = {
    "host": os.getenv("MILVUS_HOST", "localhost"),
    "port": os.getenv("MILVUS_PORT", 19530),
    "collection_name": "document_chunks",
    "embedding_model": "text-embedding-3-small",
    "embedding_dimension": 1536,
    "metric_type": "L2",  # Euclidean distance
    "search_params": {
        "metric_type": "L2",
        "params": {"nprobe": 10}
    },
    "timeout": 7.0
}
```

### Example Usage

```python
tool = RAGTool()
chunks = await tool.execute(
    query="What are the benefits of Python?",
    top_k=5,
    min_relevance=0.5
)
# Returns: List[ContextChunk] with up to 5 items
```

---

## 2. Firecrawl Tool (Web Search)

**Purpose**: Retrieve real-time web context for queries

**Implementation**: `src/tools/firecrawl_tool.py`

### Input Contract

```python
class FirecrawlToolInput(BaseModel):
    query: str  # Search query (required)
    num_results: int = 5  # Number of web results to fetch
    languages: Optional[List[str]] = ["en"]  # Language filters
    exclude_domains: Optional[List[str]] = None  # Domains to skip
    include_domains: Optional[List[str]] = None  # Only from these domains
    search_filters: Optional[Dict[str, Any]] = None  # Firecrawl API filters
```

### Output Contract

```python
class FirecrawlToolOutput(BaseModel):
    chunks: List[ContextChunk]
    total_found: int  # Total web results found
    execution_time_ms: float
    firecrawl_status: str  # "success", "partial", "timeout", "error"
    
class WebContextChunk(ContextChunk):
    metadata: WebMetadata

class WebMetadata(BaseModel):
    domain: str
    page_url: str
    page_title: str
    fetch_timestamp: datetime
    page_rank_estimate: Optional[float]  # Estimated importance
    language: str
    content_type: str  # "article", "news", "documentation", etc.
```

### API Specification

```python
async def firecrawl_search(
    query: str,
    num_results: int = 5,
    include_domains: Optional[List[str]] = None,
    exclude_domains: Optional[List[str]] = None,
    **kwargs
) -> FirecrawlToolOutput:
    """
    Search web using Firecrawl API and extract content.
    
    Process:
    1. Execute web search via Firecrawl
    2. For each result, fetch and parse page
    3. Extract main content text
    4. Break into chunks if necessary
    5. Calculate relevance scores
    6. Return top results as ContextChunk objects
    
    Error Handling:
    - API key missing/invalid: Log and return empty
    - Rate limit exceeded: Log and return partial results
    - Network error: Log and return partial results
    - Parse error on page: Skip page, continue with others
    """
```

### Firecrawl Configuration

```python
FIRECRAWL_CONFIG = {
    "api_key": os.getenv("FIRECRAWL_API_KEY"),
    "api_url": "https://api.firecrawl.dev/v0",
    "search_timeout": 7.0,
    "parse_timeout": 5.0,  # Per-page timeout
    "default_num_results": 5,
    "exclude_patterns": [
        r"^https://www\.reddit\.com",  # Reddit often low quality
        r"^https://twitter\.com",  # Twitter limited context
    ]
}
```

### Example Usage

```python
tool = FirecrawlTool()
chunks = await tool.execute(
    query="latest developments in AI safety",
    num_results=5,
    include_domains=["arxiv.org", "openai.com", "deepmind.google"]
)
# Returns: List[ContextChunk] from web pages
```

---

## 3. Arxiv Tool (Academic Papers)

**Purpose**: Retrieve peer-reviewed academic papers and research

**Implementation**: `src/tools/arxiv_tool.py`

### Input Contract

```python
class ArxivToolInput(BaseModel):
    query: str  # Search query (required)
    num_results: int = 5  # Number of papers to fetch
    sort_by: str = "relevance"  # "relevance", "date" (recent first)
    categories: Optional[List[str]] = None  # arXiv categories (cs.AI, cs.LG, etc.)
    date_from: Optional[datetime] = None  # Only papers after this date
    date_to: Optional[datetime] = None  # Only papers before this date
```

### Output Contract

```python
class ArxivToolOutput(BaseModel):
    chunks: List[ContextChunk]
    total_found: int  # Total papers matching query
    execution_time_ms: float
    arxiv_status: str  # "success", "partial", "timeout", "error"
    
class AcademicContextChunk(ContextChunk):
    metadata: AcademicMetadata

class AcademicMetadata(BaseModel):
    paper_id: str
    paper_title: str
    authors: List[str]
    publication_date: datetime
    arxiv_categories: List[str]
    arxiv_url: str
    pdf_url: str
    abstract: str
    doi: Optional[str]
    citation_count: Optional[int]
```

### API Specification

```python
async def arxiv_search(
    query: str,
    num_results: int = 5,
    sort_by: str = "relevance",
    categories: Optional[List[str]] = None,
    **kwargs
) -> ArxivToolOutput:
    """
    Search arXiv for academic papers.
    
    Process:
    1. Query arXiv API with search parameters
    2. Fetch paper metadata and abstracts
    3. For selected papers, fetch full papers (optional)
    4. Extract summary or key sections
    5. Format as ContextChunk objects
    6. Return top results
    
    Error Handling:
    - API unavailable: Log and return empty
    - Invalid query: Log and return empty
    - Rate limit: Log and return partial results
    - PDF fetch failure: Use abstract instead, continue
    """
```

### arXiv Configuration

```python
ARXIV_CONFIG = {
    "base_url": "http://export.arxiv.org/api/query",
    "search_timeout": 7.0,
    "max_results_per_query": 10,
    "sort_order": "relevance",  # Can be "relevance" or "lastUpdatedDate"
    "categories_of_interest": [
        "cs.AI",  # Artificial Intelligence
        "cs.LG",  # Machine Learning
        "cs.NE",  # Neural and Evolutionary Computing
        "stat.ML",  # Statistics - Machine Learning
    ]
}
```

### Example Usage

```python
tool = ArxivTool()
chunks = await tool.execute(
    query="transformer models attention mechanism",
    num_results=5,
    sort_by="date"  # Most recent papers first
)
# Returns: List[ContextChunk] with paper abstracts/summaries
```

---

## 4. Memory Tool (Zep Memory)

**Purpose**: Retrieve relevant conversation history and entity knowledge

**Implementation**: `src/tools/memory_tool.py`

### Input Contract

```python
class MemoryToolInput(BaseModel):
    query: str  # Current query (required)
    session_id: str  # Current session (required)
    user_id: str  # Current user (required)
    num_results: int = 3  # Number of prior interactions to retrieve
    entity_relevance: bool = True  # Include related entities?
    time_window: Optional[Tuple[datetime, datetime]] = None  # Limit to date range
```

### Output Contract

```python
class MemoryToolOutput(BaseModel):
    chunks: List[ContextChunk]
    entities_found: List[str]  # Entity IDs relevant to query
    execution_time_ms: float
    zep_status: str  # "success", "partial", "timeout", "error"
    
class MemoryContextChunk(ContextChunk):
    metadata: MemoryMetadata

class MemoryMetadata(BaseModel):
    prior_query: str  # The query that generated this context
    prior_response_summary: str  # Summary of response
    session_id: str
    interaction_timestamp: datetime
    relevance_to_current: str  # Why it's relevant
    entity_references: List[str]  # Entities mentioned
```

### API Specification

```python
async def memory_recall(
    query: str,
    session_id: str,
    user_id: str,
    num_results: int = 3,
    **kwargs
) -> MemoryToolOutput:
    """
    Retrieve relevant conversation history and entity knowledge from Zep.
    
    Process:
    1. Query Zep for similar prior queries in this session
    2. Fetch responses to those queries
    3. Extract entity mentions relevant to current query
    4. Retrieve entity relationships and context
    5. Format as ContextChunk objects
    6. Return most relevant items
    
    Error Handling:
    - Zep unavailable: Log and return empty (non-critical)
    - Invalid session_id: Log and return empty
    - Timeout: Return partial results if available
    """
```

### Zep Configuration

```python
ZEP_CONFIG = {
    "api_url": os.getenv("ZEP_API_URL", "http://localhost:8000"),
    "api_key": os.getenv("ZEP_API_KEY"),
    "request_timeout": 7.0,
    "max_history_size": 20,  # Keep last 20 messages per session
}
```

### Example Usage

```python
tool = MemoryTool()
chunks = await tool.execute(
    query="What did we discuss about Python before?",
    session_id="session_abc123",
    user_id="user_xyz"
)
# Returns: List[ContextChunk] with relevant prior context
```

---

## Tool Execution Framework

### Timeout and Resilience

```python
class ToolExecutor:
    """Manages tool execution with timeouts and error handling"""
    
    TOOL_TIMEOUT = 7.0  # Each tool gets 7 seconds
    TOTAL_TIMEOUT = 30.0  # All tools combined must complete in 30 seconds
    
    async def execute_all_tools(
        self,
        query: str,
        tools: List[Tool],
        **kwargs
    ) -> Dict[str, List[ContextChunk]]:
        """Execute all tools in parallel with timeout"""
        
        results = await asyncio.gather(
            *[
                asyncio.wait_for(
                    tool._safe_execute(query, **kwargs),
                    timeout=self.TOOL_TIMEOUT
                )
                for tool in tools
            ],
            return_exceptions=True
        )
        
        # Handle results and exceptions
        tool_results = {}
        for tool, result in zip(tools, results):
            if isinstance(result, Exception):
                logger.error(f"{tool.name} raised: {result}")
                tool_results[tool.name] = []
            else:
                tool_results[tool.name] = result
        
        return tool_results
```

### Caching (Optional)

```python
class ToolCache:
    """Optional caching layer for expensive tools"""
    
    def __init__(self, ttl_seconds: int = 3600):
        self.cache = {}
        self.ttl = ttl_seconds
    
    def get_cache_key(self, tool_name: str, query: str) -> str:
        return f"{tool_name}:{hash(query)}"
    
    def is_cached(self, key: str) -> bool:
        if key not in self.cache:
            return False
        
        timestamp, _ = self.cache[key]
        if time.time() - timestamp > self.ttl:
            del self.cache[key]
            return False
        
        return True
    
    def get(self, key: str):
        return self.cache[key][1] if self.is_cached(key) else None
    
    def set(self, key: str, value):
        self.cache[key] = (time.time(), value)
```

---

## Testing Contracts

Each tool MUST pass these tests:

```python
@pytest.mark.asyncio
async def test_tool_returns_context_chunks():
    """Tool must return List[ContextChunk]"""
    result = await tool.execute("test query")
    assert isinstance(result, list)
    assert all(isinstance(c, ContextChunk) for c in result)

@pytest.mark.asyncio
async def test_tool_respects_timeout():
    """Tool must complete within timeout"""
    start = time.time()
    result = await tool._safe_execute("test query")
    elapsed = time.time() - start
    assert elapsed < tool.timeout_seconds + 1  # 1s buffer

@pytest.mark.asyncio
async def test_tool_handles_errors():
    """Tool must never raise exception"""
    with patch.object(tool, 'execute', side_effect=Exception("test")):
        result = await tool._safe_execute("test query")
        assert result == []  # Returns empty, no exception

@pytest.mark.asyncio
async def test_tool_includes_source_attribution():
    """All chunks must include source info"""
    result = await tool.execute("test query")
    for chunk in result:
        assert chunk.source_id is not None
        assert chunk.source_type is not None
```

---

End of Tool Contracts. Ready for implementation.
