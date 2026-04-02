# Project: Dynamic Cognitive Orchestrator（推演局）

## Mission
A multi-agent debate system. Users input any topic, the system generates isolated virtual agents who analyze it from their own perspectives, then a "Director" synthesizes a structured truth report.

## Current state (already built — DO NOT recreate from scratch)
- `backend/main.py` — FastAPI backend with SSE streaming. Reads prompts from files.
- `frontend/index.html` — Dark-themed HTML/JS frontend with module toggles
- `prompts/system.md` — Flagship system prompt (DO NOT overwrite unless asked)
- `prompts/runtime.md` — Per-request variable template
- `schemas/analysis.json` — Structured output JSON schema
- `evals/cases.jsonl` — 10 test topic cases
- `evals/rubric.md` — 100-point scoring rubric
- `.env` — API key and base URL (DO NOT touch)
- `requirements.txt` — Python dependencies

## Architecture rules (non-negotiable)
- NEVER hardcode prompts inside Python code — always read from `prompts/` files
- NEVER overwrite `prompts/system.md` or `.env` unless explicitly instructed
- Frontend talks to backend at `http://localhost:8000`
- Backend uses SSE streaming (text/event-stream)
- All user-facing text is Simplified Chinese
- Keep changes minimal — don't refactor what's working

## API contract
POST /api/analyze accepts:
  topic, model, depth, audience, agent_count, active_modules (array), focus_perspectives, context, extra_instructions

GET /api/health → {"status": "ok"}
GET /api/modules → list of enhancement modules

## How to run
```bash
pip install -r requirements.txt
python backend/main.py
# Then open frontend/index.html in browser
```

## When asked to fix bugs
1. Read the relevant file first
2. Make the smallest change that fixes the issue
3. Don't change anything unrelated
4. Report exactly what you changed

## When asked to add features
1. Check if it belongs in backend, frontend, or prompts
2. Prompt changes go in prompts/system.md or prompts/runtime.md
3. Schema changes go in schemas/analysis.json
4. Never add new dependencies without asking first

## Code style
- Python: simple, readable, no over-engineering
- JS: vanilla JS only, no frameworks
- Comments in Chinese where helpful for the user
