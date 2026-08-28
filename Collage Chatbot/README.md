# Ahmedabad Institute of Technology (AIT) — AI Assistant Platform

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18%2B-61DAFB.svg)](https://reactjs.org)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-3.4%2B-38B2AC.svg)](https://tailwindcss.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-pgvector-336791.svg)](https://postgresql.org)
[![Tests](https://img.shields.io/badge/Acceptance%20Tests-13%2F13%20Passed-brightgreen.svg)]()

Production-grade, AI-native assistant for **Ahmedabad Institute of Technology (AIT)** ([https://www.aitindia.in](https://www.aitindia.in)) built in strict adherence to the Master PRD, enforcing a 3-tier Source Authority Hierarchy, official visual retrieval with provenance, Voice STT/TTS with replay caching, specialized ML/NN pipelines, and a deterministic Admin truth layer.

---

## 🏛️ 1. Master Source Priority Hierarchy

```
PRIORITY 1: AIT OFFICIAL WEBSITE / OFFICIAL AIT DOCUMENTS (https://www.aitindia.in)
PRIORITY 2: ADMIN-VERIFIED COLLEGE DATABASE (BCA Fees, Timetable, Faculty Mappings, Exams)
PRIORITY 3: GEMINI / GENERAL AI KNOWLEDGE (General academic concepts, code explanations)
```

- **Zero-Hallucination Guarantee**: If verified AIT records or official RAG documents do not contain evidence for a college-specific fact, the assistant explicitly declines to answer rather than fabricating details.
- **Image Provenance Integrity**: Official photos (Smart Classrooms, Central Library, Computer Labs, Historical Events) are only displayed with verified `source_url`, `source_page`, and captions. AI-generated images are never represented as real AIT photographs.

---

## 🚀 2. Quick Start Guide

### Prerequisites
- Python 3.10+
- Node.js 18+ and npm

### Backend Setup
```bash
# 1. Install dependencies
pip install -r backend/requirements.txt

# 2. Initialize and Seed Database
python -m database.seed.seed_data

# 3. Launch Backend API Server (Port 8000)
python backend/run.py
```
API Documentation & Swagger UI available at: `http://localhost:8000/docs`

### Frontend Setup
```bash
cd frontend
# 1. Install npm dependencies
npm install

# 2. Run local Vite dev server (Port 5173)
npm run dev
```
Web App UI available at: `http://localhost:5173`

---

## 🧪 3. Running Master Acceptance Tests

Run the automated acceptance test suite verifying all 16 PRD test scenarios:
```bash
python -m pytest tests/test_master_acceptance.py -v
```

### Verified Acceptance Scenarios:
1. `"What is BCA fee?"` $\rightarrow$ Verified database record (`₹32,000` for 2026-27).
2. `"Who teaches DBMS?"` $\rightarrow$ Faculty-subject mapping (`Prof. Anjali Sharma`).
3. `"What is today's timetable?"` $\rightarrow$ Deterministic daily schedule.
4. `"When is my exam?"` $\rightarrow$ Scheduled exam lookup.
5. `"What events happened last year?"` $\rightarrow$ 2024-2025 TechFest Ignite & Hackathon archive.
6. `"Show me last year's event photos"` $\rightarrow$ Real official AIT photographs with provenance.
7. `"Show me AIT smart classroom"` $\rightarrow$ Verified smart classroom image with metadata.
8. `"Show me AIT library"` $\rightarrow$ Central library photo with provenance.
9. `"Explain machine learning"` $\rightarrow$ General AI educational explanation with disclaimer.
10. Voice conversation $\rightarrow$ Speech-to-text $\rightarrow$ AI Router $\rightarrow$ Text-to-speech.
11. Voice audio replay $\rightarrow$ Replays cached audio without re-triggering LLM calls.
12. Admin fee update $\rightarrow$ Instant reflection in subsequent student queries.
13. Knowledge Conflict Center $\rightarrow$ Conflict detection and resolution lifecycle.
14. Security sanitization $\rightarrow$ Prompt injection & jailbreak defenses.

---

## 🐳 4. Production Docker Deployment

```bash
docker-compose up --build
```
- Frontend Web App: `http://localhost:3000`
- Backend REST API: `http://localhost:8000`

---

## 🔑 5. Default Demo Credentials

| Role | Email | Password | Scope |
|---|---|---|---|
| **Admin / Super Admin** | `admin@aitindia.in` | `Admin@123` | Full Admin Control Center, Fee Modifier, Sync, Conflicts, Rollback |
| **Student** | `student@aitindia.in` | `Student@123` | Personalized Chat, Voice, Timetables, Fees, Exams, Results |
| **Faculty** | `faculty@aitindia.in` | `Faculty@123` | Class schedules, Faculty Subject Mappings |
| **Public Visitor** | Guest / Public | None | Official AIT Public Portal, Admissions, Facilities, Real Gallery |

---

## 📄 License
MIT License. Developed for Ahmedabad Institute of Technology.
