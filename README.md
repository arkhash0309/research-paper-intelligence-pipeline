# Research Paper Intelligence Pipeline

An AI-powered tool that autonomously searches academic databases, extracts key findings, and generates structured literature reviews — powered by a custom MCP server and OpenAI.

```
┌─────────────────────────────────────────────────────┐
│                   Browser (React)                   │
│   SearchBar → PaperCards → Review → History         │
└────────────────────┬────────────────────────────────┘
                     │ HTTP (Axios, port 5173 → proxy)
┌────────────────────▼────────────────────────────────┐
│              FastAPI Backend  :8000                  │
│   /api/research/{start,analyse,synthesise,history}  │
└────────────────────┬────────────────────────────────┘
                     │ MCP over stdio (subprocess)
┌────────────────────▼────────────────────────────────┐
│              MCP Server (FastMCP)                   │
│  search_arxiv · search_semantic_scholar             │
│  extract_key_findings · identify_research_gaps      │
│  synthesise_literature_review · save_review         │
└──────────┬────────────────────────┬─────────────────┘
           │                        │
    arXiv API             OpenAI API (ChatGPT)
    Semantic Scholar API  (synthesis tools)
```

---

## Prerequisites

| Tool    | Version |
|---------|---------|
| Python  | 3.11+   |
| Node.js | 18+     |
| pip     | latest  |
| npm     | latest  |

---

## Setup

### 1. Clone the project and create a virtual environment

```bash
git clone https://github.com/arkhash0309/research-paper-intelligence-pipeline.git
cd research-paper-intelligence-pipeline

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
```

### 2. Set up the MCP server

```bash
cd mcp_server
pip install -r requirements.txt

# Create your .env from the example
cp .env.example .env
# Edit .env and fill in your OPENAI_API_KEY
# (a SEMANTIC_SCHOLAR_API_KEY is optional but strongly recommended)
```

### 3. Set up the FastAPI backend

```bash
cd ../backend
pip install -r requirements.txt   # also installs the MCP server's requirements

# Create backend .env (defaults are fine for local dev)
cp .env.example .env
```

> The backend spawns the MCP server with its own Python interpreter, so install
> both requirement files into the **same** environment.

### 4. Set up the React frontend

```bash
cd ../frontend
npm install
```

---

## Running the app

You need **two terminal windows** (the MCP server is spawned automatically as a subprocess by the backend — no third terminal needed).

**Terminal 1 — FastAPI backend**
```bash
cd research-paper-intelligence-pipeline/backend
uvicorn main:app --reload --port 8000
```

**Terminal 2 — Vite dev server**
```bash
cd research-paper-intelligence-pipeline/frontend
npm run dev
```

Then open [http://localhost:5173](http://localhost:5173) in your browser.

---

## Usage walkthrough

1. Type a research topic in the search bar (e.g. *"transformer attention mechanisms"*)
2. Choose how many papers per source (5–20) and click **Find Papers**
3. The pipeline fetches papers from arXiv and Semantic Scholar in parallel and removes duplicates. If one source is unavailable (e.g. Semantic Scholar rate limiting), the run continues with the other source and shows a warning
4. Paper cards appear with expandable abstracts and links
5. The pipeline automatically continues to **Analyse** (GPT extracts themes & findings) and **Synthesise** (GPT writes the review)
6. The finished review renders as formatted Markdown, with inline author–year citations and a References list built from the retrieved papers, plus Copy and Download buttons
7. If a step fails, click **Retry** to resume from that step without searching again
8. All reviews are auto-saved — browse them at **Saved Reviews** in the top nav (or click the saved filename under the review)

---

## Project structure

```
research-paper-intelligence-pipeline/
├── mcp_server/           # FastMCP server — 9 registered tools
│   ├── server.py         # Entry point + tool registrations
│   ├── tools/
│   │   ├── arxiv_tool.py              # arXiv Atom API
│   │   ├── semantic_scholar_tool.py   # Semantic Scholar Graph API
│   │   ├── synthesis_tool.py          # OpenAI API calls (findings, gaps, review)
│   │   └── save_tool.py               # JSON persistence in storage/reviews/
│   ├── .env.example
│   └── requirements.txt
│
├── backend/              # FastAPI REST API
│   ├── main.py           # App factory + CORS + error handling
│   ├── routers/
│   │   └── research.py   # 5 endpoints wiring MCP tools (+ paper normalisation/dedup)
│   ├── services/
│   │   └── mcp_client.py # MCP stdio client
│   ├── models/
│   │   └── schemas.py    # Pydantic v2 request/response models
│   ├── .env.example
│   └── requirements.txt
│
├── frontend/             # React + Vite + Tailwind
│   └── src/
│       ├── App.jsx
│       ├── api/researchApi.js
│       ├── hooks/useResearch.js
│       ├── components/   # SearchBar, PaperCard, LiteratureReview, …
│       └── pages/        # HomePage, ReviewPage
│
├── storage/reviews/      # Auto-created; holds saved review JSON files
├── .mcp.json             # MCP server registration for Claude Code
└── README.md
```

---

## Configuration

The backend automatically loads `mcp_server/.env` so API keys are forwarded to the MCP subprocess — you only need to set them once.

| Variable | Where | Required | Description |
|----------|-------|----------|-------------|
| `OPENAI_API_KEY` | `mcp_server/.env` | yes | Used by the analysis and synthesis tools |
| `OPENAI_MODEL` | `mcp_server/.env` | no | Chat model (default `gpt-5.4`) |
| `SEMANTIC_SCHOLAR_API_KEY` | `mcp_server/.env` | no | Raises Semantic Scholar rate limits — recommended for demos |
| `CORS_ORIGINS` | `backend/.env` | no | Comma-separated allowed origins (default `http://localhost:5173`) |
| `MCP_TOOL_TIMEOUT` | `backend/.env` | no | Seconds per search/storage tool call (default 60) |
| `MCP_LLM_TOOL_TIMEOUT` | `backend/.env` | no | Seconds per model-backed tool call (default 270) |

---

## Troubleshooting

- **"Semantic Scholar rate limit exceeded"** — the unauthenticated pool is shared and often throttled. The run continues with arXiv results; add a `SEMANTIC_SCHOLAR_API_KEY` to avoid it.
- **`No module named 'mcp.server.fastmcp'`** — mcp 2.x is installed. Reinstall with `pip install -r backend/requirements.txt`, which pins `mcp<2`.
- **"OPENAI_API_KEY environment variable is not set"** — create `mcp_server/.env` from `.env.example` and restart uvicorn.
- **A step timed out** — try fewer papers per source, or raise `MCP_LLM_TOOL_TIMEOUT`, then click **Retry**.
