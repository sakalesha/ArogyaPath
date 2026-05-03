"""
ArogyaPath · M1 + M2 + M3 Backend Service — FastAPI Entry Point
================================================================
M1: NLP → Condition Mapping
M2: Clinical Pathway Engine
M3: Hospital Discovery & Ranking
Run: uvicorn main:app --host 0.0.0.0 --port 8001 --reload
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from nlp_engine import NLPEngine
from pathway_engine import PathwayEngine
from hospital_engine import HospitalEngine
from cost_engine import CostEngine
from database import SessionLocal, get_db
from models import UserReportedCost
from sqlalchemy.orm import Session
from fastapi import Depends

# ─────────────────────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Global engine (loaded once at startup)
# ─────────────────────────────────────────────────────────────────────────────
engine: Optional[NLPEngine] = None
pathway_engine: Optional[PathwayEngine] = None
hospital_engine: Optional[HospitalEngine] = None
cost_engine: Optional[CostEngine] = None

def _get_engine() -> NLPEngine:
    """Lazy-load NLP engine (works in both uvicorn and Vercel serverless)."""
    global engine
    if engine is None:
        logger.info("Lazy-loading NLP engine (M1)...")
        engine = NLPEngine()
    return engine

def _get_pathway_engine() -> PathwayEngine:
    global pathway_engine
    if pathway_engine is None:
        logger.info("Lazy-loading Pathway engine (M2)...")
        pathway_engine = PathwayEngine()
    return pathway_engine

def _get_hospital_engine() -> HospitalEngine:
    global hospital_engine
    if hospital_engine is None:
        logger.info("Lazy-loading Hospital engine (M3)...")
        hospital_engine = HospitalEngine()
    return hospital_engine

def _get_cost_engine() -> CostEngine:
    global cost_engine
    if cost_engine is None:
        logger.info("Lazy-loading Cost engine (M4)...")
        cost_engine = CostEngine()
    return cost_engine


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI App
# ─────────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="ArogyaPath Backend — M1 + M2 + M3 + M4",
    description="M1: NLP → Conditions | M2: Clinical Pathways | M3: Hospital Ranking | M4: Cost Estimation",
    version="3.0.0",
    root_path="/api" if os.getenv("VERCEL") else ""
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Request / Response Schemas
# ─────────────────────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        example="chest pain while walking, worse in cold mornings",
        description="Free-text patient query (symptoms, conditions, or procedures)",
    )


class ConditionResult(BaseModel):
    id: str
    name: str
    icd10: str
    pathway_id: str
    confidence: float = Field(..., ge=0.0, le=1.0)


class AnalyzeResponse(BaseModel):
    query: str
    cleaned_query: str
    extracted_symptoms: list[str]
    negated_symptoms: list[str]
    conditions: list[ConditionResult]
    top_condition: Optional[str]
    severity: str
    low_confidence: bool
    emergency_flag: bool
    emergency_message: Optional[str]


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
async def health_check():
    """Liveness check — confirms engines are initialized."""
    return {
        "status": "ok",
        "nlp_engine_initialized": engine is not None,
        "pathway_engine_initialized": pathway_engine is not None,
        "hospital_engine_initialized": hospital_engine is not None,
        "cost_engine_initialized": cost_engine is not None,
        "service": "ArogyaPath M1+M2+M3+M4",
        "version": "3.0.0",
    }


@app.post(
    "/analyze-query",
    response_model=AnalyzeResponse,
    tags=["NLP"],
    summary="Translate free-text patient query to ranked medical conditions",
)
async def analyze_query(request: QueryRequest) -> AnalyzeResponse:
    """
    **Main NLP endpoint.**

    Accepts a free-text patient query and returns:
    - Extracted & confirmed symptoms (negation-filtered)
    - Ranked list of matching conditions with ICD-10 codes and confidence scores
    - Emergency flag if dangerous keywords detected
    - Low-confidence flag if top score < 0.45 (system will ask for clarification)

    **Example input:** `"chest pain while walking, worse in cold mornings"`

    **Example output:**
    ```json
    {
      "conditions": [
        {"name": "Angina / Coronary Artery Disease", "icd10": "I20", "confidence": 0.82},
        {"name": "GERD / Acid Reflux", "icd10": "K21", "confidence": 0.21},
        {"name": "Hypertension", "icd10": "I10", "confidence": 0.15}
      ],
      "emergency_flag": false,
      "low_confidence": false
    }
    ```
    """
    current_engine = _get_engine()
    try:
        result = current_engine.process(request.query)
        return AnalyzeResponse(**result)
    except Exception as e:
        logger.error(f"Error processing query '{request.query}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"NLP processing error: {str(e)}")


@app.get(
    "/conditions",
    tags=["NLP"],
    summary="List all conditions in the controlled ontology",
)
async def list_conditions():
    """Returns the full list of conditions that M1 can map to."""
    current_engine = _get_engine()
    return {
        "total": len(current_engine.conditions),
        "conditions": [
            {
                "id": c["id"],
                "name": c["name"],
                "icd10": c["icd10"],
                "pathway_id": c.get("pathway_id", ""),
            }
            for c in current_engine.conditions
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
# M2: Clinical Pathway Endpoints
# ─────────────────────────────────────────────────────────────────────────────

class PathwayRequest(BaseModel):
    pathway_id: str = Field(
        ...,
        example="pathway_angina",
        description="Pathway ID from M1 /analyze-query response.",
    )
    severity: Optional[str] = Field(
        None,
        example="moderate",
        description="Severity hint: 'mild' | 'moderate' | 'severe'. If omitted, all branches returned.",
    )


@app.post(
    "/get-pathway",
    tags=["Pathway"],
    summary="Get clinical treatment pathway for a condition",
)
async def get_pathway(request: PathwayRequest):
    """
    **M2: Clinical Pathway Engine.**

    Takes a `pathway_id` (from M1 `/analyze-query` output) and returns the
    full step-by-step treatment pathway DAG.
    """
    current_pathway_engine = _get_pathway_engine()
    try:
        result = current_pathway_engine.get_pathway(
            pathway_id=request.pathway_id,
            severity=request.severity
        )
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Pathway engine error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/pathways",
    tags=["Pathway"],
    summary="List all available clinical pathways",
)
async def list_pathways():
    """Returns summary of all pathways (id, condition, step count, has branches)."""
    current_pathway_engine = _get_pathway_engine()
    return {
        "total": len(current_pathway_engine.pathways),
        "pathways": current_pathway_engine.list_pathways(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# M3: Hospital Discovery & Ranking Endpoints
# ─────────────────────────────────────────────────────────────────────────────

class HospitalRequest(BaseModel):
    pathway_id: str = Field(..., example="pathway_angina")
    city: str = Field(..., example="Bangalore")
    top_n: int = Field(5, ge=1, le=10)
    filter_type: Optional[str] = Field(None, example="government")
    filter_nabh: bool = Field(False)


@app.post(
    "/get-hospitals",
    tags=["Hospitals"],
    summary="Get ranked hospitals for a condition and city",
)
async def get_hospitals(request: HospitalRequest):
    """
    **M3: Hospital Discovery & Ranking.**
    """
    current_hospital_engine = _get_hospital_engine()
    try:
        result = current_hospital_engine.rank_hospitals(
            pathway_id=request.pathway_id,
            city=request.city,
            top_n=request.top_n,
            filter_type=request.filter_type,
            filter_nabh=request.filter_nabh
        )
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Hospital ranking error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/cities", tags=["Hospitals"], summary="List supported cities")
async def list_cities():
    """Returns all cities currently in the hospital dataset."""
    current_hospital_engine = _get_hospital_engine()
    return {"cities": current_hospital_engine.list_cities()}


# ─────────────────────────────────────────────────────────────────────────────
# M4: Cost Estimation Endpoints
# ─────────────────────────────────────────────────────────────────────────────

class CostRequest(BaseModel):
    pathway_id: str = Field(..., example="pathway_angina", description="Pathway ID from M1 /analyze-query response.")
    city: str = Field(..., example="Bangalore", description="Patient's city for tier-based pricing.")
    hospital_type: str = Field("private", example="private", description="'government' | 'trust' | 'private' | 'corporate'")
    has_insurance: bool = Field(False, description="Whether patient has PM-JAY or insurance coverage.")

class ReportCostRequest(BaseModel):
    pathway_id: str
    city: str
    hospital_name: str
    actual_cost_paid: float
    user_rating: Optional[int] = None


@app.post(
    "/estimate-cost",
    tags=["Cost"],
    summary="Estimate treatment cost for a condition",
)
async def estimate_cost(request: CostRequest):
    """
    **M4: Cost Estimation Engine.**
    """
    current_cost_engine = _get_cost_engine()
    try:
        result = current_cost_engine.estimate(
            pathway_id=request.pathway_id,
            city=request.city,
            hospital_type=request.hospital_type,
            has_insurance=request.has_insurance,
        )
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cost estimation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/cost-pathways", tags=["Cost"], summary="List pathways with cost data")
async def list_cost_pathways():
    """Returns all pathway IDs for which cost data is available."""
    current_cost_engine = _get_cost_engine()
    return {"supported_pathways": current_cost_engine.list_supported_pathways()}

@app.post("/report-cost", tags=["Cost"], summary="Crowdsource actual treatment cost")
async def report_cost(request: ReportCostRequest, db: Session = Depends(get_db)):
    """
    **Level 3: Crowdsourcing.**
    Allows users to report what they actually paid to help others.
    """
    try:
        new_report = UserReportedCost(
            pathway_id=request.pathway_id,
            city=request.city,
            hospital_name=request.hospital_name,
            actual_cost_paid=request.actual_cost_paid,
            user_rating_of_experience=request.user_rating
        )
        db.add(new_report)
        db.commit()
        return {"status": "success", "message": "Thank you for contributing to the community pricing index!"}
    except Exception as e:
        logger.error(f"Error reporting cost: {e}")
        raise HTTPException(status_code=500, detail="Failed to save report.")
