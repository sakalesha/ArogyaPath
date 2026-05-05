# ArogyaPath: TenzorX 2026 National AI Hackathon Presentation

This document contains the structured content for a 10-slide presentation deck tailored for the hackathon submission.

---

## Slide 1: Title Slide
**Title:** ArogyaPath: Decision Intelligence for Indian Healthcare
**Subtitle:** Intelligent Symptom-to-Pathway Mapping & Hospital Discovery
**Team/Presenter:** [Your Team Name]
**Event:** TenzorX 2026 National AI Hackathon

**Speaker Notes:**
> "Welcome judges. We are thrilled to present ArogyaPath, an end-to-end healthcare navigation ecosystem designed to solve information asymmetry in the patient journey."

---

## Slide 2: The Problem
**Header:** The Healthcare Navigation Crisis
**Points:**
- **Information Asymmetry:** Patients struggle to understand their symptoms and the necessary clinical steps, leading to anxiety and confusion.
- **Fragmented Data:** Finding the right specialists, understanding costs, and locating nearby verified facilities requires visiting multiple disjointed platforms.
- **Delayed Care:** Confusion leads to delayed treatments or unnecessary visits to emergency rooms, driving up out-of-pocket costs and straining the healthcare system.

**Visual Suggestion:** A maze representing a patient's confusing journey through the healthcare system.

---

## Slide 3: Our Solution
**Header:** Meet ArogyaPath
**Points:**
- **End-to-End Navigation:** A clinical AI tool that translates plain-text symptoms into actionable healthcare journeys.
- **Core Value Proposition:** Understand symptoms ➔ Generate clinical pathways ➔ Discover localized hospitals ➔ Estimate transparent costs.
- **Empowerment:** Puts data-driven, deterministic, and actionable medical guidance directly into the patient's hands, safely and securely.

**Visual Suggestion:** A clean flow diagram showing: Patient -> ArogyaPath -> Clear Medical Plan.

---

## Slide 4: Key Features (The Four Core Engines)
**Header:** A Comprehensive Microservice Ecosystem
**Points:**
1. **NLP Symptom Mapping (M1):** Hybrid architecture using Sentence-Transformers for deep semantic intent, combined with active reverse-ontology mapping to extract precise symptoms and negations for the UI.
2. **Clinical Pathway Engine (M2):** Generates structured, dynamic protocols via JSON Medical Ontology, applying clinical heuristics to assign procedural types, mandatory flags, and branch logic for Mild, Moderate, and Severe cases.
3. **Hospital Discovery Engine (M3):** Real-world hospital localization using Google Maps API, ranked by Rating, Distance, NABH Accreditation, and Type.
4. **Cost Estimation Engine (M4):** Transparent forecasting based on City Tier and Hospital Type, generating proportional itemized cost breakdowns (Surgery, Stay, Diagnostics, etc.) and PM-JAY insurance logic.

**Visual Suggestion:** 4 specialized icons representing the M1-M4 engines.

---

## Slide 5: Methodology
**Header:** Deterministic Safety & Accuracy
**Points:**
- **Preventing Hallucinations:** Unlike standard generative chatbots, ArogyaPath uses structured medical ontologies and strict classification to prevent dangerous AI hallucinations.
- **Data-Driven Training:** NLP models are trained on extensive, verified disease datasets.
- **Real-Time Integration:** Dynamic querying using mapping APIs to find the nearest and best-rated facilities for specific conditions.
- **Modular Pipeline:** Each user request flows sequentially through specialized engines for blazing-fast inference and decoupled reliability.

---

## Slide 6: Technical Architecture
**Header:** Robust, Scalable, Modern Stack
**Points:**
- **Frontend Layer:** React + Vite, styled with Tailwind CSS, and powered by Framer Motion for a premium, dynamic, dark-mode user experience.
- **Backend Framework:** Python (FastAPI) for high-performance, asynchronous REST APIs.
- **ML/NLP Core:** Scikit-Learn pipelines combined with HuggingFace Sentence-Transformers (`all-MiniLM-L6-v2`) for hybrid intent recognition.
- **Database & Storage:** SQLite + SQLAlchemy for state management, combined with optimized JSON stores for ontologies.

**Visual Suggestion:** An architecture block diagram showing the Frontend Client, FastAPI server, the 4 modular engines, and the Database.

---

## Slide 7: Design Choices & Innovation
**Header:** Practicality Meets Premium Experience
**Points:**
- **Semantic vs. Keyword:** Moved beyond rigid keyword searches to true semantic intent recognition, while actively extracting UI-friendly symptoms via reverse-ontology mapping.
- **Glassmorphism & Educational UI:** The UI/UX is built to evoke trust using premium design tokens. We also included a dedicated "How it Works" educational layer to provide full transparency on how the AI makes decisions.
- **Microservices Approach:** Independent engines mean that if the Hospital Discovery service scales, the NLP service remains unaffected.
- **Low-Latency & Dynamic:** Using lightweight models and generating dynamic structured outputs (like itemized costs) on the fly ensures a real-time, responsive experience.

---

## Slide 8: Business Potential & Impact
**Header:** Market Impact & Monetization
**Points:**
- **B2B Lead Generation:** Partnerships with hospitals and clinics for targeted patient referrals based on specific clinical pathways.
- **Insurance Integration (PM-JAY):** Licensing the M4 Cost Engine API to health insurance providers for pre-claim cost transparency.
- **Premium Telehealth:** Upselling integrated telehealth booking directly from the recommended care pathway.
- **Target Market:** The rapidly growing digital health triage market in India.

---

## Slide 9: Scalability & Roadmap
**Header:** Scaling ArogyaPath for the Future
**Points:**
- **Phase 1 (Current):** Functional prototype with core ML models, pathway generation, and dynamic location mapping.
- **Phase 2 (Next 6 Months):** Integrate localized LLMs for conversational empathy and multi-lingual support (Hindi, Tamil, etc.) for broader Indian demographics.
- **Phase 3 (Next 12 Months):** Real-time EMR (Electronic Medical Record) and ABDM (Ayushman Bharat Digital Mission) integration.
- **Infrastructure Scale:** Containerized deployment (Docker/Kubernetes) ready for cloud-native scaling.

---

## Slide 10: Conclusion
**Header:** Navigating Healthcare, Simplified.
**Points:**
- ArogyaPath bridges the critical gap between patient confusion and medical clarity.
- Deterministic safety combined with end-to-end utility solves real-world navigation problems in the Indian healthcare system.
- **Thank You!** 

**Call to Action:** "We invite you to view our live prototype demonstration."
