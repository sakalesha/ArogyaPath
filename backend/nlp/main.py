"""
ArogyaPath · M1 + M2 + M3 Backend Service — FastAPI Entry Point
================================================================
M1: NLP → Condition Mapping
M2: Clinical Pathway Engine
M3: Hospital Discovery & Ranking
Run: uvicorn main:app --host 0.0.0.0 --port 8001 --reload
"""

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from nlp_engine import NLPEngine
from pathway_engine import PathwayEngine
from hospital_engine import HospitalEngine
from cost_engine import CostEngine

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load all three engines at startup."""
    global engine, pathway_engine, hospital_engine, cost_engine
    logger.info("Loading NLP engine (M1)...")
    engine = NLPEngine()
    logger.info("Loading Pathway engine (M2)...")
    pathway_engine = PathwayEngine()
    logger.info("Loading Hospital engine (M3)...")
    hospital_engine = HospitalEngine()
    logger.info("Loading Cost engine (M4)...")
    cost_engine = CostEngine()
    logger.info("All engines ready.")
    yield
    logger.info("Shutting down.")
    engine = None
    pathway_engine = None
    hospital_engine = None
    cost_engine = None


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI App
# ─────────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="ArogyaPath Backend — M1 + M2 + M3",
    description="M1: NLP → Conditions | M2: Clinical Pathways | M3: Hospital Ranking",
    version="3.0.0",
    lifespan=lifespan,
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
    low_confidence: bool
    emergency_flag: bool
    emergency_message: Optional[str]


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
async def health_check():
    """Liveness check — confirms both engines are loaded."""
    return {
        "status": "ok",
        "nlp_engine_loaded": engine is not None,
        "pathway_engine_loaded": pathway_engine is not None,
        "hospital_engine_loaded": hospital_engine is not None,
        "service": "ArogyaPath M1+M2+M3",
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
    if engine is None:
        raise HTTPException(status_code=503, detail="NLP engine not initialized.")

    try:
        result = engine.process(request.query)
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
    if engine is None:
        raise HTTPException(status_code=503, detail="NLP engine not initialized.")
    return {
        "total": len(engine.conditions),
        "conditions": [
            {
                "id": c["id"],
                "name": c["name"],
                "icd10": c["icd10"],
                "pathway_id": c.get("pathway_id", ""),
            }
            for c in engine.conditions
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

    - `severity` = `"mild"` | `"moderate"` | `"severe"` → resolves the branch
    - `severity` omitted → returns all branches for the UI to display

    **Example:** `pathway_id="pathway_angina"`, `severity="moderate"`
    → Returns: Consult → ECG → Echo → Stress Test → Angiography → Medical Management
    """
    if pathway_engine is None:
        raise HTTPException(status_code=503, detail="Pathway engine not initialized.")
    try:
        result = pathway_engine.get_pathway(request.pathway_id, request.severity)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Pathway error for '{request.pathway_id}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/pathways",
    tags=["Pathway"],
    summary="List all available clinical pathways",
)
async def list_pathways():
    """Returns summary of all pathways (id, condition, step count, has branches)."""
    if pathway_engine is None:
        raise HTTPException(status_code=503, detail="Pathway engine not initialized.")
    return {
        "total": len(pathway_engine.pathways),
        "pathways": pathway_engine.list_pathways(),
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
    if hospital_engine is None:
        raise HTTPException(status_code=503, detail="Hospital engine not initialized.")
    logger.info(f"[M3] /get-hospitals  pathway_id='{request.pathway_id}'  city='{request.city}'  filter_type='{request.filter_type}'  filter_nabh={request.filter_nabh}")
    try:
        result = hospital_engine.get_hospitals(
            pathway_id=request.pathway_id,
            city=request.city,
            top_n=request.top_n,
            filter_type=request.filter_type if request.filter_type else None,
            filter_nabh=request.filter_nabh,
        )
        # Return gracefully even if no results found (let frontend show empty state)
        if "error" in result and "available_cities" in result:
            # City not recognised — this is a real 404
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
    if hospital_engine is None:
        raise HTTPException(status_code=503, detail="Hospital engine not initialized.")
    return {"cities": hospital_engine.list_cities()}


# ─────────────────────────────────────────────────────────────────────────────
# M4: Cost Estimation Endpoints
# ─────────────────────────────────────────────────────────────────────────────

class CostRequest(BaseModel):
    pathway_id: str = Field(..., example="pathway_angina", description="Pathway ID from M1 /analyze-query response.")
    city: str = Field(..., example="Bangalore", description="Patient's city for tier-based pricing.")
    hospital_type: str = Field("private", example="private", description="'government' | 'trust' | 'private' | 'corporate'")
    has_insurance: bool = Field(False, description="Whether patient has PM-JAY or insurance coverage.")


@app.post(
    "/estimate-cost",
    tags=["Cost"],
    summary="Estimate treatment cost for a condition",
)
async def estimate_cost(request: CostRequest):
    """
    **M4: Cost Estimation Engine.**

    Takes a `pathway_id` (from M1), `city`, `hospital_type`, and `has_insurance`.
    Returns a detailed cost breakdown:
    - Per-component min/max ranges (consultation, diagnostics, procedure, stay, medicines)
    - Total estimated range
    - PM-JAY coverage and out-of-pocket cost

    **Example:** `pathway_id="pathway_angina"`, `city="Bangalore"`, `hospital_type="private"`, `has_insurance=true`
    """
    if cost_engine is None:
        raise HTTPException(status_code=503, detail="Cost engine not initialized.")
    try:
        result = cost_engine.estimate(
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
    if cost_engine is None:
        raise HTTPException(status_code=503, detail="Cost engine not initialized.")
    return {"supported_pathways": cost_engine.list_supported_pathways()}
