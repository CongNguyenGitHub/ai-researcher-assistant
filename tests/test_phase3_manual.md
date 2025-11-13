# Phase 3 Manual Testing Guide

## Overview
Phase 3 introduces the research query workflow with four retrieval tools, CrewAI agents, and the Streamlit UI.

## Prerequisites

### Environment Setup
```bash
cd "c:\Users\AIP\Documents\AI Research Assisstant"

# Install dependencies
pip install -r requirements.txt

# Optional: Install phase 3 tools (for real testing)
pip install pymilvus>=2.3.0
pip install firecrawl-python>=1.0.0
pip install arxiv>=1.4.0
pip install zep-python>=2.0.0
pip install crewai>=0.1.0
```

### Service Requirements

For full Phase 3 testing, the following services should be running:

1. **Milvus Vector Database** (for RAG tool)
   ```bash
   # Docker: docker run -d --name milvus -p 19530:19530 milvusdb/milvus:latest
   ```
   - Used by RAGTool for document retrieval
   - Required for testing indexed documents

2. **Zep Memory Server** (optional, for Memory tool)
   ```bash
   # Docker: docker run -d --name zep -p 8000:8000 getzep/zep:latest
   ```
   - Used by MemoryTool for conversation history
   - Can be disabled in MVP mode

3. **API Keys** (in `.env`)
   ```
   GEMINI_API_KEY=<your-key>
   FIRECRAWL_API_KEY=<your-key>  # For web scraping
   ```

## Test Scenarios

### Scenario 1: Basic RAG Tool Test
**Objective**: Verify document retrieval from Milvus works correctly

**Steps**:
1. Upload test documents via Streamlit Upload page
2. Create a simple query: "What is artificial intelligence?"
3. Expected behavior:
   - Retrieve 5 relevant chunks from indexed documents
   - Each chunk shows source title and relevance score
   - Execution time < 2 seconds

**Success Criteria**:
- ✅ Retrieved chunks match query topic
- ✅ Chunks include proper metadata (title, URL, date)
- ✅ Relevance scores between 0 and 1

### Scenario 2: Web Scraping (Firecrawl) Test
**Objective**: Verify web content retrieval works

**Steps**:
1. Create a query: "Latest AI announcements 2024"
2. Expected behavior:
   - Firecrawl searches for relevant URLs
   - Fetches content from top 3 results
   - Extracts main content and creates chunks

**Success Criteria**:
- ✅ Web chunks retrieved successfully
- ✅ Markdown content properly extracted
- ✅ URLs are valid and properly attributed

### Scenario 3: Academic Paper Retrieval (Arxiv) Test
**Objective**: Verify paper retrieval from Arxiv API

**Steps**:
1. Create a query: "Neural networks transformers"
2. Expected behavior:
   - Search Arxiv for matching papers
   - Retrieve top 3 paper abstracts
   - Include author info and publication dates

**Success Criteria**:
- ✅ Retrieved papers are relevant
- ✅ Abstracts are complete and readable
- ✅ Authors and dates are accurate

### Scenario 4: Parallel Retrieval Test
**Objective**: Verify all 4 sources retrieve simultaneously

**Steps**:
1. Create a complex query: "Machine learning applications in healthcare"
2. Monitor retrieval process with progress indicators
3. Expected behavior:
   - All 4 tools execute in parallel
   - Different tools return at different speeds
   - Total retrieval time < 10 seconds
   - Chunks aggregated and deduplicated

**Success Criteria**:
- ✅ All sources contribute chunks
- ✅ Total time < 10s (not sequential sum)
- ✅ Deduplicated chunks < total raw chunks

### Scenario 5: Context Evaluation Test
**Objective**: Verify evaluator filters low-quality context

**Steps**:
1. Create query: "How to cook pasta"
2. Inspect evaluation stage:
   - Confidence scores per chunk
   - Contradiction detection
   - Filtering summary (% removed)
3. Expected behavior:
   - Low-relevance chunks marked for removal
   - Contradictions highlighted
   - Summary stats displayed

**Success Criteria**:
- ✅ Chunks score 0.0-1.0 confidence
- ✅ Filter removes ~20-30% of chunks
- ✅ Contradictions detected and reported

### Scenario 6: Response Synthesis Test
**Objective**: Verify response generation with citations

**Steps**:
1. Create query: "What are the benefits of exercise?"
2. Observe synthesis stage
3. Expected response:
   - Multiple answer sections
   - Per-section sources cited
   - Overall confidence score
   - Export options (Markdown, JSON)

**Success Criteria**:
- ✅ Answer is coherent and comprehensive
- ✅ Citations reference specific sources
- ✅ Confidence is 0.0-1.0
- ✅ Exports generate valid files

### Scenario 7: Memory Integration Test
**Objective**: Verify conversation history is preserved

**Steps**:
1. Ask query 1: "Who is Albert Einstein?"
2. Ask query 2: "What are his famous theories?"
3. Second response should reference previous answer
4. Expected behavior:
   - Previous conversation in memory
   - Memory chunks included in retrieval
   - Context continuity across queries

**Success Criteria**:
- ✅ Query 2 references Query 1 context
- ✅ Memory chunks appear in source attribution
- ✅ Session ID consistent across queries

### Scenario 8: Error Handling Test
**Objective**: Verify graceful error handling

**Steps**:
1. Stop Milvus service
2. Create query: "Test query"
3. Expected behavior:
   - RAG tool fails gracefully (timeout/error)
   - Other tools continue
   - Response includes partial results
   - Error message displayed to user

**Success Criteria**:
- ✅ No unhandled exceptions
- ✅ Response still generated
- ✅ User sees which sources failed
- ✅ Graceful degradation message shown

### Scenario 9: CrewAI Integration Test
**Objective**: Verify agent-based evaluation and synthesis (if enabled)

**Prerequisites**:
- CrewAI installed and configured
- `use_crew=True` in orchestrator

**Steps**:
1. Enable CrewAI mode in research.py
2. Create query: "Explain quantum computing"
3. Observe agent reasoning:
   - Evaluator scores context
   - Synthesizer generates structured response
   - Agent reasoning visible in logs

**Success Criteria**:
- ✅ CrewAI agents initialize successfully
- ✅ Response reflects agent reasoning
- ✅ No blocking errors
- ✅ Generation time < 15s

### Scenario 10: UI Component Test
**Objective**: Verify all UI components render correctly

**Steps**:
1. Create query that retrieves mixed-confidence results
2. Inspect rendered components:
   - Response cards (compact/detailed view)
   - Confidence gauge colors (green/blue/orange/red)
   - Source attribution table
   - Contradiction warnings
   - Filtering summary
   - Section breakdown
   - Metadata display
   - Retrieval status grid

**Success Criteria**:
- ✅ All components render without errors
- ✅ Color coding matches confidence levels
- ✅ Tables and grids display properly
- ✅ Expandable sections work

## Performance Benchmarks

Target metrics for Phase 3:

| Metric | Target | Notes |
|--------|--------|-------|
| RAG retrieval time | < 2s | Milvus query + embedding |
| Web scraping time | < 5s | 3 URLs maximum |
| Arxiv search time | < 3s | 3 papers |
| Memory retrieval | < 1s | Session lookup |
| **Total retrieval time** | **< 8s** | Parallel execution |
| Context evaluation | < 2s | Scoring all chunks |
| Response synthesis | < 3s | Generate answer |
| **Total end-to-end** | **< 13s** | All stages combined |

## Debugging Tips

### Enable Verbose Logging
```python
# In research.py
logger = get_orchestrator_logger()
logger.setLevel(logging.DEBUG)
```

### Mock Tool Testing
Tools provide MVP mode (mock responses) without external services:
```python
# In src/pages/research.py
# Uses mock orchestrator.execute() for testing
```

### Check Tool Output
Inspect `ToolResult` objects:
```python
result = tool.execute(query)
print(f"Status: {result.status}")
print(f"Chunks: {len(result.chunks)}")
print(f"Time: {result.execution_time_ms}ms")
print(f"Error: {result.error_message}")
```

## Known Limitations (Phase 3)

1. **No Real Tool Integration Yet**
   - Tools return mock/empty responses
   - Real implementations come in Phase 4

2. **CrewAI Optional**
   - Falls back to direct service calls if crewai not installed
   - Not required for MVP

3. **Limited Error Recovery**
   - Tool failures don't retry
   - Partial results always returned

4. **Memory Service Optional**
   - Gracefully skips if Zep not available
   - MVP mode doesn't require it

## Regression Test Suite

### Quick Smoke Test (5 min)
```bash
# 1. Start Streamlit app
streamlit run src/app.py

# 2. Test basic query
# Query: "test"
# Expected: MVP response generated in ~1500ms

# 3. Verify UI renders
# Check: response card, confidence, sources visible

# 4. Test export
# Click: "Export as Markdown"
# Expected: .md file downloads
```

### Integration Test (15 min)
```bash
# 1. Run through Scenarios 1, 4, 6
# 2. Verify parallel retrieval timing
# 3. Check response quality
# 4. Validate error handling
```

### Full Test Suite (45 min)
Run all 10 scenarios in sequence

## Monitoring & Metrics

During testing, monitor:

1. **Memory Usage**: Should stay < 500MB
2. **CPU Usage**: Peaks during parallel retrieval
3. **API Calls**: Each tool makes 1-3 requests
4. **Cache Hit Rate**: Deduplication effectiveness

## Sign-Off Criteria

Phase 3 is complete when:

- ✅ All 10 scenarios pass
- ✅ Performance benchmarks met
- ✅ No unhandled exceptions
- ✅ UI renders correctly
- ✅ Error handling works
- ✅ Documentation complete
- ✅ Code reviewed and tested

## Next Steps (Phase 4)

After Phase 3 sign-off:
1. Implement real tool backends
2. Add parallel source orchestration
3. Integrate actual APIs (Milvus, Firecrawl, Arxiv, Zep)
4. Performance optimization
5. Load testing (concurrent queries)

---

**Test Results**:
- Date: [TO BE FILLED]
- Tester: [TO BE FILLED]
- Scenarios Passed: [  ] / 10
- Performance Met: [ ] Yes / [ ] No
- Sign-Off: [ ] Approved / [ ] Needs Work
