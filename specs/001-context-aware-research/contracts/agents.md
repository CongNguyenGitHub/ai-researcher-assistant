# Agent Contracts: Context-Aware Research Assistant

**Version**: 1.0  
**Date**: November 13, 2025  
**Purpose**: Define crewAI agent responsibilities and interfaces

---

## Agent Definitions

### 1. Retriever Agent

**Purpose**: Orchestrate parallel context retrieval from four sources

**Responsibilities**:
- Accept a research query
- Invoke all four retrieval tools in parallel
- Aggregate results with source attribution
- Handle tool timeouts and failures gracefully
- Return AggregatedContext object

**Input Contract**:
```python
class RetrieverInput(BaseModel):
    query_text: str  # The research question
    user_id: str
    session_id: str
    preferred_sources: Optional[List[str]]  # Order preference
    exclude_sources: Optional[List[str]]
    quality_threshold: float = 0.6
    timeout_per_source: float = 7.0  # seconds
```

**Output Contract**:
```python
class RetrieverOutput(BaseModel):
    aggregated_context: AggregatedContext
    retrieval_status: str  # "success", "partial", "failed"
    sources_used: List[str]
    sources_failed: List[str]
    error_message: Optional[str]
    execution_time_ms: float
```

**Tool Invocations**:
```python
# Parallel execution of 4 tools
async def retrieve():
    results = await asyncio.gather(
        rag_tool.execute(query),
        firecrawl_tool.execute(query),
        arxiv_tool.execute(query),
        memory_tool.execute(query),
        return_exceptions=False  # Tools handle own errors
    )
    return aggregate_results(results)
```

**Error Handling**:
- If 0 sources available: Return `{"aggregated_context": empty, "status": "failed"}`
- If 1-3 sources available: Return available results with `status: "partial"`
- If 4 sources available: Return all with `status: "success"`

---

### 2. Evaluator Agent

**Purpose**: Analyze and filter aggregated context for quality

**Responsibilities**:
- Accept AggregatedContext from Retriever
- Calculate quality scores for each chunk
- Identify and log low-quality content
- Detect and record contradictions
- Deduplicate near-identical chunks
- Return FilteredContext ready for synthesis

**Input Contract**:
```python
class EvaluatorInput(BaseModel):
    aggregated_context: AggregatedContext
    quality_threshold: float = 0.6
    user_preferences: Optional[UserPreferences]
    
    # Evaluation config
    source_reputation_weights: Optional[Dict[str, float]]
    recency_weight: float = 0.2
    relevance_weight: float = 0.4
    source_weight: float = 0.3
```

**Output Contract**:
```python
class EvaluatorOutput(BaseModel):
    filtered_context: FilteredContext
    quality_stats: QualityStatistics
    contradictions_found: List[ContradictionRecord]
    removal_rationale: List[RemovalReason]
    execution_time_ms: float

class QualityStatistics(BaseModel):
    original_chunk_count: int
    filtered_chunk_count: int
    removal_rate: float  # Percentage removed
    average_quality_score: float
    quality_distribution: Dict[str, int]  # Score buckets
```

**Quality Scoring Algorithm**:
```python
def calculate_quality_score(chunk: ContextChunk, config: EvaluatorInput) -> float:
    source_reputation = SOURCE_REPUTATION[chunk.source_type]
    recency = calculate_recency(chunk.source_date)
    relevance = chunk.semantic_relevance
    
    score = (
        config.source_weight * source_reputation +
        config.recency_weight * recency +
        config.relevance_weight * relevance
    )
    
    # Apply redundancy penalty if duplicate detected
    if is_duplicate(chunk, earlier_chunks):
        score *= 0.5
    
    return min(max(score, 0.0), 1.0)  # Clamp 0-1
```

**Contradiction Detection**:
- Identify claims in chunks that are logical opposites
- Check for numerical contradictions (e.g., "X is 100" vs "X is 50")
- Flag for Synthesizer to handle with multi-perspective approach

---

### 3. Synthesizer Agent

**Purpose**: Generate final structured answer from filtered context

**Responsibilities**:
- Accept FilteredContext from Evaluator
- Use ONLY filtered context (no hallucination)
- Structure answer with sections and citations
- Handle contradictions as multi-perspective response
- Calculate confidence scores
- Return FinalResponse

**Input Contract**:
```python
class SynthesizerInput(BaseModel):
    filtered_context: FilteredContext
    original_query: Query
    user_preferences: UserPreferences
    
    # Generation config
    max_response_length: int = 2000
    min_response_length: int = 100
    include_sections: bool = True
    response_format: str = "detailed"  # "concise", "detailed", "technical"
```

**Output Contract**:
```python
class SynthesizerOutput(BaseModel):
    final_response: FinalResponse
    generation_method: str  # "standard", "multi_perspective"
    coverage_metrics: CoverageMetrics
    execution_time_ms: float

class CoverageMetrics(BaseModel):
    query_addressed: float  # 0-1, how well query was answered
    coverage_of_topics: Dict[str, float]  # Topic → coverage %
    source_diversity: float  # How many sources contributed
    information_completeness: float  # 0-1
```

**Response Generation Pattern**:

1. **Analyze filtered context** for key themes and relationships
2. **Check for contradictions** - if found, use multi-perspective format
3. **Organize information** into logical sections
4. **Generate answer text** using only context chunks as source material
5. **Add citations** linking each section to source chunks
6. **Calculate confidence** based on source credibility and agreement
7. **Validate completeness** against original query

**Constraints**:
- MUST NOT hallucinate information not in context
- MUST cite every factual claim with source
- MUST preserve source attribution
- MUST note high-confidence items vs lower-confidence items
- CAN synthesize new insights from combining sources (with citation)

---

### 4. Memory Agent

**Purpose**: Update persistent memory with query results

**Responsibilities**:
- Accept completed FinalResponse
- Store response in ConversationHistory
- Extract and track entities
- Update user preferences if patterns detected
- Maintain entity relationship graph
- Return success status

**Input Contract**:
```python
class MemoryInput(BaseModel):
    query: Query
    final_response: FinalResponse
    session_id: str
    user_id: str
    context: Optional[Dict]  # Additional context to store
```

**Output Contract**:
```python
class MemoryOutput(BaseModel):
    status: str  # "success", "partial", "failed"
    entities_added: int
    entities_updated: int
    relationships_added: int
    conversation_entry_added: bool
    preferences_updated: bool
    error_message: Optional[str]
    execution_time_ms: float
```

**Operations**:

1. **Store message pair**:
   - User query → ConversationHistory
   - Assistant response → ConversationHistory
   - Link with timestamps and response_id

2. **Extract entities**:
   - Identify named entities (NER) in response
   - Look up or create Entity records
   - Record mentions in entity history
   - Calculate entity confidence (0-1)

3. **Update relationships**:
   - Detect entity interactions in response
   - Create or update EntityRelationship records
   - Maintain bidirectional links
   - Record relationship confidence

4. **Update preferences**:
   - If response format worked well, increase likelihood
   - If user asks follow-up, may indicate source satisfaction
   - Accumulate preferences over time
   - Periodic review to update user model

5. **Handle Zep failures**:
   - Gracefully degrade if Zep unavailable
   - Queue updates for retry
   - Never block response delivery

---

## Agent Orchestration Flow

```
Input Query
    ↓
[Retriever Agent]
    ├─ Tool: RAG (async)
    ├─ Tool: Firecrawl (async)
    ├─ Tool: Arxiv (async)
    └─ Tool: Memory (async)
    ↓
AggregatedContext
    ↓
[Evaluator Agent]
    ├─ Calculate quality scores
    ├─ Detect contradictions
    ├─ Remove low-quality chunks
    └─ Deduplicate
    ↓
FilteredContext
    ↓
[Synthesizer Agent]
    ├─ Structure answer
    ├─ Add citations
    ├─ Calculate confidence
    └─ Format response
    ↓
FinalResponse
    ↓
[Memory Agent]
    ├─ Store in history
    ├─ Extract entities
    ├─ Update preferences
    └─ Maintain graph
    ↓
Return to User
```

---

## Tool Contracts

Each tool implements this interface:

```python
class Tool(ABC):
    name: str
    description: str
    
    async def execute(self, query: str, **kwargs) -> List[ContextChunk]:
        """
        Execute the tool and return context chunks.
        
        Args:
            query: The search query or request
            **kwargs: Tool-specific parameters
        
        Returns:
            List of ContextChunk objects or empty list if error
            
        Raises:
            Never - all errors handled internally
        """
        raise NotImplementedError
```

### Tool Specifications

#### RAG Tool
```python
class RAGTool(Tool):
    name = "rag_search"
    
    async def execute(
        self,
        query: str,
        top_k: int = 5,
        timeout: float = 7.0,
        min_relevance: float = 0.5
    ) -> List[ContextChunk]:
        # 1. Embed query
        # 2. Search Milvus
        # 3. Filter by min_relevance
        # 4. Return top_k chunks
```

#### Firecrawl Tool
```python
class FirecrawlTool(Tool):
    name = "web_search"
    
    async def execute(
        self,
        query: str,
        num_results: int = 5,
        timeout: float = 7.0,
        domains: Optional[List[str]] = None
    ) -> List[ContextChunk]:
        # 1. Search web
        # 2. Crawl pages
        # 3. Extract content
        # 4. Return chunks
```

#### Arxiv Tool
```python
class ArxivTool(Tool):
    name = "academic_search"
    
    async def execute(
        self,
        query: str,
        num_results: int = 5,
        timeout: float = 7.0,
        sort_by: str = "relevance"  # or "date"
    ) -> List[ContextChunk]:
        # 1. Search Arxiv
        # 2. Fetch paper metadata
        # 3. Extract abstracts/summaries
        # 4. Return chunks
```

#### Memory Tool
```python
class MemoryTool(Tool):
    name = "memory_recall"
    
    async def execute(
        self,
        query: str,
        session_id: str,
        num_results: int = 3,
        timeout: float = 7.0
    ) -> List[ContextChunk]:
        # 1. Query Zep for session
        # 2. Find relevant prior interactions
        # 3. Extract relevant context
        # 4. Return as chunks
```

---

## Error Handling Contract

**All agents and tools MUST**:
1. Never raise unhandled exceptions
2. Log errors with context for debugging
3. Return partial/empty results rather than failing
4. Include error messages in output for transparency
5. Respect timeout limits (7s per tool, 30s total)

**Graceful Degradation**:
- Tool timeout → Empty chunk list (not error)
- Tool connection error → Empty chunk list
- Invalid query → Return error in response, not exception
- Zep unavailable → Continue without memory update

---

End of Agent Contracts. Ready for Tool Contract specifications.
