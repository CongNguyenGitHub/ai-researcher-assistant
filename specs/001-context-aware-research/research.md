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

## Summary of Design Decisions

| Area | Decision | Key Benefit |
|------|----------|------------|
| Orchestration | Sequential agents + parallel tools | Meets latency + ensures consistency |
| Storage | Milvus + connection pooling | Scalable semantic search |
| Quality | Multi-factor scoring | Transparent, tunable filtering |
| Contradictions | Multi-perspective synthesis | Honest, user-controlled resolution |
| Response Format | JSON with citations | Machine-readable + transparent |
| Memory | Dual timeline + entity graph | Multi-turn coherence + knowledge tracking |
| Resilience | Tool-level fault tolerance | Graceful degradation, user-friendly |

---

## Unknowns Resolved

✅ **CrewAI orchestration pattern**: Sequential pipeline with parallel retrieval
✅ **Milvus integration**: Async connection pooling with batch queries
✅ **Context filtering metrics**: Multi-factor scoring (source, recency, relevance, redundancy)
✅ **Handling contradictions**: Multi-perspective synthesis with confidence
✅ **Response format**: JSON schema with source attribution and confidence scores
✅ **Zep memory schema**: Dual-mode (conversation history + entity graph)
✅ **Error handling**: Tool-level fault tolerance with graceful degradation

All Phase 0 research complete. Ready for Phase 1: Design & Contracts.
