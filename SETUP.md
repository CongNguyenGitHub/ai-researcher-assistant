# Setup Guide: Context-Aware Research Assistant

**Version**: 0.1.0-mvp  
**Last Updated**: November 13, 2025  
**Status**: Production Ready

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start (Docker)](#quick-start-docker)
3. [Manual Installation](#manual-installation)
4. [Configuration](#configuration)
5. [Running the System](#running-the-system)
6. [Testing](#testing)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements
- **OS**: Windows, macOS, or Linux
- **Python**: 3.10 or higher
- **Docker**: (Optional, for containerized setup)
- **Memory**: 8GB minimum, 16GB recommended
- **Storage**: 10GB for vector database

### External Services
- **Milvus Vector Database**: 2.3 or higher
- **Zep Memory Service**: 2.0 or higher
- **API Keys Required**:
  - Google Gemini API key
  - Firecrawl API key (optional, for web search)
  - Arxiv API (free, no key needed)

---

## Quick Start (Docker)

### 1. Clone & Setup

```bash
git clone <repository-url>
cd "AI Research Assisstant"
```

### 2. Environment Configuration

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your API keys
# Required:
#   GOOGLE_API_KEY=your-gemini-api-key
#   FIRECRAWL_API_KEY=your-firecrawl-key (optional)
```

### 3. Start Services

```bash
# Start Milvus and Zep with Docker Compose
docker-compose up -d

# Wait for services to be ready (30-60 seconds)
docker-compose logs -f milvus
```

### 4. Install Python Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 5. Run the Application

```bash
# Start Streamlit UI
streamlit run src/pages/search.py

# Open browser: http://localhost:8501
```

---

## Manual Installation

### Step 1: Python Environment

```bash
# Create virtual environment
python3.10 -m venv venv
source venv/bin/activate  # macOS/Linux
# OR
venv\Scripts\activate  # Windows

# Verify Python version
python --version  # Should be 3.10+
```

### Step 2: Install Dependencies

```bash
# Install core dependencies
pip install -r requirements.txt

# Core packages:
# - crewai>=0.35.0
# - python-dotenv>=1.0.0
# - pymilvus>=2.3.0
# - firecrawl-python>=1.0.0
# - arxiv>=1.4.0
# - zep-python>=2.0.0
# - streamlit>=1.28.0
# - pytest>=9.0.0
# - pydantic>=2.0.0
```

### Step 3: Milvus Setup

**Option A: Docker Container**
```bash
docker run -d --name milvus \
  -p 19530:19530 \
  -p 9091:9091 \
  -e COMMON_STORAGETYPE=local \
  milvusdb/milvus:v2.3.0
```

**Option B: Docker Compose**
```bash
docker-compose up -d milvus
```

**Option C: Local Installation** (Advanced)
See: https://milvus.io/docs/install_standalone.md

### Step 4: Zep Memory Setup

**Option A: Docker Container**
```bash
docker run -d --name zep \
  -p 8000:8000 \
  -p 8001:8001 \
  getzep/zep:latest
```

**Option B: Docker Compose**
```bash
docker-compose up -d zep
```

### Step 5: Verify Connectivity

```bash
# Test Milvus connection
python -c "from pymilvus import connections; connections.connect('default', host='localhost', port=19530); print('Milvus OK')"

# Test Zep connection
curl http://localhost:8000/health

# Test Google Gemini API
python -c "import google.generativeai as genai; genai.configure(api_key='YOUR_KEY'); print('Gemini OK')"
```

---

## Configuration

### Environment Variables (.env)

```bash
# Google Gemini API
GOOGLE_API_KEY=sk-...your-key...

# Firecrawl (optional)
FIRECRAWL_API_KEY=your-firecrawl-key

# Milvus Connection
MILVUS_HOST=localhost
MILVUS_PORT=19530

# Zep Memory
ZEP_API_URL=http://localhost:8000

# System Configuration
LOG_LEVEL=INFO
MAX_WORKERS=4
RESPONSE_TIMEOUT_SECONDS=30
QUALITY_THRESHOLD=0.6

# Optional Features
ENABLE_MEMORY_PERSISTENCE=true
ENABLE_PERFORMANCE_LOGGING=true
ENABLE_CONTRADICTION_DETECTION=true
```

### .env.example

See `.env.example` for full template with all available options.

### Configuration File Locations

```
project-root/
├── .env                    # Your secrets (NOT in git)
├── .env.example            # Template (in git)
├── config/
│   ├── logging.yaml        # Logging configuration
│   └── streamlit_config.toml # Streamlit settings
└── src/
    └── config.py           # Python config module
```

---

## Running the System

### Option 1: Streamlit Web UI (Recommended)

```bash
# Activate virtual environment
source venv/bin/activate

# Start Streamlit
streamlit run src/pages/search.py

# Open browser to http://localhost:8501
```

**Features Available**:
- Submit research queries
- View responses with citations
- Browse conversation history
- Track entity relationships

### Option 2: Python Script

```python
from src.services.orchestrator import Orchestrator
from src.models.query import Query

# Initialize orchestrator
orchestrator = Orchestrator()

# Create query
query = Query(
    user_id="user-1",
    session_id="session-1",
    text="What are recent advances in machine learning?"
)

# Process query
response = orchestrator.process_query(query)

# Print response
print(f"Answer: {response.answer}")
print(f"Confidence: {response.overall_confidence:.2%}")
print(f"Sources: {len(response.sources)}")
```

### Option 3: API (If Deployed)

```bash
# Submit query
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-1",
    "session_id": "session-1",
    "text": "What is quantum computing?"
  }'

# Response includes:
# - answer: string
# - sections: array of sections
# - sources: array with attributions
# - confidence: float 0-1
# - alternatives: array of conflicting perspectives
```

---

## Testing

### Unit Tests

```bash
# Run all unit tests
pytest tests/ -v

# Run specific test file
pytest tests/test_phase7_integration.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

### Integration Tests

```bash
# Run Phase 4 tests (Retrieval)
pytest tests/test_phase4_integration.py -v

# Run Phase 5 tests (Evaluation)
pytest tests/test_phase5_integration.py -v

# Run Phase 6 tests (Synthesis)
pytest tests/test_phase6_integration.py -v

# Run Phase 7 tests (Orchestration)
pytest tests/test_phase7_integration.py -v
```

### Manual Testing

See `MANUAL_TESTING_GUIDE.md` for comprehensive test scenarios.

```bash
# Quick smoke test
python -m pytest tests/test_phase7_integration.py::TestPhase7AcceptanceCriteria::test_ac_p7_001_complete_workflow_execution -v
```

---

## Troubleshooting

### Milvus Connection Failed

**Error**: `Failed to connect to Milvus`

**Solutions**:
```bash
# Check if container is running
docker ps | grep milvus

# Check logs
docker logs milvus

# Verify port is open
lsof -i :19530  # macOS/Linux
netstat -ano | findstr :19530  # Windows

# Restart service
docker restart milvus
```

### Zep Connection Failed

**Error**: `Failed to connect to Zep Memory service`

**Solutions**:
```bash
# Check if container is running
docker ps | grep zep

# Verify connectivity
curl http://localhost:8000/health

# Check logs
docker logs zep

# Restart service
docker restart zep
```

### Google Gemini API Error

**Error**: `Invalid API key` or `Quota exceeded`

**Solutions**:
1. Verify API key in `.env`: `GOOGLE_API_KEY=sk-...`
2. Check API key is for Generative AI (not other services)
3. Verify quota at: https://console.cloud.google.com/
4. Regenerate key if necessary

### Streamlit Port Conflict

**Error**: `Port 8501 already in use`

**Solutions**:
```bash
# Use different port
streamlit run src/pages/search.py --server.port 8502

# Or kill process using port
lsof -i :8501  # Find process ID
kill -9 <PID>   # Kill it
```

### Memory Usage High

**Error**: Vector database consuming excessive memory

**Solutions**:
```bash
# Check Milvus memory
docker stats milvus

# Reduce collection size
# Remove old documents from Milvus

# Increase Docker memory limit
# In docker-compose.yml: mem_limit: 8gb
```

### Tests Failing

**Error**: Tests pass locally but fail in CI

**Common Causes**:
- Missing environment variables → Set in CI/CD secrets
- Service connectivity issues → Verify Milvus/Zep running
- Python version mismatch → Use Python 3.10+
- Missing dependencies → Run `pip install -r requirements.txt`

**Debug Steps**:
```bash
# Run with verbose output
pytest tests/ -vv -s

# Run single failing test
pytest tests/test_specific.py::TestClass::test_method -vv

# Check imports
python -c "import src.services.orchestrator; print('Import OK')"
```

---

## Next Steps

1. **Upload Documents**: Use Streamlit UI to upload PDFs/documents
2. **Index Documents**: System automatically indexes with embeddings
3. **Submit Queries**: Ask research questions
4. **Review Responses**: Check answers with citations
5. **Track History**: View conversation history and entities

---

## Support & Documentation

- **Architecture**: See `ARCHITECTURE.md`
- **Testing**: See `MANUAL_TESTING_GUIDE.md`
- **Specification**: See `specs/001-context-aware-research/spec.md`
- **API Docs**: See inline docstrings in `src/`

---

## Version History

- **v0.1.0-mvp** (Nov 13, 2025): Initial release with Phases 0-7 complete
  - Multi-source parallel retrieval
  - Context evaluation & filtering
  - Response synthesis with citations
  - Workflow orchestration
  - Full error handling

---

**Setup Complete!** 🎉

You're now ready to use the Context-Aware Research Assistant. Start with the Streamlit UI and follow the on-screen prompts.

Questions? Check troubleshooting section or review inline code documentation.
