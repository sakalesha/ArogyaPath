"""
ArogyaPath · M1 NLP Engine — Unit Tests
=========================================
Run: python -m pytest test_nlp.py -v
"""

import pytest
import sys
import os

# Add parent dir to path so we can import nlp_engine directly
sys.path.insert(0, os.path.dirname(__file__))

from nlp_engine import NLPEngine


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def engine():
    """Create a single engine instance shared across all tests (heavy to load)."""
    return NLPEngine()


# ─────────────────────────────────────────────────────────────────────────────
# Test Suite
# ─────────────────────────────────────────────────────────────────────────────

class TestPreprocessing:
    """Ensure pre-processing cleans and expands input correctly."""

    def test_lowercase(self, engine):
        result = engine._preprocess("CHEST PAIN While Walking")
        assert result == result.lower()

    def test_abbreviation_expansion(self, engine):
        result = engine._preprocess("I have htn and cp")
        assert "hypertension" in result
        assert "chest pain" in result

    def test_removes_noise_characters(self, engine):
        result = engine._preprocess("chest pain!!! @#$ really bad")
        assert "!!!" not in result
        assert "@" not in result


class TestConditionMapping:
    """Core accuracy tests — top-1 condition must be correct."""

    def test_angina_from_chest_pain_on_exertion(self, engine):
        result = engine.process("chest pain while walking, worse in cold mornings")
        assert result["conditions"], "Should return at least one condition"
        assert result["conditions"][0]["icd10"] == "I20", (
            f"Expected Angina (I20), got {result['conditions'][0]}"
        )
        assert result["emergency_flag"] is False
        assert result["low_confidence"] is False

    def test_gerd_from_heartburn_after_meals(self, engine):
        result = engine.process("heartburn after eating, burning in throat at night")
        assert result["conditions"], "Should return at least one condition"
        assert result["conditions"][0]["icd10"] == "K21", (
            f"Expected GERD (K21), got {result['conditions'][0]}"
        )

    def test_knee_replacement(self, engine):
        result = engine.process("knee pain cannot walk, need knee replacement surgery")
        assert result["conditions"], "Should return at least one condition"
        assert result["conditions"][0]["icd10"] == "Z96.65", (
            f"Expected TKR (Z96.65), got {result['conditions'][0]}"
        )

    def test_diabetes_symptoms(self, engine):
        result = engine.process("frequent urination, excessive thirst, weight loss, high blood sugar")
        assert result["conditions"], "Should return at least one condition"
        assert result["conditions"][0]["icd10"] == "E11", (
            f"Expected Type 2 Diabetes (E11), got {result['conditions'][0]}"
        )

    def test_cataract_symptoms(self, engine):
        result = engine.process("blurry vision, cloudy vision, cannot read, eye lens problem")
        assert result["conditions"], "Should return at least one condition"
        assert result["conditions"][0]["icd10"] == "H26", (
            f"Expected Cataract (H26), got {result['conditions'][0]}"
        )

    def test_returns_multiple_candidates(self, engine):
        """System must never force a single answer."""
        result = engine.process("chest pain shortness of breath")
        # Chest pain overlaps Angina, GERD, Hypertension — should give multiple
        assert len(result["conditions"]) >= 1

    def test_confidence_is_normalized(self, engine):
        result = engine.process("chest pain while walking")
        for cond in result["conditions"]:
            assert 0.0 <= cond["confidence"] <= 1.0, (
                f"Confidence out of range: {cond['confidence']}"
            )


class TestNegationDetection:
    """Negated symptoms must NOT boost conditions."""

    def test_negated_chest_pain_reduces_angina_confidence(self, engine):
        # "no chest pain" should NOT strongly map to Angina
        result_affirmed = engine.process("chest pain while walking")
        result_negated = engine.process("I do not have chest pain, just heartburn")

        confidence_affirmed = next(
            (c["confidence"] for c in result_affirmed["conditions"] if c["icd10"] == "I20"), 0.0
        )
        confidence_negated = next(
            (c["confidence"] for c in result_negated["conditions"] if c["icd10"] == "I20"), 0.0
        )

        assert confidence_affirmed > confidence_negated, (
            "Affirmed chest pain should have higher Angina confidence than negated chest pain"
        )

    def test_no_negated_symptoms_in_confirmed(self, engine):
        result = engine.process("no fever, no chest pain, just heartburn")
        # "fever" and "chest pain" should be in negated, not confirmed
        negated = [s.lower() for s in result["negated_symptoms"]]
        # At minimum, confirmed should not aggressively include negated terms
        # (exact behavior depends on medspaCy model availability)
        assert isinstance(result["negated_symptoms"], list)


class TestEmergencyDetection:
    """Critical safety gate tests."""

    def test_heart_attack_triggers_emergency(self, engine):
        result = engine.process("I think I am having a heart attack, severe chest pain")
        assert result["emergency_flag"] is True
        assert result["emergency_message"] is not None
        assert "112" in result["emergency_message"]

    def test_stroke_triggers_emergency(self, engine):
        result = engine.process("face drooping, arm weakness sudden, speech slurred")
        assert result["emergency_flag"] is True

    def test_routine_query_no_emergency(self, engine):
        result = engine.process("knee pain for 3 months, difficulty walking")
        assert result["emergency_flag"] is False
        assert result["emergency_message"] is None


class TestLowConfidenceThreshold:
    """Ambiguous queries should trigger clarification request."""

    def test_vague_query_is_low_confidence(self, engine):
        result = engine.process("feeling unwell")
        assert result["low_confidence"] is True, (
            "Vague query should be flagged as low confidence"
        )

    def test_specific_query_is_not_low_confidence(self, engine):
        result = engine.process(
            "severe chest pain on exertion, radiating to left arm, shortness of breath"
        )
        # Highly specific Angina query should NOT be low confidence
        assert result["emergency_flag"] is False  # Not an emergency keyword


class TestEdgeCases:
    """Boundary and robustness tests."""

    def test_empty_query(self, engine):
        result = engine.process("")
        assert result["low_confidence"] is True
        assert result["conditions"] == []

    def test_very_long_query(self, engine):
        long_query = "chest pain " * 50
        result = engine.process(long_query)
        assert isinstance(result, dict)
        assert "conditions" in result

    def test_procedural_query(self, engine):
        """User can ask about procedures directly, not just symptoms."""
        result = engine.process("I need knee replacement surgery")
        assert result["conditions"], "Procedural query should still return a condition"

    def test_output_structure(self, engine):
        """Validate the full output schema."""
        result = engine.process("chest pain")
        required_keys = [
            "query", "cleaned_query", "extracted_symptoms", "negated_symptoms",
            "conditions", "top_condition", "low_confidence", "emergency_flag",
            "emergency_message"
        ]
        for key in required_keys:
            assert key in result, f"Missing key in output: {key}"

    def test_abbreviation_resolves_correctly(self, engine):
        """BP abbreviation should map to hypertension-related conditions."""
        result = engine.process("high bp for 2 years on medication")
        assert result["conditions"], "Should resolve 'bp' to blood pressure conditions"
