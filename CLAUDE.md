# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

will*AI*am is a RAG (Retrieval-Augmented Generation) system for the Birmingham AI community. It answers questions like "has this topic been talked about?" using meeting notes, slide summaries, and transcripts. The system uses OpenAI's `gpt-4o-mini` for analysis and `text-embedding-3-large` for embeddings.

## Common Commands

### Environment Setup
```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows PowerShell

# Install dependencies
pip install -r requirements.txt
```

### Environment Configuration
Create a `.env` file from `.env.example` and configure:
```
OPENAI_API_KEY=sk-...

# Optional: Langfuse observability
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_BASE_URL=https://us.cloud.langfuse.com
```

### Processing Pipeline

**1. Process PDF slides** (optional, if working with slide decks)
```bash
python -m backend.actions.process_slides
```
- Processes all PDF files in `slides/` directory
- Extracts key points using OpenAI
- Outputs JSON to `sources/` (e.g., `presentation.pdf` → `sources/presentation.json`)

**2. Embed meeting notes or processed slides**
```bash
python -m backend.actions.embed --year 2025 --month 10 --notes-file sources/2025-10-meeting.json
python -m backend.actions.embed --year 2025 --month 10 --notes-file sources/2025-10-meeting.json --point-summary
```
- Creates embeddings for meeting notes or slide JSON files
- Outputs to `embeddings/{year}-{month}-meeting-embed.json`
- Use `--point-summary` for per-point embeddings instead of per-slide

**3. Bundle embeddings for search**
```bash
python -m backend.actions.bundle
```
- Gathers all `embeddings/*-meeting-embed.json` files
- Adds year/month metadata to each record
- Creates `embeddings/bundled/bundle-{n}.json` with auto-incrementing index

**4. Query the system (CLI)**
```bash
python -m backend.actions.ask
```
- Interactive CLI that prompts for questions
- Uses vector similarity search to find relevant content
- GPT-4o-mini synthesizes conversational answers with citations (YEAR/MONTH format)

### Backend API

**Run the FastAPI backend locally**
```bash
# From project root, using uvicorn
cd backend && uvicorn app:app --reload --host 0.0.0.0 --port 8000

# Or from backend directory
cd backend && python app.py
```
- API will be available at `http://localhost:8000`
- Interactive API docs at `http://localhost:8000/docs`

**Run with Docker**
```bash
# Build and start the container
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the container
docker-compose down
```
- Backend runs on port 8000
- Embeddings directory is mounted as read-only volume
- Health checks ensure service availability

## Architecture

### Data Flow
```
PDFs (slides/) → [backend.actions.process_slides] → JSON (sources/)
                                                         ↓
Meeting JSON (sources/) → [backend.actions.embed] → Embeddings (embeddings/)
                                                         ↓
Multiple embeddings → [backend.actions.bundle] → Bundled file (embeddings/bundled/)
                                                         ↓
User question → [CLI: backend.actions.ask OR API: backend.app] → Vector search → GPT synthesis → Answer with citations
```

### Backend API Architecture

**FastAPI Application** (`backend/app.py`):
- RESTful API with three main endpoints
- CORS middleware for frontend integration
- Health check endpoint at `/`

**Endpoints**:
- `POST /api/ask` - Non-streaming question answering with results
- `POST /api/ask/stream` - Server-Sent Events (SSE) streaming responses
- `GET /api/search` - Vector similarity search only (no synthesis)

**RAG Service** (`backend/services/rag_service.py`):
- Encapsulates all RAG logic (search, embedding, synthesis)
- Supports both streaming and non-streaming answer generation
- Reuses same embedding and similarity logic as CLI
- OpenAI SDK tracing disabled for ZDR organizations

**Langfuse Tracing** (`backend/services/langfuse_tracing.py`):
- Optional observability via Langfuse (OpenTelemetry-based)
- Enabled via `LANGFUSE_ENABLED=true` environment variable
- Tracks user IP as `user_id` for session analysis
- Captures agent runs, tool calls, and token usage

### Key Modules

**backend/actions/process_slides.py**
- Uses PyMuPDF to extract text from PDF slides
- Calls OpenAI with JSON mode to extract structured key points
- Output format: `[{"page": int, "text": str, "analysis": {...}}]`
- Skips empty pages automatically
- Combines slide title and key points into the `text` field for embedding compatibility

**backend/actions/embed.py**
- Reads JSON meeting notes/slides from `sources/`
- Creates embeddings via OpenAI's `text-embedding-3-large` model
- Two modes: per-slide (default) or per-point (`--point-summary` flag)
- Handles both manually-created meeting notes and processed slide JSON files
- Preserves all original fields from input JSON, adds `embedding` field
- Output stored in `embeddings/` directory

**backend/actions/bundle.py**
- Scans `embeddings/` for all `*-meeting-embed.json` files
- Parses year/month from filenames using regex pattern `YYYY-M(M)-meeting-embed.json`
- Merges all records, injects `year` and `month` fields into each record
- Creates versioned bundles with auto-incrementing index to prevent overwrites
- Ensures `embeddings/bundled/` directory structure exists

**backend/actions/ask.py**
- Loads the latest bundled embeddings file (`bundle-{max}.json`)
- Embeds user query with same model (`text-embedding-3-large`)
- Computes cosine similarity against all stored embeddings
- Returns top-k results (default: 5)
- Uses OpenAI Agents SDK with streaming to synthesize conversational answer citing year/month
- Streams responses token-by-token for real-time display
- Async implementation using asyncio
- Displays supporting results with similarity scores

### Data Format Expectations

**Meeting JSON** (in `sources/`):
- Array of objects with at least `text` field
- Optional: `slide` or `page`, `points`, `summary`
- Can be manually created or generated from `process_slides.py`

**Embedding JSON** (in `embeddings/`):
- Same structure as input, plus `embedding` array
- Includes `year`, `month`, `slide`/`page`, `text`

**Bundled JSON** (in `embeddings/bundled/`):
- Flat array of all embedding records
- Each record includes `year`, `month` for citation purposes

## Python Version
This codebase requires Python 3.12+. Originally developed using the `py` launcher on Windows, but works cross-platform.

## Dependencies
Core libraries in `requirements.txt`:
- `openai==2.8.0` - OpenAI API client for GPT and embeddings
- `openai-agents==0.6.1` - OpenAI Agents SDK for streaming responses
- `pandas==2.3.3` - Data manipulation for JSON processing
- `numpy==2.3.5` - Vector operations for cosine similarity
- `PyMuPDF==1.26.6` - PDF text extraction for slide processing
- `python-dotenv==1.2.1` - Environment variable management
- `fastapi==0.115.6` - Modern web framework for building APIs
- `uvicorn[standard]==0.32.1` - ASGI server for running FastAPI
- `requests==2.32.5` - HTTP library for health checks

## Docker Deployment

**Directory Structure**:
```
willAIam/
├── backend/              # All backend code
│   ├── app.py           # Main FastAPI application
│   ├── services/
│   │   └── rag_service.py  # RAG logic
│   ├── actions/         # Data processing pipeline
│   │   ├── process_slides.py
│   │   ├── embed.py
│   │   ├── bundle.py
│   │   └── ask.py       # CLI interface
│   ├── Dockerfile       # Container definition
│   ├── requirements.txt # Python dependencies
│   ├── .dockerignore    # Build exclusions
│   ├── test_backend.py  # Test script
│   ├── README.md        # API documentation
│   └── DEPLOYMENT.md    # Deployment guide
├── embeddings/          # Generated embeddings (mounted in Docker)
│   └── bundled/
│       └── bundle-*.json
├── sources/             # Meeting notes JSON (mounted in Docker)
├── slides/              # PDF files to process
├── docker-compose.yml   # Service orchestration (root level)
└── .env                 # Environment variables
```

**Docker Commands**:
```bash
# Build the image
docker build -t willaim-backend .

# Run with docker-compose (recommended)
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f backend

# Stop and remove containers
docker-compose down

# Rebuild after code changes
docker-compose up -d --build
```

**Environment Variables**:
The container requires `OPENAI_API_KEY` in the `.env` file, which is automatically loaded by docker-compose. Optional Langfuse variables (`LANGFUSE_ENABLED`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL`) can be added for observability.

**Volumes**:
- `./embeddings:/app/embeddings:ro` - Read-only access to embeddings
- `./sources:/app/sources:ro` - Read-only access to source files (optional)

## Project Goals (from AGENTS.md)
- Build a RAG that answers Birmingham AI community questions based on previous meetings
- Track what people are asking
- ✅ Host as API (completed with FastAPI backend and Docker deployment)
