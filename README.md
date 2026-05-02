# UutisAnkka - No-BS News Briefing

Mobile-first app that ingests Finnish and international RSS news, removes low-value noise, ranks by personal relevance, and serves a concise daily briefing you swipe through in minutes.

## MVP user flow

```
Onboarding → Daily briefing → Swipe feedback → History → Preferences
```

1. **Onboarding** — first-time setup: choose news scope (Finland / World / Local), pick interesting and uninteresting topics, select city if local news chosen.
2. **Daily briefing** — top-ranked articles based on your preferences. Swipe right (relevant) or left (not relevant) to give feedback.
3. **Swipe feedback** — each swipe is recorded and fed back into the ranking model so the briefing improves over time.
4. **History** — review previously seen articles grouped by day, filterable by relevance.
5. **Preferences** — adjust topics, scope, and source filters at any time.

## Out of scope (this MVP)

- User accounts and authentication
- Premium features or payments
- Multi-user support
- Full web feature parity with mobile

## Stack

- **Mobile:** React Native (Expo 54) — primary interface
- **Backend:** FastAPI + SQLite
- **RSS parsing:** feedparser (~50 Finnish and international sources)
- **Summarization:** OpenAI gpt-4o-mini with deterministic fallback
- **Scoring:** heuristic no-BS model with user feedback loop
- **Web:** React + Vite (secondary, dev/demo use)

## What the backend does

- Fetches RSS feeds from Finnish + international sources
- Stores normalized articles to SQLite with content-hash deduplication
- Scores articles with a no-BS heuristic model:
  - Penalizes clickbait and low-signal patterns
  - Downranks celebrity and entertainment topics
  - Boosts politics, technology, economy, geopolitics
  - Applies per-user preference boosts and feedback penalties
- Generates bullet-point summaries (OpenAI, with deterministic fallback if no API key)
- Translates international articles to Finnish before summarizing
- Re-ingests feeds every 30 minutes in the background
- Records swipe feedback and surfaces it to the ranking model

## Project structure

```
backend/
  app/
    main.py          App bootstrap: logging config, CORS, lifespan, router mounting
    config.py        RSS feed list, topic weights, regional settings
    database.py      SQLite schema and thread-safe query helpers
    models.py        Pydantic request/response schemas
    api/
      briefing.py    GET /api/briefing, GET /api/briefing/random
      preferences.py GET|PUT /api/preferences
      feedback.py    POST /api/feedback
      articles.py    GET /api/history, /api/metrics, /api/articles
      ingest.py      POST /api/ingest
      admin.py       POST /api/admin/reenrich, /api/admin/resummarize + status
      errors.py      Global exception handler → {"detail": …, "error_code": …}
    services/
      ingest.py      RSS fetch, dedup, enrichment orchestration
      scoring.py     Relevance and no-BS scoring logic
      summarizer.py  Bullet summary generation (OpenAI + fallback)
      translator.py  English → Finnish translation for intl sources

frontend-mobile/
  App.jsx            Screen orchestrator (thin shell, imports domain hooks)
  src/
    api.js           API client (configure base URL via EXPO_PUBLIC_API_BASE)
    navigation/
      routes.js              Route name constants
      useAppNavigation.js    Navigation state hook
    state/
      useBriefingState.js    Article, progress, and surprise story state
      usePreferencesState.js User preferences state
      useSessionUiState.js   Onboarding, loading, busy, error state
    components/
      OnboardingScreen.jsx   First-run setup flow
      ArticleCard.jsx        Swipe card UI and feedback
      HistoryScreen.jsx      Previously seen articles
      PreferencesPanel.jsx   Topic and source settings
      AllNewsScreen.jsx      Full article list (dev/debug)

frontend/            React + Vite web UI (dev and demo use)
  src/
    App.jsx
    api.js
```

## Run locally (Windows Git Bash)

### 1) Backend

```bash
cd /g/UutisAnkka/backend
python3.10 -m pip install -r requirements.txt
python3.10 -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Copy `.env.example` to `.env` and add your `OPENAI_API_KEY` to enable LLM summarization. Without it the app falls back to deterministic summaries.

Optional env vars:
- `LOG_LEVEL` — logging verbosity: `DEBUG`, `INFO` (default), `WARNING`
- `CORS_ALLOW_ORIGINS` — comma-separated extra origins beyond the defaults
- `CORS_ALLOW_ORIGIN_REGEX` — regex for dynamic Expo tunnels (e.g. `https://.*\.ngrok\.io`)
- `INGEST_INTERVAL_SECONDS` — background feed polling interval (default: `1800`)

### 2) Mobile (Expo)

```bash
cd /g/UutisAnkka/frontend-mobile
npm install
cp .env.example .env
npm start
```

Set `EXPO_PUBLIC_API_BASE` in `frontend-mobile/.env` to switch environment without code changes.
Examples:

- Local simulator/web: `http://127.0.0.1:8000`
- Local phone over LAN: `http://192.168.10.50:8000`
- Demo backend: `https://demo.example.com`

Scan the QR code with Expo Go, or press `w` to open in browser.

### 3) Web (optional)

```bash
cd /g/UutisAnkka/frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Open `http://127.0.0.1:5173`.

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check |
| POST | `/api/ingest` | Trigger RSS fetch manually |
| GET | `/api/briefing?limit=10` | Top-ranked articles for current preferences |
| GET | `/api/briefing/random?limit=10` | Random article selection |
| GET | `/api/preferences` | Get user preference profile |
| PUT | `/api/preferences` | Update preferences and re-score |
| POST | `/api/feedback` | Submit swipe feedback for an article |
| GET | `/api/history?limit=100` | Swipe history |
| GET | `/api/metrics?limit=10` | Acceptance rate and feedback stats |
| POST | `/api/admin/reenrich` | Re-score all articles in background |
| POST | `/api/admin/resummarize` | Reset and regenerate all summaries |
| GET | `/api/admin/reenrich/status` | Background job status |
