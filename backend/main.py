"""
main.py
───────
FastAPI backend for the Resume Screening Tool.

Routes:
  POST   /api/analyze-jd          Upload JD → derive ranking dimensions
  GET    /api/ranking-file         Download generated ranking YAML
  GET    /api/ranking-file/content Get ranking file as JSON
  POST   /api/evaluate-cv          Upload CV → score against dimensions
  GET    /api/candidates           List all evaluated candidates
  GET    /api/candidates/{id}      Get single candidate result
  POST   /api/notes/{id}           Save HR notes for a candidate
  GET    /api/export               Export session as JSON
  GET    /api/session              Get current session state
  DELETE /api/session              Reset session
"""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

from pdf_extractor import extract_text
from pii_scrubber import scrub_pii
from jd_analyzer import analyze_jd
from cv_evaluator import evaluate_cv
from ranking_file import write_ranking_file, read_ranking_file

load_dotenv()

app = FastAPI(title="Resume Screening Tool", version="1.0.0")

# Allow frontend (served from file:// or localhost) to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./outputs")
Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

# ── In-memory session ────────────────────────────────────────────────────────
session: dict = {
    "jd_scrubbed": None,
    "dimensions": [],
    "ranking_file_path": None,
    "candidates": {},
    "notes": {},
    "created_at": None,
}


# ── Pydantic models ───────────────────────────────────────────────────────────
class NotesPayload(BaseModel):
    notes: str


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {"message": "Resume Screening Tool API", "version": "1.0.0"}


@app.get("/api/session")
async def get_session():
    return {
        "has_jd": session["jd_scrubbed"] is not None,
        "dimension_count": len(session["dimensions"]),
        "candidate_count": len(session["candidates"]),
        "candidate_ids": list(session["candidates"].keys()),
        "created_at": session["created_at"],
    }


@app.delete("/api/session")
async def reset_session():
    session.update({
        "jd_scrubbed": None,
        "dimensions": [],
        "ranking_file_path": None,
        "candidates": {},
        "notes": {},
        "created_at": None,
    })
    return {"message": "Session reset."}


@app.post("/api/analyze-jd")
async def analyze_jd_endpoint(file: UploadFile = File(...)):
    """Upload a JD (PDF or TXT). Returns derived ranking dimensions."""
    try:
        raw_bytes = await file.read()
        filename = file.filename or "job_description.txt"

        jd_text = extract_text(raw_bytes, filename)
        if not jd_text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from JD file.")

        # Scrub PII from JD too (for consistency)
        jd_scrubbed, jd_redactions = scrub_pii(jd_text)

        # Derive ranking dimensions from the JD via LLM
        dimensions = analyze_jd(jd_scrubbed)

        # Write ranking file BEFORE any CV is evaluated
        ranking_path = write_ranking_file(dimensions, OUTPUT_DIR)

        session.update({
            "jd_scrubbed": jd_scrubbed,
            "dimensions": dimensions,
            "ranking_file_path": ranking_path,
            "candidates": {},
            "notes": {},
            "created_at": datetime.now().isoformat(),
        })

        return {
            "success": True,
            "filename": filename,
            "jd_redactions": len(jd_redactions),
            "dimensions": dimensions,
            "ranking_file": os.path.basename(ranking_path),
            "dimension_count": len(dimensions),
        }

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"JD analysis failed: {str(e)}")


@app.get("/api/ranking-file")
async def download_ranking_file():
    """Download the current ranking YAML file."""
    if not session["ranking_file_path"]:
        raise HTTPException(status_code=404, detail="No ranking file available. Analyse a JD first.")
    path = session["ranking_file_path"]
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Ranking file not found on disk.")
    return FileResponse(
        path,
        media_type="application/x-yaml",
        filename=os.path.basename(path),
    )


@app.get("/api/ranking-file/content")
async def get_ranking_file_content():
    """Get ranking file contents as JSON (for display in UI)."""
    if not session["ranking_file_path"]:
        raise HTTPException(status_code=404, detail="No ranking file available.")
    return read_ranking_file(session["ranking_file_path"])


@app.post("/api/evaluate-cv")
async def evaluate_cv_endpoint(file: UploadFile = File(...)):
    """
    Upload a CV. Scrubs PII locally, then evaluates against
    the current session's ranking dimensions.
    """
    if not session["dimensions"]:
        raise HTTPException(
            status_code=400,
            detail="No ranking dimensions available. Please analyse a JD first.",
        )

    try:
        raw_bytes = await file.read()
        filename = file.filename or "cv.txt"
        candidate_id = Path(filename).stem

        cv_text = extract_text(raw_bytes, filename)
        if not cv_text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from CV.")

        # ⚠️ PII scrubbing happens HERE, before any LLM call
        cv_scrubbed, cv_redactions = scrub_pii(cv_text)

        result = evaluate_cv(
            cv_text=cv_scrubbed,
            candidate_id=candidate_id,
            dimensions=session["dimensions"],
        )

        result["filename"] = filename
        result["pii_redactions"] = len(cv_redactions)
        result["evaluated_at"] = datetime.now().isoformat()

        session["candidates"][candidate_id] = result
        if candidate_id not in session["notes"]:
            session["notes"][candidate_id] = ""

        return {"success": True, "result": result}

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CV evaluation failed: {str(e)}")


@app.get("/api/candidates")
async def list_candidates():
    return {
        "candidates": [
            {**v, "notes": session["notes"].get(k, "")}
            for k, v in session["candidates"].items()
        ]
    }


@app.get("/api/candidates/{candidate_id}")
async def get_candidate(candidate_id: str):
    if candidate_id not in session["candidates"]:
        raise HTTPException(status_code=404, detail=f"Candidate '{candidate_id}' not found.")
    result = dict(session["candidates"][candidate_id])
    result["notes"] = session["notes"].get(candidate_id, "")
    return result


@app.post("/api/notes/{candidate_id}")
async def save_notes(candidate_id: str, payload: NotesPayload):
    if candidate_id not in session["candidates"]:
        raise HTTPException(status_code=404, detail=f"Candidate '{candidate_id}' not found.")
    session["notes"][candidate_id] = payload.notes
    return {"success": True, "candidate_id": candidate_id}


@app.get("/api/export")
async def export_session():
    """Export full session (dimensions + all evaluations + notes) as JSON."""
    if not session["dimensions"]:
        raise HTTPException(status_code=400, detail="No session data to export.")

    export_data = {
        "exported_at": datetime.now().isoformat(),
        "ranking_dimensions": session["dimensions"],
        "candidates": [
            {**result, "notes": session["notes"].get(cid, "")}
            for cid, result in session["candidates"].items()
        ],
    }

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_path = os.path.join(OUTPUT_DIR, f"export_{ts}.json")
    with open(export_path, "w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)

    return FileResponse(
        export_path,
        media_type="application/json",
        filename=os.path.basename(export_path),
    )


# ── Serve frontend static files ───────────────────────────────────────────────
frontend_dir = Path(__file__).parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/app", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
