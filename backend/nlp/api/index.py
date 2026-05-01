"""
Vercel Serverless Entry Point for ArogyaPath FastAPI backend.
Mangum wraps the ASGI app so Vercel can call it as a serverless function.
"""
import sys
import os

# Ensure the parent directory (backend/nlp/) is on the path
# so all imports (nlp_engine, cost_engine, etc.) resolve correctly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from mangum import Mangum

# This is the Vercel handler
handler = Mangum(app, lifespan="off")
