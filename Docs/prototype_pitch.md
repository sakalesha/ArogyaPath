# ArogyaPath: Prototype Demo & Video Pitch Script

This document contains the functional prototype demo script and the short video pitch script designed for the TenzorX 2026 National AI Hackathon submission.

---

## Part 1: Functional Prototype Demo Script (For Judges)

**Objective:** To showcase the core functionality of ArogyaPath and explain the technical design choices in a clear, demonstrable format.

### 1. Introduction (1 Minute)
**Presenter:** "Hello Judges. Welcome to the ArogyaPath prototype. Our goal today is to demonstrate how our system transforms confusing patient symptoms into a clear, actionable healthcare journey."

### 2. The Demo Scenario (3 Minutes)
**Action:** Open the chatbot interface / API testing tool.

**Step 1: Symptom Input**
- **Presenter:** "Let's say a patient is feeling unwell. Instead of Googling and getting overwhelmed, they type their natural symptoms into ArogyaPath: *'I have a severe headache, blurred vision, and I feel dizzy.'*"
- **Action:** Enter the text into the chat.

**Step 2: NLP Symptom Mapping (Module 1)**
- **Presenter:** "Our NLP Engine processes this instantly. Instead of basic keyword matching, it uses a trained Scikit-learn model to semantically map these symptoms to likely underlying conditions, such as 'Migraine' or 'Hypertension'."
- **Action:** Show the JSON response identifying the symptoms and conditions.

**Step 3: Clinical Pathway Generation (Module 2)**
- **Presenter:** "Next, the Pathway Engine consults our structured medical ontologies. It generates a recommended clinical path. In this case, it advises: 1. Measure Blood Pressure, 2. Consult a Neurologist or General Physician."
- **Action:** Point out the generated pathway on the screen.

**Step 4: Hospital Discovery & Ranking (Module 3)**
- **Presenter:** "Knowing *what* to do isn't enough; the patient needs to know *where* to go. Our Hospital Engine pings the Google Maps API, filters for highly-rated local Neurologists or Clinics, and ranks them by distance and rating."
- **Action:** Show the top 3 recommended clinics with their distance and rating.

**Step 5: Cost Estimation (Module 4)**
- **Presenter:** "Finally, our Cost Engine calculates estimated out-of-pocket expenses for the recommended consultations and baseline tests, bringing complete financial transparency to the journey."
- **Action:** Show the estimated cost breakdown.

### 3. Explanation of Design Choices (1 Minute)
**Presenter:** "Why did we build it this way?
1. **Microservices Architecture:** By splitting NLP, Pathways, Discovery, and Cost into independent modules using FastAPI, the system is highly scalable and fault-tolerant.
2. **Deterministic AI over Generative AI for Pathways:** We use trained ML models and structured JSON ontologies rather than purely generative LLMs to prevent 'hallucinations'. In healthcare, clinical accuracy and safety are paramount.
3. **Speed:** Using serialized Joblib models ensures real-time inference, making the chatbot incredibly responsive."

---

## Part 2: Video Pitch Script (2 Minutes)

**Target Length:** 2 Minutes
**Tone:** Professional, Urgent, Innovative.

**[0:00 - 0:15] The Hook**
*(Visual: Patient looking stressed at a computer screen showing confusing medical search results.)*
**Voiceover:** "When you're sick, the last thing you need is more confusion. But today's healthcare journey starts with fragmented data, overwhelming search results, and hidden costs."

**[0:15 - 0:45] The Solution**
*(Visual: ArogyaPath logo appears. Transition to a clean, mobile chatbot interface.)*
**Voiceover:** "Enter ArogyaPath. We are bridging the gap between patient confusion and medical clarity. ArogyaPath is an intelligent, end-to-end clinical chatbot that translates your plain-text symptoms into an actionable healthcare journey."

**[0:45 - 1:20] How It Works (The Demo)**
*(Visual: Fast-paced screen recording of the prototype in action. User typing symptoms -> AI mapping -> Hospital showing on map -> Cost displaying.)*
**Voiceover:** "Just tell ArogyaPath how you feel. 
First, our advanced NLP engine semantically extracts your symptoms and maps them to likely conditions. 
Second, it generates a standardized clinical pathway, telling you exactly which specialists to see and what tests to expect. 
Third, our geolocation engine instantly finds and ranks the highest-rated hospitals and specialists near you. 
And finally, it provides a transparent out-of-pocket cost estimate."

**[1:20 - 1:45] Under the Hood & Scalability**
*(Visual: An animated architecture diagram showing FastAPI, Scikit-learn, JSON ontologies, and Google Maps API scaling up.)*
**Voiceover:** "Built on a robust FastAPI microservices architecture, ArogyaPath is designed for speed and scale. By utilizing structured medical ontologies and fast ML inference, we ensure clinical accuracy with zero hallucinations. As we scale, our modular design easily integrates with live EMR systems and telehealth platforms."

**[1:45 - 2:00] The Vision & Call to Action**
*(Visual: Team photo or ArogyaPath logo with the tagline "Navigating Healthcare, Simplified".)*
**Voiceover:** "We aren't just building a chatbot; we are building the future of patient empowerment. Transparent, accessible, and data-driven healthcare is no longer a luxury. It's ArogyaPath. Thank you from Team TenzorX."
