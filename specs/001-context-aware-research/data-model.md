# Data Model: Context-Aware Research Assistant

**Date**: November 13, 2025  
**Status**: Complete  
**Purpose**: Define all data entities, relationships, and validation rules

---

## Core Domain Model

### 1. Query

**Purpose**: Represents a user's research question with context and metadata

**Fields**:
```python
class Query(BaseModel):
    id: str  # UUID or hash of user+timestamp+query
    user_id: str  # User identifier for memory tracking
    session_id: str  # Conversation session identifier
    text: str  # The actual research question
    timestamp: datetime  # When query was submitted
    
    # Optional metadata
    topic_category: Optional[str]  # User-provided category (e.g., "technology", "science")
    context_window: Optional[str]  # Prior context from conversation
    preferences: Optional[QueryPreferences]  # Query-specific preferences override
    
    # Status tracking
    status: str  # "submitted", "processing", "completed", "failed"
    error_message: Optional[str]
```

**Validation Rules**:
- `text` must be non-empty and <5000 characters
- `user_id` and `session_id` must be non-empty
- `timestamp` must be valid and not in future
- `status` must be one of: "submitted", "processing", "completed", "failed"

**Relationships**:
- One Query belongs to one Session (1:1)
- One Query has many ContextChunks (1:N)
- One Query produces one FinalResponse (1:1)

---

### 1b. Document

**Purpose**: Represents a user-uploaded file to be indexed in the RAG system

**Fields**:
```python
class Document(BaseModel):
    id: str  # UUID
    user_id: str  # User who uploaded it
    filename: str  # Original filename
    file_type: str  # "pdf", "docx", "txt", "markdown"
    file_size: int  # Bytes
    
    # Upload info
    uploaded_at: datetime
    upload_status: str  # "pending", "parsing", "embedding", "storing", "complete", "failed"
    
    # Processing metadata
    parsing_status: str  # Current processing stage
    parsed_document: Optional[ParsedDocument]  # Result of parsing
    chunks_created: int  # How many chunks from this document
    embedding_status: str  # Status of embedding chunks
    storage_status: str  # Status of storing in Milvus
    
    # Document metadata (extracted during parsing)
    title: Optional[str]
    author: Optional[str]
    created_date: Optional[datetime]
    modification_date: Optional[datetime]
    language: Optional[str]  # Detected language
    pages: Optional[int]  # For PDF, DOCX
    
    # Errors
    error_message: Optional[str]  # If failed
    error_details: Optional[Dict]  # Stack trace, API response, etc.
    
    # Tracking
    last_updated: datetime
    collection_name: str  # Milvus collection where chunks are stored

class ParsedDocument(BaseModel):
    """Result of TensorLake parsing"""
    id: str
    document_id: str  # Reference to parent Document
    raw_text: str  # Full extracted text
    chunks: List[DocumentChunk]  # Extracted chunks
    
    # Parsing metadata
    parser_version: str  # Which parser/API version used
    parsing_time_ms: float
    chunk_count: int
    estimated_tokens: int  # Total tokens in document
    quality_score: float  # How well parsing succeeded (0-1)
    
    timestamp: datetime

class DocumentChunk(BaseModel):
    """A discrete section of a parsed document"""
    id: str  # UUID
    document_id: str  # Parent document
    parsed_document_id: str
    
    # Content
    text: str  # Chunk text content
    chunk_number: int  # Order in document (0-indexed)
    position_in_source: int  # Character offset in original document
    
    # Chunking metadata
    start_page: Optional[int]  # For paginated documents
    end_page: Optional[int]
    section_title: Optional[str]  # For structured documents
    heading_level: Optional[int]  # If markdown/hierarchical
    
    # Encoding info
    token_count: int  # Actual tokens in chunk
    character_count: int
    
    # Embedding
    embedding: Optional[List[float]]  # 768-dimensional Gemini embedding
    embedding_model: str  # "text-embedding-004"
    embedding_time_ms: float
    
    # Storage
    milvus_id: Optional[int]  # ID assigned by Milvus
    stored_in_milvus: bool
    storage_timestamp: Optional[datetime]
    
    # Quality metrics
    coherence_score: Optional[float]  # Does chunk make sense on its own?
    quality_score: float  # Overall chunk quality (0-1)
    
    # Metadata for search
    metadata: Dict[str, Any]  # Source document, timestamps, etc.
    
    # Status
    status: str  # "created", "embedded", "stored", "error"
    timestamp: datetime
```

**Validation Rules** (Document):
- `filename` must be non-empty and include valid extension
- `file_type` must be one of: "pdf", "docx", "txt", "markdown"
- `file_size` must be > 0 and < 100MB (configurable)
- `upload_status` must be valid state in pipeline
- `user_id` must be non-empty

**Validation Rules** (DocumentChunk):
- `text` must be non-empty and <= 512 tokens (approx 2000 characters)
- `chunk_number` must be >= 0
- `token_count` must match actual token count
- `embedding` must be 768-dimensional (if provided)
- `quality_score` must be 0-1
- All timestamps must be valid and not in future

**Relationships**:
- One Document has many ParsedDocuments (1:N) - typically 1 but allows reprocessing
- One ParsedDocument has many DocumentChunks (1:N)
- DocumentChunks stored in Milvus collection via milvus_id

**Document Upload Workflow**:
```
Document (uploaded) 
  → file_type validation
  → upload_status: "pending"
  → TensorLake API call
  → ParsedDocument created
  → upload_status: "parsing"
  → DocumentChunks extracted
  → upload_status: "embedding"
  → Gemini embeddings generated
  → upload_status: "storing"
  → Milvus batch insert
  → upload_status: "complete"
  → Document indexed and searchable
```

---

### 2. Query

**Purpose**: Individual piece of information retrieved from any source

**Fields**:
```python
class ContextChunk(BaseModel):
    id: str  # Unique identifier
    query_id: str  # Reference to originating query
    source_type: str  # "rag", "web", "arxiv", "memory"
    text: str  # The actual content
    
    # Quality metrics (filled during retrieval)
    semantic_relevance: float  # 0-1, from embedding similarity
    source_reputation: float  # 0-1, based on source type
    recency_score: float  # 0-1, based on document age
    metadata: Dict  # Source-specific data
    
    # Source attribution
    source_id: str  # ID of original document/webpage/paper
    source_title: Optional[str]
    source_url: Optional[str]
    source_date: Optional[datetime]  # When content was published
    
    # Position info
    position_in_source: Optional[int]  # Chunk order in document
    chunk_number: Optional[int]  # Sequential chunk number
```

**Validation Rules**:
- `text` must be non-empty and <1000 characters (chunk size limit)
- All score fields must be between 0 and 1
- `source_type` must be one of: "rag", "web", "arxiv", "memory"
- `source_id` must be non-empty
- `source_date`, if provided, must not be in future

**Source-Specific Metadata**:
```python
# RAG source
class RAGChunkMetadata:
    document_id: str
    collection_name: str
    embedding_model: str
    chunk_size: int

# Web source
class WebChunkMetadata:
    domain: str
    page_rank: Optional[float]  # If available
    crawl_depth: int

# Arxiv source
class ArxivChunkMetadata:
    paper_id: str
    paper_title: str
    arxiv_url: str
    publication_date: datetime
    authors: List[str]

# Memory source
class MemoryChunkMetadata:
    session_context: str  # Which prior query/response this came from
    relevance_to_current: str  # Why it's relevant to current query
```

---

### 3. AggregatedContext

**Purpose**: Collection of all context chunks from parallel retrieval before evaluation

**Fields**:
```python
class AggregatedContext(BaseModel):
    id: str  # UUID for this aggregation
    query_id: str
    chunks: List[ContextChunk]
    
    # Statistics
    retrieval_time_ms: float
    sources_consulted: List[str]  # Which sources returned results
    sources_failed: List[str]  # Which sources failed
    total_chunks_before_dedup: int
    total_chunks_after_dedup: int  # After removing exact duplicates
    
    # Metadata
    timestamp: datetime
```

**Relationships**:
- One AggregatedContext produced from one Query (1:1)
- Contains many ContextChunks (1:N)

**Deduplication Rules**:
- Exact text match: Remove all but first occurrence
- High similarity (>95% token overlap): Remove lower-quality one
- Log removed duplicates with sources for transparency

---

### 4. FilteredContext

**Purpose**: High-quality subset of aggregated context after evaluation

**Fields**:
```python
class FilteredContext(BaseModel):
    id: str
    query_id: str
    original_chunk_count: int
    filtered_chunk_count: int
    
    chunks: List[FilteredChunk]  # Re-scored chunks
    
    # Filtering statistics
    filtering_time_ms: float
    average_quality_score: float
    quality_threshold_used: float
    
    # Filtering details
    removed_chunks: List[RemovedChunkRecord]  # For transparency
    contradictions_detected: List[ContradictionRecord]
    
    timestamp: datetime

class FilteredChunk(ContextChunk):
    # Original fields plus:
    quality_score: float  # Composite: 0.3*reputation + 0.2*recency + 0.4*relevance + 0.1*dedup
    quality_components: QualityScoring
    filtering_decision: str  # "kept", "deduplicated", "low_quality", "contradictory"
    
class QualityScoring(BaseModel):
    source_reputation: float
    recency_score: float
    semantic_relevance: float
    redundancy_penalty: float
    
class RemovedChunkRecord(BaseModel):
    original_chunk_id: str
    reason: str  # "low_quality", "redundant", "contradictory"
    quality_score: float
    source: str
    
class ContradictionRecord(BaseModel):
    claim_1: str  # First contradictory claim
    claim_1_source: str
    claim_2: str  # Second contradictory claim
    claim_2_source: str
    severity: str  # "minor", "moderate", "critical"
```

**Validation Rules**:
- `filtered_chunk_count` must be <= `original_chunk_count`
- `quality_score` for kept chunks must be >= `quality_threshold_used`
- All removed chunk records must reference valid original chunks
- Contradiction records must have valid sources

**Quality Threshold Configuration**:
- Default: 0.6 (60% score required)
- Configurable by query type or user preference
- Documented in response metadata

---

### 5. FinalResponse

**Purpose**: Synthesized answer to the user's query

**Fields**:
```python
class FinalResponse(BaseModel):
    id: str  # UUID
    query_id: str
    user_id: str
    session_id: str
    
    # Content
    answer: str  # Main answer/summary
    sections: List[ResponseSection]  # Detailed breakdown
    
    # Perspectives (if contradictions exist)
    perspectives: Optional[List[Perspective]]  # Multiple viewpoints
    
    # Quality metrics
    overall_confidence: float  # 0-1
    generation_time_ms: float
    
    # Source attribution
    sources: List[SourceAttribution]
    source_count: int
    sources_consulted: List[str]  # Source types used
    
    # Metadata
    timestamp: datetime
    response_quality: ResponseQuality

class ResponseSection(BaseModel):
    heading: str
    content: str
    confidence: float  # For this section
    sources: List[str]  # Source IDs contributing to this section
    order: int  # Display order

class Perspective(BaseModel):
    viewpoint: str  # The actual claim/perspective
    summary: str  # Explanation of perspective
    confidence: float
    sources: List[str]  # Source IDs supporting this viewpoint
    weight: float  # How many sources support this vs alternatives

class SourceAttribution(BaseModel):
    id: str  # Source ID
    type: str  # "rag", "web", "arxiv", "memory"
    title: str
    url: Optional[str]
    relevance: float  # How relevant to final answer
    contribution: str  # How this source contributed

class ResponseQuality(BaseModel):
    has_contradictions: bool
    degraded_mode: bool  # Generated with limited context
    completeness: float  # How well query was addressed (0-1)
    informativeness: float  # Quality of information provided (0-1)
```

**Validation Rules**:
- `answer` must be non-empty
- `overall_confidence` must be between 0 and 1
- If `perspectives` list exists, it must have 2+ items
- All section confidences must be 0-1
- Source attributions must reference valid sources

---

### 6. ConversationHistory

**Purpose**: Persistent record of user interactions across sessions

**Fields**:
```python
class ConversationHistory(BaseModel):
    session_id: str
    user_id: str
    created_at: datetime
    last_updated: datetime
    
    # Message history
    messages: List[Message]  # Ordered by timestamp
    
    # Inferred user model
    topics_discussed: List[str]
    user_preferences_inferred: UserPreferences
    
    # Statistics
    query_count: int
    average_confidence: float
    
class Message(BaseModel):
    role: str  # "user" or "assistant"
    content: str  # Full message text
    timestamp: datetime
    
    # For assistant messages only
    metadata: Optional[Dict]  # Sources, confidence, etc.
    response_id: Optional[str]  # Link to FinalResponse
    
    # For user messages only
    preferences_override: Optional[QueryPreferences]
```

**Relationships**:
- One ConversationHistory per Session (1:1)
- Contains many Messages (1:N)
- Messages link to Queries and Responses

**Retention Policy**:
- Keep all messages for <30 days
- Archive older messages (retention per user preference)
- Implement cleanup task for expired data

---

### 7. UserPreferences

**Purpose**: User settings that affect response generation

**Fields**:
```python
class UserPreferences(BaseModel):
    user_id: str
    
    # Response format preferences
    response_format: str  # "concise", "detailed", "technical", "narrative"
    max_response_length: int  # Characters
    include_citations: bool  # Default True
    
    # Source preferences
    preferred_sources: List[str]  # Order of preference: ["rag", "arxiv", "web", "memory"]
    exclude_sources: List[str]  # Sources to never use
    preferred_domains: Optional[List[str]]  # For web searches
    
    # Information preferences
    information_depth: str  # "overview", "comprehensive", "expert"
    date_preference: str  # "recent", "any", "historical"
    
    # Learning preferences
    explanation_style: str  # "academic", "casual", "instructional"
    topic_interests: List[str]  # Topics the user cares about
    
    # Updated
    last_updated: datetime
    
class QueryPreferences(BaseModel):
    """Override UserPreferences for a specific query"""
    response_format: Optional[str]
    preferred_sources: Optional[List[str]]
    information_depth: Optional[str]
    # ... other overrideable fields
```

**Validation Rules**:
- `response_format` must be one of: "concise", "detailed", "technical", "narrative"
- `information_depth` must be one of: "overview", "comprehensive", "expert"
- `preferred_sources` and `exclude_sources` must not overlap
- Source types must be valid: "rag", "arxiv", "web", "memory"

**Derivation from History**:
```python
def infer_preferences_from_history(history: ConversationHistory) -> UserPreferences:
    # Analyze past queries and responses to infer preferences
    # Count source type usage, measure response satisfaction, etc.
    # Update user preferences if patterns detected
```

---

### 8. Entity

**Purpose**: Named concepts tracked across interactions for knowledge graph

**Fields**:
```python
class Entity(BaseModel):
    id: str  # Unique entity ID
    name: str  # Display name
    entity_type: str  # "person", "organization", "concept", "technology", etc.
    
    # Knowledge
    description: Optional[str]  # What is this entity?
    attributes: Dict[str, Any]  # Type-specific properties
    
    # Relationships
    relationships: List[EntityRelationship]  # Links to other entities
    
    # Mention history
    mentions: List[EntityMention]  # Where this entity appeared
    mention_count: int
    first_mentioned: datetime
    last_mentioned: datetime
    
    # Metadata
    confidence: float  # How confident are we this is a real entity?
    created_at: datetime
    updated_at: datetime

class EntityMention(BaseModel):
    session_id: str
    query_id: str
    response_id: str
    mention_context: str  # Surrounding text
    mention_type: str  # "subject", "object", "comparison", "reference"
    sentiment: Optional[str]  # If discernible: "positive", "neutral", "negative"

class EntityRelationship(BaseModel):
    source_entity_id: str  # This entity
    target_entity_id: str  # Related entity
    relationship_type: str  # "is_part_of", "compared_with", "authored_by", etc.
    direction: str  # "forward", "backward", "bidirectional"
    context: str  # How they're related
    strength: float  # How confident we are in this relationship (0-1)
```

**Entity Types**:
- `person`: People, authors, researchers
- `organization`: Companies, universities, institutions
- `location`: Places, cities, regions
- `concept`: Abstract ideas, theories, techniques
- `technology`: Software, frameworks, tools
- `publication`: Papers, books, articles
- `event`: Conferences, occurrences, dates

**Relationship Types**:
- `is_part_of`: Component/parent relationships
- `compared_with`: Comparative relationships
- `authored_by`: Authorship
- `mentions`: Direct reference
- `contradicts`: Logical opposition
- `supports`: Provides evidence for

---

## State Diagram

```
Query (submitted)
  ↓
Query (processing)
  ├→ Parallel Retrieval (4 sources)
  └→ AggregatedContext
       ↓
  Evaluation Phase
       ↓
  FilteredContext
       ↓
  Synthesis Phase
       ↓
  FinalResponse
       ↓
  Memory Update
       ├→ Update ConversationHistory
       ├→ Update UserPreferences
       └→ Update Entity Graph
              ↓
  Query (completed)
```

---

## Database Schema (Milvus - Vector Searches)

```yaml
collection: "document_chunks"
fields:
  - name: "id"
    type: "Int64"
    is_primary: true
    
  - name: "document_id"
    type: "VarChar"
    
  - name: "chunk_text"
    type: "VarChar"
    
  - name: "embedding"
    type: "FloatVector"
    dimension: 768  # Google Gemini text-embedding-004
    
  - name: "metadata"
    type: "JSON"
    
  - name: "source_type"
    type: "VarChar"
    
  - name: "publish_date"
    type: "Int64"  # Timestamp
    
  - name: "chunk_number"
    type: "Int32"
    
  - name: "quality_score"
    type: "Float"
    
indexes:
  - field: "embedding"
    index_type: "IVF_FLAT"
    params:
      nlist: 128
      
  - field: "source_type"
    index_type: "HASH"
    
  - field: "publish_date"
    index_type: "SORT"
    
  - field: "quality_score"
    index_type: "SORT"
```

---

## Database Schema (Zep - Conversations & Entities)

```yaml
# Zep handles this via their API, but conceptually:

collections:
  
  - name: "sessions"
    documents:
      - session_id (primary)
      - user_id
      - created_at
      - metadata
  
  - name: "messages"
    documents:
      - id (primary)
      - session_id (foreign key)
      - role
      - content
      - timestamp
      - metadata
  
  - name: "entities"
    documents:
      - entity_id (primary)
      - session_id
      - name
      - type
      - mentions (array)
      - relationships (array)
      - confidence
      
  - name: "user_preferences"
    documents:
      - user_id (primary)
      - preferences (JSON)
      - last_updated
```

---

## Validation Rules Summary

| Entity | Critical Fields | Validation |
|--------|-----------------|-----------|
| Query | text, user_id, session_id | Non-empty, length limits, valid status |
| ContextChunk | text, source_type, source_id | Non-empty, valid source type, scores 0-1 |
| AggregatedContext | chunks, query_id | Valid chunk references, coherent stats |
| FilteredContext | chunks, quality_threshold | Chunks must meet threshold, valid reasons |
| FinalResponse | answer, overall_confidence | Non-empty, valid confidence, citations |
| ConversationHistory | messages, session_id, user_id | Valid message sequence, timestamps ordered |
| UserPreferences | response_format, user_id | Valid enum values, non-overlapping sources |
| Entity | name, entity_type, id | Non-empty, valid type, valid relationships |

---

## Migration Strategy (for future schema evolution)

1. **Version all schemas** with `schema_version: "1.0"`
2. **Support dual-read** during transitions (old + new schemas)
3. **Gradual write migration** to new schema version
4. **Archive old records** after migration complete
5. **Document breaking changes** in release notes

---

Data model complete. Ready for Phase 1: Contracts definition.
