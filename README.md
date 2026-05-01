# UutisAnkka - No-BS News Briefing MVP

Full-stack MVP that ingests Finnish and international RSS news, removes low-value noise, ranks by relevance, generates concise bullet summaries, and serves a fast daily briefing UI with browser text-to-speech.

## Stack

- Backend: FastAPI + SQLite
- RSS parsing: feedparser
- Frontend: React + Vite
- TTS: Web Speech API (browser)
- Summarization: deterministic placeholder summarizer (LLM-ready integration point)

## Features in this MVP

- Fetches RSS feeds from Finnish + international sources
- Stores normalized articles to SQLite
- Deduplicates by content hash and near-title similarity
- Scores articles with a No-BS heuristic model:
  - Penalizes clickbait and low-signal patterns
  - Downranks celebrity/entertainment topics
  - Boosts politics, technology, economy, and geopolitics
  - Applies user preference boosts/penalties
- Generates a daily briefing endpoint with top ranked stories
- Creates 3-5 bullet factual summaries per story
- Supports browser TTS playback for top stories and per-article summaries
- Shows score breakdown per story (why the rank is what it is)
- Collects user feedback (relevant / not relevant) and feeds it back into ranking
- Exposes top-N acceptance metric based on feedback votes

## Project structure

- backend/app/main.py: FastAPI app and routes
- backend/app/database.py: SQLite schema and persistence helpers
- backend/app/services/ingest.py: RSS ingestion + dedupe + enrichment orchestration
- backend/app/services/scoring.py: relevance and no-noise scoring
- backend/app/services/summarizer.py: placeholder high-signal bullet summarizer
- frontend/src/App.jsx: briefing UI + personalization + TTS controls
- frontend/src/api.js: API client for backend endpoints

## Run locally (Windows Git Bash)

### 1) Backend

```bash
cd /g/UutisAnkka/backend
C:/Users/silve/AppData/Local/Microsoft/WindowsApps/python3.10.exe -m pip install -r requirements.txt
C:/Users/silve/AppData/Local/Microsoft/WindowsApps/python3.10.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 2) Frontend

```bash
cd /g/UutisAnkka/frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Open `http://127.0.0.1:5173`.

## API endpoints

- `GET /api/health`
- `POST /api/ingest`
- `GET /api/preferences`
- `PUT /api/preferences`
- `GET /api/briefing?limit=10`
- `POST /api/feedback`
- `GET /api/metrics?limit=10`

## Notes

- Startup triggers background periodic ingestion every 30 minutes.
- Summarization is intentionally deterministic placeholder logic for MVP speed.
- Ready to replace with an LLM summarization provider behind `services/summarizer.py`.
