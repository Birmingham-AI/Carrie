# Carrie Backend API

FastAPI backend for the Birmingham AI community RAG system.

## API Endpoints

### Health Check
```bash
GET /
```
Returns service status and version.

**Response**:
```json
{
  "status": "healthy",
  "service": "Carrie Backend API",
  "version": "1.0.0"
}
```

### Ask Question (Streaming with Agent)
```bash
POST /api/ask
Content-Type: application/json

{
  "question": "What topics were discussed about AI agents?",
  "enable_web_search": true  // optional, default: true
}
```

The agent will:
1. Search meeting notes using the RAGService tool
2. Optionally search the web for additional context (if enabled)
3. Synthesize a comprehensive answer with citations
4. Stream the response in real-time

**Response**: Server-Sent Events (SSE) stream
```
data: AI agents were
data:  discussed in
data:  2025/09...
data: [DONE]
```

### Search Only
```bash
GET /api/search?question=AI+agents&top_k=5
```

**Response**:
```json
{
  "results": [
    {
      "slide": 1,
      "year": 2025,
      "month": 9,
      "text": "Introduction to AI Agents...",
      "score": 0.8542
    }
  ]
}
```

## Running the API

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run with auto-reload
uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000
```

### Docker
```bash
# Using docker-compose (recommended)
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop
docker-compose down
```

## Interactive Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Example Usage

### Python
```python
import requests

# Non-streaming
response = requests.post(
    "http://localhost:8000/api/ask",
    json={"question": "What is transformer architecture?", "top_k": 5}
)
print(response.json())

# Streaming
response = requests.post(
    "http://localhost:8000/api/ask/stream",
    json={"question": "What is transformer architecture?"},
    stream=True
)
for line in response.iter_lines():
    if line:
        print(line.decode('utf-8'))
```

### cURL
```bash
# Non-streaming
curl -X POST "http://localhost:8000/api/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is transformer architecture?", "top_k": 5}'

# Streaming
curl -X POST "http://localhost:8000/api/ask/stream" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is transformer architecture?"}' \
  --no-buffer
```

### JavaScript (Fetch)
```javascript
// Non-streaming
const response = await fetch('http://localhost:8000/api/ask', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    question: 'What is transformer architecture?',
    top_k: 5
  })
});
const data = await response.json();
console.log(data);

// Streaming with EventSource
const eventSource = new EventSource(
  'http://localhost:8000/api/ask/stream',
  {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question: 'What is transformer architecture?' })
  }
);

eventSource.onmessage = (event) => {
  if (event.data === '[DONE]') {
    eventSource.close();
  } else {
    console.log(event.data);
  }
};
```

## Environment Variables

Required in `.env`:
```
OPENAI_API_KEY=sk-...
```

## Error Responses

**404 Not Found** - Source data not found:
```json
{
  "detail": "No source data available for the requested query."
}
```

**500 Internal Server Error**:
```json
{
  "detail": "Internal server error: <error message>"
}
```
