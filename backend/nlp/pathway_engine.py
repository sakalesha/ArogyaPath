"""
ArogyaPath · Module M2 — Clinical Pathway Engine (Severity-Enabled)
==================================================================
Input:  pathway_id (from M1 output) + severity hint (from M1)
Output: List of treatment steps for the specific severity.
"""

import json
import logging
from pathlib import Path
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

PATHWAYS_PATH = Path(__file__).parent / "pathways.json"

class PathwayEngine:
    """
    Loads clinical pathways and returns steps based on severity.
    """

    def __init__(self):
        self._load_pathways()
        logger.info(f"PathwayEngine loaded: {len(self.pathways)} pathways.")

    def _load_pathways(self):
        try:
            with open(PATHWAYS_PATH, encoding="utf-8") as f:
                self.pathways = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load pathways.json: {e}")
            self.pathways = {}

    def get_pathway(self, pathway_id: str, severity: Optional[str] = "moderate") -> Dict:
        """
        Returns the specific steps for a pathway and severity.
        """
        # Normalize severity to lowercase and handle "severe" -> "emergency" mapping
        sev = (severity or "moderate").lower()
        if sev == "severe":
            sev = "emergency"
            
        if pathway_id not in self.pathways:
            return {
                "pathway_id": pathway_id,
                "error": f"Pathway '{pathway_id}' not found.",
                "available": list(self.pathways.keys())
            }

        pathway_data = self.pathways[pathway_id]
        
        # Fallback logic for severity
        if sev not in pathway_data:
            logger.warning(f"Severity '{sev}' not found in '{pathway_id}'. Falling back to moderate.")
            sev = "moderate"

        steps = pathway_data.get(sev, [])
        
        # Dynamically build rich PathwayStep objects expected by the new UI
        base_steps = []
        has_surgery = False
        
        for i, step_text in enumerate(steps):
            text_lower = step_text.lower()
            
            # Heuristics for type
            step_type = "procedure"
            if "consult" in text_lower or "visit" in text_lower:
                step_type = "consultation"
            elif "ecg" in text_lower or "test" in text_lower or "scan" in text_lower or "mri" in text_lower or "x-ray" in text_lower or "ultrasound" in text_lower or "evaluation" in text_lower:
                step_type = "diagnostic"
            elif "medication" in text_lower or "antibiotic" in text_lower or "drugs" in text_lower or "antacids" in text_lower or "insulin" in text_lower or "ppi" in text_lower:
                step_type = "medication"
            elif "diet" in text_lower or "lifestyle" in text_lower or "exercise" in text_lower or "salt" in text_lower:
                step_type = "lifestyle"
            elif "surgery" in text_lower or "angioplasty" in text_lower or "appendectomy" in text_lower or "replacement" in text_lower:
                step_type = "surgery"
                has_surgery = True
            elif "physiotherapy" in text_lower or "therapy" in text_lower:
                step_type = "therapy"
                
            # Heuristics for cost tier
            if step_type == "surgery":
                cost_label = "Premium"
                cost_range = "₹50,000+"
            elif step_type == "diagnostic":
                cost_label = "Mid-Range"
                cost_range = "₹1,000 - ₹5,000"
            elif step_type == "consultation":
                cost_label = "Budget"
                cost_range = "₹500 - ₹1,500"
            elif step_type == "lifestyle":
                cost_label = "Free"
                cost_range = "₹0"
            else:
                cost_label = "Variable"
                cost_range = "Depends on prescription"

            base_steps.append({
                "id": f"step_{i}",
                "order": i + 1,
                "name": step_text,
                "type": step_type,
                "mandatory": True if step_type in ["surgery", "diagnostic", "consultation"] else False,
                "description": f"Standard clinical protocol action for {pathway_data.get('name', 'this condition')}.",
                "cost_tier": cost_label.lower(),
                "cost_tier_info": {
                    "label": cost_label,
                    "range": cost_range
                }
            })
            
        # Optional branching logic based on severity
        resolved_branch = None
        if sev == "emergency":
            resolved_branch = {
                "condition": "Critical",
                "label": "Emergency Branch",
                "steps": [
                    {
                        "id": "branch_1",
                        "order": len(base_steps) + 1,
                        "name": "Immediate ICU Admission",
                        "type": "procedure",
                        "mandatory": True,
                        "description": "Critical care monitoring required.",
                        "cost_tier": "premium",
                        "cost_tier_info": {"label": "Premium", "range": "₹10,000+/day"}
                    }
                ]
            }

        return {
            "pathway_id": pathway_id,
            "condition": pathway_data.get("name", "Unknown Condition"),
            "icd10": "TBD", # M1 will have provided the accurate ICD10 in reality
            "severity_requested": sev,
            "base_steps": base_steps,
            "resolved_branch": resolved_branch,
            "total_steps": len(base_steps),
            "has_surgery": has_surgery,
            "mandatory_steps": [s for s in base_steps if s["mandatory"]],
            "optional_steps": [s for s in base_steps if not s["mandatory"]]
        }

    def list_pathways(self) -> List[Dict]:
        """Returns summary list of all available pathways."""
        return [
            {
                "pathway_id": pid,
                "name": p.get("name", "Unknown"),
                "has_emergency": "emergency" in p
            }
            for pid, p in self.pathways.items()
        ]
