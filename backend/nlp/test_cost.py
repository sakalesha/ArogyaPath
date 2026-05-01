"""
ArogyaPath · M4 Cost Engine — Unit Tests
==========================================
Run: python -m pytest test_cost.py -v
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from cost_engine import CostEngine


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def engine():
    """Single engine shared across all tests."""
    return CostEngine()


# ─────────────────────────────────────────────────────────────────────────────
# Test Suite
# ─────────────────────────────────────────────────────────────────────────────

class TestEngineSetup:
    """Validate engine loads correctly."""

    def test_engine_loads(self, engine):
        assert engine is not None

    def test_conditions_loaded(self, engine):
        assert len(engine.conditions) == 10, f"Expected 10 conditions, got {len(engine.conditions)}"

    def test_all_10_pathways_present(self, engine):
        expected = [
            "pathway_angina", "pathway_gerd", "pathway_tkr",
            "pathway_angioplasty", "pathway_appendicitis", "pathway_gallstones",
            "pathway_diabetes", "pathway_hypertension", "pathway_lower_back",
            "pathway_cataract"
        ]
        for pathway_id in expected:
            assert pathway_id in engine.conditions, f"Missing pathway: {pathway_id}"

    def test_list_supported_pathways(self, engine):
        pathways = engine.list_supported_pathways()
        assert isinstance(pathways, list)
        assert len(pathways) == 10


class TestOutputSchema:
    """Validate the full output structure contains all required fields."""

    def test_required_keys_present(self, engine):
        result = engine.estimate("pathway_angina", "Bangalore", "private", False)
        required_keys = [
            "condition_name", "icd10", "pathway_id", "city", "city_tier",
            "hospital_type", "combined_multiplier", "breakdown",
            "total_min", "total_max", "total_range_label", "insurance",
            "notes", "disclaimer"
        ]
        for key in required_keys:
            assert key in result, f"Missing key in output: {key}"

    def test_insurance_schema_keys(self, engine):
        result = engine.estimate("pathway_angina", "Bangalore", "private", True)
        insurance_keys = [
            "eligible", "scheme", "covered_amount",
            "out_of_pocket_min", "out_of_pocket_max", "note"
        ]
        for key in insurance_keys:
            assert key in result["insurance"], f"Missing insurance key: {key}"

    def test_breakdown_is_list(self, engine):
        result = engine.estimate("pathway_angina", "Bangalore", "private", False)
        assert isinstance(result["breakdown"], list)
        assert len(result["breakdown"]) > 0

    def test_breakdown_items_have_required_fields(self, engine):
        result = engine.estimate("pathway_angina", "Bangalore", "private", False)
        for item in result["breakdown"]:
            assert "component" in item
            assert "label" in item
            assert "min" in item
            assert "max" in item

    def test_total_range_label_contains_rupee_symbol(self, engine):
        result = engine.estimate("pathway_angina", "Bangalore", "private", False)
        assert "₹" in result["total_range_label"]


class TestCityTierMultipliers:
    """Validate city tier multipliers are applied correctly."""

    def test_tier1_city_has_higher_cost_than_tier3(self, engine):
        tier1 = engine.estimate("pathway_angina", "Mumbai", "private", False)
        tier3 = engine.estimate("pathway_angina", "Mysore", "private", False)
        assert tier1["total_max"] > tier3["total_max"], \
            "Tier 1 city (Mumbai) should cost more than Tier 3 city (Mysore)"

    def test_tier1_multiplier_is_1_5(self, engine):
        result = engine.estimate("pathway_angina", "Bangalore", "private", False)
        # Bangalore is Tier 1 (1.5) × Private (1.8) = 2.7
        assert result["combined_multiplier"] == 2.7

    def test_tier2_multiplier_is_1_2(self, engine):
        result = engine.estimate("pathway_angina", "Pune", "private", False)
        # Pune is Tier 2 (1.2) × Private (1.8) = 2.16
        assert result["combined_multiplier"] == 2.16

    def test_tier3_multiplier_is_1_0(self, engine):
        result = engine.estimate("pathway_angina", "Mysore", "private", False)
        # Mysore is Tier 3 (1.0) × Private (1.8) = 1.8
        assert result["combined_multiplier"] == 1.8

    def test_unknown_city_defaults_to_tier2(self, engine):
        result = engine.estimate("pathway_angina", "UnknownCity", "private", False)
        # Unknown city should default to Tier 2 (1.2) × Private (1.8) = 2.16
        assert result["combined_multiplier"] == 2.16
        assert "tier2" in result["city_tier"].lower()


class TestHospitalTypeMultipliers:
    """Validate hospital type multipliers are applied correctly."""

    def test_corporate_costs_more_than_government(self, engine):
        govt = engine.estimate("pathway_angina", "Bangalore", "government", False)
        corp = engine.estimate("pathway_angina", "Bangalore", "corporate", False)
        assert corp["total_max"] > govt["total_max"], \
            "Corporate hospital should cost more than government"

    def test_hospital_type_ordering(self, engine):
        """government < trust < private < corporate"""
        govt = engine.estimate("pathway_tkr", "Bangalore", "government", False)
        trust = engine.estimate("pathway_tkr", "Bangalore", "trust", False)
        private = engine.estimate("pathway_tkr", "Bangalore", "private", False)
        corp = engine.estimate("pathway_tkr", "Bangalore", "corporate", False)
        assert govt["total_max"] < trust["total_max"] < private["total_max"] < corp["total_max"]

    def test_invalid_hospital_type_defaults_to_private(self, engine):
        result = engine.estimate("pathway_angina", "Bangalore", "invalid_type", False)
        assert result["hospital_type"] == "private"


class TestInsuranceCalculation:
    """Validate PM-JAY coverage logic."""

    def test_no_insurance_not_eligible(self, engine):
        result = engine.estimate("pathway_angina", "Bangalore", "private", False)
        assert result["insurance"]["eligible"] is False
        assert result["insurance"]["covered_amount"] == 0

    def test_insurance_eligible_for_covered_condition(self, engine):
        # Angina (pathway_angina) is PM-JAY covered
        result = engine.estimate("pathway_angina", "Bangalore", "private", True)
        assert result["insurance"]["eligible"] is True
        assert result["insurance"]["covered_amount"] > 0

    def test_insurance_not_eligible_for_uncovered_condition(self, engine):
        # GERD (pathway_gerd) is NOT PM-JAY covered
        result = engine.estimate("pathway_gerd", "Bangalore", "private", True)
        assert result["insurance"]["eligible"] is False
        assert result["insurance"]["covered_amount"] == 0

    def test_out_of_pocket_never_negative(self, engine):
        """OOP should always be >= 0, even if PM-JAY limit exceeds total."""
        result = engine.estimate("pathway_cataract", "Mysore", "government", True)
        assert result["insurance"]["out_of_pocket_min"] >= 0
        assert result["insurance"]["out_of_pocket_max"] >= 0

    def test_covered_amount_does_not_exceed_pmjay_limit(self, engine):
        result = engine.estimate("pathway_angina", "Bangalore", "government", True)
        # PM-JAY limit for angina is 500,000
        assert result["insurance"]["covered_amount"] <= 500000

    def test_oop_max_equals_total_max_minus_coverage(self, engine):
        result = engine.estimate("pathway_tkr", "Mysore", "government", True)
        covered = result["insurance"]["covered_amount"]
        total_max = result["total_max"]
        oop_max = result["insurance"]["out_of_pocket_max"]
        assert oop_max == max(0, total_max - covered)

    def test_insurance_note_contains_pmjay(self, engine):
        result = engine.estimate("pathway_angina", "Bangalore", "private", True)
        assert "PM-JAY" in result["insurance"]["note"]


class TestCostSanity:
    """Sanity checks — costs must be positive and reasonable."""

    def test_total_min_less_than_total_max(self, engine):
        result = engine.estimate("pathway_angina", "Bangalore", "private", False)
        assert result["total_min"] < result["total_max"]

    def test_total_is_sum_of_nonzero_breakdown(self, engine):
        result = engine.estimate("pathway_angina", "Bangalore", "private", False)
        expected_min = sum(item["min"] for item in result["breakdown"])
        expected_max = sum(item["max"] for item in result["breakdown"])
        assert result["total_min"] == expected_min
        assert result["total_max"] == expected_max

    def test_costs_are_positive_integers(self, engine):
        result = engine.estimate("pathway_tkr", "Bangalore", "private", False)
        assert result["total_min"] > 0
        assert result["total_max"] > 0
        assert isinstance(result["total_min"], int)
        assert isinstance(result["total_max"], int)

    def test_procedure_heavy_condition_costs_more_than_medicine_only(self, engine):
        """TKR (surgery) should cost significantly more than Hypertension (medication)."""
        surgery = engine.estimate("pathway_tkr", "Bangalore", "private", False)
        medication = engine.estimate("pathway_hypertension", "Bangalore", "private", False)
        assert surgery["total_max"] > medication["total_max"] * 5, \
            "Surgery condition should cost vastly more than a medication-managed condition"


class TestInvalidInputs:
    """Edge cases and error handling."""

    def test_unknown_pathway_returns_error(self, engine):
        result = engine.estimate("pathway_nonexistent", "Bangalore", "private", False)
        assert "error" in result

    def test_error_message_helpful(self, engine):
        result = engine.estimate("bad_pathway", "Bangalore", "private", False)
        assert "bad_pathway" in result["error"]
        assert "Available:" in result["error"]

    def test_all_conditions_produce_valid_output(self, engine):
        """Smoke test — all 10 pathways must return a valid result."""
        for pathway_id in engine.list_supported_pathways():
            result = engine.estimate(pathway_id, "Bangalore", "private", False)
            assert "error" not in result, f"Error for {pathway_id}: {result.get('error')}"
            assert result["total_min"] >= 0
            assert result["total_max"] > 0
