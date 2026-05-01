"""
ArogyaPath · Module M3 — Hospital Discovery & Ranking Engine
=============================================================
Input:  pathway_id + city (+ optional filters)
Output: Ranked hospital list with transparent 4-signal scoring

Scoring formula (from PPTX Slide 5):
  score = (0.35 × rating_score) + (0.30 × distance_score)
        + (0.20 × type_score)   + (0.15 × nabh_bonus)
"""

import json
import math
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

HOSPITALS_PATH = Path(__file__).parent / "hospitals.json"

# Scoring weights (transparent, judge-friendly)
WEIGHTS = {"rating": 0.35, "distance": 0.30, "type": 0.20, "nabh": 0.15}

# Hospital type scores (government < private < corporate for capability)
TYPE_SCORES = {"government": 0.60, "private": 0.80, "corporate": 1.00}

# Max distance considered (km) — beyond this, score = 0
MAX_DISTANCE_KM = 500

TRADEOFF_LABELS = {
    "best_quality":      {"icon": "⭐", "label": "Best Quality"},
    "lowest_cost":       {"icon": "💰", "label": "Lowest Cost"},
    "balanced":          {"icon": "⚖️", "label": "Balanced"},
    "high_cost":         {"icon": "💸", "label": "Premium Pricing"},
    "pm_jay_eligible":   {"icon": "🏛️", "label": "PM-JAY Eligible"},
    "cardiac_specialist":{"icon": "❤️", "label": "Cardiac Specialist"},
    "specialist_centre": {"icon": "🎯", "label": "Specialist Centre"},
    "good_quality":      {"icon": "✅", "label": "Good Quality"},
    "good_value":        {"icon": "💡", "label": "Good Value"},
}


class HospitalEngine:
    """
    Discovers and ranks hospitals for a given condition + location.

    Scoring is 100% transparent (4 signals, published weights).
    """

    def __init__(self):
        self._load_data()
        logger.info(f"HospitalEngine loaded: {len(self.hospitals)} hospitals, {len(self.cities)} cities.")

    def _load_data(self):
        with open(HOSPITALS_PATH, encoding="utf-8") as f:
            data = json.load(f)
        self.hospitals = data["hospitals"]
        self.cities = data["cities"]
        self.weights = data["_meta"]["weights"]

    # ── Public API ─────────────────────────────────────────────────────────

    def get_hospitals(
        self,
        pathway_id: str,
        city: str,
        top_n: int = 5,
        filter_type: Optional[str] = None,
        filter_nabh: bool = False,
    ) -> dict:
        """
        Main ranking endpoint.

        Args:
            pathway_id:   e.g. "pathway_angina" (from M1/M2)
            city:         e.g. "Bangalore"
            top_n:        number of hospitals to return (default 5)
            filter_type:  "government" | "private" | "corporate" | None
            filter_nabh:  if True, only NABH-accredited hospitals

        Returns ranked list with scores, tradeoff tags, and scoring breakdown.
        """
        # Resolve city coordinates
        city_coords = self._resolve_city(city)
        if not city_coords:
            return {
                "error": f"City '{city}' not found.",
                "available_cities": list(self.cities.keys()),
            }

        # Filter hospitals that handle this procedure
        candidates = [
            h for h in self.hospitals
            if pathway_id in h.get("procedures", [])
        ]

        # Apply optional filters
        if filter_type:
            candidates = [h for h in candidates if h["type"] == filter_type]
        if filter_nabh:
            candidates = [h for h in candidates if h["nabh_accredited"]]

        if not candidates:
            return {
                "pathway_id": pathway_id,
                "city": city,
                "error": "No hospitals found for this condition + filters.",
                "results": [],
            }

        # Score and rank
        scored = []
        for h in candidates:
            score_data = self._score_hospital(h, city_coords)
            scored.append({**h, **score_data})

        scored.sort(key=lambda x: x["final_score"], reverse=True)
        top = scored[:top_n]

        return {
            "pathway_id": pathway_id,
            "city": city,
            "city_coordinates": city_coords,
            "total_found": len(candidates),
            "showing": len(top),
            "scoring_weights": WEIGHTS,
            "results": [self._format_result(h, rank + 1) for rank, h in enumerate(top)],
        }

    def list_cities(self) -> list[str]:
        return list(self.cities.keys())

    # ── Scoring Engine ─────────────────────────────────────────────────────

    def _score_hospital(self, hospital: dict, city_coords: dict) -> dict:
        """
        Compute transparent 4-signal score for a hospital.
        All sub-scores are 0.0–1.0 before weighting.
        """
        # 1. Rating score (0–5 → 0–1)
        rating_score = hospital["rating"] / 5.0

        # 2. Distance score (closer = higher score)
        distance_km = self._haversine(
            city_coords["lat"], city_coords["lng"],
            hospital["lat"], hospital["lng"]
        )
        distance_score = max(0.0, 1.0 - (distance_km / MAX_DISTANCE_KM))

        # 3. Hospital type score
        type_score = TYPE_SCORES.get(hospital["type"], 0.5)

        # 4. NABH bonus
        nabh_bonus = 1.0 if hospital["nabh_accredited"] else 0.0

        # Weighted sum
        final_score = (
            WEIGHTS["rating"]   * rating_score +
            WEIGHTS["distance"] * distance_score +
            WEIGHTS["type"]     * type_score +
            WEIGHTS["nabh"]     * nabh_bonus
        )

        return {
            "distance_km": round(distance_km, 1),
            "final_score": round(final_score, 4),
            "score_breakdown": {
                "rating_score":   round(rating_score, 3),
                "distance_score": round(distance_score, 3),
                "type_score":     round(type_score, 3),
                "nabh_bonus":     round(nabh_bonus, 3),
            },
        }

    @staticmethod
    def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Great-circle distance between two lat/lng points in kilometres."""
        R = 6371.0
        dlat = math.radians(lat2 - lat1)
        dlng = math.radians(lng2 - lng1)
        a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
        return R * 2 * math.asin(math.sqrt(a))

    def _resolve_city(self, city: str) -> Optional[dict]:
        """Case-insensitive city lookup."""
        for name, coords in self.cities.items():
            if name.lower() == city.lower():
                return coords
        return None

    # ── Formatting ─────────────────────────────────────────────────────────

    def _format_result(self, hospital: dict, rank: int) -> dict:
        """Clean output dict for API response."""
        tags = [
            {"tag": t, **TRADEOFF_LABELS.get(t, {"icon": "•", "label": t})}
            for t in hospital.get("tradeoff_tags", [])
        ]
        return {
            "rank": rank,
            "id": hospital["id"],
            "name": hospital["name"],
            "city": hospital["city"],
            "state": hospital["state"],
            "type": hospital["type"],
            "type_label": hospital["type"].capitalize(),
            "rating": hospital["rating"],
            "review_count": hospital["review_count"],
            "nabh_accredited": hospital["nabh_accredited"],
            "cost_category": hospital["cost_category"],
            "cost_multiplier": hospital["cost_multiplier"],
            "distance_km": hospital["distance_km"],
            "icu_available": hospital["icu_available"],
            "emergency": hospital["emergency"],
            "bed_count": hospital["bed_count"],
            "phone": hospital["phone"],
            "tradeoff_tags": tags,
            "final_score": hospital["final_score"],
            "score_breakdown": hospital["score_breakdown"],
            "pm_jay_eligible": hospital["type"] == "government",
        }
