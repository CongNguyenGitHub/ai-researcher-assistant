# Complete End-to-End Picture: Context-Aware Research Assistant

## Executive Summary

The **Context-Aware Research Assistant** is a comprehensive research platform that transforms user queries into well-synthesized, multi-sourced answers. It orchestrates multiple AI agents and data sources to deliver high-quality research results with full transparency and source attribution.

**Core Promise**: Answer research questions comprehensively by gathering context from multiple sources, evaluating quality, synthesizing answers, and maintaining conversation continuity.

---

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          STREAMLIT WEB UI                                   │
│  ┌─────────────────────┬──────────────────────┬──────────────────────┐    │
│  │  Research Page      │  Conversation Page   │  Document Processing │    │
│  │  (Query Input)      │  (History & Memory)  │  (Ingestion)         │    │
│  └────────────┬────────┴──────────┬───────────┴─────────────┬────────┘    │
│               │                   │                         │              │
└───────────────┼───────────────────┼─────────────────────────┼──────────────┘
                │                   │                         │
         ┌──────▼──────────────────▼─────────────┐    ┌──────▼─────────┐
         │  CREWAI ORCHESTRATION LAYER          │    │  DATA INGESTION│
         │  ┌─────────────────────────────────┐ │    │  PIPELINE      │
         │  │  Sequential Agent Workflow      │ │    │ ┌────────────┐ │
         │  │  1. Retriever Agent             │ │    │ │ TensorLake │ │
         │  │  2. Evaluator Agent             │ │    │ │ Parser     │ │
         │  │  3. Synthesizer Agent           │ │    │ │            │ │
         │  │  4. Memory Agent                │ │    │ └─────┬──────┘ │
         │  └──────┬──────────────────────────┘ │    │       │       │
         │         │                            │    │ ┌─────▼──────┐ │
         │  ┌──────▼─────────────────────────┐ │    │ │  Gemini    │ │
         │  │  PARALLEL TOOL EXECUTION       │ │    │ │  Embedder  │ │
         │  │  (Within Retriever Agent)      │ │    │ │            │ │
         │  │ ┌────────┬────────┬────────┐   │ │    │ └─────┬──────┘ │
         │  │ │  RAG   │  Web   │ Arxiv  │   │ │    │       │       │
         │  │ │ Tool   │ Tool   │ Tool   │   │ │    │ ┌─────▼──────┐ │
         │  │ └────────┴────────┴────────┘   │ │    │ │ Milvus     │ │
         │  └─────────────────────────────────┘ │    │ │ Loader     │ │
         │                                      │    │ └────────────┘ │
         └──────────────────┬───────────────────┘    └────────────────┘
                            │
          ┌─────────────────┼─────────────────┬──────────────────┐
          │                 │                 │                  │
    ┌─────▼─────┐  ┌───────▼────────┐  ┌────▼─────┐  ┌────────▼──────┐
    │  Milvus   │  │  Firecrawl API │  │ Arxiv    │  │ Zep Memory    │
    │  Vector   │  │  (Web Search)  │  │ (Papers) │  │ (Conversation)│
    │  Database │  │                │  │          │  │               │
    │ (RAG)     │  └────────────────┘  └──────────┘  └───────────────┘
    └───────────┘
```

---

## Data Flow: End-to-End Query Processing

### Phase 1: User Query Submission
```
User Input (Streamlit UI)
    ↓
Query Validation & Initialization
    ├─ Generate Query ID
    ├─ Store in session state
    ├─ Load user preferences from memory
    └─ Status: "submitted" → "processing"
```

### Phase 2: Parallel Context Retrieval
```
Retriever Agent (CrewAI)
    │
    ├─→ RAG Tool (Milvus)
    │   ├─ Embed query with Gemini (768 dims)
    │   ├─ Vector similarity search in Milvus
    │   ├─ Retrieve top-5 document chunks
    │   └─ Extract metadata (source, filename, page)
    │
    ├─→ Web Search Tool (Firecrawl)
    │   ├─ Execute web search
    │   ├─ Fetch HTML from top results
    │   ├─ Extract and chunk relevant text
    │   └─ Score by domain reputation
    │
    ├─→ Academic Tool (Arxiv API)
    │   ├─ Query paper abstracts & metadata
    │   ├─ Retrieve references
    │   └─ Extract DOI & citation info
    │
    └─→ Memory Tool (Zep Memory)
        ├─ Retrieve conversation history
        ├─ Extract relevant prior Q&A
        ├─ Fetch user preferences & entities
        └─ Load entity relationships

    Result: ContextChunk[] = [chunk1, chunk2, ..., chunkN]
    Total time: ~15-25 seconds (parallel execution)
```

### Phase 3: Context Evaluation & Filtering
```
Evaluator Agent (CrewAI)
    │
    ├─ For each ContextChunk:
    │  ├─ Compute source_reputation (by source type)
    │  │  ├─ RAG docs: 0.9 (internal, vetted)
    │  │  ├─ Academic: 0.85 (peer-reviewed)
    │  │  ├─ Web: 0.6-0.8 (domain dependent)
    │  │  └─ Memory: 0.7 (previous user context)
    │  │
    │  ├─ Compute recency_score (by age)
    │  │  ├─ < 1 month: 1.0
    │  │  ├─ 1-12 months: 0.8
    │  │  ├─ 1-5 years: 0.5
    │  │  └─ > 5 years: 0.2
    │  │
    │  ├─ Compute semantic_relevance (embedding distance)
    │  │  └─ 0.0-1.0 based on cosine similarity to query
    │  │
    │  └─ Check deduplication
    │     └─ If >95% overlap with existing chunk: reduce to 0.1
    │
    ├─ Quality Score = (0.30 × reputation) + (0.20 × recency) 
    │                + (0.40 × relevance) + (0.10 × dedup)
    │
    ├─ Filter: Keep chunks with quality_score > 0.5
    │
    └─ Output: FilteredContextChunk[]
    
    Result: High-quality context ready for synthesis
    Time: ~5 seconds
```

### Phase 4: Response Synthesis
```
Synthesizer Agent (CrewAI)
    │
    ├─ Input: FilteredContextChunk[] (only high-quality)
    │
    ├─ For each key point:
    │  ├─ Identify supporting chunks
    │  ├─ Check for contradictions
    │  │  └─ If found: Note both perspectives with sources
    │  ├─ Generate claim text
    │  └─ Assign confidence_score (0.0-1.0)
    │
    ├─ Synthesize main answer
    │  ├─ Integrate multi-source insights
    │  ├─ Add transitions between sources
    │  └─ Flag any knowledge gaps
    │
    └─ Format response as structured JSON
        ├─ Main answer text with source links
        ├─ Key claims array (with citations)
        ├─ Confidence scores per claim
        ├─ Source attribution
        ├─ Timestamp
        └─ Available/unavailable sources
    
    Time: ~5-10 seconds
```

### Phase 5: Memory Update
```
Memory Agent (CrewAI)
    │
    ├─ Store in Zep Memory:
    │  ├─ Query text
    │  ├─ Final response
    │  ├─ Retrieved sources
    │  ├─ User interaction data
    │  └─ Identified entities
    │
    ├─ Extract and link entities
    │  ├─ People, organizations, concepts
    │  └─ Build relationship graph
    │
    └─ Update user preferences
        ├─ Inferred topics of interest
        ├─ Preferred sources
        └─ Query patterns
    
    Time: ~2-3 seconds
    Persistence: For future queries
```

### Phase 6: Response Delivery
```
Streamlit UI
    │
    ├─ Display final answer (markdown formatted)
    │
    ├─ Show source attribution
    │  ├─ Clickable source links
    │  └─ Per-claim confidence indicators
    │
    ├─ Show processing metrics
    │  ├─ Total time: ~30-35 seconds
    │  ├─ Sources queried: 4
    │  ├─ Chunks retrieved: N
    │  └─ Chunks used: M (after filtering)
    │
    └─ Enable follow-up interactions
        ├─ Ask clarification question
        ├─ Request source details
        └─ Provide feedback
```

---

## Component Deep-Dives

### 1. DATA INGESTION PIPELINE
**Purpose**: Convert user documents into searchable knowledge base

```
Document Input (PDF, DOCX, TXT, MD)
    ↓
TensorLake Parser
    ├─ Call TensorLake API
    ├─ Extract text and structure
    ├─ Identify document metadata
    └─ Output: ParsedDocument
         ├─ chunks: List[Dict]
         │  └─ {text, page_number, type, metadata}
         └─ metadata: {title, author, date, source}
    ↓
Chunking Strategy
    ├─ 512 tokens per chunk
    ├─ 64 tokens overlap
    └─ Preserve boundaries (sentences, paragraphs)
    ↓
Gemini Embedder
    ├─ For each chunk: Generate embedding
    ├─ Model: text-embedding-004
    ├─ Output dimension: 768
    └─ Batch process for efficiency
    ↓
Milvus Loader
    ├─ Create collection (if needed)
    ├─ Batch insert vectors
    ├─ Store metadata
    └─ Build indexes (IVF_FLAT)
    ↓
Vector Database (Milvus)
    ├─ Indexed and searchable
    ├─ 768-dim vectors
    ├─ Full chunk text + metadata stored
    └─ Ready for RAG queries
```

**UI Component** (Streamlit):
- Drag-and-drop file upload
- Progress indicators
- Status dashboard: "X documents indexed"
- Recent processing history

### 2. QUERY PROCESSING PIPELINE
**Purpose**: Answer research questions with synthesized context

```
Core Workflow (Orchestrated by CrewAI)
    │
    Step 1: Input & Routing
    ├─ User submits query
    ├─ Parse and validate
    ├─ Route to Retriever Agent
    └─ Status: Processing
    │
    Step 2: Parallel Retrieval (Retriever Agent)
    ├─ RAG Search
    │  ├─ Embed query → 768-dim vector
    │  ├─ Search Milvus (top-5)
    │  ├─ Output: Internal document chunks
    │  └─ Score: 0.9 reputation
    │
    ├─ Web Search (Firecrawl)
    │  ├─ Execute search query
    │  ├─ Crawl & extract relevant text
    │  ├─ Output: Web snippets
    │  └─ Score: 0.6-0.8 (domain dependent)
    │
    ├─ Academic Search (Arxiv)
    │  ├─ Query papers & abstracts
    │  ├─ Extract key insights
    │  ├─ Output: Paper summaries
    │  └─ Score: 0.85 reputation
    │
    └─ Memory Retrieval (Zep)
       ├─ Fetch conversation history
       ├─ Extract relevant prior Q&A
       ├─ Retrieve entity context
       └─ Score: 0.7 reputation
    │
    Step 3: Context Evaluation (Evaluator Agent)
    ├─ Score each chunk: 
    │  └─ quality = (0.3×reputation) + (0.2×recency) 
    │              + (0.4×relevance) + (0.1×dedup)
    ├─ Filter: quality_score > 0.5
    ├─ Deduplicate similar chunks
    └─ Output: Filtered, ranked context
    │
    Step 4: Response Synthesis (Synthesizer Agent)
    ├─ Generate answer from filtered context
    ├─ Detect contradictions
    ├─ Cite sources for each claim
    ├─ Assign confidence scores
    └─ Format as JSON response
    │
    Step 5: Memory Update (Memory Agent)
    ├─ Store Q&A pair in Zep
    ├─ Extract and link entities
    ├─ Update user preferences
    └─ Build knowledge graph
    │
    Final Output: Structured JSON Response
    {
      "answer": "Main synthesized answer text...",
      "claims": [
        {
          "text": "Key claim 1",
          "confidence": 0.95,
          "sources": ["source_id_1", "source_id_2"],
          "citations": ["quote from source 1", "quote from source 2"]
        },
        ...
      ],
      "sources": [
        {"id": "source_id_1", "title": "...", "url": "...", "type": "rag"},
        ...
      ],
      "metadata": {
        "response_time": "32 seconds",
        "sources_queried": 4,
        "chunks_retrieved": 23,
        "chunks_used": 18,
        "unavailable_sources": []
      }
    }
```

### 3. CREWAI ORCHESTRATION
**Purpose**: Manage multi-agent workflow

```
Crew Definition
├─ Agents (Sequential Execution):
│  │
│  ├─ Agent 1: Retriever
│  │  ├─ Role: "Research Information Retriever"
│  │  ├─ Goal: "Gather relevant context from all sources"
│  │  ├─ Tools: [rag_tool, web_tool, arxiv_tool, memory_tool]
│  │  └─ Execution: Parallel tool calls
│  │
│  ├─ Agent 2: Evaluator
│  │  ├─ Role: "Context Quality Evaluator"
│  │  ├─ Goal: "Filter and score context for relevance"
│  │  ├─ Tools: [evaluation_tool]
│  │  └─ Inputs: Retrieved context from Agent 1
│  │
│  ├─ Agent 3: Synthesizer
│  │  ├─ Role: "Answer Synthesizer"
│  │  ├─ Goal: "Create comprehensive response"
│  │  ├─ Tools: [synthesis_tool, formatting_tool]
│  │  └─ Inputs: Filtered context from Agent 2
│  │
│  └─ Agent 4: Memory Manager
│     ├─ Role: "Conversation Memory Manager"
│     ├─ Goal: "Update memory and track entities"
│     ├─ Tools: [memory_tool]
│     └─ Inputs: Query + response from Agent 3
│
├─ Task Definitions:
│  ├─ Task 1: Retrieve context (15-25s)
│  ├─ Task 2: Evaluate quality (5s)
│  ├─ Task 3: Synthesize answer (5-10s)
│  └─ Task 4: Update memory (2-3s)
│
├─ Error Handling:
│  ├─ Tool-level retries: 2 attempts per tool
│  ├─ Graceful degradation: Continue if 1 source fails
│  ├─ Logging: All agent decisions, tool calls
│  └─ Callbacks: Track execution progress
│
└─ LLM Provider: Google Gemini 2.0 Flash
   └─ Powers all agent reasoning and synthesis
```

### 4. MILVUS VECTOR DATABASE
**Purpose**: Fast semantic search over documents

```
Collection Schema
├─ id (INT64, auto-increment, primary key)
├─ embedding (FLOAT_VECTOR, 768 dimensions)
├─ text (VARCHAR, up to 65KB)
├─ document_id (VARCHAR, 256)
├─ chunk_id (VARCHAR, 256)
├─ filename (VARCHAR, 512)
├─ page_number (INT32, nullable)
└─ chunk_type (VARCHAR, 64)

Indexing Strategy
├─ Primary: IVF_FLAT on embedding field
│  ├─ nlist: 128 (cluster partitions)
│  ├─ metric: L2 (Euclidean distance)
│  └─ probes: 10 (per query)
└─ Secondary: None needed (VARCHAR indexed by default)

Query Pattern
├─ 1. Embed query text: query_embedding ← Gemini(query_text)
├─ 2. Vector search: results ← Milvus.search(query_embedding, top_k=5)
├─ 3. Process results:
│  ├─ Extract chunk text
│  ├─ Retrieve metadata
│  ├─ Calculate relevance score
│  └─ Return ranked list
└─ Time: <500ms per query

Storage Characteristics
├─ Vector size: 768 dims × 4 bytes = 3,072 bytes per vector
├─ Metadata overhead: ~100-500 bytes per chunk
├─ Example: 100,000 chunks ≈ 307 MB vectors + ~50 MB metadata
└─ Scaling: Can handle millions of chunks efficiently
```

### 5. ZEP MEMORY SYSTEM
**Purpose**: Maintain conversation continuity and entity knowledge

```
Memory Structure
├─ Session Memory
│  ├─ Conversation history (last N turns)
│  ├─ Query-response pairs
│  └─ Interaction timestamps
│
├─ Entity Graph
│  ├─ People, organizations, concepts
│  ├─ Relationships between entities
│  ├─ Mention frequency
│  └─ Context for each mention
│
├─ User Preferences
│  ├─ Preferred source types
│  ├─ Topic interests
│  ├─ Response style preferences
│  └─ Previous Q&A summaries
│
└─ Cross-Session Learning
   ├─ Long-term user interests
   ├─ Knowledge accumulation
   └─ Personalization signals

Memory Lifecycle
├─ On Query Submission:
│  └─ Retrieve: Conversation history, relevant entities, preferences
│
├─ During Processing:
│  └─ Reference: Prior context to influence filtering and synthesis
│
└─ On Response Completion:
   ├─ Store: Query, response, sources, timestamp
   ├─ Extract: New entities, relationships
   ├─ Update: User preference signals
   └─ Link: Connections to existing entity graph
```

### 6. STREAMLIT USER INTERFACE
**Purpose**: Multi-page web app for research interactions

```
Page 1: research.py (Main Query Interface)
├─ Input Section
│  ├─ Text input for research query
│  ├─ Optional filters/preferences
│  └─ Submit button
│
├─ Processing Indicator
│  ├─ Real-time status updates
│  ├─ Progress bar
│  └─ Current stage (Retrieving, Evaluating, Synthesizing)
│
└─ Results Section
   ├─ Main answer text (markdown formatted)
   ├─ Key claims with confidence scores
   ├─ Source citations (clickable links)
   ├─ Processing metadata (time, sources, chunks)
   └─ Follow-up options (refine, explain, new query)

Page 2: document_processing.py (Data Ingestion)
├─ Upload Section (Left Panel)
│  ├─ Drag-and-drop file upload
│  ├─ Multiple file support
│  ├─ Supported formats: PDF, DOCX, TXT, MD
│  └─ Process button (with progress)
│
└─ Status Section (Right Panel)
   ├─ Knowledge base metrics
   │  ├─ Total documents indexed
   │  ├─ Total chunks
   │  └─ Database size
   ├─ Recent processing results
   ├─ Processing history table
   └─ Error display (if any)

Page 3: conversation.py (Multi-Turn History)
├─ Conversation Timeline
│  ├─ All prior queries and responses
│  ├─ Chronological display
│  ├─ Expandable detail view
│  └─ Export options
│
├─ Entity Browser
│  ├─ List of extracted entities
│  ├─ Mention frequency
│  └─ Related entities
│
└─ Session Management
   ├─ Load previous sessions
   ├─ Clear history
   └─ Export conversation

Page 4: entities.py (Knowledge Graph)
├─ Entity List
│  ├─ All identified entities
│  ├─ Type: Person, Organization, Concept
│  ├─ Mention count
│  └─ Context snippets
│
├─ Relationship Graph
│  ├─ Visual node-link diagram
│  ├─ Interactive exploration
│  ├─ Filter by entity type
│  └─ Show relationship strength
│
└─ Search & Filter
   ├─ Find entities by name
   ├─ Filter by type or frequency
   └─ Show relationship details
```

---

## Configuration & Environment

```yaml
# .env Configuration
GEMINI_API_KEY: "AIzaSyA..."           # Google API for LLM & embeddings
GEMINI_EMBEDDING_MODEL: "text-embedding-004"  # 768-dim model
EMBEDDING_DIMENSIONS: 768

TENSORLAKE_API_KEY: "tl_apiKey_..."    # Document parser
TENSORLAKE_BASE_URL: "https://api.tensorlake.ai"

FIRECRAWL_API_KEY: "..."               # Web crawling/search
ARXIV_API_KEY: (optional)              # Academic papers

ZEP_API_KEY: "..."                     # Conversation memory
ZEP_BASE_URL: "https://api.getzep.com"

MILVUS_HOST: "localhost"               # Vector database
MILVUS_PORT: 19530
MILVUS_USER: "default"
MILVUS_PASSWORD: "Milvus"
MILVUS_COLLECTION_NAME: "documents"

# Application Settings
LOG_LEVEL: "INFO"
RESPONSE_TIMEOUT: 35                   # seconds
MAX_CONTEXT_TOKENS: 4000               # for synthesis
QUALITY_SCORE_THRESHOLD: 0.5           # filtering threshold
```

---

## Data Models

### Query
```python
{
  "id": "query_20251113_001",
  "user_id": "user_123",
  "session_id": "session_abc",
  "text": "How does machine learning work?",
  "timestamp": "2025-11-13T10:30:00Z",
  "topic_category": "technology",
  "status": "processing"
}
```

### ContextChunk
```python
{
  "id": "chunk_001",
  "query_id": "query_20251113_001",
  "source_type": "rag",  # or "web", "arxiv", "memory"
  "text": "Machine learning is a subset of artificial intelligence...",
  "semantic_relevance": 0.92,
  "source_reputation": 0.9,
  "recency_score": 1.0,
  "quality_score": 0.84,  # (0.3×0.9) + (0.2×1.0) + (0.4×0.92) + (0.1×1.0)
  "source_id": "doc_ml_basics",
  "source_title": "Machine Learning Fundamentals",
  "source_url": "https://example.com/ml-basics"
}
```

### FinalResponse
```python
{
  "query_id": "query_20251113_001",
  "answer": "Machine learning is a field of artificial intelligence...",
  "claims": [
    {
      "text": "ML enables systems to learn from data",
      "confidence": 0.95,
      "source_ids": ["doc_001", "arxiv_paper_123"],
      "citations": [
        "From Machine Learning Fundamentals: 'systems that improve with experience'",
        "From arXiv paper: 'learning algorithms adjust based on training data'"
      ]
    }
  ],
  "sources": [
    {
      "id": "doc_001",
      "title": "ML Basics",
      "url": "https://...",
      "type": "rag",
      "reputation": 0.9
    }
  ],
  "metadata": {
    "response_time_seconds": 31,
    "sources_queried": 4,
    "chunks_retrieved": 23,
    "chunks_used": 18,
    "available_sources": ["rag", "web", "arxiv"],
    "unavailable_sources": [],
    "timestamp": "2025-11-13T10:30:31Z"
  }
}
```

---

## Quality Assurance & Evaluation

### Context Quality Scoring Formula
```
quality_score = (reputation × 0.30) 
              + (recency × 0.20) 
              + (relevance × 0.40) 
              + (dedup_factor × 0.10)

Where:
- reputation: 0.9 (RAG), 0.85 (Academic), 0.6-0.8 (Web), 0.7 (Memory)
- recency: 1.0 (<1mo), 0.8 (1-12mo), 0.5 (1-5yr), 0.2 (>5yr)
- relevance: Cosine similarity of embeddings (0.0-1.0)
- dedup_factor: 1.0 (unique), 0.5 (partial dup), 0.1 (>95% dup)

Threshold: Keep chunks with quality_score > 0.5
```

### Response Confidence Metrics
```
Per-Claim Confidence:
- 0.90-1.0: High confidence (multiple sources agree)
- 0.70-0.89: Good confidence (primary source + support)
- 0.50-0.69: Moderate (single credible source)
- <0.50: Low (weak sourcing, flagged)

Overall Response Confidence:
- Aggregate across all claims
- Adjusted for source diversity
- Reduced if contradictions found
```

---

## Error Handling & Graceful Degradation

```
Scenario 1: Individual Source Failure
├─ Firecrawl API timeout
├─ Action: Continue with remaining sources
├─ Logging: Log timestamp, error message
├─ Response: Note "Web search unavailable" in metadata
└─ Result: Return answer from 3 sources instead of 4

Scenario 2: All Sources Fail
├─ All 4 sources return no results
├─ Action: Return transparent response
├─ Response: "No relevant context found. Try refining your query or upload seed documents."
└─ Result: User can adjust query or upload documents

Scenario 3: Memory Service Failure
├─ Zep unavailable
├─ Action: Continue without conversation history
├─ Result: Loss of continuity, but query still processed
└─ Note: Memory update queued for retry

Scenario 4: Synthesis Failure
├─ Gemini API error during synthesis
├─ Action: Return raw filtered context with minimal synthesis
├─ Result: User gets information but less structured
└─ Logging: Log error for debugging
```

---

## Performance Characteristics

| Stage | Duration | Notes |
|-------|----------|-------|
| Query Input & Validation | <1s | Client-side |
| Retrieval (4 sources parallel) | 15-25s | Limited by slowest source |
| Evaluation & Filtering | 5s | Per-chunk scoring |
| Synthesis | 5-10s | LLM generation |
| Memory Update | 2-3s | Async-friendly |
| **Total Response Time** | **~30-35s** | Target: <30s, actual: 30-35s |

**Optimization Opportunities**:
- Reduce Firecrawl timeout
- Cache frequent queries
- Precompute entity relationships
- Optimize Milvus indexing

---

## Security & Privacy

```
Data Classification
├─ User Queries: Sensitive (not logged beyond session)
├─ Retrieved Context: Per-source policy
├─ Responses: User-owned (stored in Zep if opted-in)
├─ Conversation Memory: Encrypted in transit and at rest
└─ Entity Graph: Aggregated (no PII in links)

API Key Management
├─ Environment variables (.env)
├─ Never committed to git
├─ Rotation policy: Every 90 days
├─ Scope: Minimal required per service
└─ Monitoring: Track API usage per key

Access Control
├─ User sessions isolated (Streamlit session state)
├─ Memory queries filtered by user_id
├─ No cross-session data leakage
└─ Future: Multi-tenant with session keys
```

---

## Future Enhancements

**Phase 2**:
- Multi-user sessions with login
- Document-level access control
- Custom source connectors
- Async processing for large batches

**Phase 3**:
- Real-time collaborative research
- Citation export (BibTeX, APA, MLA)
- Research paper generation
- Advanced knowledge graph visualization

**Phase 4**:
- ML-based quality metric refinement
- A/B testing of agent prompts
- Source-specific ranking models
- Automated fact-checking
- Integration with external knowledge bases (Wikipedia, Wikidata)

---

## Deployment Architecture

```
Development
├─ Local machine
├─ Docker Compose: Milvus + (optional) Zep
└─ Streamlit dev server

Staging
├─ Cloud VM (AWS/GCP/Azure)
├─ Managed vector DB (Milvus Cloud)
├─ Managed memory service (Zep Cloud)
└─ Docker container for app

Production
├─ Kubernetes cluster
├─ Managed databases
├─ Load balancer
├─ Session persistence
└─ Monitoring & alerting
```

---

## Summary: Why This Architecture?

1. **Multi-Source Context**: Combines internal docs (RAG), real-time web, academic papers, and conversation history for comprehensive answers

2. **Quality Filtering**: Multi-factor scoring ensures only relevant, credible information influences synthesis

3. **Transparency**: Full source attribution and confidence scores allow users to verify claims

4. **Scalability**: Modular design (tools, agents, services) makes it easy to add new sources or improve agents

5. **User Experience**: Streamlit provides interactive interface with real-time progress and follow-up options

6. **Continuity**: Zep memory maintains conversation context across sessions and personalizes responses

7. **Resilience**: Graceful degradation means loss of one source doesn't break the entire system

This architecture delivers the core promise: **comprehensive, high-quality, transparent research answers powered by multiple AI agents and data sources.**
