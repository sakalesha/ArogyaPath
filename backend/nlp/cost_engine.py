"""
ArogyaPath · Module M4 — Cost Estimation Engine
=================================================
Takes a pathway_id + city + hospital_type and returns:
- Min/max cost breakdown per component (consultation, diagnostics, procedure, stay, medicines, contingency)
- Total min/max range
- PM-JAY coverage details (covered amount + out-of-pocket)
- City tier + hospital type multipliers applied
"""

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

COSTS_PATH = Path(__file__).parent / "costs.json"


class CostEngine:
    """
    M4: Cost Estimation Engine.

    Inputs:
    - pathway_id   : from M1 /analyze-query (e.g. "pathway_angina")
    - city         : patient's city (e.g. "Bangalore")
    - hospital_type: "government" | "trust" | "private" | "corporate"
    - has_insurance: bool (PM-JAY eligibility)

    Output:
    - Cost breakdown per component with min/max ranges
    - Total estimated cost (min/max)
    - Out-of-pocket cost after PM-JAY (if eligible)
    - Confidence note
    """

    def __init__(self):
        logger.info("Initializing Cost Engine (M4)...")
        self._load_data()
        logger.info(f"Cost Engine ready: {len(self.conditions)} conditions loaded.")

    def _load_data(self):
        with open(COSTS_PATH, encoding="utf-8") as f:
            data = json.load(f)
        self.conditions = data["conditions"]
        self.city_tiers = data["city_tier_multipliers"]
        self.hospital_multipliers = data["hospital_type_multipliers"]

    # ── Public API ─────────────────────────────────────────────────────────

    def estimate(
        self,
        pathway_id: str,
        city: str,
        hospital_type: str = "private",
        has_insurance: bool = False,
    ) -> dict:
        """
        Main entry point. Returns the full cost estimate JSON.
        """
        if pathway_id not in self.conditions:
            return {"error": f"No cost data for pathway '{pathway_id}'. Available: {list(self.conditions.keys())}"}

        if hospital_type not in self.hospital_multipliers:
            hospital_type = "private"

        condition_data = self.conditions[pathway_id]
        city_multiplier = self._get_city_multiplier(city)
        hospital_multiplier = self.hospital_multipliers[hospital_type]
        combined_multiplier = round(city_multiplier * hospital_multiplier, 2)

        breakdown = []
        total_min = 0
        total_max = 0

        for component, values in condition_data["cost_components"].items():
            base_min = values["min"]
            base_max = values["max"]

            # Skip zero-cost components (e.g. "no procedure needed")
            if base_min == 0 and base_max == 0:
                breakdown.append({
                    "component": component,
                    "label": values["label"],
                    "min": 0,
                    "max": 0,
                    "note": "Not applicable for this condition"
                })
                continue

            adjusted_min = round(base_min * combined_multiplier)
            adjusted_max = round(base_max * combined_multiplier)

            breakdown.append({
                "component": component,
                "label": values["label"],
                "min": adjusted_min,
                "max": adjusted_max,
            })

            total_min += adjusted_min
            total_max += adjusted_max

        # PM-JAY / Insurance layer
        insurance_info = self._calculate_insurance(
            condition_data, total_min, total_max, has_insurance
        )

        tier_label = self._get_city_tier_label(city)

        return {
            "condition_name": condition_data["condition_name"],
            "icd10": condition_data["icd10"],
            "pathway_id": pathway_id,
            "city": city,
            "city_tier": tier_label,
            "hospital_type": hospital_type,
            "combined_multiplier": combined_multiplier,
            "breakdown": breakdown,
            "total_min": total_min,
            "total_max": total_max,
            "total_range_label": f"₹{total_min:,} – ₹{total_max:,}",
            "insurance": insurance_info,
            "notes": condition_data.get("notes", ""),
            "disclaimer": "Cost ranges are indicative only. Actual costs may vary based on patient condition, complications, and hospital negotiations.",
        }

    def list_supported_pathways(self) -> list:
        return list(self.conditions.keys())

    # ── Helpers ────────────────────────────────────────────────────────────

    def _get_city_multiplier(self, city: str) -> float:
        city_lower = city.lower()
        for tier_data in self.city_tiers.values():
            if any(c.lower() == city_lower for c in tier_data["cities"]):
                return tier_data["multiplier"]
        # Default to Tier 2 if city not found
        logger.warning(f"City '{city}' not in tier list. Defaulting to Tier 2 multiplier.")
        return 1.2

    def _get_city_tier_label(self, city: str) -> str:
        city_lower = city.lower()
        for tier_name, tier_data in self.city_tiers.items():
            if any(c.lower() == city_lower for c in tier_data["cities"]):
                return tier_name
        return "tier2 (estimated)"

    def _calculate_insurance(
        self,
        condition_data: dict,
        total_min: int,
        total_max: int,
        has_insurance: bool,
    ) -> dict:
        pmjay_covered = condition_data.get("pmjay_covered", False)
        pmjay_limit = condition_data.get("pmjay_limit", 0)

        if not has_insurance or not pmjay_covered:
            return {
                "eligible": False,
                "scheme": "PM-JAY",
                "covered_amount": 0,
                "out_of_pocket_min": total_min,
                "out_of_pocket_max": total_max,
                "note": "Not covered under PM-JAY or insurance not provided." if not has_insurance
                        else "This condition is not covered under PM-JAY.",
            }

        # PM-JAY covers up to pmjay_limit
        covered = min(pmjay_limit, total_max)
        oop_min = max(0, total_min - covered)
        oop_max = max(0, total_max - covered)

        return {
            "eligible": True,
            "scheme": "PM-JAY",
            "covered_amount": covered,
            "out_of_pocket_min": oop_min,
            "out_of_pocket_max": oop_max,
            "note": f"PM-JAY covers up to ₹{pmjay_limit:,}. Your estimated out-of-pocket is ₹{oop_min:,} – ₹{oop_max:,}.",
        }
