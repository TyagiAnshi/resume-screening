# ResumeIQ — AI-Powered Resume Screening Tool

A proof-of-concept tool that helps HR coordinators screen CVs against a job description — without needing deep domain knowledge of the role.

---

## What I Built

**ResumeIQ** addresses the core problem: conventional ATS keyword-matching misses context and penalises candidates who describe experience differently. This tool uses an LLM to reason contextually — the way a human reviewer would — while keeping all PII processing fully local.

### Key Features

| Feature | Implementation |
|---|---|
| PDF + Text extraction | `pdfplumber` — fully local |
| **PII scrubbing (local)** | Microsoft Presidio (pattern/regex engine) — no spaCy NLP model needed, no data sent externally |
| JD-derived ranking dimensions | LLM reads the JD and generates role-specific evaluation criteria |
| **Ranking file** | YAML written to `outputs/` *before* any CV is evaluated — inspectable transparency artifact |
| Multi-dimensional CV scoring | 0–10 score per dimension with justification + evidence quotes |
| Highlights summary | Strengths, gaps, concerns, candidate-specific interview probes |
| Premium web UI | Dark glassmorphism, animated score bars, leaderboard, expandable detail cards |
| HR Notes | Per-candidate notes, auto-saved in session |
| Export | One-click JSON export of the full session |
| Multiple CVs | Screen as many CVs as needed against one JD |

---

## Architecture

```
resume-screener/
├── backend/
│   ├── main.py            # FastAPI server (all routes)
│   ├── pdf_extractor.py   # Local PDF/text extraction (pdfplumber)
│   ├── pii_scrubber.py    # Local PII removal (Presidio + spaCy)
│   ├── jd_analyzer.py     # JD → ranking dimensions (LLM)
│   ├── ranking_file.py    # Write/read ranking YAML
│   ├── cv_evaluator.py    # CV → multi-dim scores + highlights (LLM)
│   └── requirements.txt
├── frontend/
│   ├── index.html         # Three-step UI (no framework, no build step)
│   ├── style.css          # Design system
│   └── app.js             # All frontend logic
├── sample_data/
│   ├── jd_sample.txt      # Senior Backend Engineer JD
│   ├── cv_strong.txt      # Strong-fit candidate
│   ├── cv_medium.txt      # Medium-fit candidate
│   └── cv_weak.txt        # Weak-fit candidate
├── outputs/               # Ranking files + exports (auto-created)
├── .env.example
└── README.md
```

---

## How to Run Locally

### 1. Create and activate a virtual environment

```bash
cd resume-screener/backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_lg
```

### 3. Configure your LLM API key

```bash
cp ../.env.example ../.env
```

Edit `.env`:

```env
# OpenRouter (recommended — access Claude, GPT-4o, Gemini, etc.)
OPENROUTER_API_KEY=sk-or-your-key-here
LLM_MODEL=anthropic/claude-sonnet-4-5
LLM_BASE_URL=https://openrouter.ai/api/v1

# OR use OpenAI directly:
# OPENAI_API_KEY=sk-your-key-here
# LLM_MODEL=gpt-4o
# LLM_BASE_URL=https://api.openai.com/v1
```

### 4. Start the backend

```bash
cd resume-screener/backend
uvicorn main:app --reload --port 8000
```

### 5. Open the frontend

Open `resume-screener/frontend/index.html` in your browser.

No build step needed — plain HTML/CSS/JS.

*(Or serve it: `cd frontend && python3 -m http.server 3000` → open http://localhost:3000)*

---

## Sample Data Walkthrough

```
Upload jd_sample.txt     → 5–8 role-specific dimensions derived
Upload cv_strong.txt     → STRONG_YES  (~8–9/10)
Upload cv_medium.txt     → YES / MAYBE (~5–7/10)
Upload cv_weak.txt       → NO          (~2–4/10)
```

After each CV, check `outputs/ranking_*.yaml` to inspect the dimensions used.

---

## Non-Local Dependencies

| Dependency | Purpose | Required? |
|---|---|---|
| LLM API (OpenRouter or OpenAI) | JD analysis + CV evaluation | **Yes** |
| Google Fonts | UI typography (Inter, JetBrains Mono) | No — degrades gracefully |

**Everything else runs locally**: PDF extraction, PII scrubbing, file I/O, ranking file.

---

## Key Assumptions

1. **Single JD per session** — one JD drives all CV evaluations.
2. **PII scrubs before LLM** — Presidio runs first; only anonymised text is sent to the LLM.
3. **No database** — session state is in-memory. Refresh = fresh session (POC by design).
4. **No auth** — single-user local tool.
5. **Ranking dimensions are not hardcoded** — derived fresh from each JD, making the tool role-agnostic.
6. **Ranking file is written before any CV is evaluated** — HR coordinator can inspect and validate the criteria first.

---

## Ranking File Format

Example `outputs/ranking_20250618_143022.yaml`:

```yaml
generated_at: '2025-06-18T14:30:22'
description: Auto-derived ranking dimensions from the job description...
dimensions:
  - id: streaming_systems_experience
    name: Streaming Systems Experience
    description: Hands-on experience with Kafka, Flink, or Spark at production scale
    what_to_look_for: |
      - Evidence of Kafka/Flink/Spark in production (not just tutorials)
      - Scale indicators (events/day, throughput numbers)
      - Operational experience (SLOs, incident response)
    weight: 5
    disqualifying: true
  - id: python_backend_proficiency
    name: Python & Backend Engineering
    ...
```

---

## Natural Extensions Implemented

- ✅ Multiple CVs against a single JD in the same session
- ✅ HR coordinator notes per candidate (auto-saved)
- ✅ Export full session as shareable JSON summary
