import sys
import os

# Add backend/nlp to path so imports like 'nlp_engine' work
backend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backend', 'nlp')
sys.path.insert(0, backend_path)

from main import app
from mangum import Mangum

# Vercel handler
handler = Mangum(app, lifespan="off")
