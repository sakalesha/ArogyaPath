# ArogyaPath — Project Process & Evolution

## Starting Point
The project began with only 3 files in the directory:
- `Plan.docx` — a rough but detailed plan covering all modules (NLP, Pathways, Hospitals, Cost, Insurance)
- `ArogyaPath_v3 (1).pptx` — the presentation deck
- `Problem Statement 4 - Ai powered estimation chatbot.docx` — the original hackathon problem statement

No code existed. No folder structure existed.

---

## Phase 0: Folder Structure
The very first step was reading the `Plan.docx` to understand the proposed tech stack (MERN + Python microservice) and create a standard project folder structure:

```
frontend/ → React UI
backend/  → Node.js + Express APIs
nlp_engine/ → Python + FastAPI
data/ → raw and processed datasets
docs/ → documentation
```

This was done by a single PowerShell `mkdir` command.

---

## Phase 1: Architecture Decisions (Back and Forth)

This phase involved a lot of clarification conversations before any code was written.

**Decision 1 — Frontend:**
The team clarified that Google AI Studio was already handling the frontend (a React-based single `index.html`). The backend would be exposed to the Google AI Studio frontend using `ngrok`.

**Decision 2 — LLM or No LLM:**
Initial plan included using LLMs for the NLP layer. After discussion, LLMs were rejected entirely to avoid API rate limits. The final decision: pure Python NLP with optional SpaCy libraries.

**Decision 3 — NLP Stack:**
Research found `SciSpaCy` (biomedical entity extraction) + `medSpaCy` (negation detection) + a rule-based mapping layer was the ideal approach. This was documented in `Document-Project-Flow`.

**Decision 4 — Frontend Integration Method:**
Decided on Function Calling (Tools) in Google AI Studio so Gemini handles conversational understanding and calls the FastAPI backend for real data.

---

## Phase 2: Backend Build (Modules M1 → M4)

It was discovered that a partially-built backend already existed in `backend/nlp/` with:
- `nlp_engine.py` (M1: NLP + Condition Mapping)
- `pathway_engine.py` (M2: Clinical Pathway Engine)
- `hospital_engine.py` (M3: Hospital Ranking)
- Complete JSON data files (`condition_ontology.json`, `pathways.json`, `hospitals.json`)
- Unit test files for all three modules

**M4 — Cost Estimation Engine (Built from scratch):**
- Created `costs.json` with CGHS/NHP-reference pricing for all 10 conditions
- Created `cost_engine.py` with city-tier multipliers, hospital-type multipliers, and PM-JAY insurance calculation
- Wired M4 into `main.py` with `/estimate-cost` and `/cost-pathways` endpoints

**SpaCy Removal:**
The existing `nlp_engine.py` depended on SpaCy, SciSpaCy, and medSpaCy. When `pip install` was run, it failed entirely due to Python 3.13 incompatibility (C-extension compilation failure for `blis`). The NLP engine was rewritten to use pure Python keyword extraction and a sliding-window negation detection algorithm, making it fully compatible with Python 3.13 without any external ML libraries.

---

## Phase 3: Running the Server

The server was started using:
```bash
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

All 4 engines loaded successfully:
- M1 NLP Engine: 10 conditions, 199 unique keywords indexed
- M2 Pathway Engine: 10 pathways
- M3 Hospital Engine: 25 hospitals, 11 cities
- M4 Cost Engine: 10 conditions with full cost data

---

## Phase 4: ngrok Tunnel

ngrok was already installed (version 3.26.0). The backend was exposed publicly via:
```bash
ngrok http 8001
```
Public URL: `https://transfer-parka-rental.ngrok-free.dev`

---

## Phase 5: Google AI Studio Integration Guide

A complete integration guide was written for the frontend team, covering:
- System prompt for Gemini to behave as ArogyaPath assistant
- 4 Tool (Function) definitions for `analyze_query`, `get_pathway`, `get_hospitals`, `estimate_cost`
- Endpoint URLs and API request formats

A VIEW 5 (Cost Estimation screen) prompt was also written for the Google AI Studio frontend developer to extend the existing UI.

---

## Current State (as of May 1, 2026)
- Backend: Fully functional, 4 modules, 8 API endpoints
- Frontend: Managed by Google AI Studio (M1–M4 views being built incrementally via prompts)
- Tunnel: Live via ngrok
- Tests: All M1/M2/M3 unit tests pass. M4 manual testing done via API docs.
