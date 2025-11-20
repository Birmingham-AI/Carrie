# will*AI*am

Internal RAG playground for answering **"has this topic been talked about?"** from meeting notes, slide summaries, and livestream transcripts.

## Demo

<video src="demo.mov" controls width="100%"></video>

## Quick Start

1. **Clone and configure**
   ```bash
   git clone https://github.com/Birmingham-AI/willAIam.git
   cd willAIam
   ```

2. **Set up environment**
   - Copy `.env.example` to `.env` (or create `.env` manually)
   - Add your OpenAI API key:
     ```
     OPENAI_API_KEY=sk-...
     ```

3. **Start the application**
   ```bash
   docker-compose up -d
   ```
   - Frontend: http://localhost:5174
   - Backend API: http://localhost:8001
   - API docs: http://localhost:8001/docs

4. **Ask questions!**
   - Open http://localhost:5174 in your browser
   - Type your question in the chat interface
   - Get AI-generated answers based on Birmingham AI meeting history

## Project Structure

```
willAIam/
├── backend/                    # FastAPI backend service
│   ├── app.py                 # Main API application
│   ├── services/
│   │   └── rag_service.py     # RAG logic (search, embedding, synthesis)
│   ├── actions/               # Data processing pipeline (CLI tools)
│   │   ├── process_slides.py  # Extract key points from PDF slides
│   │   ├── embed.py           # Generate embeddings from meeting notes
│   │   ├── bundle.py          # Combine embeddings for search
│   │   └── ask.py             # CLI question interface
│   ├── tests/                 # Backend tests
│   ├── Dockerfile             # Backend container definition
│   └── requirements.txt       # Python dependencies
├── frontend/                  # React frontend application
│   ├── src/
│   │   ├── components/        # React components
│   │   ├── services/          # API service layer
│   │   └── App.tsx            # Main application component
│   ├── Dockerfile             # Frontend container definition
│   └── package.json           # Node.js dependencies
├── slides/                    # PDF slide decks to process
├── sources/                   # Meeting notes JSON files
├── embeddings/                # Generated embeddings
│   └── bundled/              # Bundled embeddings for search
├── docker-compose.yml         # Service orchestration
└── .env                       # Environment variables (create from .env.example)
```

## Prerequisites

- **Docker & Docker Compose** (recommended for easiest setup)
- **OR** for local development:
  - Python 3.12+
  - Node.js 18+
  - OpenAI API key

## How It Works

### Data Pipeline

```
PDF Slides → Extract → JSON → Embed → Bundle → Search Index
Meeting Notes ────────┘
```

1. **Process slides** (optional): Extract key points from PDF slide decks
2. **Embed notes**: Convert meeting notes/slides to vector embeddings
3. **Bundle**: Combine all embeddings into searchable index
4. **Query**: Ask questions via web UI, get AI-synthesized answers with citations

### Architecture

- **Frontend**: React app with real-time streaming responses
- **Backend**: FastAPI with OpenAI Agents SDK
- **RAG Service**: Vector similarity search + GPT-4o-mini synthesis
- **Models**: `text-embedding-3-large` for embeddings, `gpt-4o-mini` for generation

## Data Processing (Optional)

If you need to add new meeting notes or process slide decks, use these CLI tools:

### 1. Process PDF Slides

```bash
# Place PDFs in slides/ directory, then:
python -m backend.actions.process_slides
```
- Extracts text and key points from each slide
- Outputs JSON to `sources/` (e.g., `presentation.pdf` → `sources/presentation.json`)

### 2. Create Embeddings

```bash
python -m backend.actions.embed --year 2025 --month 10 --notes-file sources/2025-10-meeting.json
```
- Generates vector embeddings from meeting notes or processed slides
- Outputs to `embeddings/{year}-{month}-meeting-embed.json`
- Add `--point-summary` flag for per-point embeddings instead of per-slide

### 3. Bundle for Search

```bash
python -m backend.actions.bundle
```
- Combines all embeddings in `embeddings/` directory
- Adds year/month metadata for citations
- Creates `embeddings/bundled/bundle-{n}.json` with auto-incrementing index

## Development

### Local Backend Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -r backend/requirements.txt

# Run backend
cd backend
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### Local Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

## API Endpoints

- `POST /api/ask` - Server-Sent Events streaming responses
- `GET /api/search` - Vector similarity search only (no synthesis)
- `GET /` - Health check

Full API documentation: http://localhost:8001/docs

## Data Format

### Meeting Notes JSON
```json
[
  {
    "slide": 1,
    "text": "Discussion about RAG systems...",
    "summary": "Overview of retrieval-augmented generation"
  }
]
```

### Embedding Output
```json
[
  {
    "year": 2025,
    "month": 10,
    "slide": 1,
    "text": "Discussion about RAG systems...",
    "embedding": [0.123, -0.456, ...]
  }
]
```

## Troubleshooting

- **No answers returned**: Ensure embeddings are bundled (`python -m backend.actions.bundle`)
- **OpenAI API errors**: Check `.env` file has valid `OPENAI_API_KEY`
- **Docker issues**: Run `docker-compose down && docker-compose up --build`
- **Frontend can't connect**: Ensure backend is running on port 8000

## Technologies

- **Backend**: FastAPI, OpenAI Agents SDK, NumPy, Pandas
- **Frontend**: React, TypeScript, Tailwind CSS
- **AI**: OpenAI GPT-4o-mini, text-embedding-3-large
- **Infrastructure**: Docker, Docker Compose
