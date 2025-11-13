# Implementation Plan: Context-Aware Research Assistant

**Branch**: `001-context-aware-research` | **Date**: November 13, 2025 | **Spec**: [specs/001-context-aware-research/spec.md](./spec.md)
**Input**: Feature specification from `specs/001-context-aware-research/spec.md`

**Note**: This plan is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

The Context-Aware Research Assistant is a crewAI-orchestrated system that accepts user research queries and synthesizes comprehensive answers by gathering context in parallel from four distinct sources: an internal knowledge base (Milvus vector database with RAG), real-time web search (Firecrawl), academic literature (Arxiv API), and user-specific conversation history (Zep Memory). An Evaluator agent filters aggregated context to remove low-quality information, and a Synthesizer agent produces the final structured response. The system updates memory for future interactions, maintaining conversation continuity and user preferences. Built in Python with crewAI orchestration, deployed as a Streamlit web application for interactive research sessions.

## Technical Context

**Language/Version**: Python 3.10+  
**Primary Dependencies**: crewai, crewai-tools, python-dotenv, pymilvus, firecrawl-python, arxiv, zep-python, streamlit  
**Storage**: Milvus (vector database for RAG), Zep Memory (conversation/entity storage), external (Firecrawl/Arxiv APIs)  
**Testing**: MVP mode - no automated tests, manual testing only  
**Target Platform**: Linux/Mac/Windows web application (Streamlit), deployable as standalone web service  
**Project Type**: Single Python project (Streamlit web application with backend orchestration)  
**Performance Goals**: <30 second response time per query, parallel execution across 4 sources  
**Constraints**: <30 second total latency, graceful degradation if any single source fails, maintain context coherence across multi-turn conversations  
**Scale/Scope**: MVP supports single-user/multi-turn conversations via web UI, designed for future scaling to multi-user with session management

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
├── app.py               # Streamlit main application entry point
├── pages/
│   ├── research.py      # Main research query interface
│   ├── conversation.py  # Multi-turn conversation history
│   └── entities.py      # Entity browser and knowledge graph
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
├── ui/
│   ├── __init__.py
│   ├── components.py    # Reusable Streamlit components
│   └── styles.py        # UI styling and themes
├── config.py            # Configuration and environment setup
├── logging_config.py    # Structured logging configuration
└── utils/
    ├── __init__.py
    ├── validators.py    # Data validation utilities
    └── formatters.py    # Response formatting utilities

.env.example            # Example environment configuration
requirements.txt        # Python dependencies (includes streamlit)
pyproject.toml         # Project metadata and configuration
streamlit_config.toml  # Streamlit configuration
```

**Structure Decision**: Single Python project with Streamlit web UI and layered backend (models → tools → services → agents → orchestration). The modular design allows:
- Independent testing of each tool and agent (manual testing for MVP)
- Easy addition of new context sources (new tools)
- Clear separation of concerns (UI, models, services, agents)
- Streamlit pages for different features (research, conversation, entities)
- Extensible to multi-page application without core changes
- Supports both Streamlit web interface and programmatic usage


## Phase 0: Research & Unknowns Resolution

Phase 0 will resolve the following research areas identified from the specification and technical context:

### Research Tasks

**CLARIFIED from Spec Session 2025-11-13**: The following research areas now have explicit decisions from specification clarifications and should be updated in research.md:

1. **CrewAI Best Practices for Multi-Agent Orchestration**
   - Task: Research optimal crewAI patterns for parallel task execution and inter-agent communication
   - Clarification: Orchestrator must handle graceful degradation when individual source fails (continue with remaining sources, log failure with timestamp)
   - Deliverable: research.md section on agent communication patterns, error handling, and source failure logging

2. **Milvus Vector Database Integration**
   - Task: Best practices for Milvus integration in Python, connection pooling, and query optimization
   - Deliverable: research.md section on Milvus setup, chunking strategy, and query patterns

3. **Context Filtering and Quality Metrics** ⭐ **CLARIFIED**
   - Task: Define metrics for "low-quality" context filtering
   - **Clarification Decision**: Multi-factor quality scoring formula: **30% source reputation + 20% recency + 40% semantic relevance + 10% deduplication**
   - This scoring directly operationalizes the Evaluator agent's evaluation criteria
   - Deliverable: research.md section detailing how each factor (reputation, recency, relevance, dedup) is computed and weighted

4. **Handling Contradictory Information** ⭐ **CLARIFIED**
   - Task: Research patterns for surfacing and reconciling contradictory sources in synthesis
   - **Clarification Decision**: When sources contradict, Synthesizer MUST:
     - Acknowledge both perspectives with explicit source attribution
     - Explicitly note the contradiction in the response
     - Let the user decide which source/perspective to trust
     - Never choose one source arbitrarily or synthesize false consensus
   - Deliverable: research.md section on contradiction detection, dual-source citation patterns, and user-decision-making support

5. **Structured Response Format Design** ⭐ **CLARIFIED**
   - Task: Define JSON schema for final responses
   - **Clarification Decision**: JSON with **three citation levels**:
     1. Main answer text with source links (URL attribution)
     2. Key claims as array with specific chunk citations and per-claim confidence scores (0.0-1.0)
     3. Overall response confidence score and source availability status
   - Includes metadata: synthesis timestamp, source count, failed/unavailable sources
   - Deliverable: research.md with complete JSON schema definition, validation rules, and examples showing contradiction handling

6. **Zep Memory Integration Patterns**
   - Task: Best practices for conversation history, entity relationship graphs, user preference storage
   - Deliverable: research.md section on memory schema and retrieval patterns

7. **Error Resilience and Graceful Degradation** ⭐ **CLARIFIED**
   - Task: Patterns for handling individual source failures and fallback strategies
   - **Clarification Decisions**:
     - When a single source times out/fails: continue with remaining sources (not fail-fast)
     - Log failure with source name, timestamp, and error details
     - Include source availability status in response (which sources contributed, which were unavailable)
     - When ALL sources return empty: return transparent response explaining no context found, invite user to refine query or provide documents for RAG
   - Deliverable: research.md section on resilience patterns, failure logging strategy, and no-context user guidance

8. **Streamlit UI Best Practices for Research Assistant**
   - Task: Research Streamlit patterns for multi-page apps, session state management, streaming responses
   - Clarification: UI must display source availability status and handle contradiction display gracefully
   - Deliverable: research.md section on Streamlit component patterns, caching strategies, and handling of confidence scores/citations in UI

**Output**: `research.md` file with all NEEDS CLARIFICATION items resolved and decision rationales documented, including all clarified decisions from spec session.

## Phase 1: Design & Contracts

Phase 1 will finalize the system design and define all contracts for agent communication and tool interfaces.

### 1.1 Data Model Design (`data-model.md`)

Extract and define all entities from feature spec:

**Core Entities**:
- **Query**: User research question with metadata (user_id, timestamp, session_id)
- **ContextChunk**: Individual piece of context (source, text, confidence_score, relevance_score, metadata)
- **AggregatedContext**: Collection of context chunks from all sources with source attribution
- **FilteredContext**: High-quality subset after evaluation using multi-factor scoring (30% reputation + 20% recency + 40% relevance + 10% dedup), includes filtering rationale for removed items
- **FinalResponse**: Structured JSON answer with **three citation levels**: (1) main answer text with source links, (2) key claims array with per-claim confidence scores and chunk citations, (3) overall response confidence and source availability status. Includes metadata (timestamp, source count, failed sources). Handles contradictions by documenting conflicting claims with dual-source attribution.
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
- Filtered context must have filtering rationale and quality scores based on formula (30% reputation + 20% recency + 40% relevance + 10% dedup)
- Final response must cite sources at three levels: main answer URLs, per-claim chunk citations, per-claim confidence scores (0-1)
- Contradictory claims must explicitly document both sources and let user decide
- Source availability must be tracked and reported (which sources succeeded, which failed/timed out)
- Entity relationships must be bidirectional and versioned

### 1.2 API Contracts (`contracts/`)

Define contracts for:

**agents.yaml** - CrewAI Agent definitions:
- Evaluator Agent: 
  - Input: AggregatedContext (chunks from all sources)
  - Process: Apply multi-factor quality scoring (30% source reputation + 20% recency + 40% relevance + 10% dedup)
  - Output: FilteredContext with quality scores and filtering rationale for removed items
- Synthesizer Agent: 
  - Input: FilteredContext
  - Process: Generate structured JSON response with three citation levels; detect and explicitly document contradictions
  - Output: FinalResponse with main answer, key claims with per-claim citations and confidence, overall confidence, source availability status
- Orchestrator: 
  - Coordinates parallel retrieval from all 4 sources
  - On source timeout/failure: continue with remaining sources, log failure (timestamp, source name, error), include source status in final response
  - On all sources empty: return transparent response explaining no context found, invite user to refine query or seed RAG

**tools.yaml** - Tool specifications:
- RAG Tool: Query Milvus with semantic similarity, return top-k chunks with confidence scores
- Firecrawl Tool: Execute web searches, parse results into context chunks with recency metadata
- Arxiv Tool: Search academic papers, fetch summaries and citations with source reputation metadata
- Memory Tool: Store/retrieve conversation history and entity relationships

**api.openapi.yaml** - REST endpoints (if REST layer added):
- POST /query: Submit research query
- GET /query/{id}: Retrieve query status and response (with source availability and contradiction handling)
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

1. **crewAI Orchestration**: Use crewAI agents for clean separation of concerns (Evaluator vs Synthesizer) and easy extensibility. Orchestrator handles parallel retrieval with graceful degradation.
2. **Quality Filtering Formula**: Evaluator uses multi-factor scoring **30% source reputation + 20% recency + 40% semantic relevance + 10% deduplication** to operationalize "low-quality" filtering.
3. **Contradiction Handling**: Synthesizer explicitly documents contradictory sources with dual attribution and lets user decide (never arbitrarily chooses one source or falsely synthesizes consensus).
4. **Three-Level Citations**: Final response uses JSON with three citation levels: (1) main answer with source URLs, (2) key claims with chunk citations, (3) per-claim confidence scores (0-1) enabling both casual reading and deep verification.
5. **Graceful Degradation**: System continues with available sources if any single source fails; logs failure with timestamp/source name; includes source availability status in response. When all sources empty, returns transparent guidance.
6. **Source Failure Handling**: Individual source timeouts don't block workflow; system logs the failure and continues with remaining sources rather than failing fast.
7. **Memory Integration**: Zep handles both conversation history and entity relationship tracking; failures to update memory don't block response delivery.
8. **Streamlit Web UI**: Interactive multi-page web application for user queries and conversation history, displaying source citations and confidence scores.
9. **MVP Focus**: No automated testing framework, manual testing only to accelerate MVP delivery. Source availability tracking enables manual validation.

## Next Steps

After Phase 1 completion:
1. All NEEDS CLARIFICATION items resolved in research.md
2. Data model fully specified in data-model.md
3. API contracts defined in contracts/ directory
4. Agent context updated with new technologies
5. Quickstart guide ready for developers
6. Ready for Phase 2: `/speckit.tasks` to generate detailed implementation tasks
