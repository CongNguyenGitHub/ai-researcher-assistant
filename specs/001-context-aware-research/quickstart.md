# Quickstart Guide: Context-Aware Research Assistant

**Version**: 1.0  
**Date**: November 13, 2025  
**Status**: Ready for Development

---

## Project Overview

The Context-Aware Research Assistant is a Python-based system that answers user research queries by orchestrating parallel retrieval from multiple sources (internal documents, web, academic papers, and memory) using crewAI agents.

**Architecture**: 
- **Orchestration**: crewAI agents (Retriever, Evaluator, Synthesizer, Memory)
- **Storage**: Milvus (vector DB), Zep (conversation memory)
- **Language**: Python 3.10+
- **Deployment**: CLI tool with extensible REST API

---

## Getting Started

### 1. Clone and Setup

```bash
# Clone the repository
git clone <repo-url>
cd "AI Research Assisstant"

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration

Create a `.env` file in the project root with your API keys:

```env
# LLM Provider (OpenAI or equivalent)
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4-turbo

# Milvus Vector Database
MILVUS_HOST=localhost
MILVUS_PORT=19530
MILVUS_COLLECTION=document_chunks
EMBEDDING_MODEL=text-embedding-3-small

# Firecrawl Web Search
FIRECRAWL_API_KEY=...
FIRECRAWL_API_URL=https://api.firecrawl.dev/v0

# Arxiv API (no key needed, public API)
ARXIV_BASE_URL=http://export.arxiv.org/api/query

# Zep Memory Service
ZEP_API_URL=http://localhost:8000
ZEP_API_KEY=...  # Optional if local instance

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json  # or "text"
```

**Copy example configuration**:
```bash
cp .env.example .env
# Edit .env with your actual values
```

### 3. Install External Services

#### Option A: Using Docker (Recommended)

```bash
# Start Milvus vector database
docker run -d --name milvus \
  -p 19530:19530 \
  -p 9091:9091 \
  milvusdb/milvus:latest

# Start Zep memory service
docker run -d --name zep \
  -p 8000:8000 \
  -e DATABASE_URL=sqlite:///zep.db \
  getzep/zep:latest
```

#### Option B: Local Installation

**Milvus**:
```bash
# See: https://milvus.io/docs/install-pymilvus.md
pip install pymilvus
# Start Milvus server separately (Docker recommended)
```

**Zep**:
```bash
# See: https://docs.getzep.com/
pip install zep-python
# Start Zep server separately (Docker recommended)
```

### 4. Initialize Database

```bash
# Create Milvus collection and load sample documents
python scripts/init_milvus.py

# Initialize Zep
python scripts/init_zep.py
```

---

## Running the Assistant

### Basic Query

```bash
# Single query
python -m src.main --query "What are the benefits of Python?"

# Output:
# {
#   "answer": "...",
#   "confidence": 0.92,
#   "sources": [...],
#   "session_id": "..."
# }
```

### Interactive Mode (Conversation)

```bash
python -m src.main --interactive

# Then type queries:
# > What is machine learning?
# < [Response with sources...]
# > Tell me more about neural networks
# < [Multi-turn response, maintaining context...]
# > exit
```

### With Configuration Options

```bash
# Response format: concise, detailed, technical
python -m src.main \
  --query "latest AI research" \
  --format detailed \
  --preferred-sources arxiv,rag \
  --information-depth comprehensive

# Exclude specific sources
python -m src.main \
  --query "Python tutorial" \
  --exclude-sources web \
  --quality-threshold 0.7
```

---

## Testing

### Unit Tests (Individual Components)

```bash
# Test data models
pytest tests/unit/test_models.py -v

# Test tools
pytest tests/unit/test_tools/test_rag_tool.py -v
pytest tests/unit/test_tools/test_firecrawl_tool.py -v
pytest tests/unit/test_tools/test_arxiv_tool.py -v
pytest tests/unit/test_tools/test_memory_tool.py -v

# Test agents
pytest tests/unit/test_agents.py -v

# Run all unit tests
pytest tests/unit/ -v
```

### Integration Tests (Complete Workflows)

```bash
# Test end-to-end query processing
pytest tests/integration/test_orchestration.py -v

# Test context flow through pipeline
pytest tests/integration/test_context_flow.py -v

# Test memory persistence
pytest tests/integration/test_memory_integration.py -v

# Run all integration tests
pytest tests/integration/ -v
```

### Contract Tests (Tool Interfaces)

```bash
# Verify tools implement contracts correctly
pytest tests/contract/test_tool_contracts.py -v

# Verify agent communication contracts
pytest tests/contract/test_agent_contracts.py -v
```

### Coverage Report

```bash
# Generate coverage report
pytest --cov=src --cov-report=html

# View report
open htmlcov/index.html  # On macOS: open
# On Windows: start htmlcov/index.html
```

---

## Architecture Overview

### Directory Structure

```
src/
├── main.py              # CLI entry point
├── config.py            # Configuration management
├── logging_config.py    # Logging setup
│
├── models/
│   ├── query.py        # Query, QueryPreferences
│   ├── context.py      # ContextChunk, AggregatedContext, FilteredContext
│   ├── response.py     # FinalResponse, ResponseSection
│   └── memory.py       # ConversationHistory, Entity
│
├── agents/
│   ├── __init__.py
│   ├── retriever.py    # Retriever agent
│   ├── evaluator.py    # Evaluator agent
│   ├── synthesizer.py  # Synthesizer agent
│   └── memory.py       # Memory agent
│
├── tasks/
│   ├── __init__.py
│   ├── retrieval.py    # Retrieval task definition
│   ├── evaluation.py   # Evaluation task definition
│   ├── synthesis.py    # Synthesis task definition
│   └── memory_update.py # Memory update task definition
│
├── tools/
│   ├── __init__.py
│   ├── base.py         # Tool base class and interface
│   ├── rag_tool.py     # Milvus search implementation
│   ├── firecrawl_tool.py # Web search implementation
│   ├── arxiv_tool.py   # Academic paper search implementation
│   └── memory_tool.py  # Zep memory interaction implementation
│
├── services/
│   ├── __init__.py
│   ├── orchestrator.py # CrewAI workflow orchestration
│   ├── quality_scorer.py # Quality scoring for filtering
│   └── response_formatter.py # Response formatting utilities
│
└── utils/
    ├── __init__.py
    ├── validators.py   # Data validation
    ├── embeddings.py   # Embedding generation
    └── logger.py       # Logging utilities

tests/
├── unit/
│   ├── test_models.py
│   ├── test_agents.py
│   ├── test_tasks.py
│   └── test_tools/
│       ├── test_rag_tool.py
│       ├── test_firecrawl_tool.py
│       ├── test_arxiv_tool.py
│       └── test_memory_tool.py
├── integration/
│   ├── test_orchestration.py
│   ├── test_context_flow.py
│   └── test_memory_integration.py
└── contract/
    ├── test_tool_contracts.py
    └── test_agent_contracts.py

specs/
├── 001-context-aware-research/
│   ├── spec.md          # Feature specification
│   ├── plan.md          # Implementation plan (this document)
│   ├── research.md      # Research & design decisions
│   ├── data-model.md    # Data model definitions
│   ├── contracts/       # API and tool contracts
│   │   ├── agents.md
│   │   └── tools.md
│   └── quickstart.md    # This file
```

### Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      User Query Input                           │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Query Validation     │
                    │ Session Setup        │
                    │ Load Preferences     │
                    └──────────┬───────────┘
                               │
                               ▼
        ┌──────────────────────────────────────────────┐
        │      RETRIEVER AGENT (Parallel Phase)       │
        │  ┌─────────────┐  ┌──────────────────┐     │
        │  │  RAG Tool   │  │ Firecrawl Tool   │     │
        │  │  (Milvus)   │  │  (Web Search)    │     │
        │  └─────────────┘  └──────────────────┘     │
        │  ┌─────────────┐  ┌──────────────────┐     │
        │  │  Arxiv Tool │  │  Memory Tool     │     │
        │  │  (Papers)   │  │  (Zep)           │     │
        │  └─────────────┘  └──────────────────┘     │
        └──────────┬───────────────────────────────────┘
                   │
                   ▼
        ┌──────────────────────────────────────────┐
        │   AggregatedContext                      │
        │   (All chunks from all sources)          │
        └──────────┬───────────────────────────────┘
                   │
                   ▼
        ┌──────────────────────────────────────────┐
        │      EVALUATOR AGENT                     │
        │  ├─ Calculate quality scores             │
        │  ├─ Remove low-quality chunks            │
        │  ├─ Detect contradictions                │
        │  └─ Deduplicate content                  │
        └──────────┬───────────────────────────────┘
                   │
                   ▼
        ┌──────────────────────────────────────────┐
        │   FilteredContext                        │
        │   (High-quality chunks ready for synthesis)
        └──────────┬───────────────────────────────┘
                   │
                   ▼
        ┌──────────────────────────────────────────┐
        │      SYNTHESIZER AGENT                   │
        │  ├─ Structure answer                     │
        │  ├─ Add citations                        │
        │  ├─ Handle contradictions                │
        │  └─ Calculate confidence                 │
        └──────────┬───────────────────────────────┘
                   │
                   ▼
        ┌──────────────────────────────────────────┐
        │   FinalResponse                          │
        │   (Structured answer with sources)       │
        └──────────┬───────────────────────────────┘
                   │
                   ▼
        ┌──────────────────────────────────────────┐
        │      MEMORY AGENT                        │
        │  ├─ Store in Zep                         │
        │  ├─ Extract entities                     │
        │  ├─ Update preferences                   │
        │  └─ Maintain knowledge graph             │
        └──────────┬───────────────────────────────┘
                   │
                   ▼
        ┌──────────────────────────────────────────┐
        │   Return to User                         │
        │   (JSON response with metadata)          │
        └──────────────────────────────────────────┘
```

---

## Development Workflow

### 1. Add a New Tool

```python
# src/tools/newtool.py
from .base import Tool, ContextChunk
from typing import List

class NewTool(Tool):
    name = "new_tool"
    description = "Retrieve context from new source"
    
    async def execute(self, query: str, **kwargs) -> List[ContextChunk]:
        # Implement tool logic
        # Return List[ContextChunk] or [] on error
        # NEVER raise exceptions
        pass

# src/agents/retriever.py - Update to include new tool
async def retrieve_context(query: str):
    results = await asyncio.gather(
        rag_tool.execute(query),
        firecrawl_tool.execute(query),
        arxiv_tool.execute(query),
        memory_tool.execute(query),
        new_tool.execute(query),  # Add here
    )
```

### 2. Modify Response Format

```python
# src/models/response.py - Update FinalResponse class
class FinalResponse(BaseModel):
    # Existing fields...
    new_field: str  # Add your field

# src/services/response_formatter.py - Update formatting logic
def format_response(response: FinalResponse) -> Dict:
    # Update formatting to include new_field
    pass
```

### 3. Add Quality Metric

```python
# src/services/quality_scorer.py
def calculate_quality_score(chunk: ContextChunk) -> float:
    # Add new metric to scoring calculation
    # Update weights as needed
    pass
```

### 4. Write Tests

```python
# tests/unit/test_new_feature.py
import pytest
from src.models import ...

@pytest.mark.asyncio
async def test_new_feature():
    # Arrange
    # Act
    # Assert
    pass

# Run test
pytest tests/unit/test_new_feature.py -v
```

---

## Troubleshooting

### Milvus Connection Error

```
Error: Failed to connect to Milvus at localhost:19530
```

**Solution**:
```bash
# Check Milvus is running
docker ps | grep milvus

# Start Milvus if not running
docker run -d --name milvus -p 19530:19530 milvusdb/milvus:latest

# Verify connection
python -c "from pymilvus import connections; connections.connect(host='localhost', port=19530); print('Connected')"
```

### Zep Connection Error

```
Error: Failed to connect to Zep at http://localhost:8000
```

**Solution**:
```bash
# Check Zep is running
docker ps | grep zep

# Start Zep if not running
docker run -d --name zep -p 8000:8000 getzep/zep:latest

# Verify connection
python -c "from zep_python import ZepClient; client = ZepClient(api_url='http://localhost:8000'); print('Connected')"
```

### API Key Issues

```
Error: OPENAI_API_KEY not set
```

**Solution**:
```bash
# Verify .env file exists and has correct keys
cat .env | grep OPENAI_API_KEY

# If missing, add to .env
echo "OPENAI_API_KEY=sk-..." >> .env

# Reload environment
source venv/bin/activate
# Or restart Python process
```

### Slow Queries

**Check Milvus indexing**:
```bash
# Connect to Milvus and verify index
python scripts/check_milvus_index.py
```

**Tune retrieval timeouts** in `.env`:
```env
RAG_TIMEOUT=5.0
WEB_TIMEOUT=7.0
ARXIV_TIMEOUT=6.0
```

---

## Next Steps

1. **Phase 2**: Run `/speckit.tasks` to generate detailed implementation tasks
2. **Development**: Begin implementation following task list
3. **Testing**: Run tests frequently using commands above
4. **Integration**: Connect to REST API layer once core system stable
5. **Deployment**: Package and deploy as service

---

## Additional Resources

- **crewAI**: https://docs.crewai.com/
- **Milvus**: https://milvus.io/docs/
- **Zep**: https://docs.getzep.com/
- **Firecrawl**: https://firecrawl.dev/
- **arXiv API**: https://arxiv.org/help/api
- **OpenAI**: https://platform.openai.com/docs/

---

## Support

For issues or questions:
1. Check troubleshooting section above
2. Review test files for usage examples
3. Check logs: `LOG_LEVEL=DEBUG python -m src.main --query "..."`
4. Consult specification at `specs/001-context-aware-research/spec.md`

Ready to start development! 🚀
