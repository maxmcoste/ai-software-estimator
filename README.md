# AI Software Estimator

An AI-powered web application that estimates software projects using the **Core & Satellites** model and the Claude API. Upload your requirements, get a detailed manday + cost breakdown in seconds.

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-green)
![Claude](https://img.shields.io/badge/Claude-claude--opus--4--6-purple)

---

## Features

- **Structured estimates** — Core (FCU) + 5 Satellites: PM, Architecture, Security, UX, QA
- **GitHub analysis** — optionally point to a repo so Claude can distinguish existing vs. new work
- **Custom model support** — upload your own estimation model `.md` file to override the default
- **Financial breakdown** — configurable manday rate and currency
- **Downloadable Markdown report** — ready to attach to a proposal
- **Dark-themed single-page UI** — no page reloads, live progress polling

---

## Architecture

```
Estimate/
├── EstimateModel/
│   └── Modello di Stima.md     # Default Core & Satellites model (Italian)
├── app/
│   ├── main.py                 # FastAPI app
│   ├── config.py               # pydantic-settings
│   ├── dependencies.py         # DI helpers
│   ├── api/
│   │   ├── routes.py           # POST /api/estimate · GET /status · GET /report
│   │   └── schemas.py          # Pydantic request/response models
│   ├── core/
│   │   ├── claude_client.py    # Anthropic SDK wrapper + tool schema
│   │   ├── github_client.py    # Repo fetching + context management
│   │   ├── estimator.py        # Job orchestration (in-memory store)
│   │   └── report_generator.py # Jinja2 → Markdown report
│   ├── models/
│   │   └── estimate.py         # Pydantic domain models
│   └── templates/
│       ├── index.html          # Single-page web UI
│       └── report_template.md.j2
├── static/
│   ├── style.css
│   └── app.js
└── reports/                    # Generated reports (gitignored)
```

---

## Getting Started

### 1. Clone and install

```bash
git clone https://github.com/maxmcoste/ai-software-estimator.git
cd ai-software-estimator
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
```

Edit `.env` and set:

```env
ANTHROPIC_API_KEY=sk-ant-...
GITHUB_TOKEN=ghp_...          # optional, for private repos
```

### 3. Run

```bash
uvicorn app.main:app --reload
```

Open [http://localhost:8000](http://localhost:8000).

---

## How It Works

1. **Submit** — upload (or paste) a Markdown requirements document
2. **Analyze** — Claude reads your requirements + optional GitHub codebase
3. **Estimate** — Claude calls the `produce_estimate` tool, returning a validated JSON breakdown
4. **Report** — financial post-processing (mandays × rate) and Jinja2 rendering produce a Markdown report
5. **Download** — the report is displayed in-page and available as a `.md` download

### Core & Satellites Model

| Component | What it measures |
|:---|:---|
| **Core** | Functional complexity: data entities (CRUD) + API integrations + business logic |
| **PM & Orchestration** | Calendar-based governance cost, team complexity |
| **Solution Architecture** | Design blueprints, environment setup, FinOps |
| **Cybersecurity** | Attack surface, compliance gates (GDPR, ISO…) |
| **Digital Experience** | User journey complexity, accessibility (WCAG 2.1) |
| **Quality Assurance** | Verification points, criticality tier, performance tests |

### Structured Output

Claude is forced to call the `produce_estimate` tool via `tool_choice={"type":"any"}`, guaranteeing structured JSON that is validated against Pydantic models before any further processing.

---

## API Reference

| Method | Endpoint | Description |
|:---|:---|:---|
| `POST` | `/api/estimate` | Submit estimation job (multipart form) |
| `GET` | `/api/estimate/{job_id}/status` | Poll job status |
| `GET` | `/api/estimate/{job_id}/report` | Download Markdown report |

### POST `/api/estimate` form fields

| Field | Type | Required | Default |
|:---|:---|:---|:---|
| `requirements_file` | file | ✓ (or text) | — |
| `requirements_text` | string | ✓ (or file) | — |
| `estimation_model_file` | file | — | built-in model |
| `github_url` | string | — | — |
| `github_token` | string | — | env `GITHUB_TOKEN` |
| `manday_cost` | number | — | `500` |
| `currency` | string | — | `EUR` |

---

## Requirements

- Python 3.11+
- [Anthropic API key](https://console.anthropic.com/)
- GitHub token (optional, for private repo analysis)

---

## License

MIT
