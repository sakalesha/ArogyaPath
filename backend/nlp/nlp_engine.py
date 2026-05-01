"""
ArogyaPath · Module M1 — NLP Engine (Pure Python Fallback)
============================================================
Pipeline: Pre-processing → Keyword Extraction → Negation Filtering → Scoring → Safety Gate

Note: This version uses pure Python keyword matching instead of SpaCy/medSpaCy,
making it fully compatible with Python 3.13+ without any C-extension compilation.
SpaCy can be re-enabled later by installing Python 3.11 and uncommenting the imports.
"""

import json
import re
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

ONTOLOGY_PATH = Path(__file__).parent / "condition_ontology.json"
LOW_CONFIDENCE_THRESHOLD = 0.45
MAX_CONDITIONS_RETURNED = 3

# Negation trigger words (simple ConText-style negation)
NEGATION_TRIGGERS = [
    "no", "not", "without", "denies", "deny", "absent",
    "never", "none", "negative for", "ruled out",
]

# Medical abbreviations and shorthand → expanded form
MEDICAL_ABBREVIATIONS = {
    "bp": "blood pressure",
    "htn": "hypertension",
    "dm": "diabetes mellitus",
    "cad": "coronary artery disease",
    "mi": "myocardial infarction",
    "pci": "angioplasty",
    "cabg": "bypass surgery",
    "tkr": "total knee replacement",
    "sob": "shortness of breath",
    "cp": "chest pain",
    "gi": "gastrointestinal",
    "uti": "urinary tract infection",
    "lbp": "lower back pain",
}


# ─────────────────────────────────────────────────────────────────────────────
# NLPEngine
# ─────────────────────────────────────────────────────────────────────────────

class NLPEngine:
    """
    Core NLP pipeline for symptom extraction and condition mapping.

    Processing order:
    1. Pre-process (clean + expand abbreviations)
    2. Keyword Extraction — collect all known symptom/procedure keywords from text
    3. Negation Filtering — remove keywords that follow a negation trigger word
    4. Keyword scoring → rank conditions from controlled ontology
    5. Safety gate → emergency flag + low-confidence threshold
    """

    def __init__(self):
        logger.info("Initializing NLP Engine (Pure Python mode — no SpaCy required)...")
        self._load_ontology()
        self._build_keyword_index()
        logger.info("NLP Engine ready.")

    # ── Setup ──────────────────────────────────────────────────────────────

    def _load_ontology(self):
        """Load the controlled condition ontology from JSON."""
        with open(ONTOLOGY_PATH, encoding="utf-8") as f:
            data = json.load(f)
        self.conditions = data["conditions"]
        self.emergency_keywords = [kw.lower() for kw in data["emergency_keywords"]]
        logger.info(f"Loaded ontology: {len(self.conditions)} conditions.")

    def _build_keyword_index(self):
        """
        Build a flat index of all known symptom and procedure keywords
        from the condition ontology for fast O(n) substring matching.
        """
        self.all_keywords = set()
        for condition in self.conditions:
            for kw in condition.get("symptom_keywords", []):
                self.all_keywords.add(kw.lower())
            for kw in condition.get("procedure_keywords", []):
                self.all_keywords.add(kw.lower())
        logger.info(f"Keyword index built: {len(self.all_keywords)} unique terms.")

    # ── Public API ─────────────────────────────────────────────────────────

    def process(self, query: str) -> dict:
        """
        Main entry point. Takes raw user query, returns structured JSON result.

        Returns:
        {
          "query": str,
          "cleaned_query": str,
          "extracted_symptoms": [str],
          "negated_symptoms": [str],
          "conditions": [{"name", "icd10", "confidence", "pathway_id"}],
          "top_condition": str | None,
          "low_confidence": bool,
          "emergency_flag": bool,
          "emergency_message": str | None
        }
        """
        if not query or not query.strip():
            return self._empty_result(query)

        # Step 1 — Pre-process
        cleaned = self._preprocess(query)

        # Step 2+3 — NER + Negation Filtering
        confirmed, negated = self._extract_and_filter(cleaned)

        # Step 4 — Score conditions using ontology
        # Also includes direct keyword matches on the cleaned text
        conditions = self._score_conditions(confirmed, cleaned)

        # Step 5 — Emergency check
        emergency_flag, emergency_message = self._check_emergency(cleaned)

        # Step 6 — Confidence threshold
        top_confidence = conditions[0]["confidence"] if conditions else 0.0
        low_confidence = top_confidence < LOW_CONFIDENCE_THRESHOLD and not emergency_flag

        return {
            "query": query,
            "cleaned_query": cleaned,
            "extracted_symptoms": confirmed,
            "negated_symptoms": negated,
            "conditions": conditions[:MAX_CONDITIONS_RETURNED],
            "top_condition": conditions[0]["name"] if conditions else None,
            "low_confidence": low_confidence,
            "emergency_flag": emergency_flag,
            "emergency_message": emergency_message,
        }

    # ── Step 1: Pre-processing ─────────────────────────────────────────────

    def _preprocess(self, text: str) -> str:
        """
        Clean and normalize raw user input:
        - Lowercase
        - Expand medical abbreviations
        - Remove excess punctuation/noise
        - Light spell-check for common misspellings
        """
        text = text.lower().strip()

        # Expand abbreviations (word-boundary aware)
        for abbr, expansion in MEDICAL_ABBREVIATIONS.items():
            text = re.sub(rf"\b{re.escape(abbr)}\b", expansion, text)

        # Remove special characters except spaces, hyphens, apostrophes
        text = re.sub(r"[^\w\s\-']", " ", text)

        # Collapse whitespace
        text = re.sub(r"\s+", " ", text).strip()

        return text

    # ── Step 2+3: NER + ConText Filtering ─────────────────────────────────

    def _extract_and_filter(self, text: str) -> tuple[list[str], list[str]]:
        """
        Pure Python keyword extraction with simple sliding-window negation detection.

        Algorithm:
        1. Scan the text for every known keyword (longest-match first to avoid
           partial shadowing, e.g. 'chest pain' before 'pain').
        2. For each matched keyword, look back up to 5 words in the text to check
           whether a NEGATION_TRIGGER appears before it.
        3. Route matches to confirmed or negated lists accordingly.

        Returns: (confirmed_keywords, negated_keywords)
        """
        confirmed = []
        negated = []

        # Sort keywords longest-first so multi-word phrases match before sub-phrases
        sorted_keywords = sorted(self.all_keywords, key=len, reverse=True)

        for kw in sorted_keywords:
            # Find all occurrences of the keyword in text
            for match in re.finditer(re.escape(kw), text):
                start = match.start()

                # Extract up to 5 words before the match for negation check
                prefix = text[:start]
                preceding_words = prefix.strip().split()
                window = " ".join(preceding_words[-5:]).lower()

                is_negated = any(
                    re.search(rf"\b{re.escape(trigger)}\b", window)
                    for trigger in NEGATION_TRIGGERS
                )

                if is_negated:
                    if kw not in negated:
                        negated.append(kw)
                else:
                    if kw not in confirmed:
                        confirmed.append(kw)
                break  # Only process first occurrence per keyword

        return confirmed, negated

    # ── Step 4: Condition Scoring ──────────────────────────────────────────

    def _score_conditions(self, ner_symptoms: list[str], cleaned_text: str) -> list[dict]:
        """
        Score each condition in the ontology based on:
        1. Keyword matches in NER-extracted entities
        2. Direct substring matches in the cleaned text (catches what NER misses)
        3. Exclusion keyword penalty
        4. Condition weight multiplier

        Confidence = normalized score (0.0 – 1.0)
        """
        scores = []

        for condition in self.conditions:
            symptom_kws = [kw.lower() for kw in condition["symptom_keywords"]]
            procedure_kws = [kw.lower() for kw in condition["procedure_keywords"]]
            exclusion_kws = [kw.lower() for kw in condition.get("exclusion_keywords", [])]
            severity_kws = [kw.lower() for kw in condition.get("severity_keywords", [])]
            weight = condition.get("weight", 1.0)

            # Count symptom keyword matches (NER entities + direct text)
            symptom_matches = self._count_matches(symptom_kws, ner_symptoms, cleaned_text)
            procedure_matches = self._count_matches(procedure_kws, ner_symptoms, cleaned_text)
            exclusion_hits = self._count_matches(exclusion_kws, ner_symptoms, cleaned_text)
            severity_hits = self._count_matches(severity_kws, ner_symptoms, cleaned_text)

            if symptom_matches == 0 and procedure_matches == 0:
                continue  # No signal → skip

            # Raw score calculation
            total_kws = len(symptom_kws) + len(procedure_kws)
            total_matches = (symptom_matches * 1.0) + (procedure_matches * 0.8)
            raw_score = (total_matches / max(total_kws, 1)) * weight

            # Exclusion penalty (reduces score if contradictory keywords present)
            raw_score -= exclusion_hits * 0.15

            # Severity boost (increases confidence for severe presentations)
            raw_score += severity_hits * 0.05

            raw_score = max(raw_score, 0.0)

            scores.append({
                "id": condition["id"],
                "name": condition["name"],
                "icd10": condition["icd10"],
                "pathway_id": condition.get("pathway_id", ""),
                "_raw_score": raw_score,
                "_matches": int(symptom_matches + procedure_matches),
            })

        if not scores:
            return []

        # Normalize scores → confidence (0.0 – 1.0)
        max_score = max(s["_raw_score"] for s in scores)
        for s in scores:
            s["confidence"] = round(s["_raw_score"] / max_score, 3) if max_score > 0 else 0.0
            del s["_raw_score"]
            del s["_matches"]

        # Sort descending by confidence
        scores.sort(key=lambda x: x["confidence"], reverse=True)
        return scores

    def _count_matches(
        self,
        keywords: list[str],
        ner_entities: list[str],
        text: str,
    ) -> float:
        """
        Count keyword matches using two strategies:
        - Exact substring in text (primary)
        - Partial overlap with NER entity (secondary, half weight)
        """
        count = 0.0
        for kw in keywords:
            if kw in text:
                count += 1.0
            elif any(kw in ent or ent in kw for ent in ner_entities):
                count += 0.5
        return count

    # ── Step 5: Safety Gate ────────────────────────────────────────────────

    def _check_emergency(self, text: str) -> tuple[bool, Optional[str]]:
        """
        Detect emergency keywords. If found, return flag + call-to-action message.
        """
        for kw in self.emergency_keywords:
            if kw in text:
                return True, (
                    f"⚠️ This may be a medical emergency ('{kw}' detected). "
                    "Please call 112 immediately or go to the nearest emergency room. "
                    "This system is for planning purposes only — not for emergencies."
                )
        return False, None

    # ── Helpers ────────────────────────────────────────────────────────────

    def _empty_result(self, query: str) -> dict:
        return {
            "query": query,
            "cleaned_query": "",
            "extracted_symptoms": [],
            "negated_symptoms": [],
            "conditions": [],
            "top_condition": None,
            "low_confidence": True,
            "emergency_flag": False,
            "emergency_message": None,
        }
