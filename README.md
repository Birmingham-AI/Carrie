# will.a.i.am

Internal RAG playground for answering **“has this topic been talked about?”** from meeting notes, slide summaries, and livestream transcripts.

## Getting Started (fresh clone → question)

1. **Sync the repo**
   ```bash
   git clone <repo-url> will.a.i.am   # or cd into the repo and run `git pull`
   cd will.a.i.am
   ```

2. **Create/activate a virtual environment (optional but recommended)**
   ```bash
   py -m venv .venv
   .venv\\Scripts\\activate  # Windows PowerShell
   ```

3. **Install Python dependencies**
   ```bash
   py -m pip install -r requirements.txt
   ```

4. **Configure secrets**
   - Copy `.env.example` to `.env` if it exists, or create `.env` manually.
   - Add `OPENAI_API_KEY=sk-...` (the scripts use `gpt-4o-mini` + `text-embedding-3-large`).

5. **Prepare embeddings**
   - Drop the latest meeting notes into `sources/{year}-{month}-meeting.json`.
   - Embed them:
     ```bash
     py -m actions.embed --year 2025 --month 10 --notes-file sources/2025-10-meeting.json
     ```
   - Bundle (creates/updates `embeddings/bundled/bundle-{n}.json`):
     ```bash
     py -m actions.bundle
     ```

6. **Ask a question**
   ```bash
   py -m actions.ask
   ```
   Enter your prompt when asked; the tool returns a conversational answer plus the supporting rows.

## Project Structure

- `sources/` – raw meeting notes (`{year}-{month}-meeting.json`).
- `actions/embed.py` – CLI to embed a notes file and save to `embeddings/`.
- `embeddings/` – per-meeting embedding JSON (`{year}-{month}-meeting-embed.json`).
- `actions/bundle.py` – gathers all per-meeting files and writes `embeddings/bundled/bundle-{n}.json`.
- `actions/ask.py` – CLI search assistant that answers a question and cites where/when it was addressed.
- `embed_meeting_notes.py` – legacy helper if you need the older flow.

## Prerequisites

- **Python 3.12+** (repo was built/tested with `py` launcher on Windows).
- `pip install -r requirements.txt` installs everything needed (`pandas`, `python-dotenv`, `numpy`, `openai`).
- `.env` in the repo root with `OPENAI_API_KEY=...`.

## Typical Workflow

1. **Embed a meeting’s notes**

   ```bash
   py -m actions.embed --year 2025 --month 10 --notes-file sources/2025-10-meeting.json \
       --point-summary  # optional flag for per-point vs per-slide embeddings
   ```

   - Outputs `embeddings/2025-10-meeting-embed.json` unless `--output-file` is provided.
   - Months can be `6` or `06`; files follow `{year}-{month}-meeting-embed.json`.

2. **Bundle embeddings for search**

   ```bash
   py -m actions.bundle
   ```

   - Reads every `embeddings/*-meeting-embed.json` file.
   - Adds `year` and `month` into each record.
   - Writes `embeddings/bundled/bundle-{n}.json`, where `n` increments based on the highest existing bundled file (so deletions won’t cause overwrites).

3. **Ask questions**

   ```bash
   py -m actions.ask
   ```

   - Prompts for a question, embeds it, finds the top matches from the latest bundle, then crafts a conversational answer (citing `YEAR/MONTH`) and lists the supporting rows with similarity scores.
   - If no bundled file exists, it reminds you to run the bundler first.

## Data Expectations

- Meeting JSON files should be arrays of objects where each entry contains at least `slide` (or `point`), `text`, maybe `summary`. The embedding CLI will preserve whatever fields exist plus `embedding`.
- Bundled files keep the same structure as the original entries with two added keys: `year` and `month`.
- Downstream tooling assumes UTF-8 JSON; avoid NDJSON (the scripts now read/write standard arrays).

## Troubleshooting

- **`FileNotFoundError` when running ask** – no `embeddings/bundled/bundle-*.json` yet; run `py -m actions.bundle` after producing embeddings.
- **`unrecognized arguments: False`** – boolean CLI flags use `--flag` for true (set via `action='store_true'`). Pass `--point-summary` without `True/False`.
- **OpenAI errors** – confirm API key in `.env` and that the `gpt-4o-mini` + `text-embedding-3-large` models are enabled for the provided key.

## Future Ideas

- Automate bundling after every embed.
- Add streaming/GUI front-end for `actions.ask`.
- Explore LangChain or other frameworks for more advanced retrieval flows once the current pipeline feels limiting.
