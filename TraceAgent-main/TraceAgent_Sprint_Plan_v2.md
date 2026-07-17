# TraceAgent: Automated SRS-to-Code Traceability & Compliance Auditor
### Revised Sprint Cycles 1–3 | Project Execution Plan

---

## Project Metadata

| Field | Details |
|---|---|
| **Course** | Software Engineering – 22AIE311 |
| **Team No.** | 2 |
| **Project** | TraceAgent: Automated SRS-to-Code Traceability & Compliance Auditor |
| **Total Duration** | 5 Weeks (Week 1 – Week 5) |
| **Total Story Points** | 39 points across 7 tickets |
| **Document Version** | v2.0 – Revised |

### Team Members

| Member | Roll No. |
|---|---|
| Aaryan Gera | BL.EN.U4AIE23102 |
| Sathvik Reddy V | BL.EN.U4AIE23127 |
| K.V.S Aditya | BL.EN.U4AIE23161 |

---

## Revision Summary

This document is the corrected and revised version of the original Sprint Cycles 1–3 submission. The following issues identified in the audit have been resolved:

| Ticket | Issue Found | Correction Applied |
|---|---|---|
| **Global** | 3 sprints × 2 weeks = 6 weeks (exceeds 5-week deadline) | Sprint 3 compressed to 1 week; total = 5 weeks |
| **TRACE-101** | "100% text extraction" is an unachievable acceptance criterion | Changed to ≥95% extraction with error logging for failures |
| **TRACE-102** | FAISS (local) contradicts 'cloud Vector DB' requirement; Milvus dropped without explanation | Pinecone locked as primary; FAISS allowed as local dev fallback only |
| **TRACE-201** | Java AST parsing mentioned but no Java library specified; 'in-memory clone' is imprecise | Java support removed from scope; GitPython specified for repo cloning |
| **TRACE-202** | Bi-directional audit missing: reverse pass (Orphan Requirement detection) absent from AC | Full reverse-pass acceptance criteria added; output schema extended |
| **TRACE-202** | No handling for near-threshold ambiguous matches | Confidence score + human-review flag added to output schema |
| **TRACE-301** | Frontend tech choice (Streamlit vs React) undecided at Sprint 3 | Streamlit locked in at project start; noted in TRACE-000 |
| **TRACE-301** | WebSockets adds unnecessary complexity for a 5-week project | Replaced with HTTP polling; WebSockets noted as stretch goal |
| **TRACE-302** | 2-page SRS too sparse to generate meaningful embeddings | Minimum 8–10 distinct functional requirements specified |
| **Global** | No secrets/credentials management plan | New ticket TRACE-000 (pre-sprint setup) added |
| **Global** | No team task allocation defined | Owner assigned to every ticket; allocation table added |
| **Global** | No sprint review/retrospective ceremonies | Review + retrospective added at the end of each sprint block |

---

## Project Timeline Overview

The project runs for exactly 5 weeks. Sprint 3 has been compressed to 1 week to fit the deadline; its scope is intentionally smaller (frontend + demo environment) to make this feasible.

| Sprint | Duration | Weeks | Core Deliverable | Story Points |
|---|---|---|---|---|
| **Setup** | Pre-Sprint | Week 0* | Env setup, secrets, scaffolding | — |
| **Sprint 1** | 2 Weeks | Weeks 1–2 | Document ingestion + vector DB pipeline | 13 |
| **Sprint 2** | 2 Weeks | Weeks 3–4 | AST extractor + AI traceability agent | 18 |
| **Sprint 3** | 1 Week | Week 5 | Dashboard + SafeBank demo + presentation | 8 |

> **Revision note:** The original document scheduled three 2-week sprints (6 weeks total), exceeding the 5-week deadline. Sprint 3 is now 1 week. All tickets in Sprint 3 have been scoped accordingly.

---

## Team Task Allocation

Each ticket has a designated primary owner. All members are expected to participate in daily standups, sprint reviews, and retrospectives. Ownership means accountability for delivery, not exclusivity of work.

| Member | Roll No. | Primary Tickets | Domain Focus |
|---|---|---|---|
| Aaryan Gera | BL.EN.U4AIE23102 | TRACE-000, TRACE-101, TRACE-301 | Backend infra, file pipeline, frontend UI |
| Sathvik Reddy V | BL.EN.U4AIE23127 | TRACE-102, TRACE-302 | Vector DB / RAG pipeline, SafeBank demo |
| K.V.S Aditya | BL.EN.U4AIE23161 | TRACE-201, TRACE-202 | AST parsing, AI agent (ML specialist) |

> **Stand-up schedule:** Daily, 15 minutes maximum. Each member answers: (1) What did I complete yesterday? (2) What will I do today? (3) Any blockers?

---

## Pre-Sprint Setup | Duration: Day 0 (Before Week 1 Begins)

Before any sprint work begins, the team must establish the shared development environment. This setup work is not assigned story points as it is infrastructure scaffolding, not feature delivery. It must be completed on Day 0.

| Ticket ID | Type | Title | Points | Owner |
|---|---|---|---|---|
| TRACE-000 | Setup Task | Project Environment, Secrets Management & Repository Scaffolding | — | Aaryan Gera |

### Description

Establish the shared GitHub repository, project folder structure, virtual environment, and all API credential management protocols before any sprint work begins. This prevents credential leaks, dependency conflicts, and onboarding friction for the team.

### Acceptance Criteria

- A shared private GitHub repository is created with branch protection on `main`.
- Project is structured as a Python monorepo with separate directories: `/ingestion`, `/agent`, `/frontend`, `/demo`.
- A `.env.example` file documents every required environment variable (no real values committed).
- `python-dotenv` is integrated and all API clients load credentials from environment variables only.
- A shared `requirements.txt` (or `pyproject.toml`) captures all dependencies.
- A `README.md` documents local setup steps so any team member can onboard in under 10 minutes.

### Technical Sub-Tasks

- Create private GitHub repo; add all three members as collaborators.
- Set up branch protection rules: require pull request review before merging to `main`.
- Create `.env` with the following variables (real values shared via secure channel, never via Git):
  - `OPENAI_API_KEY` or `GEMINI_API_KEY` (LLM provider)
  - `PINECONE_API_KEY` and `PINECONE_ENV` (vector database)
  - `GITHUB_TOKEN` (for repository fetching in TRACE-201)
- Install and verify: `fastapi`, `uvicorn`, `python-dotenv`, `pdfplumber`, `langchain`, `pinecone-client`, `gitpython`, `streamlit`.
- Create a minimal FastAPI app (`main.py`) with a `/health` endpoint to confirm the server runs.
- Confirm all three members can run the app locally before Sprint 1 begins.

---

## Sprint 1: Knowledge Ingestion & Semantic Storage | Duration: 2 Weeks (Week 1 – Week 2)

**Epic:** System Requirements Specification (SRS) Data Pipeline

**Sprint Goal:** Establish the full pipeline to ingest SRS documents, extract and sanitize requirement text, chunk it semantically, and store dense vector embeddings in Pinecone so that the AI Agent can perform semantic searches in Sprint 2.

| Field | Details |
|---|---|
| **Sprint Duration** | 2 Weeks (Week 1 – Week 2) |
| **Syllabus Alignment** | Unit 2 – Requirements Engineering (SRS structure); Unit 3 – Code Inspection principles |
| **Sprint Ceremonies** | Sprint Planning (Day 1, Week 1) \| Daily Stand-ups \| Sprint Review + Retrospective (Day 5, Week 2) |
| **Total Story Points** | 13 points (TRACE-101: 5 pts + TRACE-102: 8 pts) |

---

### TRACE-101 — Develop Document Ingestion and Sanitization Pipeline

| Ticket ID | Type | Title | Points | Owner |
|---|---|---|---|---|
| TRACE-101 | User Story | Develop Document Ingestion and Sanitization Pipeline | 5 pts | Aaryan Gera |

#### Description

As a backend system process, we need to reliably ingest IEEE-830 formatted SRS documents (PDF/Docx), strip irrelevant formatting (headers, footers, tables of contents), and extract high-quality paragraph text so that the NLP chunking engine receives clean, high-signal data.

> **Revision note:** The original acceptance criterion required '100% extraction' of paragraph text. This is technically unachievable due to complex PDF layouts, embedded tables, and scanned images. The criterion has been revised to ≥95% extraction of body text, with failed extractions logged for manual review.

#### Acceptance Criteria (BDD Format)

- **Given** an authenticated user uploads a valid `.pdf` or `.docx` file containing SRS content.
- **When** the payload is processed by the `/api/v1/documents/upload` endpoint.
- **Then** the system must successfully extract ≥95% of core paragraph body text (headers, footers, page numbers, and tables of contents are explicitly excluded).
- **And** any page or section that fails extraction is logged with its page number and a failure reason (e.g., `'scanned image'`, `'complex table'`) — it must not silently fail.
- **And** the endpoint returns a sanitized JSON payload containing: `extracted_text` (string), `document_metadata` (filename, upload_date, page_count, version), `failed_pages` (list), and an HTTP 200 OK status.

#### Technical Sub-Tasks

- Implement file upload endpoint in Python using FastAPI with file-type validation (accept `.pdf` and `.docx` only; reject all others with HTTP 415).
- Integrate `pdfplumber` as the primary PDF parser. Use `python-docx` for `.docx` files.
- Write rule-based sanitization functions to strip: page numbers (regex on digit-only lines), repeated header/footer text, and tables of contents (detected via `'Contents'` heading + dotted lines).
- Implement a failure logger: if a page yields zero extractable text, record it in `failed_pages` with page number and inferred reason.
- Write unit tests covering: valid PDF upload, valid docx upload, unsupported file type rejection, and a PDF with one blank/scanned page (verifying it appears in `failed_pages`).

---

### TRACE-102 — Implement Semantic Chunking and Vector Database Integration (RAG)

| Ticket ID | Type | Title | Points | Owner |
|---|---|---|---|---|
| TRACE-102 | User Story | Implement Semantic Chunking and Vector Database Integration (RAG) | 8 pts | Sathvik Reddy V |

#### Description

As the AI Auditor, I require the sanitized SRS text to be logically divided into isolated Requirement Chunks and converted into vector embeddings. This enables high-speed semantic similarity searches when the AI Agent evaluates code chunks against stored requirements.

> **Revision note:** The original document listed both FAISS and Pinecone as options, which introduced a contradiction: FAISS is a local in-memory library and cannot serve as a cloud vector database. Pinecone is now the designated production vector database. FAISS may be used locally for development and testing only, clearly distinguished from the production setup.

#### Acceptance Criteria (BDD Format)

- **Given** a sanitized JSON string of SRS text received from TRACE-101.
- **When** the text is passed through the embedding pipeline.
- **Then** the text is partitioned into overlapping chunks using LangChain's `RecursiveCharacterTextSplitter` (`chunk_size=500` tokens, `chunk_overlap=50` tokens).
- **And** each chunk is converted into a dense vector embedding via the configured LLM embedding API (`OpenAI text-embedding-ada-002` or Gemini embedding endpoint).
- **And** all embeddings are upserted into Pinecone (production) with metadata: `{Requirement_ID, chunk_index, source_document, page_number}`.
- **And** FAISS may be used as a local-only substitute during development/testing when Pinecone is unavailable, clearly documented via a `USE_LOCAL_VECTOR_DB=true` environment flag.
- **And** failed embedding API calls due to rate limits are retried with exponential backoff (max 3 retries) before raising an error.

#### Technical Sub-Tasks

- Configure the LangChain document splitting pipeline with `RecursiveCharacterTextSplitter`.
- Provision a Pinecone index (dimension = 1536 for OpenAI embeddings; 768 for Gemini). Document the index name and region in `.env`.
- Implement the upsert pipeline: chunk → embed → upsert with metadata tags.
- Implement exponential backoff retry logic for LLM embedding API rate-limit errors (HTTP 429).
- Implement a local FAISS fallback controlled by a `USE_LOCAL_VECTOR_DB` environment variable. The code path must be clearly separated so production never accidentally uses FAISS.
- Write an integration test that ingests a short 3-requirement dummy SRS and verifies all chunks appear in the vector DB with correct metadata.

---

### Sprint 1 – Review & Retrospective (End of Week 2)

- **Sprint Review (30 min):** Demonstrate the working document upload endpoint and a live query against the Pinecone index. The system should return the top-3 most similar requirement chunks for a test query.
- **Sprint Retrospective (20 min):** Each member answers — What went well? What was slower than expected? What do we change for Sprint 2? Document outcomes in a shared Notion/Google Doc.

---

## Sprint 2: The Core AI Engine & Code Traceability | Duration: 2 Weeks (Week 3 – Week 4)

**Epic:** Source Code Analysis & Bi-Directional Auditing

**Sprint Goal:** Connect a target GitHub repository to the system, parse its Python source code using AST analysis, and deploy the LLM Auditor Agent to perform a full bi-directional compliance check — detecting both Ghost Code (coded but undocumented) and Orphan Requirements (documented but not coded).

| Field | Details |
|---|---|
| **Sprint Duration** | 2 Weeks (Week 3 – Week 4) |
| **Syllabus Alignment** | Unit 3 – Code Inspection, Static Analysis, Code Walkthrough; Unit 2 – Functional Requirements |
| **Sprint Ceremonies** | Sprint Planning (Day 1, Week 3) \| Daily Stand-ups \| Sprint Review + Retrospective (Day 5, Week 4) |
| **Total Story Points** | 18 points (TRACE-201: 5 pts + TRACE-202: 13 pts) |

---

### TRACE-201 — Develop Abstract Syntax Tree (AST) Source Code Extractor

| Ticket ID | Type | Title | Points | Owner |
|---|---|---|---|---|
| TRACE-201 | User Story | Develop Abstract Syntax Tree (AST) Source Code Extractor | 5 pts | K.V.S Aditya |

#### Description

As the AI Agent, I need the target Python codebase broken down into discrete functional units (classes and functions/methods) rather than flat text. Structured AST extraction prevents LLM context-window exhaustion and allows precise identification of which code unit is responsible for (or missing) a given requirement.

> **Revision note:** Two corrections applied: (1) Java AST support has been removed from scope. The original ticket mentioned 'Python/Java files' but only specified Python's `ast` module. Java parsing requires a separate library (`javalang`/`tree-sitter`) and is out of scope for a 5-week project. (2) 'Clones the repository in-memory' was imprecise. GitHub's REST API fetches file contents individually — it does not perform a git clone. GitPython is now explicitly specified for repository cloning.

#### Acceptance Criteria (BDD Format)

- **Given** a valid public or private GitHub repository URL and a branch name, with a valid `GITHUB_TOKEN` in the environment.
- **When** the AST extraction pipeline is triggered for that repository.
- **Then** the system clones the repository to a temporary local directory using GitPython and deletes it after extraction.
- **And** all `.py` files in the repository are parsed using Python's native `ast` module.
- **And** the output is a structured dictionary mapping `{file_path}/{class_name}/{function_name}` → isolated source code string.
- **And** irrelevant files are excluded: `__init__.py`, config files (`*config.py`, `settings.py`), test files (`test_*.py`), and migration files.
- **And** scope is limited to Python (`.py`) files only. Support for other languages is explicitly out of scope for this project.

#### Technical Sub-Tasks

- Implement GitHub repository fetching using GitPython (`git.Repo.clone_from`). Clone to a `/tmp/` directory; delete after extraction using `shutil.rmtree`.
- Implement AST parsing logic using Python's `ast` module. Walk the AST tree to extract:
  - All `FunctionDef` and `AsyncFunctionDef` nodes (standalone functions)
  - All `ClassDef` nodes with their child `FunctionDef` nodes (methods)
- For each extracted unit, capture: function/method name, class name (if applicable), file path, line number range, and the raw source code string (using `ast.get_source_segment` or `inspect.getsource`).
- Implement the file exclusion filter as a configurable list of glob patterns.
- Write unit tests: parse a small mock Python file and verify the output dictionary contains all expected function keys and no excluded files.

---

### TRACE-202 — Engineer LLM-Driven Bi-Directional Traceability Agent

| Ticket ID | Type | Title | Points | Owner |
|---|---|---|---|---|
| TRACE-202 | User Story | Engineer LLM-Driven Bi-Directional Traceability Agent | 13 pts | K.V.S Aditya (ML Specialist) |

#### Description

As a Compliance Auditor, I need an intelligent evaluation engine that performs a complete bi-directional compliance check between the codebase and the SRS requirements.

- **Direction A (Ghost Code Detection):** Each code chunk is checked against the requirement Vector DB — if no matching requirement exists, it is flagged as unauthorised scope creep.
- **Direction B (Orphan Requirement Detection):** Each stored requirement embedding is checked against all extracted code chunks — if no code chunk satisfies it, it is flagged as an unimplemented requirement.

Both directions are mandatory.

> **Revision note:** Critical correction: the original ticket was named 'Bi-Directional' but its acceptance criteria only described Direction A (code → requirements). Direction B (requirements → code), which detects Orphan Requirements, was entirely absent. This is the more academically important direction for an SRS compliance tool and has now been added as an explicit set of acceptance criteria. Additionally, a confidence score and human-review flag have been added to the output schema to handle ambiguous near-threshold matches.

#### Direction A: Ghost Code Detection (Code → Requirements)

- **Given** an extracted code chunk (e.g., `def execute_trade():`) from TRACE-201.
- **When** the Agent performs a semantic search against the Pinecone Vector DB.
- **Then** if the top similarity score is **below** the defined threshold (default: 0.75 cosine similarity), output:
  ```json
  {
    "ticket_id": "TRACE-A-001",
    "direction": "A",
    "status": "FAIL",
    "flag": "GHOST_CODE",
    "code_unit": "execute_trade",
    "matched_requirement": null,
    "confidence": "<score>",
    "severity": "HIGH",
    "needs_review": false
  }
  ```
- **And** if the score meets the threshold, evaluate the matched requirement text against the code logic and output a PASS result with the matching `Requirement_ID`.
- **And** if the score is within ±0.05 of the threshold (ambiguous zone), set `needs_review: true` and `severity: MEDIUM` regardless of pass/fail — a human must confirm.

#### Direction B: Orphan Requirement Detection (Requirements → Code)

- **Given** all requirement embeddings stored in Pinecone from TRACE-102.
- **When** the Agent iterates over every stored requirement chunk.
- **Then** for each requirement, perform a semantic search across all extracted code chunks from TRACE-201.
- **And** if no code chunk meets the similarity threshold for a given requirement, output:
  ```json
  {
    "ticket_id": "TRACE-B-001",
    "direction": "B",
    "status": "FAIL",
    "flag": "ORPHAN_REQUIREMENT",
    "requirement_id": "REQ-04",
    "requirement_text": "<summary>",
    "matched_code_unit": null,
    "confidence": "<score>",
    "severity": "HIGH",
    "needs_review": false
  }
  ```
- **And** if a code match exists, output a PASS with the matched code unit name and file path.
- **And** the same ambiguous-zone rule applies: confidence within ±0.05 of threshold sets `needs_review: true`.

#### Technical Sub-Tasks

- Construct LangChain prompt templates for both agent directions (A and B). Prompts must instruct the LLM to reason about functional intent, not just keyword overlap.
- Implement Direction A loop: iterate over all code chunks from TRACE-201, query Pinecone for top-3 similar requirements, evaluate via LLM, produce output record.
- Implement Direction B loop: iterate over all requirement IDs stored in Pinecone, query all code chunks for semantic matches, evaluate via LLM, produce output record.
- Implement cosine similarity threshold logic with the ambiguous-zone rule (±0.05 band → `needs_review: true`).
- Define Pydantic models for both output schemas (Direction A and Direction B) to enforce structured JSON output from the LLM.
- Aggregate all Direction A and Direction B results into a single Audit Report JSON object with a summary:
  ```json
  {
    "total_code_units": "<int>",
    "ghost_code_count": "<int>",
    "total_requirements": "<int>",
    "orphan_requirement_count": "<int>",
    "needs_review_count": "<int>"
  }
  ```

---

### Sprint 2 – Review & Retrospective (End of Week 4)

- **Sprint Review (30 min):** Run the full AI Agent against the SafeBank v2 branch (built in Sprint 3 but can be partially prepared now). Demonstrate at least one Ghost Code flag and one Orphan Requirement flag being correctly identified. Show the structured JSON audit report.
- **Sprint Retrospective (20 min):** Focus on AI accuracy — is the cosine threshold well-calibrated? Were there false positives/negatives? Document threshold adjustments made and rationale.

---

## Sprint 3: Enterprise Integration & Demonstration | Duration: 1 Week (Week 5)

**Epic:** User Interface & Target Application Simulation

**Sprint Goal:** Deliver a working Streamlit dashboard that wraps the Sprint 1 and Sprint 2 backend, and build the SafeBank demo microservice with deliberate compliance violations to validate and demonstrate the full system end-to-end for evaluation.

> **Revision note:** Sprint 3 is compressed from 2 weeks to 1 week to meet the 5-week deadline. All tickets in this sprint are intentionally scoped to be deliverable within one week. The frontend framework has been locked to Streamlit (not React) given the time constraint. WebSockets have been replaced with HTTP polling.

| Field | Details |
|---|---|
| **Sprint Duration** | 1 Week (Week 5) |
| **Syllabus Alignment** | Unit 3 – System Testing, Integration Testing, Software Documentation; Unit 2 – SRS document authoring |
| **Sprint Ceremonies** | Sprint Planning (Day 1, Week 5) \| Daily Stand-ups \| Final Demo + Retrospective (Day 5, Week 5) |
| **Total Story Points** | 8 points (TRACE-301: 5 pts + TRACE-302: 3 pts) |

---

### TRACE-301 — Build Compliance Dashboard (Streamlit Frontend)

| Ticket ID | Type | Title | Points | Owner |
|---|---|---|---|---|
| TRACE-301 | User Story | Build Compliance Dashboard (Streamlit Frontend) | 5 pts | Aaryan Gera |

#### Description

As a System Administrator or QA Lead, I need a visual interface to upload an SRS document, provide a GitHub repository URL, trigger a full bi-directional audit, and view the resulting traceability matrix — clearly showing which requirements are met, which code is orphaned, and which items need human review.

> **Revision note:** Two corrections applied: (1) The framework is now locked to Streamlit. React is out of scope for a 5-week team-of-3 project and this decision must not remain open at Sprint 3. (2) WebSockets have been replaced with HTTP polling (`st.rerun()` or manual refresh) — this is adequate for a demo-grade tool and avoids the concurrency complexity of WebSocket connections in Streamlit.

#### Acceptance Criteria (BDD Format)

- **Given** the Streamlit app is running locally (`streamlit run app.py`).
- **When** the user uploads a valid SRS document and provides a GitHub repository URL, then clicks 'Run Audit'.
- **Then** the app calls the FastAPI backend endpoints from Sprints 1 and 2 sequentially and displays a progress indicator while the audit runs.
- **And** once complete, the results panel displays a side-by-side traceability matrix: Requirement ID and summary on the left; matched code unit and file path on the right.
- **And** Ghost Code violations are highlighted in **red**; Orphan Requirements in **orange**; items flagged `needs_review: true` in **yellow**; passing items in **green**.
- **And** a summary metrics bar at the top shows: Total Requirements, Requirements Met, Orphan Requirements, Ghost Code Units, Items Needing Review.
- **And** the full audit report is exportable as a JSON file via a **Download Report** button.

#### Technical Sub-Tasks

- Build the Streamlit app (`app.py`) with: file uploader widget (`st.file_uploader`), text input for GitHub URL and branch, and an audit trigger button.
- Implement API calls to the FastAPI backend using the `requests` library. Display `st.spinner()` while waiting for the audit to complete.
- Build the results section using `st.dataframe()` or `st.table()` with conditional row coloring based on `status` and `flag` fields.
- Implement `st.metric()` cards for the summary bar (Total Requirements, Orphan Count, Ghost Code Count, etc.).
- Implement JSON report download using `st.download_button()` with the aggregated audit report JSON.
- Test the full end-to-end flow: upload SafeBank SRS → point to SafeBank v2 repo → verify the dashboard shows the injected Ghost Code and Orphan Requirement correctly flagged.

---

### TRACE-302 — Develop 'SafeBank' Target Microservice for E2E Demonstration

| Ticket ID | Type | Title | Points | Owner |
|---|---|---|---|---|
| TRACE-302 | User Story | Develop 'SafeBank' Target Microservice for E2E Demonstration | 3 pts | Sathvik Reddy V |

#### Description

As an evaluator, I need to see the TraceAgent tool operating on a realistic, industry-standard codebase that contains deliberate compliance violations. SafeBank is a controlled banking API built specifically to demonstrate the system's efficacy to industry evaluators and academic assessors.

> **Revision note:** The SafeBank SRS has been expanded from '2 pages' to a minimum of 8–10 distinct functional requirements. A 2-page SRS generates too few requirement chunks to meaningfully exercise the vector DB or produce a convincing traceability matrix. 8–10 requirements ensures sufficient semantic coverage for the demo while remaining achievable in one week.

#### Acceptance Criteria (BDD Format)

- **Given** the need for a controlled demonstration environment.
- **When** the project is presented to evaluators.
- **Then** a SafeBank IEEE-830 SRS document is available containing a minimum of 8–10 distinct, clearly numbered functional requirements (e.g., FR-01 through FR-10).
- **And** a SafeBank FastAPI microservice (`safebank_api.py`) is available with a `v1` branch whose implemented functions map 1:1 to every FR in the SRS — TraceAgent must return 100% PASS on `v1`.
- **And** the `v2` branch contains exactly the following deliberate violations:
  - **Ghost Code:** One or more undocumented functions present in code but absent from the SRS (e.g., an internal `crypto_wallet_transfer()` function not listed in any FR).
  - **Orphan Requirement:** One or more SRS requirements with no corresponding implementation in the codebase (e.g., FR-07: OTP verification — function defined in SRS but missing from the code).
- **And** TraceAgent must correctly flag both violations on the `v2` branch during the live demo.

#### Technical Sub-Tasks

- Draft the SafeBank IEEE-830 SRS: minimum 8 functional requirements covering standard banking operations (user registration, login, account balance, deposit, withdrawal, transaction history, fund transfer, OTP verification). Number requirements FR-01 through FR-08 (or more).
- Implement the SafeBank FastAPI app (`safebank_api.py`) with clean CRUD endpoints matching all FRs. Commit to the `v1` branch.
- Create the `v2` branch from `v1` and introduce the deliberate flaws:
  - Add `crypto_wallet_transfer()` with no corresponding SRS entry.
  - Comment out or delete the OTP verification endpoint.
- Verify manually: run TraceAgent on `v1` → confirm all PASS. Run on `v2` → confirm Ghost Code and Orphan Requirement flags appear correctly.
- Document the expected audit results for `v2` in a `DEMO_SCRIPT.md` so the team can present confidently.

---

### Sprint 3 – Final Demo & Retrospective (End of Week 5)

- **Final Demo (45 min):** Present the complete TraceAgent system to evaluators. Run the live audit against SafeBank v2 in real time. Walk through the dashboard, highlight the Ghost Code and Orphan Requirement detections, and export the JSON audit report. Tie each demo moment to the relevant course outcome (CO1–CO5) and syllabus unit.
- **Final Retrospective (20 min):** What would the team build next if given more time (e.g., multi-language AST support, CI/CD integration, a scoring dashboard)? Document lessons learned.

---

## Syllabus & Course Outcome Mapping

| CO | Unit | Syllabus Topic | TraceAgent Connection |
|---|---|---|---|
| CO1 | Unit 1 | Software Engineering principles; SDLC models | The project follows an Agile Scrum framework (sprints, stories, reviews, retrospectives). |
| CO2 | Unit 1 | Agile methodologies; Scrum | Sprint structure, daily stand-ups, story points, and retrospectives directly implement Scrum. |
| CO3 | Unit 2 | Requirements Engineering; SRS structure; Functional & Non-functional Requirements | TRACE-101 and TRACE-102 parse and semantically index IEEE-830 SRS documents. TRACE-302 produces a full IEEE-830 SRS for SafeBank. |
| CO4 | Unit 2 | Software Design; Cohesion, Coupling; Microservices; UML | TraceAgent uses a microservices architecture (ingestion, agent, frontend) with low coupling between services via REST APIs. |
| CO5 | Unit 3 | Code Inspection; Code Walkthrough; Static Analysis; Testing | TRACE-202 automates Code Inspection and Walkthrough at scale using LLM-based static analysis. TRACE-301 visualises results as a traceability matrix. |

---

## Technology Stack Reference

| Layer | Technology | Library / Service | Purpose |
|---|---|---|---|
| **Backend** | Python 3.11+ | FastAPI, Uvicorn | REST API server for document ingestion and audit trigger endpoints |
| **Document Parsing** | Python | pdfplumber, python-docx, python-dotenv | PDF and docx text extraction; environment variable management |
| **AI / RAG** | LangChain | RecursiveCharacterTextSplitter, LLM chains | Document chunking and LLM prompt orchestration |
| **Embeddings** | OpenAI / Gemini | text-embedding-ada-002 or Gemini embedding API | Converting text chunks into dense semantic vectors |
| **Vector Database (Prod)** | Pinecone | pinecone-client | Cloud vector storage and semantic similarity search |
| **Vector Database (Dev)** | FAISS | faiss-cpu | Local development substitute; controlled by `USE_LOCAL_VECTOR_DB` flag |
| **Code Analysis** | Python AST | ast (stdlib), GitPython | Structured extraction of functions/classes from Python source code |
| **LLM Agent** | LangChain | ChatOpenAI / ChatGoogleGenerativeAI, Pydantic | Bi-directional compliance reasoning with structured JSON output |
| **Frontend** | Streamlit | streamlit, requests | Interactive dashboard for audit triggering and result visualisation |
| **Demo App** | Python | FastAPI or Flask | SafeBank microservice for end-to-end demonstration |
| **Version Control** | Git / GitHub | GitPython (for cloning) | Source control, branch management, repo access for code analysis |
