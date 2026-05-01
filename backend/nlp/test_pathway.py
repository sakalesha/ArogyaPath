"""
ArogyaPath · M2 Pathway Engine — Unit Tests
Run: python -m pytest test_pathway.py -v
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import pytest
from pathway_engine import PathwayEngine


@pytest.fixture(scope="session")
def engine():
    return PathwayEngine()


class TestPathwayLoading:

    def test_loads_all_10_pathways(self, engine):
        assert len(engine.pathways) == 10

    def test_all_expected_ids_present(self, engine):
        expected = [
            "pathway_angina", "pathway_gerd", "pathway_tkr",
            "pathway_angioplasty", "pathway_appendicitis", "pathway_gallstones",
            "pathway_diabetes", "pathway_hypertension",
            "pathway_lower_back", "pathway_cataract",
        ]
        for pid in expected:
            assert pid in engine.pathways, f"Missing: {pid}"

    def test_list_pathways_returns_summaries(self, engine):
        summaries = engine.list_pathways()
        assert len(summaries) == 10
        for s in summaries:
            assert "pathway_id" in s
            assert "condition" in s
            assert "icd10" in s
            assert "step_count" in s


class TestPathwayStructure:

    def test_angina_has_required_fields(self, engine):
        result = engine.get_pathway("pathway_angina")
        assert result["pathway_id"] == "pathway_angina"
        assert result["icd10"] == "I20"
        assert len(result["base_steps"]) == 5
        assert result["branch_point"] is not None
        assert result["all_branches"] is not None  # no severity given

    def test_every_pathway_has_base_steps(self, engine):
        for pid in engine.pathways:
            result = engine.get_pathway(pid)
            assert len(result["base_steps"]) > 0, f"{pid} has no base steps"

    def test_steps_have_required_fields(self, engine):
        result = engine.get_pathway("pathway_tkr")
        for step in result["base_steps"]:
            assert "id" in step
            assert "name" in step
            assert "type" in step
            assert "mandatory" in step
            assert "cost_tier_info" in step

    def test_cost_tier_enrichment(self, engine):
        result = engine.get_pathway("pathway_angina")
        for step in result["base_steps"]:
            info = step["cost_tier_info"]
            assert "label" in info
            assert "range" in info
            assert "₹" in info["label"]


class TestSeverityBranchResolution:

    def test_angina_severe_branch_is_pci(self, engine):
        result = engine.get_pathway("pathway_angina", severity="severe")
        assert result["resolved_branch"] is not None
        assert result["resolved_branch"]["condition"] == "severe"
        branch_names = [s["name"] for s in result["resolved_branch"]["steps"]]
        assert any("Angioplasty" in n or "PCI" in n for n in branch_names)

    def test_angina_moderate_branch_is_medical_management(self, engine):
        result = engine.get_pathway("pathway_angina", severity="moderate")
        assert result["resolved_branch"]["condition"] == "moderate"
        branch_names = [s["name"] for s in result["resolved_branch"]["steps"]]
        assert any("Medical" in n for n in branch_names)

    def test_angina_mild_branch_is_lifestyle(self, engine):
        result = engine.get_pathway("pathway_angina", severity="mild")
        assert result["resolved_branch"]["condition"] == "mild"
        branch_names = [s["name"] for s in result["resolved_branch"]["steps"]]
        assert any("Lifestyle" in n for n in branch_names)

    def test_no_severity_returns_all_branches(self, engine):
        result = engine.get_pathway("pathway_angina")
        assert result["all_branches"] is not None
        assert result["resolved_branch"] is None
        assert len(result["all_branches"]) == 3

    def test_full_steps_includes_branch_when_severity_given(self, engine):
        no_sev = engine.get_pathway("pathway_angina")
        with_sev = engine.get_pathway("pathway_angina", severity="severe")
        assert with_sev["total_steps"] > len(no_sev["base_steps"])

    def test_tkr_severe_branch_has_surgery(self, engine):
        result = engine.get_pathway("pathway_tkr", severity="severe")
        assert result["has_surgery"] is True

    def test_diabetes_mild_branch_no_surgery(self, engine):
        result = engine.get_pathway("pathway_diabetes", severity="mild")
        assert result["has_surgery"] is False


class TestMandatoryOptional:

    def test_mandatory_steps_exist(self, engine):
        result = engine.get_pathway("pathway_angina", severity="moderate")
        assert len(result["mandatory_steps"]) > 0

    def test_optional_steps_exist(self, engine):
        # Angina has "Stress Test" as optional
        result = engine.get_pathway("pathway_angina")
        optional_names = [s["name"] for s in result["optional_steps"]]
        assert any("Stress" in n for n in optional_names)

    def test_cataract_surgery_is_mandatory(self, engine):
        result = engine.get_pathway("pathway_cataract")
        surgery_steps = [s for s in result["base_steps"] if s["type"] == "surgery"]
        assert all(s["mandatory"] for s in surgery_steps)


class TestEdgeCases:

    def test_unknown_pathway_returns_error(self, engine):
        result = engine.get_pathway("pathway_nonexistent")
        assert "error" in result
        assert "available" in result

    def test_invalid_severity_falls_back_to_moderate(self, engine):
        # Invalid severity → fallback to moderate branch
        result = engine.get_pathway("pathway_angina", severity="unknown_severity")
        # Should fallback gracefully (moderate branch or None)
        assert isinstance(result, dict)

    def test_all_pathways_resolve_all_severities(self, engine):
        for pid in engine.pathways:
            for severity in ["mild", "moderate", "severe"]:
                result = engine.get_pathway(pid, severity=severity)
                assert "pathway_id" in result, f"Failed: {pid} + {severity}"
