# Carrie

RAG-powered knowledge base for the Birmingham AI community. Named after Carrie A. Tuggle (1858-1924), a Birmingham educator who founded the first orphanage for African-American children in Alabama. Ask questions about past meetups, presentations, and livestreams.

## Demo

<img src="chat.gif" width="800" />

## Quick Start

1. **Clone and configure**
   ```bash
   git clone https://github.com/Birmingham-AI/carrie.git
   cd carrie
   ```

2. **Set up environment**

   Copy `.env.example` to `.env` and configure:
   ```bash
   # Required
   OPENAI_API_KEY=sk-...

   # Required for YouTube transcription and vector search
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your-service-role-key

   # Required for YouTube upload protection
   UPLOAD_API_KEY=your-secret-key
   ```

3. **Initialize Supabase database**

   Run the SQL script in `backend/SQL/initialize.sql` in your Supabase SQL editor to create the required tables and functions.

4. **Start the application**

   For Docker:
   ```bash
   docker-compose up -d
   ```

   For Podman:
   ```bash
   python -m podman_compose up -d
   ```

   - Frontend: http://localhost:5174
   - Backend API: http://localhost:8001
   - API docs: http://localhost:8001/docs

5. **Use the app**
   - **Chat**: Ask questions at http://localhost:5174
   - **Upload**: Add YouTube videos at http://localhost:5174/upload

## Features

- **AI-powered Q&A**: Ask questions about Birmingham AI meetup content
- **YouTube transcription**: Upload YouTube videos to automatically transcribe and embed for search
- **Vector search**: Find relevant content using semantic similarity via Supabase pgvector
- **Streaming responses**: Real-time AI answers with source citations
- **Web search integration**: Optional web search for additional context

## Architecture

### System Overview

![Carrie Architecture](drawings/carrie-architecture.svg)

### Agent Tool Routing

![Agent Tool Routing](drawings/agent-tool-routing.svg)

### Content Ingestion Pipeline

![Content Ingestion Pipeline](drawings/content-ingestion-pipeline.svg)

## Project Structure

```
carrie/
├── backend/
│   ├── app.py                    # FastAPI application
│   ├── routes/
│   │   ├── ask.py                # Q&A streaming endpoint
│   │   └── youtube.py            # YouTube upload endpoints
│   ├── services/
│   │   ├── rag_service.py        # Vector search via Supabase
│   │   └── streaming_agent.py    # OpenAI agent for answers
│   ├── actions/
│   │   ├── transcribe_youtube.py # YouTube transcription + embedding
│   │   └── process_slides.py     # PDF slide extraction
│   ├── clients/
│   │   ├── openai.py             # Async OpenAI client
│   │   └── supabase.py           # Async Supabase client
│   ├── models/
│   │   └── schemas.py            # Pydantic request/response models
│   ├── SQL/
│   │   └── initialize.sql        # Database schema
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── chat/             # Chat UI components
│   │   │   ├── upload/           # YouTube upload UI
│   │   │   └── error/            # Error boundary
│   │   ├── services/
│   │   │   └── ApiService.ts     # API client
│   │   └── App.tsx               # Routes and layout
│   └── package.json
├── docker-compose.yml
└── .env
```

## API Endpoints

### Q&A
- `POST /api/ask` - Streaming Q&A with conversation history
- `GET /api/search?question=...&top_k=5` - Vector search only

### YouTube
- `POST /api/youtube/verify-key` - Verify API key (requires `X-API-Key` header)
- `POST /api/youtube/upload` - Start transcription job (requires `X-API-Key` header)
- `GET /api/youtube/status/{job_id}` - Check job status
- `GET /api/youtube/sources` - List processed videos
- `DELETE /api/youtube/sources/{id}` - Delete video and embeddings (requires `X-API-Key` header)

### Health
- `GET /` - Health check

Full API documentation: http://localhost:8001/docs

## YouTube Transcription

Add YouTube videos to the knowledge base via the web UI or API:

**Web UI**: Navigate to http://localhost:5174/upload

**CLI**:
```bash
python -m backend.actions.transcribe_youtube \
  --url "https://www.youtube.com/watch?v=VIDEO_ID" \
  --session "Nov 2024 Birmingham AI Meetup"
```

**API**:
```bash
curl -X POST http://localhost:8001/api/youtube/upload \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-key" \
  -d '{"url": "VIDEO_URL", "session_info": "Session Name"}'
```

Options:
- `chunk_size`: Characters per chunk (default: 1000)
- `overlap`: Sentences to overlap between chunks (default: 1)
- `language`: Transcript language code (default: "en")

## Development

### Backend
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

cd backend
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Database Schema

The system uses Supabase with pgvector for vector similarity search:

**sources**: Tracks uploaded content (YouTube videos, etc.)
- `id`, `source_type`, `source_id`, `session_info`, `chunk_count`, `processed_at`

**embeddings**: Stores text chunks with vector embeddings
- `id`, `source_id`, `text`, `timestamp`, `embedding` (vector 1536)

**match_embeddings()**: RPC function for cosine similarity search

## Technologies

- **Backend**: FastAPI, OpenAI Agents SDK, Supabase (async)
- **Frontend**: React, TypeScript, Tailwind CSS, React Router
- **AI**: OpenAI GPT-4o-mini, text-embedding-3-small
- **Database**: Supabase PostgreSQL with pgvector
- **Infrastructure**: Docker, Docker Compose
