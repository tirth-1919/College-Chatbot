# AIT College AI Assistant — Security & Compliance Architecture

This document describes the security protocols, authentication safeguards, data privacy standards, and AI defense mechanisms implemented across the AIT College AI Assistant platform.

---

## 1. Authentication & Role-Based Access Control (RBAC)

- **Password Hashing**: Passwords are encrypted using PBKDF2/SHA-256 with cryptographically random per-user salts and 100,000 hash iterations.
- **JWT Session Tokens**: Standard RFC 7519 JSON Web Tokens signed with HMAC-SHA256. Tokens are short-lived and validate role claims on every protected API endpoint.
- **Hierarchical Roles**:
  - `SUPER_ADMIN`: Unrestricted platform governance, system configuration, and audit access.
  - `ADMIN`: Knowledge base updates, fee structures, faculty assignments, and conflict resolution.
  - `FACULTY`: Class schedules, subject materials, and academic submissions.
  - `STUDENT`: Personalized timetable, fees, private examination results, and study coach.
  - `PUBLIC`: Admissions FAQ, general courses, facility overviews, and public image galleries.

---

## 2. AI Safety & Prompt Injection Defenses

The AI Layer incorporates multi-stage sanitization before queries reach LLM reasoning models:
1. **Input Sanitization**: HTML tag stripping and character sequence normalization.
2. **Jailbreak Pattern Detection**: Heuristic regex scanner matching instruction overrides (e.g. `ignore previous instructions`, `DAN mode`, `reveal admin password`).
3. **Context Isolation**: User input is strictly separated from system prompts and ground truth evidence blocks.
4. **PII Masking**: Personal identifiers (Aadhaar numbers, payment card digits, phone numbers) are scrubbed prior to dataset ingestion for ML training.

---

## 3. Data Integrity & Provenance Guarantee

- **No-Hallucination Policy**: Academic numbers (fees, credits, marks) and dates (exams, timetables) are pulled deterministically from the database and validated against retrieved evidence before output.
- **Visual Image Provenance**: Real AIT images require verified `source_url` and `source_page` references. AI models are prohibited from claiming AI-generated artwork as real AIT photographs.
