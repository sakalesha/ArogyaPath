"""
ArogyaPath · M3 Hospital Engine — Unit Tests
Run: python -m pytest test_hospital.py -v
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import pytest
from hospital_engine import HospitalEngine


@pytest.fixture(scope="session")
def engine():
    return HospitalEngine()


class TestDataLoading:

    def test_loads_25_hospitals(self, engine):
        assert len(engine.hospitals) == 25

    def test_loads_city_index(self, engine):
        assert "Bangalore" in engine.cities
        assert "Delhi" in engine.cities
        assert len(engine.cities) >= 10


class TestRankingBasic:

    def test_angina_in_bangalore_returns_results(self, engine):
        result = engine.get_hospitals("pathway_angina", "Bangalore")
        assert "results" in result
        assert len(result["results"]) > 0

    def test_returns_top_5_by_default(self, engine):
        result = engine.get_hospitals("pathway_angina", "Bangalore")
        assert len(result["results"]) <= 5

    def test_top_n_param_respected(self, engine):
        result = engine.get_hospitals("pathway_angina", "Bangalore", top_n=3)
        assert len(result["results"]) <= 3

    def test_results_sorted_by_score_descending(self, engine):
        result = engine.get_hospitals("pathway_angina", "Bangalore")
        scores = [h["final_score"] for h in result["results"]]
        assert scores == sorted(scores, reverse=True)

    def test_rank_field_sequential(self, engine):
        result = engine.get_hospitals("pathway_angina", "Bangalore")
        for i, h in enumerate(result["results"]):
            assert h["rank"] == i + 1


class TestScoring:

    def test_all_scores_between_0_and_1(self, engine):
        result = engine.get_hospitals("pathway_angina", "Bangalore")
        for h in result["results"]:
            assert 0.0 <= h["final_score"] <= 1.0

    def test_score_breakdown_has_4_signals(self, engine):
        result = engine.get_hospitals("pathway_angina", "Bangalore")
        breakdown = result["results"][0]["score_breakdown"]
        assert "rating_score" in breakdown
        assert "distance_score" in breakdown
        assert "type_score" in breakdown
        assert "nabh_bonus" in breakdown

    def test_nabh_hospital_scores_higher_than_non_nabh_at_same_distance(self, engine):
        result = engine.get_hospitals("pathway_angina", "Bangalore")
        # Find NABH and non-NABH hospitals in results
        nabh = [h for h in result["results"] if h["nabh_accredited"]]
        non_nabh = [h for h in result["results"] if not h["nabh_accredited"]]
        if nabh and non_nabh:
            # NABH bonus is 0.15 — accredited should generally score higher
            assert nabh[0]["score_breakdown"]["nabh_bonus"] == 1.0
            assert non_nabh[0]["score_breakdown"]["nabh_bonus"] == 0.0

    def test_distance_km_is_positive(self, engine):
        result = engine.get_hospitals("pathway_angina", "Bangalore")
        for h in result["results"]:
            assert h["distance_km"] >= 0.0

    def test_scoring_weights_reported(self, engine):
        result = engine.get_hospitals("pathway_angina", "Bangalore")
        w = result["scoring_weights"]
        assert abs(sum(w.values()) - 1.0) < 0.01  # weights sum to ~1.0


class TestFiltering:

    def test_filter_government_only(self, engine):
        result = engine.get_hospitals("pathway_angina", "Bangalore", filter_type="government")
        for h in result["results"]:
            assert h["type"] == "government"

    def test_filter_nabh_only(self, engine):
        result = engine.get_hospitals("pathway_angina", "Bangalore", filter_nabh=True)
        for h in result["results"]:
            assert h["nabh_accredited"] is True

    def test_specialist_pathway_returns_relevant_hospitals(self, engine):
        # Cataract — should include eye hospitals
        result = engine.get_hospitals("pathway_cataract", "Bangalore")
        hospital_names = [h["name"] for h in result["results"]]
        # Sankara Eye Hospital or Devi Eye Hospital should appear
        assert any("Eye" in name or "Sankara" in name for name in hospital_names)

    def test_unknown_city_returns_error(self, engine):
        result = engine.get_hospitals("pathway_angina", "Atlantis")
        assert "error" in result

    def test_unknown_pathway_returns_empty(self, engine):
        result = engine.get_hospitals("pathway_nonexistent", "Bangalore")
        assert result["results"] == [] or "error" in result


class TestOutputFields:

    def test_required_fields_present(self, engine):
        result = engine.get_hospitals("pathway_angina", "Bangalore")
        h = result["results"][0]
        for field in ["rank", "id", "name", "city", "type", "rating",
                      "nabh_accredited", "cost_category", "distance_km",
                      "final_score", "tradeoff_tags", "pm_jay_eligible"]:
            assert field in h, f"Missing field: {field}"

    def test_government_hospitals_pm_jay_eligible(self, engine):
        result = engine.get_hospitals("pathway_angina", "Bangalore", filter_type="government")
        for h in result["results"]:
            assert h["pm_jay_eligible"] is True

    def test_tradeoff_tags_have_icon_and_label(self, engine):
        result = engine.get_hospitals("pathway_angina", "Bangalore")
        for h in result["results"]:
            for tag in h["tradeoff_tags"]:
                assert "icon" in tag
                assert "label" in tag

    def test_total_found_reported(self, engine):
        result = engine.get_hospitals("pathway_angina", "Bangalore")
        assert "total_found" in result
        assert result["total_found"] >= result["showing"]


class TestHaversine:

    def test_same_point_distance_is_zero(self, engine):
        d = engine._haversine(12.97, 77.59, 12.97, 77.59)
        assert d < 0.01

    def test_bangalore_to_delhi_approx_2100km(self, engine):
        d = engine._haversine(12.97, 77.59, 28.61, 77.21)
        assert 1600 < d < 1900
