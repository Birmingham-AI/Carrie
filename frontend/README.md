# Carrie Frontend

A clean, minimal chat interface for the Carrie RAG system. Simple single-session chat with streaming responses.

## Features

- Simple chat bubbles (user on right, assistant on left)
- Streaming responses with markdown support
- Web search toggle (enable/disable web search)
- No authentication, no persistence, no history
- Responsive design

## Setup

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Configure environment:**
   Create a `.env` file in the project root (not in frontend/):
   ```bash
   VITE_API_BASE_URL=http://localhost:8001
   ```

3. **Run development server:**
   ```bash
   npm run dev
   ```

   The app will be available at `http://localhost:5173`

## Build for Production

```bash
npm run build
```

The built files will be in the `dist/` directory.

## Docker

The frontend is configured to run with Docker Compose:

```bash
# From project root
docker-compose up
```

The frontend will be available at `http://localhost:5174`

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── chat/
│   │   │   ├── ChatContainer.tsx    # Main container
│   │   │   ├── MessageList.tsx      # Message display
│   │   │   └── MessageInput.tsx     # Input with web search toggle
│   │   └── error/
│   │       └── ErrorBoundary.tsx    # Error handling
│   ├── services/
│   │   └── ApiService.ts            # Backend API (streaming)
│   ├── types/
│   │   └── chat.ts                  # Type definitions
│   ├── App.tsx                      # Main app
│   ├── main.tsx                     # Entry point
│   ├── config.ts                    # API config
│   └── index.css                    # Minimal styles
├── package.json
└── vite.config.ts
```

## How It Works

1. User types a message
2. Globe icon toggles web search on/off
3. Message streams from backend `/api/ask` endpoint
4. Response appears in real-time
5. New chat clears everything - no persistence

## Dependencies

Minimal dependencies (5 total):

- **React** - UI framework
- **React Markdown** - Markdown rendering
- **Remark GFM** - GitHub Flavored Markdown
- **Lucide React** - Icons (Globe, Bot, User, etc.)
- **Tailwind CSS** - Styling

## Configuration

- **Vite** - Build tool and dev server
- **TypeScript** - Type safety
- **ESLint** - Code linting

## API Integration

Connects to Carrie backend at `/api/ask`:

```typescript
POST /api/ask
{
  "question": "user question",
  "enable_web_search": true/false
}
```

Receives Server-Sent Events (SSE) for streaming responses.
