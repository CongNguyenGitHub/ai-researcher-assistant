# Implementation Tasks: Context-Aware Research Assistant

**Feature**: Context-Aware Research Assistant  
**Branch**: `001-context-aware-research`  
**Created**: November 13, 2025  
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

## Overview

This document defines all implementation tasks for the Context-Aware Research Assistant, organized by user story in priority order (P1 → P2). All tasks follow strict checklist format and include explicit file paths for implementation.

**Total Tasks**: 47  
**User Stories**: 6 (5 P1 + 1 P2)  
**Phases**: 5 (Setup + Foundational + 4 User Stories)

### MVP Scope Recommendation

**Minimum Viable Product** (Phase 1-4): Complete User Stories 1-4 (all P1):
- ✅ User Story 1: Submit Research Query
- ✅ User Story 2: Multi-Source Context Retrieval  
- ✅ User Story 3: Context Evaluation and Filtering
- ✅ User Story 4: Answer Synthesis with Filtered Context
- ✅ User Story 6: Workflow Orchestration via crewAI

This delivers end-to-end query processing with parallel multi-source retrieval, evaluation, and synthesis.

**Post-MVP** (Phase 5): Add User Story 5 (P2) for multi-turn conversation memory.

### Task Execution Strategy

1. **Sequential by Phase**: Phases 1-2 are blocking prerequisites; Phases 3-5 can overlap after Phase 2 completion
2. **Within Phase**: Many tasks marked [P] (parallelizable) can run concurrently
3. **Testing**: MVP mode uses manual testing only; no automated test suite
4. **Delivery**: Each phase is independently deliverable and testable

---

## Phase 1: Setup & Project Initialization

**Goal**: Establish Python project structure, environment configuration, and base dependencies

**Independent Test**: Can run `python -c "import crewai, streamlit, pymilvus, arxiv, firecrawl_python, zep_python"` without errors

### Setup Tasks

- [ ] T001 Create project structure per plan.md layout (Python 3.10+): Create directories `src/`, `src/pages/`, `src/models/`, `src/services/`, `src/tools/`, `src/ui/`, `src/utils/`

- [ ] T002 Create `requirements.txt` with core dependencies: crewai==0.35.0, google-generativeai==0.3.0, streamlit==1.28.0, pymilvus==2.3.0, firecrawl-python==0.2.0, arxiv==2.1.0, zep-python==0.40.0, python-dotenv==1.0.0, pydantic==2.0.0, requests==2.31.0

- [ ] T003 Create `.env.example` template with environment variables: `GEMINI_API_KEY`, `GEMINI_MODEL`, `MILVUS_HOST`, `MILVUS_PORT`, `FIRECRAWL_API_KEY`, `ZEP_API_URL`, `ZEP_API_KEY`

- [ ] T004 Create `pyproject.toml` with project metadata: name="context-aware-research-assistant", version="0.1.0", description, Python>=3.10 requirement, dependencies pointing to requirements.txt

- [ ] T005 Create `streamlit_config.toml` with Streamlit configuration: theme="light", max_upload_size=200 MB, logger.level="info"

- [ ] T006 Initialize git branch and create initial commit: `git checkout -b 001-context-aware-research && git add . && git commit -m "init: project structure and dependencies"`

---

## Phase 2: Foundational & Cross-Cutting Infrastructure

**Goal**: Build foundational infrastructure used by all user stories (models, config, logging, base tools)

**Blocking Dependencies**: All subsequent user stories depend on Phase 2 completion

**Independent Test**: Can import all models and services without errors; config loads from .env; logging is configured

### Configuration & Logging

- [ ] T007 Create `src/config.py`: Load environment variables, validate required settings (Gemini, Milvus, Firecrawl, Arxiv, Zep), raise ConfigError if missing, expose as Config dataclass

- [ ] T008 Create `src/logging_config.py`: Set up structured logging with JSON formatter, log levels (DEBUG/INFO/WARNING/ERROR), file rotation (daily, 10MB), include timestamps and context IDs

### Data Models

- [ ] T009 Create `src/models/query.py`: Implement Query dataclass with fields (id, user_id, text, timestamp, session_id, metadata dict), validation (non-empty text, max 5000 chars)

- [ ] T010 Create `src/models/context.py`: Implement ContextChunk dataclass with fields (id, source, text, confidence_score 0-1, relevance_score 0-1, metadata dict, timestamp), AggregatedContext as List[ContextChunk], FilteredContext with filtering_rationale

- [ ] T011 Create `src/models/response.py`: Implement FinalResponse dataclass with JSON schema structure: main_answer (text, source_links list), key_claims (list of {text, chunk_citations list, confidence_score 0-1}), overall_confidence 0-1, source_availability {source_name: succeeded/failed/timeout}, metadata {timestamp, source_count, failed_sources list}

- [ ] T012 Create `src/models/memory.py`: Implement ConversationHistory (user_id, session_id, messages list, timestamp), UserPreferences (response_format, depth, source_preferences, topic_interests), Entity (name, type, relationships list, created_at)

### Base Tool Infrastructure

- [ ] T013 Create `src/tools/__init__.py`: Define ToolBase abstract class with execute() method, timeout handling (7s max per spec), return type List[ContextChunk], error handling that never raises exceptions, include source attribution

- [ ] T014 Create `src/tools/config.py`: Define tool configuration (timeouts, retry counts, rate limits) for RAG (Milvus), Firecrawl, Arxiv, Memory (Zep)

### Utilities & Validators

- [ ] T015 Create `src/utils/validators.py`: Implement validate_query(), validate_context_chunk(), validate_filtered_context(), validate_response() functions with detailed error messages

- [ ] T016 Create `src/utils/formatters.py`: Implement JSON response formatter, citation formatter (3-level: main answer → key claims → per-claim confidence), contradiction formatter (dual-source explicit notation)

### Environment & Initialization

- [ ] T017 Copy `.env.example` to `.env` in development environment, populate with test credentials/endpoints for Milvus, Firecrawl, Arxiv, Zep

- [ ] T018 Create `src/__init__.py`: Export Config, Query, ContextChunk, AggregatedContext, FilteredContext, FinalResponse, ConversationHistory, UserPreferences, Entity, logging configuration

---

## Phase 3: User Story 1 - Submit Research Query (P1)

**User Story Goal**: Enable users to submit research queries and receive comprehensive answers  
**Acceptance Test**: Submit a query via Streamlit UI, receive final response within 30s with structured JSON output  
**Success Criteria**: SC-001 (response within 30s), SC-004 (response addresses query with 90% accuracy)

### US1 - Models & Services

- [ ] [P] T019 [US1] Create `src/services/orchestrator.py`: Implement Orchestrator class with method process_query(Query) → FinalResponse, execute workflow steps sequentially (retrieval → evaluation → synthesis → memory), handle step failures with fallback strategies, log workflow execution

- [ ] [P] T020 [US1] Create `src/services/evaluator.py`: Implement Evaluator service with calculate_quality_score(ContextChunk) applying formula (30% reputation + 20% recency + 40% relevance + 10% dedup), filter_context(AggregatedContext) → FilteredContext with filtering_rationale

- [ ] [P] T021 [US1] Create `src/services/synthesizer.py`: Implement Synthesizer service with generate_response(FilteredContext, Query) → FinalResponse, handle contradictions by documenting dual sources explicitly, format response with 3-level citations

### US1 - Agents & Orchestration

- [ ] [P] T022 [US1] Create `src/agents.py`: Define CrewAI Evaluator Agent (role="Context Evaluator", goal="Filter low-quality context", backstory) with access to quality scoring logic

- [ ] [P] T023 [US1] Create `src/agents.py` (continued): Define CrewAI Synthesizer Agent (role="Answer Synthesizer", goal="Generate comprehensive responses", backstory) with access to response formatting and contradiction handling

- [ ] T024 [US1] Create `src/tasks.py`: Implement EvaluateContextTask (agent=Evaluator, description, expected_output), SynthesizeResponseTask (agent=Synthesizer, description, expected_output), both with tool access

- [ ] T025 [US1] Implement Orchestrator.execute() in `src/services/orchestrator.py`: Initialize crewAI Crew with Evaluator + Synthesizer agents and tasks, handle task execution sequentially, catch exceptions and apply graceful degradation, return FinalResponse

### US1 - Streamlit UI

- [ ] T026 [US1] Create `src/app.py`: Implement Streamlit main entry point with page config, session state initialization, navigation to pages (research, conversation, entities), load config and logger

- [ ] T027 [US1] Create `src/pages/research.py`: Implement research query page with text input for query, submit button, display final response with 3-level citations, source availability status, confidence scores, loading indicator during processing

- [ ] T028 [US1] Create `src/ui/components.py`: Implement display_response() component to render FinalResponse JSON with formatted main answer, key claims with citations, confidence visualizations

- [ ] T029 [US1] Create `src/ui/components.py` (continued): Implement display_source_status() component showing which sources succeeded/failed/timed out, failure reasons and timestamps

### US1 - Integration

- [ ] T030 [US1] Implement end-to-end workflow: Query (text) → parse to Query model → Orchestrator.process_query() → Evaluator filters context → Synthesizer generates response → return FinalResponse → Streamlit displays formatted response

- [ ] T031 [US1] Add error handling in Orchestrator: Catch orchestration exceptions, return transparent error response explaining issue (e.g., "Query processing failed: all sources unavailable"), suggest user actions (refine query, try later)

- [ ] T032 [US1] Implement manual testing for US1: Create test_query.md with 5 test scenarios (simple query, complex query, no-context query, timeout simulation, contradiction scenario), document expected outputs and validation criteria

---

## Phase 4: User Story 2 - Multi-Source Context Retrieval (P1)

**User Story Goal**: Retrieve context in parallel from 4 distinct sources (Milvus RAG, Firecrawl web, Arxiv academic, Zep memory)  
**Acceptance Test**: Submit a query, verify context successfully retrieved from all 4 sources and aggregated; execution time < 15s for parallel retrieval  
**Success Criteria**: SC-002 (at least 2 of 4 sources succeed for 95% of queries), SC-005 (parallel execution < sequential time)

### US2 - RAG Tool (Milvus)

- [ ] [P] T033 [US2] Create `src/tools/rag_tool.py`: Implement RAGTool class extending ToolBase, constructor connects to Milvus (host, port from config), timeout=7s

- [ ] [P] T034 [US2] Implement RAGTool.execute(Query) in `src/tools/rag_tool.py`: Embed query text (use OpenAI embeddings), semantic search in Milvus, return top-k ContextChunks (k from config, default 5), include confidence scores and source="rag", catch connection errors and return empty list

- [ ] [P] T035 [US2] Add error handling to RAGTool: Catch TimeoutError after 7s, MilvusException, connection errors; log failure details (timestamp, error message); return empty list (graceful degradation)

### US2 - Firecrawl Tool (Web Search)

- [ ] [P] T036 [US2] Create `src/tools/firecrawl_tool.py`: Implement FirecrawlTool class extending ToolBase, initialize Firecrawl client with API key from config, timeout=7s

- [ ] [P] T037 [US2] Implement FirecrawlTool.execute(Query) in `src/tools/firecrawl_tool.py`: Search web using Firecrawl, parse results into ContextChunks, include URL, title, snippet, confidence scores (from search ranking), source="web", extract recency metadata (publish date if available)

- [ ] [P] T038 [US2] Add error handling to FirecrawlTool: Catch TimeoutError after 7s, API errors (rate limit, invalid key); log failure with source name; return empty list; never raise exceptions

### US2 - Arxiv Tool (Academic)

- [ ] [P] T039 [US2] Create `src/tools/arxiv_tool.py`: Implement ArxivTool class extending ToolBase, initialize Arxiv client, timeout=7s

- [ ] [P] T040 [US2] Implement ArxivTool.execute(Query) in `src/tools/arxiv_tool.py`: Search Arxiv for papers, fetch top results (default 5), extract title, authors, summary, published date, arXiv link, convert to ContextChunks with source="arxiv", include recency metadata (publication year)

- [ ] [P] T041 [US2] Add error handling to ArxivTool: Catch TimeoutError, network errors; log failure; return empty list; ensure academic source reputation metadata is attached to chunks

### US2 - Memory Tool (Zep)

- [ ] [P] T042 [US2] Create `src/tools/memory_tool.py`: Implement MemoryTool class extending ToolBase, initialize Zep client (API URL, API key from config), timeout=7s

- [ ] [P] T043 [US2] Implement MemoryTool.execute(Query) in `src/tools/memory_tool.py`: Query Zep for conversation history (retrieve recent interactions, user preferences, entities relevant to query), convert to ContextChunks with source="memory", include relevance scores from entity matching

- [ ] [P] T044 [US2] Add error handling to MemoryTool: Catch TimeoutError, Zep API errors; log failure; return empty list; if Zep unavailable, note in response that memory retrieval failed

### US2 - Parallel Retrieval Orchestration

- [ ] T045 [US2] Implement parallel retrieval in Orchestrator.process_query(): Execute all 4 tools concurrently (use asyncio or concurrent.futures), collect results with timeout handling, aggregate into AggregatedContext with source attribution, log which sources succeeded/failed

- [ ] T046 [US2] Implement aggregation logic in `src/services/orchestrator.py`: Combine ContextChunks from all sources, preserve source attribution, maintain order by confidence score, create AggregatedContext with metadata (total chunks, sources retrieved, sources failed)

- [ ] T047 [US2] Implement no-context handling: If all 4 sources return empty, log warning, create transparent response explaining "No context found for your query", invite user to refine query or provide seed documents for RAG

---

## Phase 5: User Story 3 - Context Evaluation and Filtering (P1)

**User Story Goal**: Evaluate and filter aggregated context using multi-factor quality scoring  
**Acceptance Test**: Provide aggregated context from all 4 sources, run Evaluator, verify filtered context removes low-quality items and retains high-quality items; filter improves answer relevance by 30%+  
**Success Criteria**: SC-003 (filter improves relevance by 30%), context filtering maintains citation integrity

### US3 - Quality Scoring Implementation

- [ ] [P] T048 [US3] Implement quality scoring formula in `src/services/evaluator.py`: calculate_quality_score(chunk, context) applies:
  - Source reputation (30%): academic > web > memory > rag (configurable weights)
  - Recency (20%): favor recent documents, decay exponentially with age
  - Semantic relevance (40%): cosine similarity to query (embed query, compare)
  - Deduplication (10%): penalize chunks with high text overlap with higher-scored chunks

- [ ] [P] T049 [US3] Implement score thresholding in `src/services/evaluator.py`: Define quality_threshold (e.g., 0.5), filter out chunks below threshold, create FilteredContext with remaining chunks sorted by quality score descending

- [ ] [P] T050 [US3] Add filtering rationale: For each removed chunk, document reason in filtering_rationale (e.g., "Low relevance score (0.25)", "Duplicate of #12345"), enable user review of filtering decisions

### US3 - Evaluator Agent Integration

- [ ] T051 [US3] Implement Evaluator.filter_context() in `src/services/evaluator.py`: Receive AggregatedContext, apply quality scoring to all chunks, filter using threshold, return FilteredContext with rationale

- [ ] T052 [US3] Integrate EvaluateContextTask into Orchestrator workflow: After parallel retrieval, execute evaluation task, log filtering statistics (chunks retained: X%, quality scores range: Y-Z), pass FilteredContext to synthesis

- [ ] T053 [US3] Handle edge case: All context filtered as low-quality: Return transparent response explaining quality thresholds excluded all available information, suggest user review RAG documents or refine query

---

## Phase 6: User Story 4 - Answer Synthesis with Filtered Context (P1)

**User Story Goal**: Synthesize comprehensive answers using filtered context with 3-level citations  
**Acceptance Test**: Provide filtered context, run Synthesizer, verify response directly addresses query, includes all 3 citation levels, handles contradictions explicitly  
**Success Criteria**: SC-004 (response accuracy 90%), SC-006 (user satisfaction 4.0+/5.0)

### US4 - Response Generation

- [ ] [P] T054 [US4] Implement Synthesizer.generate_response() in `src/services/synthesizer.py`: Receive FilteredContext + Query, use LLM (Google Gemini 2.0 Flash) to generate comprehensive answer addressing query, ensure response uses only filtered context (no hallucination), return structured response

- [ ] [P] T055 [US4] Implement 3-level citation structure in `src/services/synthesizer.py`:
  - Level 1: Main answer text with source_links list (URLs from context chunks)
  - Level 2: Key claims extracted from response, each with chunk_citations list (chunk IDs + text snippets)
  - Level 3: Per-claim confidence_score (0-1, derived from average chunk scores in citation)

- [ ] [P] T056 [US4] Implement contradiction detection in `src/services/synthesizer.py`: Analyze filtered context for conflicting claims (same topic, different assertions), flag contradictions, document in response structure as conflicting_claims list with dual source attribution

- [ ] [P] T057 [US4] Implement contradiction handling: For each contradiction, generate response that acknowledges both perspectives, explicitly notes contradiction ("Sources conflict on X: A says Y, B says Z"), lets user decide, never chooses arbitrarily

### US4 - JSON Response Formatting

- [ ] T058 [US4] Implement response schema in `src/utils/formatters.py`: Serialize FinalResponse to JSON with all required fields (main_answer, key_claims, overall_confidence, source_availability, contradictions, metadata), validate schema against OpenAPI spec

- [ ] T059 [US4] Implement confidence score calculation: overall_confidence = average of key_claim confidence scores, weighted by claim importance (LLM-determined), range 0-1

- [ ] T060 [US4] Add source availability metadata: Include in response which sources were queried (all 4), which succeeded/failed/timed out, any source-specific error messages (for transparency)

### US4 - Synthesizer Agent Integration

- [ ] T061 [US4] Implement SynthesizeResponseTask in crewAI: Task receives FilteredContext, executes Synthesizer LLM prompt using Gemini 2.0 Flash (few-shot examples of 3-level citations), validates response structure, returns FinalResponse

- [ ] T062 [US4] Integrate into Orchestrator workflow: After Evaluator filtering, execute SynthesizeResponseTask, catch synthesis exceptions (timeout, LLM error), apply fallback (return response with available context even if synthesis partial)

- [ ] T063 [US4] Manual testing for US4: Create test_synthesis.md with test cases (single-source answer, multi-source answer, contradictory sources, no-context fallback), document expected response structure and validation criteria

---

## Phase 7: User Story 6 - Workflow Orchestration via crewAI (P1)

**User Story Goal**: Orchestrate entire workflow (retrieval → evaluation → synthesis → memory) using crewAI  
**Acceptance Test**: Submit query via Streamlit, verify all steps execute in sequence, correct state transitions, proper error handling for step failures  
**Success Criteria**: SC-001 (response within 30s), proper sequencing and error handling

### US6 - Orchestration Implementation

- [ ] [P] T064 [US6] Implement Orchestrator.process_query() complete workflow in `src/services/orchestrator.py`:
  1. Parse Query
  2. Execute parallel retrieval (all 4 tools concurrently)
  3. Aggregate context (AggregatedContext)
  4. Execute Evaluator task (FilteredContext)
  5. Execute Synthesizer task (FinalResponse)
  6. Attempt memory update (graceful failure)
  7. Return FinalResponse

- [ ] [P] T065 [US6] Implement error handling per step in `src/services/orchestrator.py`:
  - Retrieval failure: Continue with available sources, log each source failure
  - Evaluation failure: Return response with unfiltered context
  - Synthesis failure: Return transparent error response
  - Memory failure: Continue without persisting, note in response

- [ ] [P] T066 [US6] Implement crewAI Crew initialization in `src/services/orchestrator.py`: Create Crew(agents=[Evaluator, Synthesizer], tasks=[EvaluateContextTask, SynthesizeResponseTask], process=sequential, max_retries=2, verbose=true for logging)

- [ ] [P] T067 [US6] Add workflow logging in `src/services/orchestrator.py`: Log workflow start (timestamp, query_id), log step completion/failure (step name, status, duration), log final response metadata (sources used, confidence, contradictions)

### US6 - State Management & Recovery

- [ ] T068 [US6] Implement state tracking: Store intermediate states (Query, AggregatedContext, FilteredContext) in Orchestrator for debugging and recovery, include state in logs

- [ ] T069 [US6] Implement timeout handling: Overall workflow timeout = 30s, individual steps timeout: retrieval=15s, evaluation=5s, synthesis=8s, memory=2s; if any step exceeds timeout, log and proceed with degradation

- [ ] T070 [US6] Implement retry logic: For transient failures (network, rate limit), retry up to 2 times before graceful degradation; log retry attempts with backoff (exponential)

### US6 - Integration Testing

- [ ] T071 [US6] Create integration test scenarios in test_orchestration.md:
  - Scenario 1: All sources succeed, all steps succeed (happy path)
  - Scenario 2: One source fails (e.g., Firecrawl), others succeed, response includes source status
  - Scenario 3: Two sources fail, response notes reduced source coverage
  - Scenario 4: All sources fail, response explains no context found
  - Scenario 5: Evaluation or synthesis fails, graceful degradation response
  - Scenario 6: Timeout on one source, continues with others
  - Scenario 7: Contradictory information in filtered context, response documents both sources

- [ ] T072 [US6] Manual testing for complete workflow: Execute each scenario via Streamlit UI, verify response structure, citation levels, source availability, error handling, document results in test_orchestration_results.md

---

## Phase 8: User Story 5 - Conversation Memory Integration (P2)

**User Story Goal**: Persist conversation history and user context in Zep Memory for multi-turn interactions  
**Acceptance Test**: Submit query, verify persisted in Zep; submit follow-up query, verify prior history retrieved and influences new response  
**Success Criteria**: SC-007 (80% of follow-up queries reference prior history), entity tracking accuracy 85%

### US5 - Memory Persistence

- [ ] [P] T073 [US5] Implement memory update in `src/services/orchestrator.py`: After successful response synthesis, call memory_tool.update(FinalResponse, Query, session_id) to persist conversation

- [ ] [P] T074 [US5] Implement Zep interaction in `src/tools/memory_tool.py`: update() method adds to conversation timeline (question, answer, timestamp), extracts and tracks entities from response, updates user preference profile (inferred from query/response patterns)

- [ ] [P] T075 [US5] Implement entity tracking: From response, extract named entities (people, organizations, concepts) using NER, link relationships (mentioned_in_context, appears_with, etc.), store in Zep entity graph

### US5 - Memory Retrieval Integration

- [ ] T076 [US5] Enhance MemoryTool.execute() in `src/tools/memory_tool.py`: Query recent conversation history (last 5-10 interactions), retrieve similar past queries using semantic search in Zep, extract user preferences, retrieve related entities, return as ContextChunks

- [ ] T077 [US5] Implement conversation continuity: In Orchestrator, retrieve prior context from memory before retrieval, add to system prompt for Synthesizer to ensure coherence with prior interactions

- [ ] T078 [US5] Implement user preference personalization: Store user response preferences (format, depth, sources) in Zep; in Synthesizer prompt, instruct agent to personalize response based on user preferences

### US5 - UI for Conversation History

- [ ] T079 [US5] Create `src/pages/conversation.py`: Implement conversation history page displaying past queries/responses (chronological reverse order), clickable to view full response with citations, show entity mentions across conversations

- [ ] T080 [US5] Create `src/ui/components.py` conversation visualization: Implement display_conversation_history() showing conversation timeline (query → response → timestamp), highlight entities, show source diversity across queries

- [ ] T081 [US5] Create `src/pages/entities.py`: Implement entity browser showing all tracked entities (people, organizations, topics), relationships (who mentioned who, concepts linked), entity occurrence count across conversations, allow search/filter

### US5 - Memory Error Handling

- [ ] T082 [US5] Implement graceful memory failure: If Zep unavailable during update, log failure but continue (response still delivered), note in response "Conversation history not persisted due to service unavailability", user can still submit next query

- [ ] T083 [US5] Implement memory prune/retention policy: Configure Zep to retain last N conversations (config, default 100), auto-prune older conversations to manage storage, log pruning events

---

## Phase 9: Polish & Cross-Cutting Concerns

**Goal**: Finalize deployment, documentation, and performance optimization

### Documentation & Deployment

- [ ] T084 [P] Create `SETUP.md`: Complete setup guide (install dependencies, configure .env, run Streamlit, test basic query), environment setup for Milvus Docker, Zep service, example curl requests

- [ ] T085 [P] Create `ARCHITECTURE.md`: Document system architecture (workflows, agent roles, data flow, error handling), sequence diagrams (retrieval, evaluation, synthesis), decision rationales from clarifications

- [ ] T086 [P] Create `MANUAL_TESTING_GUIDE.md`: Compile all test scenarios (test_query.md, test_synthesis.md, test_orchestration.md), expected outputs, how to report issues, troubleshooting common failures

- [ ] T087 Create `docker-compose.yml`: Define services for Milvus (image, ports, volumes), Zep (image, ports), allow local development with single `docker-compose up -d`

- [ ] T088 Create `Docker.dev`: Dockerfile for development environment with Python 3.10, dependencies installed, Streamlit configured, allow `docker build -t research-assistant . && docker run -p 8501:8501 research-assistant`

### Performance & Observability

- [ ] [P] T089 Implement performance monitoring in `src/logging_config.py`: Log execution times for each step (retrieval, evaluation, synthesis, memory), track source response times individually, alert if any step exceeds target timeout

- [ ] [P] T090 Implement structured logging in all services: Log with context (query_id, session_id, user_id), log quality scores and filtering decisions (transparency), log source availability and error reasons

- [ ] [P] T091 Create metrics dashboard (optional): Implement simple Streamlit page showing system metrics (avg response time, source success rates, contradiction frequency, memory utilization) for monitoring

### Code Quality & Standards

- [ ] T092 Add code documentation: Docstrings for all functions (description, args, returns, raises), comments for complex logic (quality scoring formula, contradiction detection algorithm)

- [ ] T093 Add type hints: Full type hints throughout codebase (Query → FinalResponse function signatures), use Pydantic models for validation, benefit from IDE support and error catching

- [ ] T094 Create `.gitignore`: Exclude .env, __pycache__, .streamlit/secrets.toml, .venv/, .DS_Store, *.log files

### Final Integration & Validation

- [ ] T095 Create final integration test checklist: Verify all 6 user stories integrated, manual test all scenarios from test guides, verify error handling for all edge cases, performance validation (all responses within 30s)

- [ ] T096 Create deployment checklist: Verify all env vars documented, .env.example populated, requirements.txt complete, Docker setup working, Streamlit startup without errors, basic query works end-to-end

- [ ] T097 Final git commit: Commit all code with message "feat: complete context-aware research assistant MVP", tag as v0.1.0-mvp, document in CHANGELOG.md

---

## Task Dependencies & Execution Order

### Dependency Graph

```
Phase 1: Setup (T001-T006)
    ↓
Phase 2: Foundational (T007-T018)
    ↓
Phase 3: US1 (T019-T032)  ← Can proceed after Phase 2
Phase 4: US2 (T033-T047)  ← Can proceed after Phase 2 (parallel with US1)
Phase 5: US3 (T048-T053)  ← Depends on US2 completion (needs AggregatedContext)
Phase 6: US4 (T054-T063)  ← Depends on US3 completion (needs FilteredContext)
Phase 7: US6 (T064-T072)  ← Depends on US1, US2, US3, US4 (integrates all)
Phase 8: US5 (T073-T083)  ← Can start after US4, independent of critical path
Phase 9: Polish (T084-T097)  ← Final phase, all features must be complete
```

### Parallel Execution Opportunities

**After Phase 2 Completion**:
- US1 (Models & Agents) and US2 (Tools) can run in parallel (independent concerns)
- Within US2, all 4 tools (RAG, Firecrawl, Arxiv, Memory) can be implemented in parallel

**After US1 & US2 Completion**:
- US3 (Evaluation) depends on US2, can start immediately
- US4 (Synthesis) depends on US3, start after US3 models done
- US5 (Memory) can start after US4, doesn't block US6

**Recommended MVP Timeline**:
- Week 1: Phase 1-2 (Setup + Foundational)
- Week 2: Phase 3-4 (US1 + US2 in parallel)
- Week 3: Phase 5-6 (US3 + US4 sequentially)
- Week 4: Phase 7 (US6 orchestration integration + Phase 9 Polish)
- Post-MVP: Phase 8 (US5 Memory for multi-turn)

---

## Testing Strategy (MVP Mode - Manual Only)

**No Automated Test Suite**: MVP focuses on rapid delivery; manual testing only

**Manual Testing Approach**:
1. For each user story phase, create test scenario document (test_*.md)
2. Execute scenarios manually via Streamlit UI
3. Document results (pass/fail, unexpected behavior)
4. Report failures to logs
5. Validate error handling works as specified

**Test Documents to Create**:
- `test_query.md`: 5 scenarios for US1 (simple, complex, no-context, timeout, contradiction)
- `test_synthesis.md`: 5 scenarios for US4 (single-source, multi-source, contradictions, no-context, citations)
- `test_orchestration.md`: 7 scenarios for US6 (happy path, single source fail, multi-source fail, etc.)
- `test_memory.md`: 4 scenarios for US5 (persist, retrieve, entity tracking, memory fail)

**Success Criteria Validation**:
- SC-001: Time query, verify response within 30s
- SC-002: Query 20 diverse questions, 95% retrieve ≥2 sources
- SC-003: Compare filtered vs unfiltered relevance (manual rating)
- SC-004: Compare response to ground truth (manual review), 90% accuracy target
- SC-005: Compare parallel vs sequential retrieval time
- SC-006: Collect user satisfaction ratings (1-5 stars)
- SC-007: Run 10 follow-up queries, verify 80% reference prior history
- SC-010: Test entity extraction, verify 85% accuracy (manual review)

---

## Summary

- **Total Tasks**: 97 across 9 phases
- **MVP Tasks (Phases 1-7)**: 72 tasks completing all P1 user stories
- **Post-MVP Tasks (Phases 8-9)**: 25 tasks for memory integration and deployment polish
- **Parallelization**: 28 tasks marked [P] can execute concurrently
- **Critical Path**: Phase 1 → Phase 2 → US1/US2 (parallel) → US3 → US4 → US6 Orchestration
- **Estimated Timeline**: 4 weeks to MVP (all P1 user stories), 1 additional week for post-MVP
