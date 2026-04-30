# Research Paper Intelligence Pipeline

An AI-powered tool that autonomously searches academic databases, extracts key findings, and generates structured literature reviews — powered by a custom MCP server and OpeanAI.

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

### 1. Clone / unzip the project

```bash
cd research-pipeline
```

### 2. Set up the MCP server

```bash
cd mcp_server
pip install -r requirements.txt

# Create your .env from the example
cp .env.example .env
# Edit .env and fill in your OPENAI_API_KEY
```

### 3. Set up the FastAPI backend

```bash
cd ../backend
pip install -r requirements.txt

# Create backend .env (defaults are fine for local dev)
cp .env.example .env
```

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
cd research-pipeline/backend
uvicorn main:app --reload --port 8000
```

**Terminal 2 — Vite dev server**
```bash
cd research-pipeline/frontend
npm run dev
```

Then open [http://localhost:5173](http://localhost:5173) in your browser.

---

## Usage walkthrough

1. Type a research topic in the search bar (e.g. *"transformer attention mechanisms"*)
2. Choose how many papers per source (5–20) and click **Find Papers**
3. The pipeline fetches papers from arXiv and Semantic Scholar in parallel
4. Paper cards appear with expandable abstracts and links
5. The pipeline automatically continues to **Analyse** (GPT extracts themes & findings) and **Synthesise** (GPT writes the review)
6. The finished review renders as formatted Markdown with Copy and Download buttons
7. All reviews are auto-saved — browse them at **Saved Reviews** in the top nav

---

## Project structure

```
research-pipeline/
├── mcp_server/           # FastMCP server — 7 registered tools
│   ├── server.py         # Entry point + tool registrations
│   ├── tools/
│   │   ├── arxiv_tool.py              # arXiv Atom API
│   │   ├── semantic_scholar_tool.py   # Semantic Scholar Graph API
│   │   ├── paper_parser_tool.py       # Normalise + deduplicate papers
│   │   ├── synthesis_tool.py          # OpenAI API calls (findings, gaps, review)
│   │   └── save_tool.py               # JSON persistence in storage/reviews/
│   └── requirements.txt
│
├── backend/              # FastAPI REST API
│   ├── main.py           # App factory + CORS
│   ├── routers/
│   │   └── research.py   # 5 endpoints wiring MCP tools
│   ├── services/
│   │   └── mcp_client.py # MCP stdio client
│   ├── models/
│   │   └── schemas.py    # Pydantic v2 request/response models
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

The backend automatically loads `mcp_server/.env` so API keys are forwarded to the MCP subprocess — you only need to set them once.
