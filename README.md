# FolioTracker

AI portfolio and stock research platform built on [Google ADK](https://adk.dev/).

Architecture: [docs/architecture.md](docs/architecture.md)  
Implementation status: [docs/implementation-status.md](docs/implementation-status.md)

## Layout

```
app/                 # ADK entrypoint + capability packages (agents, tools, workflows, services, schemas)
docs/                # Architecture + implementation tracker
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install .
cp .env.example .env   # add GOOGLE_API_KEY
```

## Run

From the repo root:

```bash
adk web
# or
adk run app
```

Ask the agent to analyze a ticker (e.g. `Analyze NVDA`). Phase 0 calls `analyze_ticker`, which runs Yahoo → evidence → cited thesis, with local TTL cache.

### Tests / evals

```bash
pytest tests/unit          # CI default
python -m evaluations.phase0.run   # on-demand LLM evals (needs GOOGLE_API_KEY)
```

## Design principles

- **Agents** reason; they do not call HTTP APIs directly
- **Tools** fetch structured data
- **Services** own calculations (CAGR, DCF, scores)
- **Schemas / Evidence** are the contracts between layers
