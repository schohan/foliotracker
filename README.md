# FolioTracker

AI portfolio and stock research platform built on [Google ADK](https://adk.dev/).

Product requirements: [docs/PRD.md](docs/PRD.md)  
Architecture: [docs/architecture.md](docs/architecture.md)  
Implementation status: [docs/implementation-status.md](docs/implementation-status.md)

## Layout

```
app/                 # ADK entrypoint, API, agents, tools, services, schemas
web/                 # Svelte 5 watchlist dashboard (Vite)
docs/                # PRD, architecture, implementation tracker
```

## Setup

```bash
# Python (uv recommended)
uv sync --extra dev
cp .env.example .env   # add GOOGLE_API_KEY; optional ALPHA_VANTAGE_API_KEY

# Dashboard UI
cd web && npm install && cd ..
```

## Run

### Watchlist dashboard (recommended for dogfood)

Terminal 1 — API:

```bash
uv run uvicorn app.api.main:app --reload --port 8000
```

Terminal 2 — UI:

```bash
cd web && npm run dev
```

Open http://localhost:5173 — add held/watched tickers, refresh, open detail panel.

### ADK chat (single-ticker)

```bash
adk web
# or
adk run app
```

Ask the agent to analyze a ticker (e.g. `Analyze NVDA`). Uses `analyze_ticker` → `Phase0Result` JSON.

### Tests / evals

```bash
uv run pytest tests/unit          # CI default
python -m evaluations.phase0.run  # on-demand LLM evals (needs GOOGLE_API_KEY)
```

## Design principles

- **Agents** reason; they do not call HTTP APIs directly
- **Tools** fetch structured data
- **Services** own calculations (CAGR, DCF, scores)
- **Schemas / Evidence** are the contracts between layers
- Dashboard renders `Phase0Result` — never invents metrics
