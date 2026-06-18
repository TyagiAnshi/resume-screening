"""
pii_scrubber.py
───────────────
Removes PII from text using Microsoft Presidio + spaCy (en_core_web_lg).
ALL processing is 100% local — no data leaves the machine.

spaCy 3.8.x + blis 1.3.x ship arm64 wheels for Python 3.13, so this
works on Apple Silicon without any compilation.

Entities scrubbed:
  PERSON, EMAIL_ADDRESS, PHONE_NUMBER, LOCATION, URL,
  CREDIT_CARD, IBAN_CODE, IP_ADDRESS, NRP
  Plus regex layer: LinkedIn/GitHub URLs, Indian PAN/Aadhaar
"""

import re
from functools import lru_cache

from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig


ENTITIES_TO_SCRUB = [
    "PERSON",
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "LOCATION",
    "URL",
    "CREDIT_CARD",
    "IBAN_CODE",
    "IP_ADDRESS",
    "NRP",
]


@lru_cache(maxsize=1)
def _get_engines():
    """
    Initialise Presidio engines once and cache them.
    Uses spaCy en_core_web_lg for NER — runs fully locally.
    """
    configuration = {
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "en", "model_name": "en_core_web_lg"}],
    }
    provider = NlpEngineProvider(nlp_configuration=configuration)
    nlp_engine = provider.create_engine()
    analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["en"])
    anonymizer = AnonymizerEngine()
    return analyzer, anonymizer


def scrub_pii(text: str) -> tuple[str, list[dict]]:
    """
    Scrub PII from the input text locally using Presidio + spaCy.

    Args:
        text: Raw extracted text (CV or JD).

    Returns:
        (scrubbed_text, redaction_log)
        - scrubbed_text: Text with PII replaced by <ENTITY_TYPE> placeholders.
        - redaction_log: List of {entity_type, start, end, score} dicts.
    """
    if not text or not text.strip():
        return text, []

    analyzer, anonymizer = _get_engines()

    results = analyzer.analyze(
        text=text,
        entities=ENTITIES_TO_SCRUB,
        language="en",
    )

    operators = {
        entity: OperatorConfig("replace", {"new_value": f"<{entity}>"})
        for entity in ENTITIES_TO_SCRUB
    }
    operators["DEFAULT"] = OperatorConfig("replace", {"new_value": "<REDACTED>"})

    anonymized = anonymizer.anonymize(
        text=text,
        analyzer_results=results,
        operators=operators,
    )

    redaction_log = [
        {
            "entity_type": r.entity_type,
            "start": r.start,
            "end": r.end,
            "score": round(r.score, 3),
        }
        for r in results
    ]

    # Regex pass for anything the NER model might miss
    scrubbed, regex_log = _regex_cleanup(anonymized.text)
    redaction_log.extend(regex_log)

    return scrubbed, redaction_log


def _regex_cleanup(text: str) -> tuple[str, list[dict]]:
    """Regex fallback for common PII patterns."""
    log: list[dict] = []

    rules = [
        # Email
        (r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", "<EMAIL_ADDRESS>", "EMAIL_ADDRESS"),
        # LinkedIn URL
        (r"(?:https?://)?(?:www\.)?linkedin\.com/in/[^\s,\"'<>]+", "<URL>", "URL"),
        # GitHub URL
        (r"(?:https?://)?(?:www\.)?github\.com/[^\s,\"'<>]+", "<URL>", "URL"),
        # Generic https URL
        (r"https?://[^\s,\"'<>]+", "<URL>", "URL"),
        # Indian PAN
        (r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", "<IN_PAN>", "IN_PAN"),
        # Indian Aadhaar
        (r"\b\d{4}\s\d{4}\s\d{4}\b", "<IN_AADHAAR>", "IN_AADHAAR"),
        # Phone (broad international fallback)
        (r"(?<!\d)(\+?[\d][\d\s\-().]{7,}[\d])(?!\d)", "<PHONE_NUMBER>", "PHONE_NUMBER"),
    ]

    for pattern, replacement, entity_type in rules:
        def _replace(m, et=entity_type, repl=replacement):
            log.append({"entity_type": et, "start": m.start(), "end": m.end(), "score": 0.85})
            return repl
        text = re.sub(pattern, _replace, text)

    return text, log
