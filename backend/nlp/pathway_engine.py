"""
ArogyaPath · Module M2 — Clinical Pathway Engine
==================================================
Input:  pathway_id (from M1 output) + optional severity hint
Output: deterministic step-by-step treatment DAG with branch resolution
"""

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

PATHWAYS_PATH = Path(__file__).parent / "pathways.json"

# Cost tier labels for UI display
COST_TIER_LABELS = {
    "low":       {"label": "₹ Low",       "range": "< ₹10,000"},
    "medium":    {"label": "₹₹ Medium",   "range": "₹10,000 – ₹50,000"},
    "high":      {"label": "₹₹₹ High",    "range": "₹50,000 – ₹2,00,000"},
    "very_high": {"label": "₹₹₹₹ Major",  "range": "> ₹2,00,000"},
}

SEVERITY_ORDER = ["mild", "moderate", "severe"]


class PathwayEngine:
    """
    Loads clinical pathway DAGs and resolves them for a given pathway_id.

    Usage:
        engine = PathwayEngine()
        result = engine.get_pathway("pathway_angina", severity="moderate")
    """

    def __init__(self):
        self._load_pathways()
        logger.info(f"PathwayEngine loaded: {len(self.pathways)} pathways.")

    def _load_pathways(self):
        with open(PATHWAYS_PATH, encoding="utf-8") as f:
            data = json.load(f)
        self.pathways = data["pathways"]

    # ── Public API ─────────────────────────────────────────────────────────

    def get_pathway(self, pathway_id: str, severity: Optional[str] = None) -> dict:
        """
        Returns a fully resolved clinical pathway.

        Args:
            pathway_id: e.g. "pathway_angina" (from M1 output)
            severity:   "mild" | "moderate" | "severe" | None
                        If None, returns all branches (unresolved).

        Returns structured dict with base steps + resolved/all branch steps.
        """
        if pathway_id not in self.pathways:
            return self._not_found(pathway_id)

        pathway = self.pathways[pathway_id]
        base_steps = self._enrich_steps(pathway["steps"])
        branch_point = pathway.get("branch_point")

        resolved_branch = None
        all_branches = None

        if branch_point:
            if severity and severity in SEVERITY_ORDER:
                resolved_branch = self._resolve_branch(branch_point, severity)
            else:
                all_branches = self._all_branches(branch_point)

        # Build linear full_steps (base + resolved branch if available)
        full_steps = list(base_steps)
        if resolved_branch:
            full_steps.extend(self._enrich_steps(resolved_branch["steps"]))

        return {
            "pathway_id": pathway_id,
            "condition": pathway["condition"],
            "icd10": pathway["icd10"],
            "severity_requested": severity,
            "base_steps": base_steps,
            "branch_point": {
                "at_step_id": branch_point["at_step"],
                "label": branch_point["label"],
            } if branch_point else None,
            "resolved_branch": resolved_branch,
            "all_branches": all_branches,
            "full_steps": full_steps,
            "total_steps": len(full_steps),
            "has_surgery": any(s["type"] == "surgery" for s in full_steps),
            "mandatory_steps": [s for s in full_steps if s["mandatory"]],
            "optional_steps": [s for s in full_steps if not s["mandatory"]],
        }

    def list_pathways(self) -> list[dict]:
        """Returns summary list of all available pathways."""
        return [
            {
                "pathway_id": pid,
                "condition": p["condition"],
                "icd10": p["icd10"],
                "step_count": len(p["steps"]),
                "has_branch": "branch_point" in p,
            }
            for pid, p in self.pathways.items()
        ]

    # ── Internal helpers ───────────────────────────────────────────────────

    def _enrich_steps(self, steps: list[dict]) -> list[dict]:
        """Add cost_tier_info to each step for UI display."""
        enriched = []
        for s in steps:
            step = dict(s)
            tier = s.get("cost_tier", "low")
            step["cost_tier_info"] = COST_TIER_LABELS.get(tier, COST_TIER_LABELS["low"])
            enriched.append(step)
        return enriched

    def _resolve_branch(self, branch_point: dict, severity: str) -> Optional[dict]:
        """Find the branch matching the requested severity."""
        for branch in branch_point["branches"]:
            if branch["condition"] == severity:
                return {
                    "condition": severity,
                    "label": branch["label"],
                    "steps": self._enrich_steps(branch["steps"]),
                }
        # Fallback: return "moderate" if exact match not found
        for branch in branch_point["branches"]:
            if branch["condition"] == "moderate":
                return {
                    "condition": "moderate",
                    "label": branch["label"] + " (default)",
                    "steps": self._enrich_steps(branch["steps"]),
                }
        return None

    def _all_branches(self, branch_point: dict) -> list[dict]:
        """Return all branches (when severity is unknown)."""
        return [
            {
                "condition": b["condition"],
                "label": b["label"],
                "steps": self._enrich_steps(b["steps"]),
            }
            for b in branch_point["branches"]
        ]

    def _not_found(self, pathway_id: str) -> dict:
        return {
            "pathway_id": pathway_id,
            "error": f"Pathway '{pathway_id}' not found.",
            "available": list(self.pathways.keys()),
        }
