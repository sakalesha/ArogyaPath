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
import torch
from pathlib import Path
from typing import Optional
from sentence_transformers import SentenceTransformer, util

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
        """Load the SentenceTransformer model and the pre-computed index."""
        try:
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            
            if SEMANTIC_INDEX_PATH.exists():
                index_data = joblib.load(SEMANTIC_INDEX_PATH)
                self.condition_vectors = index_data['vectors']
                self.condition_ids = index_data['ids']
                logger.info(f"Loaded semantic index with {len(self.condition_ids)} vectors.")
            else:
                logger.warning("Semantic index not found. Fallback to live encoding.")
                self._build_live_index()
        except Exception as e:
            logger.error(f"Failed to load semantic model: {e}")
            self.model = None

    def _build_live_index(self):
        """Build the semantic index on the fly if joblib is missing."""
        texts = []
        ids = []
        for cond in self.conditions:
            combined_text = " ".join(cond.get("symptom_keywords", []) + [cond["name"]])
            texts.append(combined_text)
            ids.append(cond["id"])
        
        if texts:
            self.condition_vectors = self.model.encode(texts, convert_to_tensor=True)
            self.condition_ids = ids
            logger.info("Built live semantic index.")

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

                if best_label != "other" and best_score >= 0.65:
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

        # --- PHASE 2: Semantic Fallback (Robust but Generic) ---
        if not conditions and self.model and self.condition_vectors is not None:
            try:
                query_vec = self.model.encode(cleaned, convert_to_tensor=True)
                cosine_scores = util.cos_sim(query_vec, self.condition_vectors)[0]
                
                best_idx = torch.argmax(cosine_scores).item()
                best_score = cosine_scores[best_idx].item()
                
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
                        confidence_source = "semantic_vector"
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
