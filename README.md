# RaAI — Agentic RAG Emotional Wellness System
## Hack the Winter – The Second Wave
### Team Name: The Jugaadus
### Theme/Domain: AI/ML
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Next.js 15](https://img.shields.io/badge/Next.js-15-black)](https://nextjs.org/)

An AI-powered emotional intelligence coach using Retrieval-Augmented Generation (RAG) for personalized wellness exercises and journal analysis.

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- Docker & Docker Compose (optional)
- At least one LLM API key (Google Gemini, Groq, or OpenAI)

### Local Development

1. **Clone the repository**
```bash
git clone https://github.com/MuaazSM/hack-the-winter.git
cd hack-the-winter
```

2. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your API keys
```

3. **Option A: Docker Compose (Recommended)**
```bash
docker-compose up -d
```
- Backend: http://localhost:8000
- Frontend: http://localhost:3000
- MongoDB: localhost:27017
- Qdrant: http://localhost:6333

4. **Option B: Native Development**

**Backend:**
```bash
cd backend
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## 🏗️ Technical Architecture

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Next.js Frontend                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │   Dashboard  │  │   Journal    │  │    Chat      │               │
│  │   Analytics  │  │   Entry      │  │   Interface  │               │
│  └──────────────┘  └──────────────┘  └──────────────┘               │
│  (App Router, TypeScript, Tailwind, Radix UI, shadcn/ui)            │
└───────────────────────────────────────┬─────────────────────────────┘
                                        │ REST API
┌───────────────────────────────────────▼─────────────────────────────┐
│                      FastAPI Backend (Python)                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                 Multi-Agent Orchestrator                     │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │   │
│  │  │   Data   │  │ Context  │  │ Insight  │  │ Sentiment│      │   │
│  │  │  Agent   │  │  Agent   │  │  Agent   │  │  Agent   │      │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘      │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐                    │   │
│  │  │  Crisis  │  │  Memory  │  │  Coach   │                    │   │
│  │  │  Agent   │  │ Manager  │  │  Agent   │                    │   │
│  │  └──────────┘  └──────────┘  └──────────┘                    │   │
│  └──────────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                       RAG Pipeline                           │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │   │
│  │  │  Document    │  │   Chunking   │  │  Embedding   │        │   │
│  │  │   Loader     │  │   & Indexing │  │   Model      │        │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘        │   │
│  │  ┌─────────────────┐  ┌──────────────┐  ┌──────────────┐     │   │
│  │  │    Retrieval    │  │  Synthesis   │  │  Prompt      │     │   │
│  │  │ (FAISS/Qdrant)  │  │   Engine     │  │  Registry    │     │   │
│  │  └─────────────────┘  └──────────────┘  └──────────────┘     │   │
│  └──────────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                     Core Modules                             │   │
│  │  • Journal Analyzer (EQ Analysis, Cognitive Distortions)     │   │
│  │  • Safety Checker (Crisis Detection)                         │   │
│  │  • Baseline Scoring (5-Dimension EQ Assessment)              │   │
│  │  • Recommender (Personalized Exercise Generation)            │   │
│  │  • Matchmaking (User-Exercise Matching)                      │   │
│  └──────────────────────────────────────────────────────────────┘   │
└───────────┬─────────────────┬─────────────────┬─────────────────────┘
            │                 │                 │
    ┌───────▼──────┐  ┌───────▼─────┐  ┌────────▼────────┐
    │   MongoDB    │  │    FAISS    │  │  LLM Providers  │
    │  (Sessions,  │  │  (Vectors)  │  │  • OpenAI GPT   │
    │  Messages,   │  │  / Qdrant   │  │  • Google Gemini│
    │  Documents,  │  │             │  │  • Groq Llama   │
    │  Analytics)  │  │             │  └─────────────────┘
    └──────────────┘  └─────────────┘
```

### Data Flow Diagram (DFD)

```
┌─────────────┐
│   User      │
│  Input      │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────────────────────┐
│                    Request Flow                         │
│                                                         │
│  1. User Message/Journal Entry                          │
│     │                                                   │
│     ├─► Safety Checker (Crisis Detection)               │
│     │   └─► If CRISIS: Escalate + Alert                 │
│     │                                                   │
│     ├─► Sentiment Agent (Emotion Analysis)              │
│     │   └─► Extract: emotions, sentiment, mood_index    │
│     │                                                   │
│     ├─► Context Agent (RAG Retrieval)                   │
│     │   ├─► Query FAISS/Qdrant Vector Store             │
│     │   ├─► If insufficient: Web Search Augmentation    │
│     │   └─► Return: Relevant chunks + citations         │
│     │                                                   │
│     ├─► Insight Agent (Response Generation)             │
│     │   ├─► Analyze context + sentiment                 │
│     │   ├─► Select EQ facet (self-awareness, etc.)      │
│     │   ├─► Generate personalized exercise/response     │
│     │   └─► Apply prompt templates from registry        │
│     │                                                   │
│     └─► Memory Manager (Persistence)                    │
│         ├─► Save to MongoDB (sessions, messages)        │
│         ├─► Update episodic memory                      │
│         └─► Update long-term profile                    │
│                                                         │
└─────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────┐
│   Response  │
│  to User    │
└─────────────┘
```

### Agent Orchestration Flow

```
User Message
    │
    ▼
┌─────────────────┐
│  Orchestrator   │
│  (Main Router)  │
└────────┬────────┘
         │
         ├─────────────────────────────────────┐
         │                                     │
    ┌────▼────┐                          ┌────▼────┐
    │  Mode   │                          │  Mode   │
    │  "qa"   │                          │"weekly" │
    └────┬────┘                          └────┬────┘
         │                                     │
         │                                     │
    ┌────▼─────────────────────────────────────▼────┐
    │         Sentiment Agent                       │
    │  • Analyze emotions                           │
    │  • Calculate sentiment score                  │
    │  • Detect mood patterns                       │
    └───────────────┬───────────────────────────────┘
                    │
    ┌───────────────▼───────────────┐
    │      Crisis Agent             │
    │  • Evaluate risk level        │
    │  • Check z-score thresholds   │
    │  • Trigger alerts if needed   │
    └───────────────┬───────────────┘
                    │
    ┌───────────────▼───────────────┐
    │      Context Agent            │
    │  • Query RAG vector store     │
    │  • Web search if needed       │
    │  • Return relevant passages   │
    └───────────────┬───────────────┘
                    │
    ┌───────────────▼───────────────┐
    │      Insight Agent            │
    │  • Generate personalized      │
    │    response/exercise          │
    │  • Apply EQ facet targeting   │
    │  • Synthesize from context    │
    └───────────────┬───────────────┘
                    │
    ┌───────────────▼───────────────┐
    │      Memory Manager           │
    │  • Persist interaction        │
    │  • Update user profile        │
    │  • Store in MongoDB           │
    └───────────────┬───────────────┘
                    │
                    ▼
            Response to User
```

### RAG Pipeline Flow

```
Document Sources
    │
    ├─► PDF Files (Local/Upload)
    ├─► Web URLs
    ├─► YouTube Videos
    └─► Text Input
         │
         ▼
┌──────────────────────┐
│  Document Loader     │
│  (PyPDF, WebBase,    │
│   YoutubeLoader)     │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Text Splitter       │
│  (RecursiveCharacter │
│   Chunking)          │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Embedding Model     │
│  (OpenAI/Gemini)     │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Vector Store        │
│  • FAISS (Local)     │
│  • Qdrant (Cloud)    │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Retrieval           │
│  • Similarity Search │
│  • Hybrid (BM25+Vec) │
│  • Top-K Selection   │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Synthesis           │
│  • LLM Generation    │
│  • Context Injection │
│  • Exercise Creation │
└──────────┬───────────┘
           │
           ▼
    Personalized Output
```

### Key Features

- **5-Dimension EQ Analysis**: Self-awareness, self-regulation, motivation, empathy, social skills
- **Cognitive Distortion Detection**: Dual LLM + regex-based pattern recognition
- **RAG-Powered Exercises**: Personalized recommendations from wellness document corpus
- **Multi-Agent Orchestration**: Specialized agents for data, context, insight, sentiment, and crisis management
- **Session Management**: Multiple named conversations like ChatGPT
- **Offline-First Frontend**: Graceful degradation with local fallbacks
- **Voice Transcription**: AssemblyAI-powered voice-to-text journaling (frontend-only)
- **Crisis Detection**: Keyword + LLM-based safety escalation with alert system
- **Web-Augmented RAG**: Automatic web search when local knowledge is insufficient
- **Memory Management**: Episodic and long-term memory for personalized experiences







## Planned Improvements for Round 2

*Focus: High-impact, feasible improvements that enhance safety, quality, and personalization without over-engineering.*

### 1. Make the System Safer + More Trustworthy

**Why it matters**: Mental health apps live/die on safety + user trust.

- **Crisis Detection v2** (low effort, high impact)
  - Add a risk score (0–100) with clear thresholds (green/yellow/red)
  - Store why it triggered (signals), not just "crisis=true"
  - Add a "what I can / can't do" policy response (non-clinical boundaries)

- **Grounding Guardrails for RAG Outputs**
  - Force responses to cite retrieved chunks when claiming "facts"
  - If retrieval confidence is low → switch to "supportive coaching mode" (no factual claims)
  - Reduce liability, increase user confidence, improve response quality

### 2. Upgrade RAG Quality (Without Making It Complicated)

**Why it matters**: Your biggest "wow" comes from better retrieval + better synthesis, not more sources.

- **Hybrid Retrieval (BM25 + Vectors)**
  - Keep FAISS/Qdrant, but add BM25 fallback (fast + reliable for exact phrasing)
  
- **Better Chunking + Metadata**
  - Store: source, section, tags (anxiety/grief/etc.), reading_level
  - Chunk by headings (not just characters) when possible
  
- **Rerank Top Results**
  - Add a lightweight reranker step (even a small cross-encoder / LLM scoring)
  
- **"Don't Hallucinate" Synthesis Template**
  - Output structure:
    - What you're feeling (from sentiment)
    - What helped others / what the source suggests (with citations)
    - One small exercise (personalized)
    - A check-in question
  
  - Noticeable quality jump without adding new data types

### 3. Make Personalization Real (Simple Version)

**Why it matters**: "Personalization" is your retention engine — but you don't need ML training.

- **User Profile Schema v1 (Rule-Based)**
  - Store stable traits: preferred tone, triggers, coping styles, goals, sleep/exercise habits (optional)
  
- **Episodic Memory with TTL**
  - Keep recent context for ~14–30 days, decay older memories
  
- **Preference Learning (No ML)**
  - After each exercise: quick feedback 👍/👎 + "too long/too generic/too intense"
  - Update a preference_vector (just counters)
  
  - Makes the app feel "alive" and tailored with minimal engineering

### 4. Turn "Journal Analyzer" into a Product Feature

**Why it matters**: Users want clarity + action, not labels.

- **Weekly Summary** (one endpoint + one UI page)
  - Mood trend, top triggers, most common distortions, what helped
  - Keep it explainable (show examples from journal snippets)
  - One "next step" recommendation
  - Pick one focus for next week (sleep, boundaries, rumination, etc.)
  
  - Extremely sticky feature, very doable

### 5. Add the One Piece of Analytics That Matters

**Why it matters**: Avoid building dashboards that look good but mean nothing.

**Track only:**
- **Activation**: Did user complete 1 journal + 1 exercise in first 24h?
- **Retention**: Did they return within 3 days?
- **Helpfulness**: Thumbs up/down on responses + exercises completed
- **Safety events count** (and resolution flow completion)

- Lets you iterate intelligently without drowning in metrics

### 6. Performance + Cost Control (Quiet but Critical)

**Why it matters**: Multi-agent + RAG can get expensive and slow.

- **Single-Call Orchestration**
  - For most requests: sentiment + insight in one pass, not 5 separate LLM calls
  
- **Caching**
  - Cache retrieval results per session (short TTL)
  
- **Rate Limiting + Abuse Prevention**
  - Basic per-IP/session throttling
  
- **Async Tasks**
  - Move ingestion/indexing to background jobs
  
- Better UX and cheaper scaling, without changing product


## 📧 Contact

Project Link: [https://github.com/MuaazSM/hack-the-winter](https://github.com/MuaazSM/hack-the-winter)

