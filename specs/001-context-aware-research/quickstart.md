# Quickstart Guide: Context-Aware Research Assistant

**Version**: 1.0  
**Date**: November 13, 2025  
**Status**: Ready for Development

---

## Project Overview

The Context-Aware Research Assistant is a Streamlit web application that answers user research queries by orchestrating parallel retrieval from multiple sources (internal documents, web, academic papers, and memory) using crewAI agents.

**Architecture**: 
- **UI**: Streamlit multi-page web application
- **Orchestration**: crewAI agents (Retriever, Evaluator, Synthesizer, Memory)
- **Storage**: Milvus (vector DB), Zep (conversation memory)
- **Language**: Python 3.10+
- **Deployment**: Standalone web service (deployable on local machine or cloud)

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

### Dependencies

The `requirements.txt` includes:

```
# Core Framework
crewai==0.31.0
crewai-tools==0.1.0

# Streamlit Web UI
streamlit==1.28.0

# Vector Database
pymilvus==2.3.0

# Data Source APIs
firecrawl-python==0.0.1
arxiv==2.1.0

# Memory Service
zep-python==0.36.0

# LLM & Embeddings
openai==1.3.0

# Configuration & Environment
python-dotenv==1.0.0

# Data & Serialization
pydantic==2.0.0

# Async Support
aiohttp==3.9.0
asyncio-contextmanager==1.0.0

# Utilities
requests==2.31.0
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

### Start Streamlit Web App

```bash
# Launch the Streamlit application (opens in browser)
streamlit run src/app.py

# The app will be available at: http://localhost:8501
```

### Using the Web Interface

**Main Research Page** (`/research`):
1. Enter your research query in the text input
2. Click "Search" or press Enter
3. Watch as the system retrieves from 4 sources in parallel
4. View the synthesized answer with:
   - Main answer text
   - Confidence score
   - Source citations
   - Breakdown by source

**Conversation History** (`/conversation`):
1. Browse all previous queries and responses
2. Click on a prior query to view full context
3. Continue conversations from previous points
4. Manage conversation sessions

**Entity Browser** (`/entities`):
1. View all extracted entities from conversations
2. See entity relationships and knowledge graph
3. Track topic mentions across interactions
4. Search for specific entities or relationships


### Streamlit Configuration

You can customize the app behavior via `streamlit_config.toml`:

```toml
[client]
showErrorDetails = true

[logger]
level = "info"

[theme]
primaryColor = "#0066ff"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"

[server]
maxUploadSize = 200
enableXsrfProtection = true
```

---

## Development Workflow (MVP - Manual Testing)

### Testing Features Locally

**Manual Query Testing**:
1. Open Streamlit app: `streamlit run src/app.py`
2. Submit various research queries
3. Verify responses include:
   - Main answer text
   - Confidence score (0-1)
   - Source citations with URLs
   - Retrieval time under 30 seconds

**Testing Multi-turn Conversations**:
1. Submit initial query
2. Verify response appears in Conversation History page
3. Submit follow-up query related to first
4. Verify context from previous query is incorporated
5. Check that Zep memory correctly retrieved prior context

**Testing Entity Tracking**:
1. Submit queries that mention specific people/organizations/concepts
2. Visit Entity Browser page
3. Verify entities were extracted and stored
4. Check entity relationships are tracked
5. Verify subsequent queries reference related entities

**Testing Source Preferences**:
1. Go back to Conversation History
2. For any past query, adjust source preferences
3. Re-run query (simulated by new similar query)
4. Verify different sources are prioritized

### Debugging

Check logs for errors:
```bash
# Streamlit logs appear in terminal running the app
# Look for:
# - Tool timeouts (if source takes >7s)
# - Milvus connection errors
# - Zep memory errors
# - Agent response issues

# Add debug logging temporarily:
# In src/config.py, set LOG_LEVEL = "DEBUG"
```

---

## Architecture Overview

### Directory Structure

```
src/
├── app.py               # Streamlit main entry point
├── pages/               # Streamlit multi-page app
│   ├── research.py      # /research - main query interface
│   ├── conversation.py  # /conversation - history browser
│   └── entities.py      # /entities - entity graph viewer
├── config.py            # Configuration management
├── logging_config.py    # Logging setup
│
├── models/
│   ├── query.py        # Query, QueryPreferences
│   ├── context.py      # ContextChunk, AggregatedContext, FilteredContext
│   ├── response.py     # FinalResponse, ResponseSection
│   └── memory.py       # ConversationHistory, Entity
│
├── pages/
│   ├── __init__.py
│   ├── research.py     # Main research query page
│   ├── conversation.py # Conversation history browser
│   └── entities.py     # Entity relationship viewer
│
├── ui/
│   ├── __init__.py
│   ├── components.py   # Reusable Streamlit components
│   └── styles.py       # Styling and theming
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
