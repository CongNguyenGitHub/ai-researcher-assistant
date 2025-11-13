# Implementation Plan: Context-Aware Research Assistant

**Branch**: `001-context-aware-research` | **Date**: November 13, 2025 | **Spec**: [specs/001-context-aware-research/spec.md](./spec.md)
**Input**: Feature specification from `specs/001-context-aware-research/spec.md`

**Note**: This plan is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

The Context-Aware Research Assistant is a crewAI-orchestrated system that accepts user research queries and synthesizes comprehensive answers by gathering context in parallel from four distinct sources: an internal knowledge base (Milvus vector database with RAG), real-time web search (Firecrawl), academic literature (Arxiv API), and user-specific conversation history (Zep Memory). An Evaluator agent filters aggregated context to remove low-quality information, and a Synthesizer agent produces the final structured response. The system updates memory for future interactions, maintaining conversation continuity and user preferences. Built in Python with crewAI orchestration, deployed as a command-line tool with REST API capabilities.

## Technical Context

**Language/Version**: Python 3.10+  
**Primary Dependencies**: crewai, crewai-tools, python-dotenv, pymilvus, firecrawl-python, arxiv, zep-python  
**Storage**: Milvus (vector database for RAG), Zep Memory (conversation/entity storage), external (Firecrawl/Arxiv APIs)  
**Testing**: pytest for unit tests, integration tests for agent workflows  
**Target Platform**: Linux/Mac/Windows server, CLI-based with extensible REST API  
**Project Type**: Single Python project (backend orchestration service)  
**Performance Goals**: <30 second response time per query, parallel execution across 4 sources  
**Constraints**: <30 second total latency, graceful degradation if any single source fails, maintain context coherence across multi-turn conversations  
**Scale/Scope**: MVP supports single-user/multi-turn conversations, designed for future scaling to multi-user with request queueing

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Status**: PASS (No constitution defined yet - recommend establishing governance principles for this research assistant project)

The Constitution framework is not yet established for this project. Recommended principles to define:

1. **Test-First Development**: TDD required for all agent behaviors and tool implementations
2. **Agent Observability**: Structured logging of agent decisions, tool calls, and context filtering rationale
3. **Contract-Driven**: Clear API contracts for all tools and inter-agent communication
4. **Source Attribution**: All responses must maintain source citations and confidence scores
5. **Graceful Degradation**: System must continue functioning when individual sources fail

*Note: Establish formal constitution in `.specify/memory/constitution.md` for governance and future enforcement*

## Project Structure

### Documentation (this feature)

```text
specs/001-context-aware-research/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   ├── agents.yaml      # crewAI agent definitions
│   ├── tools.yaml       # Tool contract specifications
│   └── api.openapi.yaml # REST API specification (if REST interface added)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
├── main.py              # Main orchestration entry point
├── agents.py            # Evaluator and Synthesizer agent definitions
├── tasks.py             # Agent task definitions
├── models/
│   ├── query.py         # Query and response data models
│   ├── context.py       # Context, chunk, and filtering models
│   └── memory.py        # Memory and entity models
├── services/
│   ├── orchestrator.py   # CrewAI workflow orchestration
│   ├── evaluator.py     # Context evaluation logic
│   └── synthesizer.py   # Response synthesis logic
├── tools/
│   ├── __init__.py
│   ├── rag_tool.py      # Milvus vector DB queries
│   ├── firecrawl_tool.py # Firecrawl web search integration
│   ├── arxiv_tool.py    # Arxiv academic search integration
│   └── memory_tool.py   # Zep memory interactions
├── config.py            # Configuration and environment setup
├── logging_config.py    # Structured logging configuration
└── utils/
    ├── __init__.py
    ├── validators.py    # Data validation utilities
    └── formatters.py    # Response formatting utilities

tests/
├── unit/
│   ├── test_agents.py
│   ├── test_tasks.py
│   ├── test_models.py
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

.env.example            # Example environment configuration
requirements.txt        # Python dependencies
pyproject.toml         # Project metadata and configuration
```

**Structure Decision**: Single Python project with layered architecture (models → tools → services → agents → orchestration). The modular design allows:
- Independent testing of each tool and agent
- Easy addition of new context sources (new tools)
- Clear separation of concerns (models, services, agents)
- Extensible to REST API without core changes
- Supports both CLI and programmatic usage

This aligns with the crewAI framework patterns and your proposed file structure while adding proper organization for models, services, and comprehensive testing layers.


## Phase 0: Research & Unknowns Resolution

Phase 0 will resolve the following research areas identified from the specification and technical context:

### Research Tasks

1. **CrewAI Best Practices for Multi-Agent Orchestration**
   - Task: Research optimal crewAI patterns for parallel task execution and inter-agent communication
   - Deliverable: research.md section on agent communication patterns and error handling

2. **Milvus Vector Database Integration**
   - Task: Best practices for Milvus integration in Python, connection pooling, and query optimization
   - Deliverable: research.md section on Milvus setup, chunking strategy, and query patterns

3. **Context Filtering and Quality Metrics**
   - Task: Define metrics for "low-quality" context - source reputation, recency, semantic relevance
   - Deliverable: research.md section on filtering heuristics and evaluation criteria

4. **Handling Contradictory Information**
   - Task: Research patterns for surfacing and reconciling contradictory sources in synthesis
   - Deliverable: research.md section on contradiction handling strategies

5. **Structured Response Format Design**
   - Task: Define JSON schema for final responses including citations, confidence scores, source attribution
   - Deliverable: research.md with schema definition and validation rules

6. **Zep Memory Integration Patterns**
   - Task: Best practices for conversation history, entity relationship graphs, user preference storage
   - Deliverable: research.md section on memory schema and retrieval patterns

7. **Error Resilience and Graceful Degradation**
   - Task: Patterns for handling individual source failures, fallback strategies
   - Deliverable: research.md section on resilience patterns and testing strategies

**Output**: `research.md` file with all NEEDS CLARIFICATION items resolved and decision rationales documented.

## Phase 1: Design & Contracts

Phase 1 will finalize the system design and define all contracts for agent communication and tool interfaces.

### 1.1 Data Model Design (`data-model.md`)

Extract and define all entities from feature spec:

**Core Entities**:
- **Query**: User research question with metadata (user_id, timestamp, session_id)
- **ContextChunk**: Individual piece of context (source, text, confidence_score, relevance_score, metadata)
- **AggregatedContext**: Collection of context chunks from all sources with source attribution
- **FilteredContext**: High-quality subset after evaluation with filtering rationale
- **FinalResponse**: Structured answer with citations, confidence levels, source attribution
- **ConversationHistory**: Prior interactions, extracted insights, session context
- **UserPreferences**: Response format preferences, information depth, source preferences, topic interests
- **Entity**: Named concepts with relationships for knowledge graph

**State Transitions**:
```
Query → [Parallel Retrieval] → AggregatedContext → [Evaluation] → FilteredContext → [Synthesis] → FinalResponse → [Memory Update]
```

**Validation Rules**:
- Query text must be non-empty, <5000 characters
- Context chunks must have source attribution and confidence scores (0-1)
- Filtered context must have filtering rationale for removed items
- Final response must cite sources and include confidence levels
- Entity relationships must be bidirectional and versioned

### 1.2 API Contracts (`contracts/`)

Define contracts for:

**agents.yaml** - CrewAI Agent definitions:
- Evaluator Agent: Analyzes context quality, produces filter decisions
- Synthesizer Agent: Consumes filtered context, produces structured responses
- Orchestrator: Coordinates parallel retrieval and sequential evaluation/synthesis

**tools.yaml** - Tool specifications:
- RAG Tool: Query Milvus with semantic similarity, return top-k chunks
- Firecrawl Tool: Execute web searches, parse results into context chunks
- Arxiv Tool: Search academic papers, fetch summaries and citations
- Memory Tool: Store/retrieve conversation history and entity relationships

**api.openapi.yaml** - REST endpoints (if REST layer added):
- POST /query: Submit research query
- GET /query/{id}: Retrieve query status and response
- POST /conversation: Start new conversation session
- GET /memory/entities: Browse stored entities

### 1.3 Agent Context Update

Run update script to register new technologies in AI context:
```bash
.specify/scripts/powershell/update-agent-context.ps1 -AgentType copilot
```

This will update agent-specific context files with:
- crewAI framework patterns and best practices
- Tool integration patterns for Milvus, Firecrawl, Arxiv, Zep
- Python project structure and testing patterns
- Multi-agent orchestration patterns

### 1.4 Quickstart Guide (`quickstart.md`)

Create developer quickstart including:
- Environment setup (.env configuration)
- Installing dependencies (requirements.txt)
- Running the basic workflow
- Testing individual tools
- Extending with new sources
- Integration examples

## Key Design Decisions

1. **crewAI Orchestration**: Use crewAI agents for clean separation of concerns (Evaluator vs Synthesizer) and easy extensibility
2. **Parallel Retrieval**: All four sources queried concurrently to meet <30s response time
3. **Modular Tools**: Each data source as independent tool with own error handling and retry logic
4. **Structured Responses**: JSON-based with confidence scores and source citations for reliability
5. **Graceful Degradation**: System continues with available sources if any single source fails
6. **Memory Integration**: Zep handles both conversation history and entity relationship tracking

## Next Steps

After Phase 1 completion:
1. All NEEDS CLARIFICATION items resolved in research.md
2. Data model fully specified in data-model.md
3. API contracts defined in contracts/ directory
4. Agent context updated with new technologies
5. Quickstart guide ready for developers
6. Ready for Phase 2: `/speckit.tasks` to generate detailed implementation tasks
