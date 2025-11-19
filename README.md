# will*AI*am

Internal RAG playground for answering **“has this topic been talked about?”** from meeting notes, slide summaries, and livestream transcripts.

## Getting Started (fresh clone → question)

1. **Sync the repo**
   ```bash
   git clone <repo-url> will.ai.am   # or cd into the repo and run `git pull`
   cd will.ai.am
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

5. **Process slides (if working with PDF slide decks)**
   - Place PDF files in the `slides/` directory.
   - Process them to extract key points:
     ```bash
     py -m actions.process_slides
     ```
   - This creates JSON files in `sources/` (one per PDF) with slide analysis.

6. **Prepare embeddings**
   - Drop the latest meeting notes into `sources/{year}-{month}-meeting.json`, or use the JSON files generated from slide processing.
   - Embed them:
     ```bash
     py -m actions.embed --year 2025 --month 10 --notes-file sources/2025-10-meeting.json
     ```
   - Bundle (creates/updates `embeddings/bundled/bundle-{n}.json`):
     ```bash
     py -m actions.bundle
     ```

7. **Ask a question**
   ```bash
   py -m actions.ask
   ```
   Enter your prompt when asked; the tool returns a conversational answer plus the supporting rows.

## Project Structure

- `slides/` – PDF slide decks to process.
- `sources/` – raw meeting notes (`{year}-{month}-meeting.json`) and processed slide JSON files.
- `actions/process_slides.py` – processes PDF files from `slides/` directory, extracts key points using OpenAI (`gpt-4o-mini`), and saves JSON to `sources/`.
- `actions/embed.py` – CLI to embed a notes file and save to `embeddings/`.
- `embeddings/` – per-meeting embedding JSON (`{year}-{month}-meeting-embed.json`).
- `actions/bundle.py` – gathers all per-meeting files and writes `embeddings/bundled/bundle-{n}.json`.
- `actions/ask.py` – CLI search assistant that answers a question and cites where/when it was addressed.
- `embed_meeting_notes.py` – legacy helper if you need the older flow.

## Prerequisites

- **Python 3.12+** (repo was built/tested with `py` launcher on Windows).
- `pip install -r requirements.txt` installs everything needed (`pandas`, `python-dotenv`, `numpy`, `openai`, `ollama`, `PyMuPDF`).
- `.env` in the repo root with `OPENAI_API_KEY=...` (for for embedding, search, and slide processing).

## Typical Workflow

1. **Process slide PDFs (optional)**

   ```bash
   py -m actions.process_slides
   ```

   - Processes all PDF files in the `slides/` directory.
   - Extracts key points from each slide using OpenAI (`gpt-4o-mini` model).
   - Saves JSON files to `sources/` with the same name as the PDF (e.g., `presentation.pdf` → `sources/presentation.json`).
   - Each output file contains an array of slide data with `page` and `analysis` fields.
   - Empty pages are automatically skipped.

2. **Embed a meeting's notes**

   ```bash
   py -m actions.embed --year 2025 --month 10 --notes-file sources/2025-10-meeting.json \
       --point-summary  # optional flag for per-point vs per-slide embeddings
   ```

   - Outputs `embeddings/2025-10-meeting-embed.json` unless `--output-file` is provided.
   - Months can be `6` or `06`; files follow `{year}-{month}-meeting-embed.json`.
   - Can embed both manually created meeting notes or processed slide JSON files.

3. **Bundle embeddings for search**

   ```bash
   py -m actions.bundle
   ```

   - Reads every `embeddings/*-meeting-embed.json` file.
   - Adds `year` and `month` into each record.
   - Writes `embeddings/bundled/bundle-{n}.json`, where `n` increments based on the highest existing bundled file (so deletions won't cause overwrites).

4. **Ask questions**

   ```bash
   py -m actions.ask
   ```

   - Prompts for a question, embeds it, finds the top matches from the latest bundle, then crafts a conversational answer (citing `YEAR/MONTH`) and lists the supporting rows with similarity scores.
   - If no bundled file exists, it reminds you to run the bundler first.

## Data Expectations

- **Slide processing output**: JSON files from `process_slides.py` are arrays of objects with `page` (page number) and `analysis` (containing slide analysis with `file_name`, `slide_title`, `slide_analysis`, etc.).
- **Meeting JSON files**: Should be arrays of objects where each entry contains at least `slide` (or `point`), `text`, maybe `summary`. The embedding CLI will preserve whatever fields exist plus `embedding`.
- **Bundled files**: Keep the same structure as the original entries with two added keys: `year` and `month`.
- Downstream tooling assumes UTF-8 JSON; avoid NDJSON (the scripts now read/write standard arrays).

## Troubleshooting

- **`FileNotFoundError` when running ask** – no `embeddings/bundled/bundle-*.json` yet; run `py -m actions.bundle` after producing embeddings.
- **`unrecognized arguments: False`** – boolean CLI flags use `--flag` for true (set via `action='store_true'`). Pass `--point-summary` without `True/False`.
- **OpenAI errors** – confirm API key in `.env` and that the `gpt-4o-mini` + `text-embedding-3-large` models are enabled for the provided key.
- **No PDF files found** – ensure PDF files are placed in the `slides/` directory (not `sources/`).

## Future Ideas

- Automate bundling after every embed.
- Add streaming/GUI front-end for `actions.ask`.
- Explore LangChain or other frameworks for more advanced retrieval flows once the current pipeline feels limiting.
