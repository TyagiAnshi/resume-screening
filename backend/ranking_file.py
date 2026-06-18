"""
ranking_file.py
───────────────
Writes and reads the ranking dimensions YAML file.

The ranking file is a transparency artifact — it shows exactly
how the system will evaluate CVs before any CV is processed.
"""

import os
import yaml
import json
from datetime import datetime
from pathlib import Path


def write_ranking_file(dimensions: list[dict], output_dir: str = "./outputs") -> str:
    """
    Write ranking dimensions to a YAML file.

    Returns:
        Absolute path to the created file.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ranking_{timestamp}.yaml"
    filepath = os.path.join(output_dir, filename)

    payload = {
        "generated_at": datetime.now().isoformat(),
        "description": (
            "Auto-derived ranking dimensions from the job description. "
            "These dimensions drive CV evaluation. Review before proceeding."
        ),
        "dimensions": dimensions,
    }

    with open(filepath, "w", encoding="utf-8") as f:
        yaml.dump(payload, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    return filepath


def read_ranking_file(filepath: str) -> dict:
    """Load a ranking YAML file and return its contents."""
    with open(filepath, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def dimensions_to_json(dimensions: list[dict]) -> str:
    """Serialize dimensions to compact JSON for LLM prompts."""
    return json.dumps(dimensions, indent=2, ensure_ascii=False)
