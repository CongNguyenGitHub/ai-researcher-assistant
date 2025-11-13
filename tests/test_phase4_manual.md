# Phase 4 Manual Testing Guide
## User Story 2: Multi-Source Parallel Retrieval

**Status**: Phase 4 in progress
**Focus**: Implement real backends for 4 retrieval tools with parallel execution

---

## Prerequisites

### Services Required
1. **Milvus Vector Database** (for RAG)
   ```bash
   docker run -d --name milvus \
     -p 19530:19530 \
     -p 19531:19531 \
     milvusdb/milvus:latest
   ```

2. **Zep Memory Server** (optional for Memory tool)
   ```bash
   docker run -d --name zep \
     -p 8000:8000 \
     getzep/zep:latest
   ```

### API Keys (in .env)
- `GEMINI_API_KEY` - For embeddings and LLM
- `FIRECRAWL_API_KEY` - For web scraping
- `ZEP_API_KEY` - For memory service (optional)

### Python Packages
```bash
pip install pymilvus firecrawl-python arxiv zep-python
```

---

## Test Scenarios

### Scenario 1: RAG Tool Milvus Integration
**Objective**: Verify document retrieval from indexed Milvus collection

**Prerequisites**:
- Milvus running on localhost:19530
- Documents uploaded via Data Ingestion page

**Steps**:
1. In Streamlit, navigate to Research page
2. Create query: "What is semantic search?"
3. Monitor retrieval: Check RAG tool executes
4. Expected: 3-5 relevant document chunks retrieved

**Success Criteria**:
- ✅ RAG tool executes without timeout
- ✅ Chunks match query semantically
- ✅ Execution time < 2 seconds
- ✅ Source attribution includes filenames

---

### Scenario 2: Firecrawl Web Scraping Integration
**Objective**: Verify web content retrieval and scraping

**Prerequisites**:
- Firecrawl API key configured
- Internet connection available

**Steps**:
1. Create query: "latest developments in AI 2024"
2. Monitor retrieval: Check Firecrawl tool executes
3. Expected: 2-3 web content chunks from relevant websites

**Success Criteria**:
- ✅ URLs extracted via search service
- ✅ Web content successfully scraped
- ✅ Markdown extraction preserves structure
- ✅ Execution time < 5 seconds

---

### Scenario 3: Arxiv Academic Paper Retrieval
**Objective**: Verify academic paper search functionality

**Prerequisites**:
- Internet connection (Arxiv API is public)

**Steps**:
1. Create query: "neural networks attention mechanisms"
2. Monitor retrieval: Check Arxiv tool executes
3. Expected: 2-3 relevant paper abstracts with authors/dates

**Success Criteria**:
- ✅ Paper search returns relevant results
- ✅ Abstracts are complete and readable
- ✅ Author information captured
- ✅ Publication dates correct
- ✅ Execution time < 3 seconds

---

### Scenario 4: Memory Tool Conversation History
**Objective**: Verify conversation history retrieval from Zep

**Prerequisites**:
- Zep service running (or gracefully skip)
- Session ID maintained

**Steps**:
1. Ask query 1: "Who is Marie Curie?"
2. Ask query 2: "What were her major discoveries?"
3. Monitor Memory tool retrieval
4. Expected: Query 1 context available in Query 2

**Success Criteria**:
- ✅ Memory tool executes without error
- ✅ Previous conversation in context
- ✅ Entity recognition works (if Zep available)
- ✅ Graceful degradation if Zep unavailable
- ✅ Execution time < 1 second

---

### Scenario 5: Parallel Execution of All 4 Tools
**Objective**: Verify all tools execute in parallel with proper timing

**Prerequisites**:
- All 4 tools properly configured
- Milvus, Firecrawl, Zep ready

**Steps**:
1. Create complex query: "machine learning applications in healthcare"
2. Start timer as query submitted
3. Monitor each tool:
   - RAG starts immediately
   - Firecrawl starts immediately
   - Arxiv starts immediately
   - Memory starts immediately
4. Record individual completion times
5. Stop timer on final response

**Expected Behavior**:
```
Query submitted at T=0
├─ RAG Tool: Starts T=0, completes T=2.1s, retrieves 5 chunks
├─ Web Tool: Starts T=0, completes T=4.8s, retrieves 3 chunks
├─ Arxiv Tool: Starts T=0, completes T=2.9s, retrieves 3 chunks
└─ Memory Tool: Starts T=0, completes T=0.5s, retrieves 2 chunks

Total Time: ~4.8s (parallel max, not sequential 10.3s)
```

**Success Criteria**:
- ✅ All 4 tools start within 100ms of each other
- ✅ Total time ≤ slowest individual tool + 1s
- ✅ Total time < 8 seconds
- ✅ Total retrieval < sequential time (50%+ faster)
- ✅ Aggregated context shows 13+ chunks from 4 sources

---

### Scenario 6: Source Aggregation & Deduplication
**Objective**: Verify context aggregation and duplicate detection

**Prerequisites**:
- All tools returning results

**Steps**:
1. Create query: "climate change"
2. Monitor aggregation phase
3. Check filtering summary:
   - Total chunks before dedup
   - Total chunks after dedup
   - Removed percentage
4. Inspect individual sources

**Success Criteria**:
- ✅ Chunks properly attributed to sources
- ✅ Duplicates detected and merged
- ✅ Filtering summary shows statistics
- ✅ Quality scores assigned (0.0-1.0)
- ✅ Metadata preserved (URLs, dates, authors)

---

### Scenario 7: Timeout Handling
**Objective**: Verify graceful handling when tools timeout

**Prerequisites**:
- Tools configured with reasonable timeouts (7-10s)

**Steps**:
1. Temporarily stop Milvus service
2. Create query: "test query"
3. Monitor RAG tool failure
4. Observe other tools continue
5. Restart Milvus

**Expected Behavior**:
```
Query submitted
├─ RAG Tool: Timeout after 7s ❌
├─ Web Tool: Succeeds ✅
├─ Arxiv Tool: Succeeds ✅
└─ Memory Tool: Succeeds ✅

Response: Partial results with 3 sources (RAG failed noted)
```

**Success Criteria**:
- ✅ Tool timeout after 7s
- ✅ Other tools continue unaffected
- ✅ Final response still generated (partial)
- ✅ User sees which sources failed
- ✅ No unhandled exceptions
- ✅ Error gracefully noted in response metadata

---

### Scenario 8: Error Recovery
**Objective**: Verify system recovery from various error conditions

**Prerequisites**:
- System fully operational

**Test Cases**:

**8a. Invalid Query**
- Create empty query
- Expected: Validation error, helpful message

**8b. All Tools Fail**
- Stop all services
- Create query
- Expected: Graceful error response explaining issue

**8c. Partial Tool Failures**
- Stop Milvus only
- Create query
- Expected: Response from 3 sources, RAG failure noted

**8d. API Rate Limit**
- Rapidly submit 10+ queries
- Expected: Tools handle rate limits, no crashes

**Success Criteria** (all sub-tests):
- ✅ No unhandled exceptions
- ✅ User-friendly error messages
- ✅ Suggestions for recovery
- ✅ Logging captures all errors
- ✅ System remains stable

---

### Scenario 9: Performance Benchmarking
**Objective**: Verify performance meets requirements

**Prerequisites**:
- All tools operational
- Network stable
- Milvus warmed up (if cold start)

**Steps**:
1. Create 5 different queries
2. Record time for each:
   - Query submission to response display
   - Breakdown by phase (retrieval, evaluation, synthesis)
   - Per-tool timing

**Sample Query Set**:
- "simple query"
- "complex multi-part question about science?"
- "current events in technology"
- "health and exercise benefits"
- "artificial intelligence research papers"

**Success Criteria**:
- ✅ Retrieval phase: < 8 seconds
- ✅ Evaluation phase: < 2 seconds
- ✅ Synthesis phase: < 5 seconds
- ✅ Total end-to-end: < 15 seconds
- ✅ 95th percentile: < 20 seconds

---

### Scenario 10: Search Service Integration
**Objective**: Verify URL extraction for web scraping

**Prerequisites**:
- Search service configured (mock or real)

**Steps**:
1. Create query: "artificial intelligence"
2. Inspect Firecrawl tool URL extraction
3. Verify topic-appropriate URLs are selected
4. Test with various query types

**Success Criteria**:
- ✅ URLs match query topic
- ✅ Valid HTTP(S) URLs
- ✅ Top-tier authoritative sources preferred
- ✅ Appropriate result count (2-5 URLs)

---

## Performance Metrics

### Target Benchmarks

| Metric | Target | Status |
|--------|--------|--------|
| RAG retrieval | < 2.5s | ❌ To test |
| Web scraping | < 5s | ❌ To test |
| Arxiv search | < 3s | ❌ To test |
| Memory retrieval | < 1s | ❌ To test |
| **Parallel total** | **< 8s** | ❌ To test |
| Evaluation | < 2s | ❌ To test |
| Synthesis | < 3s | ❌ To test |
| **Total end-to-end** | **< 15s** | ❌ To test |

### Acceptance Criteria (from spec)
- **SC-002**: At least 2 of 4 sources succeed for 95% of queries
- **SC-005**: Parallel execution time < sequential execution time

---

## Debugging & Logs

### Check Orchestrator Logs
```python
# In research.py, enable debug logging:
import logging
logger = logging.getLogger("orchestrator")
logger.setLevel(logging.DEBUG)
```

### Monitor Tool Execution
```python
# Each tool logs:
# "Tool 'X' started: <query>"
# "Tool 'X' completed: <N> chunks, <time>ms"
# "Tool 'X' failed: <error>"
```

### Milvus Connection Debug
```bash
# Test connection
python -c "from pymilvus import connections; connections.connect(); print('OK')"
```

### Firecrawl Integration Debug
```python
# Verify search service
from services.search_service import get_search_service
search = get_search_service()
urls = search.search("test")
print(f"Found {len(urls)} URLs")
```

---

## Known Issues & Workarounds

### Issue 1: Milvus Connection Timeout
**Symptom**: RAG tool times out after 7s
**Cause**: Milvus not running or slow to respond
**Fix**: 
```bash
docker restart milvus
# Wait 30s for startup
```

### Issue 2: Firecrawl Rate Limiting
**Symptom**: Web scraping fails after multiple queries
**Cause**: API rate limit exceeded
**Fix**: Implement exponential backoff in FirecrawlTool

### Issue 3: Memory Tool Unavailable
**Symptom**: Memory retrieval fails but other tools work
**Expected**: System gracefully continues without memory
**Fix**: Already handled - Memory is optional

---

## Sign-Off Checklist

**Tester**: _______________
**Date**: _______________

- [ ] All 10 scenarios pass
- [ ] Performance benchmarks met (or documented)
- [ ] Error handling works for all 8 error cases
- [ ] Parallel execution faster than sequential (SC-005)
- [ ] At least 2 of 4 sources succeed consistently (SC-002)
- [ ] No unhandled exceptions in logs
- [ ] Logging complete and helpful
- [ ] User-facing error messages clear

**Overall Result**: 
- [ ] PASS - Ready for Phase 5
- [ ] NEEDS WORK - Issues documented below

**Issues Found**:
```
[List any failures, timeouts, or unexpected behavior]
```

---

## Next Phase (Phase 5)

After Phase 4 sign-off:
1. Implement context evaluation (quality scoring)
2. Add filtering and deduplication
3. Create response synthesis
4. Integrate all phases

See PHASE4_PLAN.md for Phase 5 details.
