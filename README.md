# AI Research Assistant

AI-powered research tool with multi-source retrieval and intelligent synthesis.

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 3. Start application
streamlit run src/pages/search.py
```

Open browser at `http://localhost:8501`

---

## Environment Variables

Required in `.env`:

```bash
# Google Gemini API
GOOGLE_API_KEY=your_api_key_here

# Milvus Vector Database
MILVUS_HOST=localhost
MILVUS_PORT=19530

# Zep Memory (optional)
ZEP_API_URL=http://localhost:8000
ZEP_API_KEY=your_zep_key

# Firecrawl (optional)
FIRECRAWL_API_KEY=your_firecrawl_key
```

---

## Features

- **Multi-Source Retrieval**: RAG (Milvus), Web (Firecrawl), Academic (Arxiv), Memory (Zep)
- **Quality Evaluation**: Reputation, recency, relevance, deduplication scoring
- **Citation Tracking**: Complete source attribution with confidence scores
- **Contradiction Detection**: Identifies and documents conflicting information
- **Performance**: ~15-20 second response time

---

## Project Structure

```
src/
├── services/       # Core logic (orchestrator, evaluator, synthesizer)
├── models/         # Data models
├── tools/          # Retrieval tools
├── pages/          # Streamlit UI
└── logging_config.py

tests/              # Integration tests (61 tests)
```

---

## Testing

```bash
# Run all tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=src
```

**Status**: 61/61 tests passing ✅

---

## Architecture

Multi-source retrieval → Quality evaluation → Synthesis → Response with citations

All sources run in parallel with graceful degradation if any source fails.

---

## License

MIT

