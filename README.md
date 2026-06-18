# ResumeIQ — AI-Powered Resume Screening Tool

> Screen CVs against a job description using contextual AI — without needing deep domain knowledge of the role.

![Python](https://img.shields.io/badge/Python-3.11%2B-blue?style=flat-square&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green?style=flat-square&logo=fastapi)
![Presidio](https://img.shields.io/badge/PII-Presidio%20%2B%20spaCy-orange?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-purple?style=flat-square)

---

## The Problem

HR coordinators manage the hiring pipeline across multiple open roles simultaneously. They receive job descriptions from hiring managers but are often not close to the technical requirements of each role. When CVs come in, they need to screen and shortlist — but without deep domain knowledge of what to look for, and while juggling several roles at once.

Conventional ATS tools address this with keyword matching — but keyword matching:
- Misses context (a candidate who says "built event pipelines" scores lower than one who says "used Kafka")
- Penalises candidates who describe experience differently
- Cannot reason about fit the way a human reviewer would

**ResumeIQ** is a proof-of-concept that solves this by using an LLM to reason contextually — deriving evaluation criteria directly from the job description and scoring each CV against those criteria, the way a thoughtful human reviewer would.

---

## What It Does

```
JD (PDF/TXT) ──► Derive ranking dimensions ──► Write ranking YAML
                                                      │
CV (PDF/TXT) ──► Scrub PII locally ──► Score against dimensions
                                                      │
                                          Highlights summary
                                          (strengths, gaps, probes)
                                                      │
                                          Leaderboard + HR notes
                                                      │
                                          Export JSON summary
```

### Key Features

| Feature | Detail |
|---|---|
| 📄 **PDF + Text extraction** | `pdfplumber` — fully local, no external service |
| 🔒 **PII scrubbing (local)** | Microsoft Presidio + spaCy `en_core_web_lg` NER — runs on your machine, **no personal data ever sent to the LLM** |
| 🧠 **JD-derived dimensions** | LLM reads your JD and generates 5–8 evaluation criteria specific to *this* role — nothing is hardcoded |
| 📊 **Ranking file** | YAML file written to `outputs/` **before** any CV is evaluated — transparent, human-readable, machine-usable |
| 🎯 **Multi-dimensional scoring** | Each CV gets a 0–10 score *per dimension* with justification + evidence quotes (not a single opaque number) |
| 💡 **Highlights summary** | Strengths, gaps, concerns, and candidate-specific interview probe questions — written for a non-technical reader |
| 🏆 **Results leaderboard** | All candidates ranked by weighted score with expandable detail cards |
| 📝 **HR notes** | Per-candidate notes auto-saved in the session |
| 📤 **Export** | One-click JSON export of the full session (dimensions + all evaluations + notes) |
| 🔁 **Multiple CVs** | Screen as many CVs as needed against one JD in the same session |

---

## Architecture

```
resume-screener/
│
├── backend/                        # Python FastAPI server
│   ├── main.py                     # All API routes + session management
│   ├── pdf_extractor.py            # PDF/text extraction (pdfplumber)
│   ├── pii_scrubber.py             # Local PII removal (Presidio + spaCy)
│   ├── jd_analyzer.py              # JD → ranking dimensions (LLM call)
│   ├── ranking_file.py             # YAML ranking file writer/reader
│   ├── cv_evaluator.py             # CV → multi-dim scores + highlights (LLM)
│   └── requirements.txt
│
├── frontend/                       # Vanilla HTML/CSS/JS (no build step)
│   ├── index.html                  # 3-step UI: JD → CVs → Results
│   ├── style.css                   # Dark glassmorphism design system
│   └── app.js                      # All frontend logic + API calls
│
├── sample_data/
│   ├── jd_sample.txt               # Sample: Senior Backend Engineer JD
│   ├── cv_strong.txt               # Strong-fit candidate (~8–9/10)
│   ├── cv_medium.txt               # Medium-fit candidate (~5–7/10)
│   └── cv_weak.txt                 # Weak-fit candidate (~2–4/10)
│
├── outputs/                        # Auto-created: ranking YAMLs + exports
├── .env.example                    # Environment variable template
└── README.md
```

### Data Flow (Step by Step)

1. **User uploads JD** → `pdf_extractor.py` extracts text locally
2. **PII scrubbed from JD** → `pii_scrubber.py` runs Presidio + spaCy locally
3. **Dimensions derived** → `jd_analyzer.py` sends scrubbed JD to LLM, receives structured JSON
4. **Ranking file written** → `ranking_file.py` saves YAML to `outputs/` — reviewer can inspect before any CV is touched
5. **User uploads CV** → extracted + PII scrubbed locally (Presidio + spaCy + regex)
6. **CV evaluated** → `cv_evaluator.py` sends (scrubbed CV + dimensions) to LLM, receives scores + highlights
7. **Results displayed** → leaderboard, detail cards, HR notes, export

---

## How to Run Locally

### Prerequisites

- Python 3.11 or higher (tested on 3.13)
- An API key from [OpenRouter](https://openrouter.ai) (free tier available) or OpenAI

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/resume-screener.git
cd resume-screener
```

### 2. Create a virtual environment and install dependencies

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Download the spaCy NLP model

```bash
python -m spacy download en_core_web_lg
```

> This downloads a ~400MB English NLP model used by Presidio for named entity recognition (PERSON, LOCATION detection). It runs fully locally — no internet access during scrubbing.

### 4. Configure your LLM API key

```bash
cp ../.env.example ../.env
```

Edit `.env`:

```env
# Option A: OpenRouter (recommended — access Claude, GPT-4o, Gemini, etc.)
OPENROUTER_API_KEY=sk-or-your-key-here
LLM_MODEL=anthropic/claude-sonnet-4-5
LLM_BASE_URL=https://openrouter.ai/api/v1

# Option B: OpenAI directly
# OPENAI_API_KEY=sk-your-key-here
# LLM_MODEL=gpt-4o
# LLM_BASE_URL=https://api.openai.com/v1
```

### 5. Start the backend server

```bash
# Make sure you're in backend/ with venv activated
uvicorn main:app --reload --port 8000
```

You should see:
```
INFO: Uvicorn running on http://127.0.0.1:8000
INFO: Application startup complete.
```

### 6. Open the frontend

Open `frontend/index.html` directly in your browser — no build step needed.

```bash
open frontend/index.html      # macOS
# or
start frontend/index.html     # Windows
```

---

## Usage Walkthrough

### Step 1 — Upload Job Description

- Drop `sample_data/jd_sample.txt` (or any JD in PDF or TXT format)
- Click **Analyse Job Description**
- The system derives 5–8 evaluation dimensions specific to that role
- A ranking YAML file is written to `outputs/` — **download and inspect it before proceeding**

### Step 2 — Screen Candidates

- Upload CVs one at a time (PDF or TXT)
- For each CV, the system:
  1. Extracts text locally
  2. Scrubs PII locally (emails, phone numbers, names, LinkedIn/GitHub URLs, etc.)
  3. Sends only the anonymised text + dimensions to the LLM
  4. Returns scores (0–10) per dimension + highlights summary

### Step 3 — Review Results

- **Leaderboard**: all candidates ranked by weighted score
- **Detail cards**: click any candidate to see:
  - Score per dimension with justification
  - Evidence quotes from the CV
  - Strengths, gaps, concerns
  - Candidate-specific interview probe questions
  - HR notes field (auto-saved)
- **Export**: download a full JSON summary of the session

---

## Sample Data Results (Expected)

| CV File | Expected Score | Expected Recommendation |
|---|---|---|
| `cv_strong.txt` | 8–9 / 10 | ⭐ Strong Yes |
| `cv_medium.txt` | 5–7 / 10 | ✓ Yes / ~ Maybe |
| `cv_weak.txt` | 2–4 / 10 | ✗ No |

---

## API Reference

The FastAPI backend exposes the following endpoints:

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/analyze-jd` | Upload JD → derive ranking dimensions |
| `GET` | `/api/ranking-file` | Download ranking YAML |
| `GET` | `/api/ranking-file/content` | Get ranking file as JSON |
| `POST` | `/api/evaluate-cv` | Upload CV → score against dimensions |
| `GET` | `/api/candidates` | List all evaluated candidates |
| `GET` | `/api/candidates/{id}` | Get single candidate result |
| `POST` | `/api/notes/{id}` | Save HR notes for a candidate |
| `GET` | `/api/export` | Export full session as JSON |
| `GET` | `/api/session` | Get current session state |
| `DELETE` | `/api/session` | Reset session |

Interactive docs available at `http://localhost:8000/docs` while the server is running.

---

## The Ranking File

The ranking file (`outputs/ranking_YYYYMMDD_HHMMSS.yaml`) is a **transparency artifact** — it captures exactly how the system will evaluate CVs before any CV is processed. An HR coordinator can read and validate it.

Example structure:

```yaml
generated_at: '2025-06-18T14:30:22'
description: Auto-derived ranking dimensions from the job description.
dimensions:
  - id: streaming_systems_experience
    name: Streaming Systems Experience
    description: Hands-on production experience with Kafka, Flink, or Spark Streaming
    what_to_look_for: |
      - Named technologies (Kafka, Flink, Spark) in production — not just tutorials
      - Scale indicators: events/day, throughput numbers, SLA targets
      - Operational ownership: SLOs, incident response, on-call
      - Depth signals: partition tuning, state store design, backpressure handling
    weight: 5
    disqualifying: true

  - id: python_backend_proficiency
    name: Python & Backend Engineering
    description: Senior-level Python development with production microservices
    what_to_look_for: |
      - Python listed as primary language with 5+ years
      - FastAPI, Flask, or Django REST frameworks
      - Evidence of performance optimisation, async patterns
      - Go or Rust mentioned as a bonus
    weight: 4
    disqualifying: false
  ...
```

The same file is fed directly into CV evaluation prompts — so the criteria driving scoring are exactly what you see in the file.

---

## PII Scrubbing — How It Works

PII scrubbing happens **before** any LLM call. The LLM never sees names, contact details, or addresses.

**Layer 1 — Presidio + spaCy NER** (entity recognition):
- `PERSON` — candidate names
- `EMAIL_ADDRESS`, `PHONE_NUMBER`, `URL`
- `LOCATION` — cities, countries, addresses
- `CREDIT_CARD`, `IBAN_CODE`, `IP_ADDRESS`, `NRP`

**Layer 2 — Regex fallback**:
- LinkedIn profile URLs
- GitHub profile URLs
- Indian PAN card (`AAAAA9999A` format)
- Indian Aadhaar (12-digit)
- Any remaining phone patterns

Each redacted entity becomes a `<ENTITY_TYPE>` placeholder (e.g. `<EMAIL_ADDRESS>`, `<PERSON>`). The original filename is preserved as the candidate identifier so results can be linked back.

---

## Non-Local Dependencies

| Dependency | Purpose | Required? |
|---|---|---|
| LLM API (OpenRouter or OpenAI) | JD analysis + CV evaluation | **Yes** |
| Google Fonts (Inter, JetBrains Mono) | UI typography | No — degrades gracefully offline |

**Everything else is fully local**: PDF extraction, PII scrubbing, file I/O, ranking YAML, session state.

---

## Key Assumptions

1. **Single JD per session** — one JD drives all CV evaluations in that session. Reset to start a new role.
2. **PII scrubs before LLM** — Presidio + spaCy runs first; only anonymised text is sent to the LLM. This is enforced in code, not configurable.
3. **No database** — session state is in-memory. Server restart = fresh session (POC by design).
4. **No authentication** — single-user local tool.
5. **Ranking dimensions are not hardcoded** — derived fresh from each JD, making the tool role-agnostic.
6. **Ranking file is written before any CV is evaluated** — the HR coordinator can inspect and validate the criteria first.

---

## Natural Extensions Implemented

Beyond the core requirements, the following extensions are included:

- ✅ **Multiple CVs per session** — screen as many CVs as needed against one JD
- ✅ **HR coordinator notes** — per-candidate text field, auto-saved on keystroke
- ✅ **Export as shareable summary** — full session exported as structured JSON

---

## Suggested Build Order (for understanding the code)

1. [`pdf_extractor.py`](backend/pdf_extractor.py) — text extraction
2. [`pii_scrubber.py`](backend/pii_scrubber.py) — local PII removal
3. [`jd_analyzer.py`](backend/jd_analyzer.py) — LLM: JD → dimensions
4. [`ranking_file.py`](backend/ranking_file.py) — YAML writer
5. [`cv_evaluator.py`](backend/cv_evaluator.py) — LLM: CV → scores + highlights
6. [`main.py`](backend/main.py) — FastAPI glue
7. [`frontend/`](frontend/) — UI

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.13, FastAPI, Uvicorn |
| PDF extraction | pdfplumber |
| PII scrubbing | Microsoft Presidio, spaCy `en_core_web_lg` |
| LLM client | OpenAI SDK (OpenRouter-compatible) |
| Config | python-dotenv |
| Serialisation | PyYAML, JSON |
| Frontend | Vanilla HTML, CSS, JavaScript (no framework, no build step) |
| Fonts | Google Fonts — Inter, JetBrains Mono |

---

## License

MIT — free to use, modify, and distribute.
