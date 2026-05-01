# ArogyaPath Backend — Deployment on Render

This folder (`backend/nlp/`) is the deployable FastAPI service.

## Deploy to Render (Free, Permanent URL)

### Step 1: Push to GitHub
```bash
git init
git add .
git commit -m "initial commit"
git remote add origin https://github.com/YOUR_USERNAME/arogyapath-backend.git
git push -u origin main
```

### Step 2: Create a Render account
- Go to https://render.com
- Sign up with GitHub (free)

### Step 3: Create a New Web Service
1. Click **"New"** → **"Web Service"**
2. Connect your GitHub repo
3. Configure:
   - **Root Directory:** `backend/nlp`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type:** Free
4. Click **Deploy**

### Step 4: Get Permanent URL
After deploy, Render gives you a permanent URL like:
`https://arogyapath-backend.onrender.com`

### Step 5: Update Frontend
Change `API_BASE` in `frontend/src/App.tsx`:
```typescript
const API_BASE = "https://arogyapath-backend.onrender.com";
```

## Local Development
```bash
cd backend/nlp
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

## All API Endpoints
| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Server health check |
| `/analyze-query` | POST | M1: Symptoms → Conditions |
| `/get-pathway` | POST | M2: Condition → Treatment Steps |
| `/get-hospitals` | POST | M3: Condition + City → Hospitals |
| `/estimate-cost` | POST | M4: Cost Breakdown + PM-JAY |
| `/docs` | GET | Interactive API documentation |
