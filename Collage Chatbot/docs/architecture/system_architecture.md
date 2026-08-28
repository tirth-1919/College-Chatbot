# AIT College AI Assistant — System Architecture & UML Documentation

This document contains architectural diagrams and UML specifications for Ahmedabad Institute of Technology's AI Assistant in alignment with the PRD.

---

## 1. System Architecture Diagram

```mermaid
graph TD
    subgraph Client Layer
        A1[Web Browser / Desktop]
        A2[Mobile / Tablet PWA]
        A3[Voice Microphone & Audio Player]
    end

    subgraph Gateway & Security
        B1[Nginx Reverse Proxy]
        B2[FastAPI Gateway / CORS / Rate Limiter]
        B3[JWT Auth & RBAC Security Layer]
    end

    subgraph AI & Orchestration Layer
        C1[AI Router]
        C2[Intent & Entity Classifier]
        C3[Source Authority Resolver]
        C4[Grounding & Hallucination Guard]
    end

    subgraph Knowledge & Truth Engines
        D1[(PostgreSQL Database - Operational Truth)]
        D2[pgvector & Hybrid RAG Engine]
        D3[Official AIT Image Registry with Provenance]
        D4[Gemini 1.5 Flash / Local AI Engine]
    end

    subgraph Background Services
        E1[AIT Portal Web Crawler: aitindia.in]
        E2[Audio Cache & Voice Synthesis]
        E3[ML Training & Rollback Registry]
        E4[Audit & Metrics Logger]
    end

    Client Layer --> Gateway & Security
    Gateway & Security --> AI & Orchestration Layer
    AI & Orchestration Layer --> Knowledge & Truth Engines
    Knowledge & Truth Engines --> Background Services
```

---

## 2. Sequence Diagram: Student Text & Voice Query

```mermaid
sequenceDiagram
    autonumber
    actor Student as Student / Public User
    participant Frontend as React / PWA UI
    participant Backend as FastAPI Gateway
    participant Router as AI Router & Grounding Guard
    participant DB as Admin-Verified DB (Priority 2)
    participant RAG as AIT Official RAG (Priority 1)
    participant Gemini as Gemini AI Layer (Priority 3)
    participant Audio as Voice Audio Cache

    Student->>Frontend: Speaks / Types "What is BCA fee?"
    Frontend->>Backend: POST /api/v1/chat/send or /chat/voice
    Backend->>Router: Language, Intent & Entity Extraction
    alt Intent is Structured Fee / Faculty / Schedule
        Router->>DB: Query Verified Record (BCA 2026-27 = ₹32,000)
        DB-->>Router: Verified Fee Record (ID, Version, Amount)
    else Intent is Institutional Notice or History
        Router->>RAG: Hybrid Search Official Knowledge Chunks
        RAG-->>Router: Official Grounded Passages & Source URLs
    else Intent is General Academic / Conceptual
        Router->>Gemini: Reasoning & Explanatory Synthesis
        Gemini-->>Router: Educational Response
    end
    Router->>Router: Grounding & No-Hallucination Verification
    alt Voice Mode
        Router->>Audio: Synthesize / Retrieve Cached Audio
        Audio-->>Router: Voice Asset ID
    end
    Router-->>Backend: Canonical Answer + Citations + Image Cards
    Backend-->>Frontend: JSON Response + Audio Stream
    Frontend-->>Student: Displays Markdown + Source Card + Voice Audio
```

---

## 3. Sequence Diagram: Visual Media & Event Photo Retrieval

```mermaid
sequenceDiagram
    autonumber
    actor User as Student / Visitor
    participant Frontend as UI Interface
    participant Router as AI Router
    participant ImgRetriever as Official Image Retriever
    participant DB as Verified Facility & Event Index

    User->>Frontend: "Show me last year's event photos"
    Frontend->>Router: Detect Intent: EVENT_IMAGE_SEARCH (Year: 2025)
    Router->>ImgRetriever: Search Verified Event Images (2025)
    ImgRetriever->>DB: Query Approved Media with Source URLs
    DB-->>ImgRetriever: Real AIT Photographs (Ignite 2025, Hackathon)
    ImgRetriever-->>Router: Image Payload + Full Provenance URLs
    Router-->>Frontend: Gallery Cards with Captions & Source Links
    Frontend-->>User: Renders Authentic AIT Photo Gallery
```

---

## 4. Entity-Relationship (ER) Diagram

```mermaid
erDiagram
    USERS ||--o{ CONVERSATIONS : starts
    USERS ||--o{ AUDIT_LOGS : records
    CONVERSATIONS ||--o{ MESSAGES : contains
    
    DEPARTMENTS ||--o{ COURSES : offers
    COURSES ||--o{ SUBJECTS : has
    COURSES ||--o{ FEES : defines
    COURSES ||--o{ TIMETABLES : schedules
    COURSES ||--o{ EXAMS : conducts
    
    FACULTY ||--o{ FACULTY_SUBJECTS : allocated_to
    SUBJECTS ||--o{ FACULTY_SUBJECTS : mapped_to
    
    FACILITIES ||--o{ FACILITY_IMAGES : has_photos
    EVENTS ||--o{ EVENT_IMAGES : has_photos
    
    KNOWLEDGE_SOURCES ||--o{ KNOWLEDGE_DOCUMENTS : crawls
    KNOWLEDGE_DOCUMENTS ||--o{ KNOWLEDGE_CHUNKS : splits
    KNOWLEDGE_SOURCES ||--o{ KNOWLEDGE_CONFLICTS : logs_dispute
```
