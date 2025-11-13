# Phase 0 Manual Testing: Data Ingestion Pipeline

## Overview

This document outlines manual testing scenarios for the Context-Aware Research Assistant's data ingestion pipeline. These tests verify that:

1. Document parsing correctly extracts text and creates chunks
2. Chunking strategy properly splits documents (512-token chunks with 64-token overlap)
3. Embedding generation creates 768-dimensional vectors
4. Milvus storage correctly indexes and retrieves documents
5. Semantic search returns relevant results
6. Error handling gracefully manages failures

## Prerequisites

### Environment Setup

1. **Install dependencies**:
   ```bash
   python -m pip install -r requirements.txt
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys:
   # - GEMINI_API_KEY: Your Google Gemini API key
   # - MILVUS_HOST: localhost (for local testing)
   # - MILVUS_PORT: 19530
   ```

3. **Start Milvus**:
   ```bash
   # Using Docker (recommended for testing)
   docker run -d --name milvus -p 19530:19530 -p 9091:9091 \
     milvusdb/milvus:latest start
   ```

4. **Start Streamlit app** (optional for UI testing):
   ```bash
   streamlit run src/app.py
   ```

## Test Data Files

Create these files in a `test_data/` directory for testing:

### Test File 1: Single Page PDF
- File: `test_data/single_page.pdf`
- Content: A 1-page document with ~500 words about machine learning
- Expected: 1-2 chunks created

### Test File 2: Multi-Page Document
- File: `test_data/whitepaper.pdf` or `.docx`
- Content: A 10-20 page document with multiple sections
- Expected: 50-100 chunks created

### Test File 3: Markdown Document
- File: `test_data/markdown_document.md`
- Content: Markdown formatted text with headers and code blocks
- Expected: Structure preserved in chunks, header context included

### Test File 4: Text File
- File: `test_data/document.txt`
- Content: Plain text file with paragraphs
- Expected: Chunks preserve paragraph boundaries where possible

## Test Scenarios

### Test 1: Single Document Upload & Indexing

**Objective**: Verify basic document parsing and indexing workflow

**Steps**:
1. Use document_processing.py Streamlit interface OR manually:
   ```python
   from src.config import get_config
   from src.data_ingestion import (
       TensorLakeDocumentParser,
       GeminiEmbedder,
       MilvusLoader,
       DataIngestionPipeline
   )
   
   # Initialize pipeline
   config = get_config()
   parser = TensorLakeDocumentParser(config.tensorlake)
   embedder = GeminiEmbedder(config.gemini)
   loader = MilvusLoader(
       host=config.milvus.host,
       port=config.milvus.port,
       embedding_dim=config.gemini.embedding_dimensions
   )
   pipeline = DataIngestionPipeline(parser, embedder, loader)
   
   # Ingest document
   result = pipeline.ingest_document("test_data/single_page.pdf")
   print(f"Status: {result.status}")
   print(f"Chunks created: {result.chunks_created}")
   print(f"Processing time: {result.processing_time_seconds}s")
   ```

**Expected Results**:
- ✓ Document successfully parsed
- ✓ Chunks created: 1-3 chunks for single page
- ✓ Processing time: < 30 seconds
- ✓ result.status == "success"
- ✓ All chunks indexed in Milvus

**Validation Criteria**:
```python
# Verify chunks in Milvus
stats = pipeline.get_knowledge_base_stats()
assert stats.total_documents >= 1
assert stats.total_chunks >= 1
print(f"Knowledge base: {stats.total_documents} docs, {stats.total_chunks} chunks")
```

---

### Test 2: Batch Document Processing

**Objective**: Verify batch processing with multiple documents

**Steps**:
1. Create test files: `test_data/doc1.txt`, `test_data/doc2.pdf`, `test_data/doc3.docx`
2. Process batch:
   ```python
   files = [
       "test_data/doc1.txt",
       "test_data/doc2.pdf",
       "test_data/doc3.docx"
   ]
   results = pipeline.ingest_batch(files)
   
   for result in results:
       print(f"{result.file_name}: {result.status}")
       if result.status == "success":
           print(f"  - Chunks: {result.chunks_created}")
       else:
           print(f"  - Error: {result.error_message}")
   ```

**Expected Results**:
- ✓ All 3 files successfully processed
- ✓ Total chunks created: 50-150 (depending on document sizes)
- ✓ Processing time: < 120 seconds
- ✓ No memory errors or API timeouts

**Validation Criteria**:
```python
# Check batch statistics
successful_count = sum(1 for r in results if r.status == "success")
total_chunks = sum(r.chunks_created for r in results if r.status == "success")
assert successful_count == 3
assert total_chunks > 0
print(f"Batch: {successful_count}/3 successful, {total_chunks} total chunks")
```

---

### Test 3: Semantic Search Verification

**Objective**: Verify that semantic search returns relevant documents

**Steps**:
1. Index a document about "Machine Learning Fundamentals"
2. Perform semantic search:
   ```python
   from src.data_ingestion import GeminiEmbedder
   
   embedder = GeminiEmbedder(config.gemini)
   query = "What are neural networks?"
   
   # Embed query
   query_embedding = embedder.embed_query(query)
   
   # Search Milvus
   results = loader.search(query_embedding, limit=5)
   
   for i, chunk in enumerate(results, 1):
       print(f"{i}. {chunk.text[:100]}...")
       print(f"   Source: {chunk.document_id}")
   ```

**Expected Results**:
- ✓ Query successfully embedded to 768 dimensions
- ✓ 5 results returned from search
- ✓ Results contain semantically relevant text about neural networks
- ✓ Search latency: < 2 seconds

**Validation Criteria**:
```python
# Verify embedding quality
assert len(query_embedding) == 768
assert len(results) <= 5
assert any("network" in chunk.text.lower() for chunk in results)
```

---

### Test 4: Chunk Quality Validation

**Objective**: Verify chunking strategy preserves document structure

**Steps**:
1. Parse a markdown document with headers:
   ```python
   result = parser.parse_document("test_data/markdown_document.md")
   
   for i, chunk in enumerate(result.chunks, 1):
       print(f"Chunk {i}:")
       print(f"  Text length: {len(chunk.text)} chars")
       print(f"  Token estimate: {len(chunk.text) // 4} tokens")
       print(f"  Metadata: {chunk.metadata}")
   ```

2. Verify chunk properties:
   ```python
   for chunk in result.chunks:
       # Chunks should be ~512 tokens
       token_estimate = len(chunk.text) // 4  # rough estimate
       assert 100 < token_estimate < 700, f"Chunk too small/large: {token_estimate}"
       
       # Metadata should include source and position
       assert "source" in chunk.metadata
       assert "page" in chunk.metadata or "line" in chunk.metadata
   ```

**Expected Results**:
- ✓ Chunks within 100-700 tokens
- ✓ Metadata includes source file and position
- ✓ Headers preserved in chunk content
- ✓ No incomplete sentences at chunk boundaries

---

### Test 5: Error Handling - Unsupported Format

**Objective**: Verify graceful error handling for unsupported file types

**Steps**:
1. Attempt to parse unsupported file:
   ```python
   try:
       result = pipeline.ingest_document("test_data/image.png")
       print(f"Status: {result.status}")
       print(f"Error: {result.error_message}")
   except Exception as e:
       print(f"Exception caught: {e}")
   ```

**Expected Results**:
- ✓ Error caught and logged
- ✓ result.status == "error"
- ✓ Clear error message explaining unsupported format
- ✓ No exception propagated to caller
- ✓ Milvus collection unaffected

---

### Test 6: Error Handling - API Timeout

**Objective**: Verify timeout handling during embedding

**Steps**:
1. Set a short timeout in embedder config
2. Attempt to embed large batch:
   ```python
   # Mock slow API or use real API with many chunks
   try:
       result = pipeline.ingest_document("test_data/large_document.pdf")
       if result.status == "error":
           print(f"Handled timeout: {result.error_message}")
   except Exception as e:
       print(f"Unhandled exception: {e}")
   ```

**Expected Results**:
- ✓ Timeout detected and handled
- ✓ Exponential backoff applied (if retrying)
- ✓ Clear error message
- ✓ Partial results preserved (if applicable)

---

### Test 7: Streamlit UI - Document Upload Interface

**Objective**: Verify Streamlit UI functionality (if running web app)

**Steps**:
1. Start Streamlit app:
   ```bash
   streamlit run src/app.py
   ```

2. Navigate to "Document Processing" page
3. Upload `test_data/single_page.pdf` via drag-and-drop
4. Monitor progress bars:
   - Upload progress
   - Parsing progress
   - Embedding progress
   - Storage progress

5. Check Knowledge Base Dashboard:
   - Total indexed documents
   - Total chunks
   - Storage size

**Expected Results**:
- ✓ File upload successful
- ✓ Progress bars show all stages
- ✓ Document appears in "Recent Uploads" table
- ✓ Status shows "Success"
- ✓ Dashboard statistics update automatically
- ✓ Refresh button updates stats

---

## Test Data Collection

Create sample files for testing. Here's a quick setup script:

```bash
mkdir -p test_data

# Create single page text file
cat > test_data/sample.txt << 'EOF'
Machine Learning Fundamentals

Machine learning is a subset of artificial intelligence that focuses on the development
of algorithms and statistical models that enable computers to improve their performance
on tasks through experience without explicit programming.

Key Concepts:
- Supervised Learning: Training on labeled data
- Unsupervised Learning: Finding patterns in unlabeled data
- Neural Networks: Biologically inspired computational models

Deep learning has revolutionized many AI applications including natural language
processing, computer vision, and recommendation systems. The field continues to evolve
with new architectures and training techniques emerging regularly.
EOF

# Create markdown file
cat > test_data/sample.md << 'EOF'
# Introduction to Neural Networks

## Overview
Neural networks are computational models inspired by biological neural networks.

## Architecture
- Input Layer
- Hidden Layers
- Output Layer

## Training Process
Neural networks learn through backpropagation.
EOF

echo "Test data files created in test_data/"
```

## Test Results Template

Use this template to record test results:

```
Test Date: [DATE]
Tester: [NAME]

Test 1: Single Document Upload
- Status: [ ] PASS [ ] FAIL
- Document: [FILENAME]
- Chunks Created: [NUMBER]
- Processing Time: [TIME]s
- Notes: [ANY ISSUES]

Test 2: Batch Processing
- Status: [ ] PASS [ ] FAIL
- Files Processed: [COUNT]
- Total Chunks: [NUMBER]
- Processing Time: [TIME]s
- Notes: [ANY ISSUES]

Test 3: Semantic Search
- Status: [ ] PASS [ ] FAIL
- Query: [QUERY TEXT]
- Results Returned: [COUNT]
- Relevance: [ASSESSMENT]
- Notes: [ANY ISSUES]

Test 4: Chunk Quality
- Status: [ ] PASS [ ] FAIL
- Average Chunk Size: [TOKENS]
- Metadata Completeness: [%]
- Notes: [ANY ISSUES]

Test 5: Error Handling
- Status: [ ] PASS [ ] FAIL
- Unsupported Format: [FORMAT]
- Error Message Clarity: [ ] GOOD [ ] NEEDS IMPROVEMENT
- Notes: [ANY ISSUES]

Test 6: API Timeout
- Status: [ ] PASS [ ] FAIL
- Timeout Handled: [ ] YES [ ] NO
- Recovery Time: [TIME]s
- Notes: [ANY ISSUES]

Test 7: Streamlit UI
- Status: [ ] PASS [ ] FAIL
- Upload Interface: [ ] WORKING [ ] BROKEN
- Progress Tracking: [ ] WORKING [ ] BROKEN
- Dashboard Stats: [ ] ACCURATE [ ] INACCURATE
- Notes: [ANY ISSUES]

Overall Phase 0 Status:
- Ready for Phase 1: [ ] YES [ ] NO
- Blockers: [LIST ANY BLOCKERS]
```

## Next Steps (Phase 1)

After Phase 0 testing is complete:

1. Document all test results
2. Fix any critical issues found
3. Update documentation with findings
4. Commit changes to git
5. Proceed to Phase 1: Setup & Project Initialization

## References

- **Data Model**: See `specs/001-context-aware-research/data-model.md`
- **Architecture**: See `ARCHITECTURE_OVERVIEW.md`
- **Configuration**: See `.env.example` for required environment variables
- **Code**: See `src/data_ingestion/` for implementation details
