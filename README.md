# ArogyaPath: Decision Intelligence for Indian Healthcare 🏥
**Intelligent Symptom-to-Pathway Mapping & Hospital Discovery**

![ArogyaPath Banner](Docs/screenshots/banner.png)

*Developed for the TenzorX 2026 National AI Hackathon*

---

## 🛑 The Problem
The Indian healthcare system suffers from massive **Information Asymmetry**. Patients struggle to understand their symptoms, don't know the exact clinical protocols required, are unable to find the right verified facilities locally, and are often blindsided by hidden medical costs. This confusion leads to delayed care, anxiety, and an overburdened healthcare system.

## 🚀 Our Solution
**ArogyaPath** is an end-to-end healthcare navigation ecosystem. It acts as a deterministic clinical AI assistant that translates plain-text symptoms into actionable, localized healthcare journeys. 

Instead of acting like a generic "chatty" LLM that might hallucinate medical advice, ArogyaPath uses strict, data-driven medical ontologies and microservices to provide perfectly accurate, safe, and transparent guidance.

---

## ⚙️ The Four Core Engines Architecture

Our backend is built on a decoupled, high-performance microservices architecture featuring 4 specialized engines:

1. **M1: NLP Symptom Mapping Engine**
   - **How it works:** Uses a hybrid architecture combining a `Scikit-learn` Logistic Regression classifier with `Sentence-Transformers` for deep semantic intent recognition.
   - **Features:** Detects emergency severities and uses active reverse-ontology mapping to extract precise symptoms and negations directly into the UI.

2. **M2: Clinical Pathway Engine**
   - **How it works:** Dynamically generates structured medical protocols via an in-memory JSON Medical Ontology.
   - **Features:** Applies clinical heuristics to assign procedural types, mandatory flags, and dynamic branch logic depending on whether the case is Mild, Moderate, or Severe.

3. **M3: Hospital Discovery Engine**
   - **How it works:** Performs real-world hospital localization using the Google Maps API.
   - **Features:** Ranks and filters hospitals based on User Distance, Google Rating, NABH Accreditation status, and Hospital Type (Public vs. Private).

4. **M4: Cost Estimation Engine**
   - **How it works:** Provides highly localized and transparent forecasting.
   - **Features:** Dynamically adjusts costs based on City Tier and Hospital Type multipliers. Generates proportional, itemized cost breakdowns (e.g., Surgery vs. Stay vs. Diagnostics) and calculates PM-JAY insurance out-of-pocket metrics.

---

## 💻 Tech Stack

**Frontend (The Premium Experience):**
- **React 18 & Vite:** Blazing fast development and optimized builds.
- **Tailwind CSS & Glassmorphism:** Modern, premium UI tokens that evoke trust and clarity.
- **Framer Motion:** Smooth micro-animations and page transitions.
- **Educational UI:** Dedicated transparency layers to show patients *how* the AI made its decisions.

**Backend (The Deterministic Core):**
- **Python 3.10 & FastAPI:** Asynchronous, high-performance REST APIs.
- **Machine Learning:** `Scikit-Learn`, `Sentence-Transformers`, `PyTorch` (optional fallback for lightweight environments).
- **Data & APIs:** Google Maps Places API, JSON Medical Ontologies, SQLite.

---

## 📸 Screenshots

*(Add your screenshots to the `Docs/screenshots/` folder to display them here!)*

| Symptom Analysis | Clinical Pathway |
| :---: | :---: |
| ![Symptom Analysis](Docs/screenshots/analysis.png) | ![Clinical Pathway](Docs/screenshots/pathway.png) |

| Hospital Discovery | Cost Estimation |
| :---: | :---: |
| ![Hospital Discovery](Docs/screenshots/hospitals.png) | ![Cost Estimation](Docs/screenshots/cost.png) |

---

## 🛠️ How to Run Locally

Since ArogyaPath relies on heavy Machine Learning models, we recommend running it locally to utilize your machine's full RAM rather than deploying on restricted Free-Tier cloud instances.

### 1. Start the Backend (FastAPI)
```bash
cd backend/nlp
python -m venv .venv

# Windows
.venv\Scripts\activate
# Mac/Linux
source .venv/bin/activate

pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8001 --reload
```

### 2. Start the Frontend (Vite)
Open a new terminal window:
```bash
cd frontend
npm install
npm run dev
```

### 3. Environment Variables
Ensure you have a `.env` file in `backend/nlp/` containing your mapping API keys:
```env
GOOGLE_MAPS_API_KEY=your_api_key_here
```

---
*Built with ❤️ for TenzorX 2026*
