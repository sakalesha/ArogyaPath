import logging
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import SessionLocal
from models import ProcedureRate, UserReportedCost

logger = logging.getLogger(__name__)

class CostEngine:
    """
    M4: Hybrid Dynamic Costing Engine.
    Combines Official CGHS Benchmarks + User Crowdsourced Data.
    """

    def __init__(self):
        logger.info("Initializing Hybrid Cost Engine (M4)...")
        # Multipliers stay in memory for speed, or could be moved to DB
        self.city_tiers = {
            "tier1": {"cities": ["Mumbai", "Delhi", "Bangalore", "Chennai", "Hyderabad", "Kolkata"], "multiplier": 1.5},
            "tier2": {"cities": ["Pune", "Ahmedabad", "Jaipur", "Lucknow"], "multiplier": 1.2},
            "tier3": {"cities": ["Others"], "multiplier": 1.0}
        }
        self.hospital_multipliers = {
            "government": 0.6,
            "trust": 0.8,
            "private": 1.2,
            "corporate": 1.5
        }

    def estimate(
        self,
        pathway_id: str,
        city: str,
        hospital_type: str = "private",
        has_insurance: bool = False,
    ) -> dict:
        db = SessionLocal()
        try:
            # 1. Fetch Official Benchmark (CGHS/PM-JAY)
            base_rate = db.query(ProcedureRate).filter(ProcedureRate.pathway_id == pathway_id).first()
            if not base_rate:
                return {"error": f"No official rate data for pathway '{pathway_id}'."}

            # 2. Fetch Crowdsourced "Market Reality" Data
            reports = db.query(UserReportedCost).filter(
                UserReportedCost.pathway_id == pathway_id,
                UserReportedCost.city == city
            ).all()

            market_avg = None
            confidence_note = "Based on official government benchmarks."
            
            if reports:
                avg_paid = db.query(func.avg(UserReportedCost.actual_cost_paid)).filter(
                    UserReportedCost.pathway_id == pathway_id,
                    UserReportedCost.city == city
                ).scalar()
                market_avg = float(avg_paid)
                confidence_note = f"Enhanced by {len(reports)} real-world patient reports from {city}."

            # 3. Apply Multipliers to CGHS Base
            city_mult = self._get_city_multiplier(city)
            hosp_mult = self.hospital_multipliers.get(hospital_type, 1.0)
            
            # The "Official Estimate"
            official_est_min = base_rate.cghs_base_rate * city_mult * hosp_mult
            official_est_max = official_est_min * 1.3 # 30% range for official
            
            # 4. Hybrid Logic: If we have market data, blend it in
            if market_avg:
                # Weighted blend: 40% Official, 60% Crowdsourced
                final_min = (official_est_min * 0.4) + (market_avg * 0.8 * 0.6)
                final_max = (official_est_max * 0.4) + (market_avg * 1.1 * 0.6)
            else:
                final_min = official_est_min
                final_max = official_est_max

            # 5. Insurance Layer
            insurance_info = self._calculate_insurance(base_rate, final_min, final_max, has_insurance)

            # 6. Generate Breakdown
            breakdown = [
                {
                    "component": "Consultation",
                    "label": "Doctor Fees",
                    "min": round(final_min * 0.10),
                    "max": round(final_max * 0.10)
                },
                {
                    "component": "Diagnostics",
                    "label": "Lab Tests & Imaging",
                    "min": round(final_min * 0.15),
                    "max": round(final_max * 0.15)
                },
                {
                    "component": "Procedure",
                    "label": "Surgery / Core Treatment",
                    "min": round(final_min * 0.50),
                    "max": round(final_max * 0.50)
                },
                {
                    "component": "Stay",
                    "label": "Hospital Room / ICU",
                    "min": round(final_min * 0.15),
                    "max": round(final_max * 0.15)
                },
                {
                    "component": "Medicines",
                    "label": "Pharmacy",
                    "min": round(final_min * 0.10),
                    "max": round(final_max * 0.10)
                }
            ]

            return {
                "condition_name": base_rate.condition_name,
                "icd10": base_rate.icd10,
                "pathway_id": pathway_id,
                "city": city,
                "city_tier": "tier1" if city_mult > 1.2 else "tier2",
                "hospital_type": hospital_type,
                "combined_multiplier": city_mult * hosp_mult,
                "benchmarks": {
                    "official_cghs_base": round(base_rate.cghs_base_rate),
                    "market_average_reported": round(market_avg) if market_avg else "No reports yet"
                },
                "breakdown": breakdown,
                "total_min": round(final_min),
                "total_max": round(final_max),
                "total_range_label": f"₹{round(final_min):,} – ₹{round(final_max):,}",
                "insurance": insurance_info,
                "confidence_note": confidence_note,
                "is_dynamic": True,
                "disclaimer": "This estimate combines official CGHS rates with real-world crowdsourced data."
            }

        finally:
            db.close()

    def _get_city_multiplier(self, city: str) -> float:
        city_lower = city.lower()
        for tier_data in self.city_tiers.values():
            if any(c.lower() == city_lower for c in tier_data["cities"]):
                return tier_data["multiplier"]
        return 1.1 # Default

    def _calculate_insurance(self, base_rate, total_min, total_max, has_insurance) -> dict:
        if not has_insurance or not base_rate.is_pmjay_covered:
            return {
                "eligible": False,
                "scheme": "PM-JAY",
                "covered_amount": 0,
                "out_of_pocket_min": round(total_min),
                "out_of_pocket_max": round(total_max)
            }

        covered = min(base_rate.pmjay_limit, total_max)
        return {
            "eligible": True,
            "scheme": "PM-JAY",
            "covered_amount": round(covered),
            "out_of_pocket_min": round(max(0, total_min - covered)),
            "out_of_pocket_max": round(max(0, total_max - covered)),
            "note": f"PM-JAY covers up to ₹{round(base_rate.pmjay_limit):,}."
        }
