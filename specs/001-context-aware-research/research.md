# Research & Design Decisions: Context-Aware Research Assistant

**Date**: November 13, 2025  
**Status**: Complete  
**Purpose**: Resolve technical unknowns and document design decisions for implementation

---

## 1. CrewAI Best Practices for Multi-Agent Orchestration

### Decision: Sequential Agent Pipeline with Parallel Tool Execution

**What we chose**: Use crewAI with a sequential workflow where agents run one after another (Query → Parallel Retrieval → Evaluation → Synthesis → Memory Update), but parallel tool execution occurs within the retrieval phase.

**Rationale**:
- **Sequential agents**: Ensures clean data flow and prevents race conditions in memory updates
- **Parallel tools**: Meets <30s response requirement by querying all sources simultaneously
- **Clear responsibility**: Each agent has single responsibility (Evaluator filters, Synthesizer synthesizes)
- **Simplicity**: Sequential workflow is easier to debug and reason about than complex async patterns

**Alternatives considered**:
- Fully parallel agents: Would be faster but risks context consistency issues and harder to implement
- Pure sequential: Violates <30s response time goal
- Pipeline parallelism: More complex, limited benefit for 4-phase workflow

### Implementation Pattern

```python
# CrewAI workflow structure
crew = Crew(
    agents=[
        Agent(name="Retriever", tools=[rag_tool, web_tool, arxiv_tool, memory_tool]),
        Agent(name="Evaluator", tools=[evaluation_tool]),
        Agent(name="Synthesizer", tools=[synthesis_tool])
    ],
    tasks=[
        Task(description="Retrieve context", agent=retriever),
        Task(description="Evaluate and filter", agent=evaluator),
        Task(description="Synthesize response", agent=synthesizer)
    ]
)
```

### Error Handling in crewAI

- Use task callbacks for error detection
- Implement retry logic at tool level (each source handles its own retries)
- Fallback: If critical agent fails, return partial result with available context
- Log all agent decisions for debugging

---

## 2. Milvus Vector Database Integration

### Decision: Asynchronous Connection Pooling with Batch Queries

**What we chose**: Use `pymilvus` library with connection pooling, batch query operations for semantic similarity search, and automatic reconnection on failure.

**Rationale**:
- **Connection pooling**: Reduces overhead of establishing connections per query
- **Batch operations**: Milvus optimized for batch similarity search (multiple vector comparisons)
- **Async support**: Python 3.10+ asyncio allows non-blocking queries
- **Resilient**: pymilvus includes automatic retry and reconnection logic

**Alternatives considered**:
- Sync connections: Simpler but blocks other parallel operations
- Document databases (Postgres with pgvector): Added complexity, Milvus is purpose-built for vectors
- In-memory embeddings: Doesn't scale beyond laptop-size datasets

### Implementation Details

**Milvus Schema**:
```json
{
  "collection": "document_chunks",
  "fields": [
    {"name": "id", "type": "Int64", "is_primary": true},
    {"name": "document_id", "type": "VarChar"},
    {"name": "chunk_text", "type": "VarChar"},
    {"name": "embedding", "type": "FloatVector", "dim": 1536},
    {"name": "metadata", "type": "JSON"},
    {"name": "source", "type": "VarChar"}
  ],
  "indexes": [
    {"field": "embedding", "index_type": "IVF_FLAT"}
  ]
}
```

**Chunking Strategy**:
- Sentence-level chunks with overlap for context preservation
- Maximum 512 tokens per chunk (fits common embedding models)
- Metadata includes source document, position, timestamp

**Query Pattern**:
```python
async def query_rag(query_text: str, top_k: int = 5):
    # 1. Embed query text
    query_embedding = await embedder.embed(query_text)
    
    # 2. Search Milvus for similar vectors
    results = collection.search(
        data=[query_embedding],
        anns_field="embedding",
        param={"metric_type": "L2", "params": {"nprobe": 10}},
        limit=top_k,
        output_fields=["chunk_text", "metadata", "source"]
    )
    
    # 3. Return context chunks with scores
    return format_context_chunks(results)
```

**Embedding Model Choice**: Use OpenAI's `text-embedding-3-small` (1536 dimensions) as default for balance of quality and cost. Make configurable for flexibility.

**Failure Handling**:
- Connection failures: Automatic reconnection with exponential backoff
- Query timeout: Return empty context chunk set rather than failing
- Index not found: Gracefully inform user that RAG source is unavailable

---

## 3. Context Filtering and Quality Metrics

### Decision: Multi-Factor Scoring with Configurable Thresholds

**What we chose**: Combine multiple quality signals (source reputation, recency, semantic relevance, redundancy) into a composite score. Filter context below configurable threshold (default 0.6/1.0).

**Rationale**:
- **Multi-factor**: Single metric (e.g., recency alone) produces poor results
- **Configurable**: Allows tuning for different query types (research vs current events)
- **Transparent**: Users understand why content was filtered
- **Implementable**: Avoids complex ML-based filtering that's hard to maintain

**Alternatives considered**:
- ML-based classifier: Better accuracy but harder to explain and maintain
- Simple recency cutoff: Biased toward recent but low-quality sources
- No filtering: Results in poor answer quality (confirmed by success criteria)

### Quality Metrics

1. **Source Reputation** (0-1):
   - RAG: 0.9 (curated documents)
   - Academic (Arxiv): 0.85 (peer-reviewed)
   - Web (Firecrawl): 0.7 (varies widely)
   - Memory (Zep): 0.8 (user-specific history)

2. **Recency Score** (0-1):
   - Based on document age: Linear decay from 1.0 (today) to 0.2 (>2 years)
   - Configurable for different domains

3. **Semantic Relevance** (0-1):
   - Similarity score from embedding search
   - Milvus returns cosine similarity: maps directly to relevance

4. **Redundancy Penalty** (0-1):
   - Detect near-duplicates: If content >80% similar to earlier chunk, multiply score by 0.5
   - Use Jaccard similarity on token sets

### Composite Score Calculation

```python
quality_score = (
    0.3 * source_reputation +
    0.2 * recency_score +
    0.4 * semantic_relevance +
    0.1 * (1 - redundancy_penalty)
)

# Filter threshold: Keep only if quality_score >= 0.6
```

### Evaluator Agent Task

The Evaluator agent will:
1. Calculate quality score for each context chunk
2. Identify and consolidate redundant chunks
3. Detect contradictions between sources
4. Produce filtering rationale for each removed item
5. Output ranked, deduplicated context ready for synthesis

---

## 4. Handling Contradictory Information

### Decision: Multi-Perspective Synthesis with Confidence Intervals

**What we chose**: When sources contradict, the Synthesizer agent presents all perspectives with source attribution and confidence levels, allowing users to see competing viewpoints.

**Rationale**:
- **Transparency**: Users deserve to know when experts disagree
- **Safety**: Choosing one source arbitrarily could spread misinformation
- **Flexibility**: Users can apply their own judgment
- **Honest**: Reflects reality that knowledge often has competing theories

**Alternatives considered**:
- Choose highest-confidence source: Risks missing important context
- Merge contradictions: Creates meaningless middle-ground answers
- Flag contradiction and refuse to answer: Reduces utility

### Implementation

```python
# Synthesizer approach for contradictions
if contradiction_detected(context_chunks):
    # Structure response as multiple perspectives
    response = {
        "query": original_query,
        "perspectives": [
            {
                "viewpoint": "Perspective A (Source: X, Y)",
                "summary": "...",
                "confidence": 0.85,
                "sources": ["source_id_1", "source_id_2"]
            },
            {
                "viewpoint": "Perspective B (Source: Z)",
                "summary": "...",
                "confidence": 0.72,
                "sources": ["source_id_3"]
            }
        ],
        "note": "Multiple perspectives exist on this topic. See sources for details."
    }
else:
    # Normal unified response
    response = {
        "answer": "...",
        "confidence": 0.88,
        "sources": [...]
    }
```

**Evaluator Detection**: Identify contradictions by:
- Checking for semantic antonyms in key claims
- Comparing numerical assertions (e.g., "X is 100 vs X is 200")
- Flagging explicitly contradictory statements for synthesis

---

## 5. Structured Response Format Design

### Decision: JSON Schema with Source Attributions and Confidence Scores

**What we chose**: JSON response format with complete source citations, per-section confidence, and structured metadata.

**Rationale**:
- **Machine-readable**: Enables further processing, UI rendering
- **Reproducible**: Citations allow verification
- **Transparent**: Users see confidence levels and sources
- **Extensible**: Easy to add new metadata fields

### Response Schema

```json
{
  "query": "What is the capital of France?",
  "response": {
    "main_answer": "Paris is the capital of France.",
    "sections": [
      {
        "heading": "Historical Background",
        "content": "Paris has been the capital since the late 12th century...",
        "confidence": 0.95,
        "sources": ["source_id_1", "source_id_2"]
      },
      {
        "heading": "Geographic Location",
        "content": "Paris is located in north-central France...",
        "confidence": 0.98,
        "sources": ["source_id_3"]
      }
    ]
  },
  "metadata": {
    "overall_confidence": 0.93,
    "response_time_ms": 18500,
    "sources_consulted": 4,
    "sources": [
      {
        "id": "source_id_1",
        "type": "rag",
        "title": "French History Encyclopedia",
        "url": "internal:///docs/france",
        "relevance": 0.92
      },
      {
        "id": "source_id_2",
        "type": "academic",
        "title": "Journal of European Studies",
        "url": "https://arxiv.org/...",
        "relevance": 0.87
      }
    ],
    "session_id": "session_abc123",
    "timestamp": "2025-11-13T14:30:45Z"
  }
}
```

### Confidence Calculation

- **Per-section**: Average of source confidences weighted by relevance
- **Overall**: Harmonic mean of all section confidences (penalizes low-confidence sections)
- **Range**: 0-1, where 0.8+ is "high confidence"

---

## 6. Zep Memory Integration Patterns

### Decision: Dual-Mode Storage (Conversation Timeline + Entity Graph)

**What we chose**: Use Zep for both sequential conversation history (for context) and entity relationship graphs (for knowledge).

**Rationale**:
- **Conversation history**: Enables multi-turn coherence
- **Entity graph**: Tracks important concepts mentioned across interactions
- **Dual model**: Balances full history (expensive) with key concepts (cheap)

**Alternatives considered**:
- Full conversation replay: Storage/retrieval expensive at scale
- Entity graph only: Loses conversational context
- Separate systems: Adds operational complexity

### Memory Schema

**Conversation History**:
```python
{
  "session_id": "session_abc",
  "user_id": "user_123",
  "messages": [
    {
      "role": "user",
      "content": "What are the benefits of Python?",
      "timestamp": "2025-11-13T14:00:00Z"
    },
    {
      "role": "assistant",
      "content": "Python offers: 1) Readability... (full response)",
      "metadata": {
        "sources": ["source_1", "source_2"],
        "confidence": 0.91
      },
      "timestamp": "2025-11-13T14:00:18Z"
    }
  ],
  "user_preferences": {
    "response_format": "detailed",
    "preferred_sources": ["academic", "rag"],
    "information_depth": "comprehensive"
  }
}
```

**Entity Graph**:
```python
{
  "session_id": "session_abc",
  "entities": [
    {
      "id": "entity_python",
      "name": "Python",
      "type": "programming_language",
      "mentioned_in": [
        {"query": "What are the benefits?", "context": "positive"},
        {"query": "Performance comparison?", "context": "comparison"}
      ]
    },
    {
      "id": "entity_java",
      "name": "Java",
      "type": "programming_language",
      "mentioned_in": [...]
    }
  ],
  "relationships": [
    {
      "source": "entity_python",
      "target": "entity_java",
      "type": "compared_with",
      "context": "both used for backend development"
    }
  ]
}
```

### Retrieval Patterns

1. **New query arrives**:
   - Fetch conversation history for context
   - Identify entities in new query
   - Retrieve related entity information from graph

2. **Context enrichment**:
   - Include prior queries about same entities
   - Add user preferences for personalization
   - Reference previous contradictions (if any)

3. **Memory update**:
   - Append new query and response to history
   - Extract new entities and relationships
   - Update user preferences if inferred

### Zep Configuration

```python
client = ZepClient(
    api_url=os.getenv("ZEP_API_URL"),
    api_key=os.getenv("ZEP_API_KEY")
)

# Create/retrieve session
session = client.memory.get_or_create_session(
    session_id=session_id,
    user_id=user_id,
    metadata={"source": "research_assistant"}
)
```

---

## 7. Error Resilience and Graceful Degradation

### Decision: Tool-Level Fault Tolerance with Fallback Synthesis

**What we chose**: Each tool handles its own errors and returns empty result set on failure. Orchestrator continues with available sources. Synthesizer generates best-possible response with available context.

**Rationale**:
- **Resilience**: System continues even if one source fails
- **User experience**: Partial answer better than no answer
- **Debuggability**: Tool-level errors isolated and clear
- **Simplicity**: Avoids complex circuit breaker patterns for MVP

**Alternatives considered**:
- Circuit breakers: Adds complexity for MVP
- Retries with exponential backoff: Increases latency
- Hard failures: Violates user expectation of robust search

### Tool Failure Handling

```python
class RAGTool(Tool):
    async def execute(self, query: str) -> List[ContextChunk]:
        try:
            # Query with timeout
            results = await asyncio.wait_for(
                self.milvus_query(query),
                timeout=7.0  # 7s timeout per source
            )
            return results
        except ConnectionError:
            logger.warning("RAG/Milvus connection failed, returning empty")
            return []  # Empty, not error
        except TimeoutError:
            logger.warning("RAG/Milvus query timeout, returning empty")
            return []
        except Exception as e:
            logger.error(f"RAG tool unexpected error: {e}")
            return []

# Same pattern for Firecrawl, Arxiv, Zep tools
```

### Orchestrator Handling

```python
async def parallel_retrieval(query: str) -> AggregatedContext:
    results = await asyncio.gather(
        rag_tool.execute(query),
        firecrawl_tool.execute(query),
        arxiv_tool.execute(query),
        memory_tool.execute(query),
        return_exceptions=False  # Exceptions already handled by tools
    )
    
    # Results may contain empty lists for failed sources
    aggregated = AggregatedContext(chunks=flatten(results))
    
    if not aggregated.chunks:
        # All sources failed - return helpful error response
        return AggregatedContext(
            chunks=[],
            error="No context available from any source"
        )
    
    return aggregated
```

### Synthesizer Degradation

```python
def synthesize_response(context: FilteredContext) -> FinalResponse:
    if not context.chunks:
        return FinalResponse(
            answer="Unable to find relevant information. Try rephrasing your query.",
            confidence=0.0,
            sources=[],
            metadata={"degraded": True, "reason": "no_context"}
        )
    elif len(context.chunks) < 3:
        # Reduced confidence for limited context
        return synthesize_with_reduced_confidence(context)
    else:
        # Normal synthesis
        return synthesize_normal(context)
```

### Timeout Strategy

- **Per-tool timeout**: 7 seconds each (4 sources × 7s = 28s max, leaves 2s for processing)
- **Total response timeout**: 30 seconds hard limit
- **Early return**: If synthesis completes before 30s, return immediately

### Logging for Debugging

```python
logger.info(
    "retrieval_complete",
    extra={
        "query_id": query_id,
        "sources_available": ["rag", "web", "arxiv"],  # Omit failed sources
        "total_chunks": len(aggregated.chunks),
        "retrieval_time_ms": elapsed_ms
    }
)
```

---

## 7. TensorLake Document Parsing Integration

### Decision: TensorLake API for Intelligent Document Parsing and Chunking

**What we chose**: Use TensorLake API as the document parser for extracting text from various file formats (PDF, DOCX, TXT, Markdown) with intelligent chunking strategy (512 tokens per chunk with 64-token overlap).

**Rationale**:
- **Format Support**: TensorLake handles multiple document formats natively without format-specific libraries
- **Intelligent Chunking**: Built-in ability to respect document structure (paragraphs, sections, pages) rather than naive token splitting
- **Metadata Extraction**: Extracts structured metadata (title, author, creation date) from documents
- **API-Based**: No dependency on local libraries; simpler deployment and version management
- **Production-Ready**: Designed for enterprise document processing with reliability guarantees

**Alternatives considered**:
- Unstructured library: Good but requires multiple format-specific parsers; more maintenance
- PyPDF + python-docx: Works but requires combining multiple libraries for each format; naive chunking
- LangChain document loaders: Good but adds another abstraction layer; less direct control
- Manual parsing per format: Too complex and error-prone for production

### Implementation Pattern

```python
# TensorLake document parsing workflow
parser = TensorLakeDocumentParser(api_key=config.tensorlake_api_key)

# Upload and parse document
parsed_doc = parser.parse_document(
    file_path="/path/to/document.pdf",
    chunk_size_tokens=512,
    chunk_overlap_tokens=64,
    extract_metadata=True
)

# Result includes:
# - raw_text: Full extracted text
# - chunks: List of DocumentChunks with:
#   - text: Chunk content
#   - position_in_source: Character offset
#   - section_title: If hierarchical
#   - metadata: Document metadata
# - quality_score: How well parsing succeeded (0-1)

for chunk in parsed_doc.chunks:
    print(f"Chunk {chunk.chunk_number}: {chunk.text[:100]}...")
    print(f"  Metadata: {chunk.metadata}")
```

### Chunk Size Rationale

- **512 tokens per chunk**: Balances context coherence with retrieval precision
  - Too small (<256): Loses semantic context, requires more vectors
  - Too large (>1024): Brings noise when retrieving, hard to match specific queries
  - 512 is sweet spot for typical documents
  
- **64-token overlap**: Ensures continuity across chunk boundaries
  - Prevents missing information at chunk transitions
  - Typical text (10 words) = 13 tokens, so 64 tokens ≈ 50 words
  - Reduces "split claim" problem where key information spans chunks

### Error Handling

```python
class TensorLakeDocumentParser:
    def parse_document(self, file_path: str) -> ParsedDocument:
        try:
            # Call TensorLake API
            response = requests.post(
                f"{config.tensorlake_api_url}/parse",
                files={"document": open(file_path, "rb")},
                headers={"Authorization": f"Bearer {config.tensorlake_api_key}"},
                timeout=60  # 1 minute timeout for parsing
            )
            response.raise_for_status()
            return ParsedDocument(**response.json())
        
        except TimeoutError:
            logger.error(f"TensorLake timeout parsing {file_path}")
            raise DocumentParsingError("Parser timeout")
        
        except HTTPError as e:
            if e.response.status_code == 400:
                raise DocumentParsingError(f"Unsupported format: {file_path}")
            elif e.response.status_code == 413:
                raise DocumentParsingError(f"File too large: {file_path}")
            raise DocumentParsingError(f"API error: {e}")
        
        except Exception as e:
            logger.error(f"Unexpected parse error: {e}")
            raise DocumentParsingError(f"Parsing failed: {e}")
```

---

## 8. Google Gemini Text Embeddings

### Decision: Google Gemini text-embedding-004 (768 Dimensions)

**What we chose**: Use Google Gemini text-embedding-004 model for generating 768-dimensional embeddings for all document chunks and queries.

**Rationale**:
- **768 Dimensions**: Balanced dimensionality
  - Captures sufficient semantic information (vs 384-dim models)
  - Reduces memory/storage overhead (vs 1536-dim OpenAI)
  - Faster similarity computations in Milvus
  - Sufficient for Milvus with IVF_FLAT indexing
  
- **Unified LLM Stack**: Using Gemini for both synthesis (LLM) and embeddings simplifies:
  - Single API authentication
  - Consistent semantic understanding
  - Simplified configuration and deployment
  - Easier future migration to newer Gemini models
  
- **Production Ready**: Gemini embeddings API is stable and well-documented
- **Cost Efficient**: Competitive pricing for production use
- **Multilingual**: Handles multiple languages naturally

**Alternatives considered**:
- OpenAI text-embedding-3-small (1536 dim): More expensive, larger vectors
- OpenAI text-embedding-3-large (3072 dim): Much more expensive, slower
- Local embeddings (sentence-transformers): Requires GPU, harder to scale
- MiniLM (384 dim): Too small for nuanced semantic matching
- Cohere embeddings: Additional API dependency

### Implementation Pattern

```python
class GeminiEmbedder:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.model = "text-embedding-004"
        self.dimension = 768
    
    def embed_text(self, text: str) -> List[float]:
        """Embed a single text, returning 768-dim vector"""
        response = self.client.embed_content(
            model=f"models/{self.model}",
            content=text,
            task_type="RETRIEVAL_DOCUMENT"  # For stored documents
        )
        embedding = response['embedding']
        assert len(embedding) == 768, f"Expected 768 dims, got {len(embedding)}"
        return embedding
    
    def embed_query(self, query: str) -> List[float]:
        """Embed a query for similarity search"""
        response = self.client.embed_content(
            model=f"models/{self.model}",
            content=query,
            task_type="RETRIEVAL_QUERY"  # For search queries
        )
        return response['embedding']
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts efficiently"""
        embeddings = []
        for text in texts:
            embeddings.append(self.embed_text(text))
        return embeddings

# Usage
embedder = GeminiEmbedder(api_key=config.gemini_api_key)

# Embed document chunks
for chunk in parsed_document.chunks:
    chunk.embedding = embedder.embed_text(chunk.text)
    chunk.embedding_model = "text-embedding-004"

# Embed query for retrieval
query_embedding = embedder.embed_query(user_query)
```

### Milvus Schema Integration

```python
# Milvus collection schema uses 768 dimensions
schema = FieldSchema(
    name="embedding",
    dtype=DataType.FLOAT_VECTOR,
    dim=768  # Google Gemini text-embedding-004
)

# IVF_FLAT indexing parameters tuned for 768-dim vectors
index_params = {
    "metric_type": "L2",  # Euclidean distance (standard for Milvus)
    "index_type": "IVF_FLAT",
    "params": {
        "nlist": 128  # 128 clusters appropriate for large corpus
    }
}

# Similarity search returns top-k by distance
results = collection.search(
    data=[query_embedding],  # 768-dim query vector
    anns_field="embedding",
    param={"metric_type": "L2", "params": {"nprobe": 10}},
    limit=5  # Return top 5 similar chunks
)
```

### Embedding Lifecycle

```python
# 1. Document ingestion phase
document_chunks = tensorlake_parser.parse(file)
for chunk in document_chunks:
    chunk.embedding = embedder.embed_text(chunk.text)
    chunk.embedding_time_ms = measure_time()
    milvus_loader.insert_chunk(chunk)

# 2. Query processing phase
query_obj = receive_user_query()
query_embedding = embedder.embed_query(query_obj.text)

# 3. Semantic search
similar_chunks = milvus_collection.search(
    data=[query_embedding],
    limit=5
)

# 4. Reranking (in Evaluator)
for chunk in similar_chunks:
    quality_score = evaluate(chunk, query_obj)  # Multi-factor scoring
    chunk.confidence_score = quality_score
```

### Error Handling for Embeddings

```python
class GeminiEmbedder:
    def embed_with_retry(self, text: str, max_retries: int = 3) -> List[float]:
        for attempt in range(max_retries):
            try:
                return self.embed_text(text)
            except RateLimitError:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.info(f"Rate limited, waiting {wait_time}s")
                    time.sleep(wait_time)
                else:
                    raise EmbeddingError("Failed after retries")
            except APIError as e:
                if "overloaded" in str(e).lower():
                    time.sleep(5)
                    continue
                raise EmbeddingError(f"API error: {e}")
            except Exception as e:
                logger.error(f"Unexpected embedding error: {e}")
                raise EmbeddingError(f"Unexpected error: {e}")
```

### Performance Characteristics

- **Latency per chunk**: ~100-200ms (network + API processing)
- **Batch efficiency**: Processing 10 chunks in parallel ≈ 200-300ms total
- **Memory per vector**: 768 floats × 4 bytes = ~3 KB per vector
- **Query latency**: ~50-100ms for Milvus similarity search on 768-dim vectors

---

## Summary of Design Decisions (Updated)

| Area | Decision | Key Benefit |
|------|----------|------------|
| Orchestration | Sequential agents + parallel tools | Meets latency + ensures consistency |
| Storage | Milvus + connection pooling | Scalable semantic search |
| Quality | Multi-factor scoring | Transparent, tunable filtering |
| Contradictions | Multi-perspective synthesis | Honest, user-controlled resolution |
| Response Format | JSON with citations | Machine-readable + transparent |
| Memory | Dual timeline + entity graph | Multi-turn coherence + knowledge tracking |
| Resilience | Tool-level fault tolerance | Graceful degradation, user-friendly |
| Document Parsing | TensorLake API | Format-agnostic, intelligent chunking (512 tokens) |
| Embeddings | Gemini text-embedding-004 (768 dims) | Balanced quality/cost, unified Gemini stack |

---

## Unknowns Resolved

✅ **CrewAI orchestration pattern**: Sequential pipeline with parallel retrieval
✅ **Milvus integration**: Async connection pooling with batch queries
✅ **Context filtering metrics**: Multi-factor scoring (source, recency, relevance, redundancy)
✅ **Handling contradictions**: Multi-perspective synthesis with confidence
✅ **Response format**: JSON schema with source attribution and confidence scores
✅ **Zep memory schema**: Dual-mode (conversation history + entity graph)
✅ **Error handling**: Tool-level fault tolerance with graceful degradation
✅ **Document parser**: TensorLake API with 512-token chunks and 64-token overlap
✅ **Embedding model**: Google Gemini text-embedding-004 (768 dimensions)
✅ **Document ingestion pipeline**: Parse → Embed → Store workflow in single data_ingestion module

All Phase 0 research complete. Ready for Phase 1: Design & Contracts.
