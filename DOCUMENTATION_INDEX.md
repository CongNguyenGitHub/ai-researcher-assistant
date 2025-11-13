# Documentation Index & Reading Guide

**Start here to understand the complete Context-Aware Research Assistant project.**

---

## Quick Navigation

### 🚀 Start Here
1. **[PROJECT_OVERVIEW.md](./PROJECT_OVERVIEW.md)** (15 min read)
   - What is this project?
   - User journey from start to finish
   - Technology decisions and why
   - Implementation status and roadmap

### 📐 Understand the Architecture
2. **[ARCHITECTURE_OVERVIEW.md](./ARCHITECTURE_OVERVIEW.md)** (25 min read)
   - Complete end-to-end system flow
   - Component deep-dives
   - Data models and relationships
   - Configuration & security

3. **[ARCHITECTURE_DIAGRAMS.md](./ARCHITECTURE_DIAGRAMS.md)** (20 min read)
   - 10 visual diagrams
   - Query processing flow
   - Data ingestion pipeline
   - Agent communication patterns
   - Error handling flows

### 🗄️ Dive Into Implementation Details
4. **[DATA_INGESTION_SUMMARY.md](./DATA_INGESTION_SUMMARY.md)** (15 min read)
   - Data ingestion pipeline components
   - TensorLake parser usage
   - Gemini embedder integration
   - Milvus loader and vector storage
   - Streamlit document processing UI

### 📋 Read the Formal Specification
Located in `specs/001-context-aware-research/`:

5. **[spec.md](./specs/001-context-aware-research/spec.md)** (20 min read)
   - 6 user stories with acceptance scenarios
   - 5 critical clarifications
   - Functional requirements
   - Edge cases and error handling

6. **[plan.md](./specs/001-context-aware-research/plan.md)** (20 min read)
   - 5 implementation phases
   - Technical context
   - Key design decisions
   - Project structure
   - Phase 0 research tasks

7. **[data-model.md](./specs/001-context-aware-research/data-model.md)** (20 min read)
   - Core domain model
   - Query, ContextChunk, FinalResponse entities
   - Relationships and validation rules
   - Source-specific metadata

8. **[research.md](./specs/001-context-aware-research/research.md)** (25 min read)
   - CrewAI orchestration patterns
   - Milvus integration strategy
   - Context filtering formulas
   - Contradiction handling
   - Response format design

9. **[quickstart.md](./specs/001-context-aware-research/quickstart.md)** (15 min read)
   - Setup and installation
   - Environment configuration
   - Running the application
   - First query walkthrough

10. **[tasks.md](./specs/001-context-aware-research/tasks.md)** (Reference)
    - 97 implementation tasks
    - Organized by phase and priority
    - Dependencies and ordering
    - Parallel execution opportunities

---

## Reading Paths by Role

### 👤 Product Manager / Non-Technical Stakeholder
**Time**: 30 minutes
1. PROJECT_OVERVIEW.md (entire file)
2. ARCHITECTURE_OVERVIEW.md (sections 1-3: "System Architecture", "Data Flow", "Component Deep-Dives")
3. spec.md (User Scenarios & Testing section)

**Output**: Understand what the system does, who benefits, and why

### 👨‍💻 Software Engineer / Developer
**Time**: 2-3 hours
1. PROJECT_OVERVIEW.md (entire)
2. ARCHITECTURE_OVERVIEW.md (entire)
3. ARCHITECTURE_DIAGRAMS.md (entire)
4. DATA_INGESTION_SUMMARY.md (entire)
5. specs/data-model.md (entire)
6. specs/research.md (sections 1-3)
7. specs/tasks.md (skim for implementation order)

**Output**: Complete understanding of system design and ready to code

### 🏗️ Solution Architect / Tech Lead
**Time**: 4-5 hours
1. PROJECT_OVERVIEW.md (entire)
2. ARCHITECTURE_OVERVIEW.md (entire)
3. ARCHITECTURE_DIAGRAMS.md (entire)
4. specs/plan.md (entire)
5. specs/research.md (entire)
6. specs/data-model.md (entire)
7. specs/spec.md (Clarifications section)
8. specs/tasks.md (Dependency analysis)

**Output**: Can make design decisions, review proposals, assign work

### 🧪 QA / Testing Specialist
**Time**: 2 hours
1. PROJECT_OVERVIEW.md (Testing & Quality Assurance section)
2. specs/spec.md (User Scenarios & Testing section)
3. ARCHITECTURE_OVERVIEW.md (Error Handling & Graceful Degradation)
4. ARCHITECTURE_DIAGRAMS.md (Scenario 7: Error Handling & Recovery)

**Output**: Understand what to test, acceptance criteria, test scenarios

### 📊 Data Scientist / ML Engineer
**Time**: 2.5 hours
1. ARCHITECTURE_OVERVIEW.md (sections 1-2, 4-5)
2. ARCHITECTURE_DIAGRAMS.md (sections 5, 8)
3. specs/research.md (sections 3-5: Context Filtering, Contradiction Handling, Response Format)
4. DATA_INGESTION_SUMMARY.md (Embedder and Chunking sections)

**Output**: Understand embedding strategy, quality metrics, synthesis patterns

### 🎨 UI/UX Designer
**Time**: 1.5 hours
1. PROJECT_OVERVIEW.md (Complete User Journey section)
2. ARCHITECTURE_DIAGRAMS.md (section 6: Streamlit UI Layout)
3. specs/quickstart.md (sections 3-4)

**Output**: Understand user flows, page structures, required components

---

## How the Documentation Works Together

```
PROJECT_OVERVIEW.md (The map)
├─ What is this?
├─ Why does it work this way?
└─ What's the status?
    ↓
ARCHITECTURE_OVERVIEW.md (The blueprint)
├─ Complete system flow end-to-end
├─ Each major component explained
├─ All data models
└─ Configuration and setup
    ↓
ARCHITECTURE_DIAGRAMS.md (The visuals)
├─ System architecture diagram
├─ Query processing flow
├─ Agent communication patterns
├─ Data ingestion pipeline
└─ Error handling scenarios
    ↓
specs/plan.md (The roadmap)
├─ Implementation phases
├─ Key design decisions
├─ Technical dependencies
└─ Execution order
    ↓
specs/spec.md (The requirements)
├─ User stories (what users need)
├─ Acceptance scenarios (how to verify)
├─ Edge cases (what can go wrong)
└─ Clarifications (ambiguities resolved)
    ↓
specs/research.md (The decisions)
├─ Why we chose this architecture
├─ Technical justifications
├─ Metrics and thresholds
└─ Implementation patterns
    ↓
specs/data-model.md (The schema)
├─ All entity definitions
├─ Field specifications
├─ Validation rules
└─ Relationships
    ↓
DATA_INGESTION_SUMMARY.md (The details)
├─ Component by component
├─ Code examples
├─ Usage patterns
└─ Integration points
    ↓
specs/tasks.md (The checklist)
├─ 97 specific tasks
├─ Dependencies
├─ Ordering
└─ Parallel opportunities
```

---

## Key Concepts Quick Reference

### Query Processing Pipeline
1. **Retriever Agent** (15-25s)
   - Embeds query in 768-dim space
   - Queries 4 sources in parallel
   - Gathers ~20-30 context chunks

2. **Evaluator Agent** (5s)
   - Scores each chunk: (30% reputation + 20% recency + 40% relevance + 10% dedup)
   - Keeps chunks with quality > 0.5
   - Produces ~15-20 high-quality chunks

3. **Synthesizer Agent** (5-10s)
   - Reads filtered context
   - Generates answer with claims
   - Cites sources for verification
   - Assigns confidence scores

4. **Memory Agent** (2-3s)
   - Stores Q&A pair
   - Extracts entities
   - Updates user preferences

### Data Quality Formula
```
Quality = (0.30 × reputation) + (0.20 × recency) 
        + (0.40 × relevance) + (0.10 × dedup)
```

**Reputation**: Source type (RAG: 0.9, Academic: 0.85, Web: 0.6-0.8)
**Recency**: Document age (<1mo: 1.0, >5yr: 0.2)
**Relevance**: Embedding similarity (0.0-1.0)
**Dedup**: Duplicate check (unique: 1.0, >95% dup: 0.1)

### Embedding Strategy
- **Model**: Google Gemini text-embedding-004
- **Dimension**: 768
- **Used for**: Query, document chunks, similarity search
- **Storage**: Milvus with IVF_FLAT indexing

### Response Structure
```json
{
  "answer": "Main synthesized answer...",
  "claims": [
    {
      "text": "Key claim",
      "confidence": 0.95,
      "sources": ["source_id_1"],
      "citations": ["quote from source"]
    }
  ],
  "sources": [
    {"id": "src_1", "title": "...", "url": "...", "type": "rag"}
  ],
  "metadata": {
    "response_time": "32 seconds",
    "chunks_retrieved": 23,
    "chunks_used": 18
  }
}
```

---

## Document Types Explained

### 📋 Specification Documents (specs/ folder)
- **Purpose**: Define what to build and why
- **Audience**: All team members
- **Scope**: Requirements, design decisions, user stories

### 📐 Architecture Documents (root folder)
- **Purpose**: Explain how to build it
- **Audience**: Engineers and architects
- **Scope**: System design, data flows, component details

### 🗂️ Source Code (src/ folder)
- **Purpose**: Implementation
- **Audience**: Developers
- **Scope**: Actual running code

---

## Frequently Asked Questions

**Q: Where do I start if I'm new to this project?**
A: Read PROJECT_OVERVIEW.md first (15 min), then ARCHITECTURE_OVERVIEW.md (25 min).

**Q: I need to implement something. Where's the specification?**
A: specs/spec.md has user stories. specs/tasks.md has the 97 specific tasks. specs/plan.md shows the phases.

**Q: I want to understand the data model.**
A: specs/data-model.md has complete entity definitions with validation rules.

**Q: How does the quality evaluation work?**
A: See ARCHITECTURE_OVERVIEW.md section "3. CONTEXT EVALUATION & FILTERING" or specs/research.md section 3.

**Q: What happens if a source fails?**
A: ARCHITECTURE_DIAGRAMS.md section 7 shows error handling. specs/spec.md Clarification #5 explains the decision.

**Q: How long does a query take?**
A: 30-35 seconds total. Breakdown in ARCHITECTURE_DIAGRAMS.md section 10 (Performance Timeline).

**Q: Is the project ready to deploy?**
A: Data ingestion pipeline is complete. Query pipeline components still need implementation (see PROJECT_OVERVIEW.md Implementation Status).

---

## Version History

| Date | Status | Key Changes |
|------|--------|-------------|
| 2025-11-13 | Draft | Initial specification and planning complete |
| 2025-11-13 | In Progress | Data ingestion pipeline implemented |
| TBD | Next | Query processing agents implementation |

---

## Document Maintenance

These documents are maintained in this order of authority:
1. **specs/** folder: Source of truth for requirements
2. **ARCHITECTURE_*.md**: Detailed design documents
3. **Source code**: Implementation (overrides docs if conflict)

When changes occur:
- Update specs/ first (requirements source)
- Update ARCHITECTURE docs (reflect new design)
- Update source code (implement change)
- Update this index if needed

---

## Quick Links to Key Sections

### Common Questions & Answers
- "How does quality filtering work?" → ARCHITECTURE_OVERVIEW.md, Phase 3
- "What are all the data models?" → specs/data-model.md
- "What are the user stories?" → specs/spec.md, User Scenarios section
- "What happens with contradictions?" → specs/research.md section 4
- "How is the response formatted?" → specs/research.md section 5
- "What's the implementation order?" → specs/tasks.md
- "How do documents get indexed?" → DATA_INGESTION_SUMMARY.md
- "What agents are needed?" → ARCHITECTURE_DIAGRAMS.md section 4
- "How do I run this?" → specs/quickstart.md

---

## Next Steps

1. **Understand the Project** (You are here)
   - Read PROJECT_OVERVIEW.md
   - Skim ARCHITECTURE_OVERVIEW.md

2. **Deep Dive on Component Interest**
   - Data ingestion? → DATA_INGESTION_SUMMARY.md
   - Query processing? → ARCHITECTURE_OVERVIEW.md + specs/plan.md
   - Agent orchestration? → specs/research.md + ARCHITECTURE_DIAGRAMS.md

3. **Implementation**
   - Check specs/tasks.md for what's assigned to you
   - Review relevant architecture documentation
   - Code with reference to data models (specs/data-model.md)

4. **Verification**
   - Check acceptance scenarios in specs/spec.md
   - Review your implementation against architecture diagrams
   - Test error cases in ARCHITECTURE_DIAGRAMS.md section 7

---

**Last Updated**: November 13, 2025  
**Maintained By**: AI Research Assistant Development Team  
**Status**: Complete and Current
