"""
jd_analyzer.py
──────────────
Sends a Job Description to the LLM and derives structured ranking dimensions.
Dimensions are derived entirely from the JD — nothing is hardcoded.
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


JD_SYSTEM_PROMPT = """You are an expert talent acquisition analyst. Your job is to read a job description and extract a structured set of evaluation dimensions that an HR coordinator can use to screen CVs — even without deep technical domain knowledge.

You must derive dimensions from the JD itself. Do not use generic or hardcoded dimensions.

Output ONLY a valid JSON array. Each element must be an object with exactly these keys:
- "id": short snake_case identifier (e.g. "python_experience")
- "name": human-readable name (e.g. "Python & Backend Engineering")
- "description": what this dimension measures (1-2 sentences)
- "what_to_look_for": concrete signals an HR reviewer should look for in a CV (3-5 bullet points as a string)
- "weight": relative importance as an integer 1-5 (5 = most critical, derived from the JD)
- "disqualifying": true if a candidate missing this dimension should be auto-rejected, false otherwise

Aim for 5-8 dimensions total. Cover both technical and soft/contextual dimensions where relevant. Be specific — dimensions should reflect THIS role, not generic hiring criteria."""


JD_USER_TEMPLATE = """Here is the job description to analyse:

---
{jd_text}
---

Extract the ranking dimensions as a JSON array. Output ONLY the JSON, no explanation, no markdown fences."""


def analyze_jd(jd_text: str) -> list[dict]:
    """
    Analyse a job description and return a list of ranking dimensions.

    Args:
        jd_text: Plain text of the job description.

    Returns:
        List of dimension dicts.

    Raises:
        ValueError: If LLM response cannot be parsed.
    """
    client = _get_client()
    model = _get_model()

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": JD_SYSTEM_PROMPT},
            {"role": "user", "content": JD_USER_TEMPLATE.format(jd_text=jd_text)},
        ],
        temperature=0.2,
        max_tokens=2000,
    )

    raw = response.choices[0].message.content.strip()

    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    if raw.endswith("```"):
        raw = raw[:-3].strip()

    try:
        dimensions = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM returned invalid JSON: {e}\nRaw: {raw[:500]}")

    if not isinstance(dimensions, list):
        raise ValueError("Expected a JSON array of dimensions.")

    required_keys = {"id", "name", "description", "what_to_look_for", "weight", "disqualifying"}
    for i, dim in enumerate(dimensions):
        missing = required_keys - set(dim.keys())
        if missing:
            raise ValueError(f"Dimension {i} missing keys: {missing}")
        dim["weight"] = int(dim.get("weight", 3))
        dim["disqualifying"] = bool(dim.get("disqualifying", False))

    return dimensions
