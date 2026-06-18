"""
cv_evaluator.py
───────────────
Evaluates a (PII-scrubbed) CV against pre-derived ranking dimensions.

Produces:
  - Multi-dimensional scores (0-10 per dimension + justification + evidence)
  - Overall weighted score
  - Key highlights summary (strengths, gaps, concerns, interview probes)
  - Recommendation: STRONG_YES | YES | MAYBE | NO
"""

import json
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


def _get_client() -> OpenAI:
    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
    return OpenAI(api_key=api_key, base_url=base_url)


def _get_model() -> str:
    return os.getenv("LLM_MODEL", "anthropic/claude-sonnet-4-5")


CV_SYSTEM_PROMPT = """You are an expert HR analyst and talent evaluator. You evaluate CVs against a set of pre-defined ranking dimensions derived from a job description.

Your goal is to produce a rigorous, contextual evaluation that a non-technical HR coordinator can act on.

Rules:
- Score each dimension 0-10 (0 = no evidence, 10 = exceptional match)
- Base scores on the CV content and the dimension's "what_to_look_for" signals
- Be honest about gaps — do not inflate scores
- The highlights summary must be written for a non-technical reader
- Interview probe questions should be specific to THIS candidate's CV, not generic

Output ONLY a valid JSON object with exactly this structure:
{
  "dimension_scores": [
    {
      "dimension_id": "string",
      "dimension_name": "string",
      "score": 0-10,
      "justification": "2-3 sentences explaining the score based on CV evidence",
      "evidence": ["specific quote or signal from CV", ...]
    }
  ],
  "overall_weighted_score": 0-10,
  "highlights": {
    "strengths": ["strength 1", "strength 2", ...],
    "gaps": ["gap 1", "gap 2", ...],
    "concerns": ["concern 1", ...],
    "interview_probes": ["specific question to ask this candidate", ...]
  },
  "recommendation": "STRONG_YES | YES | MAYBE | NO",
  "recommendation_rationale": "1-2 sentence summary for the HR coordinator"
}"""


CV_USER_TEMPLATE = """## Ranking Dimensions
{dimensions_json}

## CV Content (PII has been scrubbed locally before this call)
Candidate identifier: {candidate_id}

---
{cv_text}
---

Evaluate this CV against each dimension. Output ONLY the JSON object."""


def evaluate_cv(cv_text: str, candidate_id: str, dimensions: list[dict]) -> dict:
    """
    Evaluate a CV against the ranking dimensions.

    Args:
        cv_text:       Scrubbed CV text.
        candidate_id:  Original filename as candidate identifier.
        dimensions:    List of dimension dicts from jd_analyzer.

    Returns:
        Evaluation dict with scores, highlights, and recommendation.
    """
    client = _get_client()
    model = _get_model()

    dimensions_json = json.dumps(dimensions, indent=2, ensure_ascii=False)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": CV_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": CV_USER_TEMPLATE.format(
                    dimensions_json=dimensions_json,
                    candidate_id=candidate_id,
                    cv_text=cv_text,
                ),
            },
        ],
        temperature=0.15,
        max_tokens=3000,
    )

    raw = response.choices[0].message.content.strip()

    # Strip markdown fences
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    if raw.endswith("```"):
        raw = raw[:-3].strip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM returned invalid JSON for CV evaluation: {e}\nRaw: {raw[:500]}")

    result["candidate_id"] = candidate_id
    result["overall_weighted_score"] = _compute_weighted_score(
        result.get("dimension_scores", []), dimensions
    )

    return result


def _compute_weighted_score(dimension_scores: list[dict], dimensions: list[dict]) -> float:
    """Compute a weighted average score across all dimensions."""
    if not dimension_scores or not dimensions:
        return 0.0

    weight_map = {d["id"]: d.get("weight", 3) for d in dimensions}
    total_weight = 0
    weighted_sum = 0.0

    for ds in dimension_scores:
        weight = weight_map.get(ds.get("dimension_id", ""), 3)
        score = float(ds.get("score", 0))
        weighted_sum += score * weight
        total_weight += weight

    if total_weight == 0:
        return 0.0

    return round(weighted_sum / total_weight, 2)
