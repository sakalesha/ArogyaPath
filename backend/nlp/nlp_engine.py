"""
ArogyaPath · Module M1 — NLP Engine (Pure Semantic Version)
============================================================
Pipeline: Pre-processing → Semantic Vector Search → Result Synthesis

This version has ZERO rule-based logic. All analysis, including 
severity detection, is handled by vector similarity mapping.
"""

import json
import re
import logging
import joblib
from pathlib import Path
from typing import Optional

try:
    import spacy
    HAS_SEMANTIC = True
except ImportError:
    HAS_SEMANTIC = False

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

ONTOLOGY_PATH = Path(__file__).parent / "condition_ontology.json"
SEMANTIC_INDEX_PATH = Path(__file__).parent / "m1_semantic_index.joblib"
CLASSIFIER_MODEL_PATH = Path(__file__).parent / "m1_model.joblib"
SEMANTIC_THRESHOLD = 0.25 # Similarity score required to accept a match

# Medical abbreviations and shorthand → expanded form
MEDICAL_ABBREVIATIONS = {
    "bp": "blood pressure", "htn": "hypertension", "dm": "diabetes mellitus",
    "cad": "coronary artery disease", "mi": "myocardial infarction",
    "pci": "angioplasty", "cabg": "bypass surgery", "tkr": "total knee replacement",
    "sob": "shortness of breath", "cp": "chest pain", "gi": "gastrointestinal",
    "uti": "urinary tract infection", "lbp": "lower back pain",
}

# ─────────────────────────────────────────────────────────────────────────────
# NLPEngine
# ─────────────────────────────────────────────────────────────────────────────

class NLPEngine:
    def __init__(self):
        logger.info("Initializing Hybrid NLP Engine (Classifier + Semantic Fallback)...")
        self._load_ontology()
        self._load_classifier()
        self._load_semantic_model()
        logger.info("Hybrid NLP Engine ready.")

    def _load_ontology(self):
        with open(ONTOLOGY_PATH, encoding="utf-8") as f:
            data = json.load(f)
        self.conditions_meta = {c["id"]: c for c in data["conditions"]}
        self.conditions = data["conditions"]

    def _load_classifier(self):
        """Load the trained Logistic Regression classifier."""
        try:
            if Path(CLASSIFIER_MODEL_PATH).exists():
                self.classifier = joblib.load(CLASSIFIER_MODEL_PATH)
                logger.info("Loaded trained classifier (m1_model.joblib).")
            else:
                logger.warning("Classifier model not found. Fallback to pure semantic.")
                self.classifier = None
        except Exception as e:
            logger.error(f"Failed to load classifier: {e}")
            self.classifier = None

    def _load_semantic_model(self):
        """Load the SpaCy model and build the live semantic index."""
        if not HAS_SEMANTIC:
            logger.warning("SpaCy not installed. Running in lightweight classifier-only mode.")
            self.nlp = None
            self.condition_docs = None
            return

        try:
            self.nlp = spacy.load("en_core_web_md")
            logger.info("Loaded SpaCy en_core_web_md model.")
            self._build_live_index()
        except Exception as e:
            logger.error(f"Failed to load SpaCy model: {e}")
            self.nlp = None

    def _build_live_index(self):
        """Build the semantic index on the fly using SpaCy."""
        self.condition_docs = []
        self.condition_ids = []
        for cond in self.conditions:
            combined_text = " ".join(cond.get("symptom_keywords", []) + [cond["name"]])
            self.condition_docs.append(self.nlp(combined_text))
            self.condition_ids.append(cond["id"])
        
        logger.info("Built live semantic index with SpaCy.")

    def _detect_severity(self, text: str, condition_id: str) -> str:
        """Rule-based severity detection using ontology keywords."""
        text = text.lower()
        
        # 1. Global Emergency Check
        if not hasattr(self, "emergency_keywords"):
            with open(ONTOLOGY_PATH, encoding="utf-8") as f:
                data = json.load(f)
                self.emergency_keywords = data.get("emergency_keywords", [])
        
        if any(kw in text for kw in self.emergency_keywords):
            return "emergency"

        # 2. Condition-Specific Severity Check
        meta = self.conditions_meta.get(condition_id)
        if meta and "severity_keywords" in meta:
            skw = meta["severity_keywords"]
            # Check Emergency first
            if any(kw in text for kw in skw.get("emergency", [])):
                return "emergency"
            # Then Moderate
            if any(kw in text for kw in skw.get("moderate", [])):
                return "moderate"
            # Then Mild
            if any(kw in text for kw in skw.get("mild", [])):
                return "mild"

        return "moderate"  # Safe default

    def process(self, query: str) -> dict:
        if not query or not query.strip():
            return self._empty_result(query)

        cleaned = self._preprocess(query)
        conditions = []
        confidence_source = "none"
        
        # --- PHASE 1: Classifier (Fast & Trained) ---
        if self.classifier:
            try:
                probs = self.classifier.predict_proba([cleaned])[0]
                best_idx = probs.argmax()
                best_label = self.classifier.classes_[best_idx]
                best_score = probs[best_idx]

                # Lowered threshold since we disabled Semantic Fallback for Render Free Tier
                if best_label != "other" and best_score >= 0.20:
                    meta = self.conditions_meta.get(best_label)
                    if meta:
                        conditions.append({
                            "id": meta["id"],
                            "name": meta["name"],
                            "icd10": meta["icd10"],
                            "pathway_id": meta.get("pathway_id", ""),
                            "confidence": round(float(best_score), 3)
                        })
                        confidence_source = "trained_classifier"
            except Exception as e:
                logger.error(f"Classifier prediction failed: {e}")

        # --- PHASE 2: Semantic Fallback (SpaCy Word Vectors) ---
        if not conditions and self.nlp and self.condition_docs:
            try:
                query_doc = self.nlp(cleaned)
                
                # Check if query has word vectors (e.g., if it's completely out of vocabulary)
                if query_doc.has_vector:
                    scores = [query_doc.similarity(doc) for doc in self.condition_docs]
                    
                    best_score = max(scores)
                    best_idx = scores.index(best_score)
                    
                    if best_score >= SEMANTIC_THRESHOLD:
                        condition_id = self.condition_ids[best_idx]
                        meta = self.conditions_meta.get(condition_id)
                        if meta:
                            conditions.append({
                                "id": meta["id"],
                                "name": meta["name"],
                                "icd10": meta["icd10"],
                                "pathway_id": meta.get("pathway_id", ""),
                                "confidence": round(float(best_score), 3)
                            })
                            confidence_source = "spacy_semantic_vector"
            except Exception as e:
                logger.error(f"Semantic fallback failed: {e}")

        # Calculate Severity and Emergency status
        top_condition_id = conditions[0]["id"] if conditions else None
        severity = self._detect_severity(cleaned, top_condition_id)
        is_emergency = (severity == "emergency")

        # Low confidence if top score is weak
        low_confidence = not conditions or conditions[0]["confidence"] < 0.45

        # Extract Symptoms for UI
        extracted_symptoms = []
        if top_condition_id:
            meta = self.conditions_meta.get(top_condition_id)
            if meta and "symptom_keywords" in meta:
                # Sort by length to match longer phrases first
                keywords = sorted(meta["symptom_keywords"], key=len, reverse=True)
                for kw in keywords:
                    if kw in cleaned and not any(kw in e.lower() for e in extracted_symptoms):
                        extracted_symptoms.append(kw.title())
        
        if not extracted_symptoms:
            # Heuristic fallback
            stop_words = {"i", "have", "been", "feeling", "a", "an", "the", "with", "after", "while", "worse", "in", "on", "my", "is", "and", "or", "but", "so", "to", "for", "of", "am", "are"}
            extracted_symptoms = [w.title() for w in cleaned.split() if w not in stop_words and len(w) > 3]
            
        # Simple heuristic for negations
        negated_symptoms = []
        if "no " in cleaned or "not " in cleaned or "without " in cleaned:
            parts = re.split(r'\b(no|not|without)\b', cleaned)
            for i in range(1, len(parts), 2):
                if i+1 < len(parts):
                    neg_target = parts[i+1].strip().split()[0] if parts[i+1].strip() else ""
                    if neg_target and len(neg_target) > 2:
                        negated_symptoms.append(f"{parts[i]} {neg_target}".title())

        return {
            "query": query,
            "cleaned_query": cleaned,
            "extracted_symptoms": extracted_symptoms[:5], # Limit to top 5
            "negated_symptoms": negated_symptoms,
            "conditions": conditions,
            "top_condition": conditions[0]["name"] if conditions else None,
            "severity": severity,
            "low_confidence": low_confidence,
            "confidence_source": confidence_source,
            "emergency_flag": is_emergency,
            "emergency_message": "EMERGENCY: Symptoms suggest a critical condition. Please call 112 immediately." if is_emergency else None
        }

    def _preprocess(self, text: str) -> str:
        text = text.lower().strip()
        for abbr, expansion in MEDICAL_ABBREVIATIONS.items():
            text = re.sub(rf"\b{re.escape(abbr)}\b", expansion, text)
        text = re.sub(r"[^\w\s\-']", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    def _empty_result(self, query: str) -> dict:
        return {
            "query": query, 
            "cleaned_query": "", 
            "extracted_symptoms": [],
            "negated_symptoms": [],
            "conditions": [],
            "top_condition": None, 
            "low_confidence": True,
            "confidence_source": "none",
            "emergency_flag": False, 
            "emergency_message": None,
        }
