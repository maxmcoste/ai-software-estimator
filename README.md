# AI Software Estimator ⚠️ Alpha

> **This project is in active development and is not yet production-ready.** APIs, data formats, and workflows may change between commits. Use for evaluation and experimentation only.

An AI-powered web application that produces detailed software project estimates using the **Core & Satellites** model and the Anthropic Claude API. Submit a requirements document, optionally enrich the analysis with a GitHub repository, and receive a structured breakdown of mandays and costs — split across functional development and five governance satellites.

![Alpha](https://img.shields.io/badge/status-alpha-orange)
![Python](https://img.shields.io/badge/Python-3.11+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-green)
![Claude](https://img.shields.io/badge/Claude-claude--opus--4--6-purple)
![License](https://img.shields.io/badge/license-Apache%202.0-blue)

---

## Table of Contents

1. [Features](#features)
2. [The Core & Satellites Model](#the-core--satellites-model)
3. [Project Structure](#project-structure)
4. [Getting Started](#getting-started)
5. [User Workflows](#user-workflows)
6. [AI Architecture](#ai-architecture)
7. [API Reference](#api-reference)
8. [Data Persistence](#data-persistence)
9. [Configuration](#configuration)
10. [Requirements](#requirements)

---

## Features

| Feature | Description |
|:---|:---|
| **Structured estimation** | Core (FCU) + 5 Satellites, each with independent metrics. Satellites are only activated when genuinely justified by the project. |
| **GitHub codebase analysis** | Point to any public or private repo — the app fetches the file tree, reads source and config files (up to 80 k chars), and passes the summary to Claude so it can distinguish existing from new work. |
| **Custom estimation model** | Override the built-in model by uploading any `.md` file. Useful for client-specific methodologies or translated versions of the model. |
| **Financial breakdown** | Configurable manday rate and currency (EUR, USD, GBP, CHF). All costs are computed as `mandays × rate` after the AI returns its structured output. |
| **AI chat refinement** | After an estimate is generated, a chat panel lets you ask Claude to explain any choice or override specific values. The report refreshes live when changes are applied. |
| **Re-run estimation** | From the results page, re-run the estimation with a new model file, updated requirements, or both — GitHub analysis is reused automatically. |
| **Save & History** | Save any estimate as a **draft** and access it later from the History page. Finalize a draft to freeze it permanently. |
| **Change a draft** | Open any saved draft for editing: refine the estimate via AI chat, edit or replace the requirements document, swap the estimation model, then sync the changes back to the draft with **Update draft**. |
| **Live progress log** | An activity log and elapsed timer keep the user informed throughout the 30–90 second Claude call. |
| **Downloadable Markdown report** | Every estimate produces a `.md` report with executive summary table, per-satellite detail, and reasoning block. |

---

## The Core & Satellites Model

The application implements the **"Core & Satellites" post-GenAI estimation model**, which decouples the cost of *building* (Core) from the cost of *guaranteeing* (Satellites). This reflects the reality that AI-assisted development reduces coding time but does not reduce governance, security, or quality assurance complexity.

### Core — Functional Complexity Units (FCU)

The Core estimate is driven by **functional density**, not hours:

| Driver | Description |
|:---|:---|
| **Data Entities** | Each entity requiring CRUD operations is enumerated individually. A simple entity ≈ 1–3 mandays; a complex one ≈ 3–6. |
| **API Integrations** | Each external integration is listed with direction (inbound / outbound / bidirectional) and complexity (simple / moderate / complex). |
| **Business Logic** | A flat manday allocation for orchestration, rules, and workflow logic that doesn't map to a single entity. |
| **Scalability Multiplier** | Low (<1k users/month) = 1.0×, Medium (1k–50k) = 1.3×, High (>50k or critical) = 1.8×. Applied to the base FCU sum. |
| **SPIKEs** | Fixed add-ons for technology unknowns or legacy integrations requiring R&D investigation. |

**Formula:** `Core Total = (Base FCU × Scalability Multiplier) + Σ SPIKE mandays`

### The Five Satellites

Each satellite is independent of code volume and is only activated when the project genuinely requires it.

| Satellite | Metric | Key Drivers |
|:---|:---|:---|
| **PM & Orchestration** | Calendar-Based Service Unit (CBSU) | Project duration, team size, multi-vendor factor |
| **Solution Architecture & Infra** | Blueprint + ECU + FinOps | Number of external systems, environment complexity, cloud governance |
| **Cybersecurity & Compliance** | Attack surface + Security Gates | Data sensitivity tier (basic / standard / critical), GDPR/ISO compliance |
| **Digital Experience (UX/UI)** | User Journey Complexity (UJC) | Flow complexity (linear / transactional / expert), WCAG 2.1 accessibility |
| **Quality Assurance** | Verification Points × Criticality | Business logic checkpoints, criticality tier (1–3), performance testing |

### Typical Cost Distribution

| Component | Typical Share |
|:---|:---|
| Core (AI-Assisted) | 30–40% |
| Governance Satellites (PM + Architecture) | 25–30% |
| Quality Satellites (QA + Cybersecurity + DX) | 30–40% |

---

## Project Structure

```
Estimate/
├── EstimateModel/
│   └── Modello di Stima.md          # Built-in Core & Satellites model (Italian)
│
├── app/
│   ├── main.py                      # FastAPI app factory, routes /, /history
│   ├── config.py                    # pydantic-settings (API keys, paths)
│   ├── dependencies.py              # Cached get_settings()
│   │
│   ├── api/
│   │   ├── routes.py                # All HTTP endpoints
│   │   └── schemas.py               # Pydantic request/response models
│   │
│   ├── core/
│   │   ├── claude_client.py         # Anthropic SDK wrapper, tool schema, chat function
│   │   ├── github_client.py         # GitHub tree fetch, context truncation
│   │   ├── estimator.py             # In-memory job store, run_estimation()
│   │   ├── report_generator.py      # Jinja2 → Markdown report
│   │   └── saves.py                 # JSON-file persistence for saved estimates
│   │
│   ├── models/
│   │   └── estimate.py              # Pydantic domain models (EstimateResult, FinancialSummary…)
│   │
│   └── templates/
│       ├── index.html               # Main estimation page
│       ├── history.html             # Saved estimates history page
│       └── report_template.md.j2   # Jinja2 Markdown report template
│
├── static/
│   ├── style.css                    # Dark theme (CSS variables, responsive)
│   ├── app.js                       # Main page: form, polling, chat, save, re-run, change
│   └── history.js                   # History page: list, detail view, change, finalize, delete
│
├── reports/                         # Generated .md reports — ephemeral, gitignored
├── saves/                           # Persisted estimates as JSON — gitignored
├── .env.example
├── pyproject.toml
└── requirements.txt
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

Edit `.env`:

```env
ANTHROPIC_API_KEY=sk-ant-...    # required
GITHUB_TOKEN=ghp_...            # optional — needed for private repos
```

### 3. Run

```bash
uvicorn app.main:app --reload
```

Open [http://localhost:8000](http://localhost:8000).

To use a different port:

```bash
uvicorn app.main:app --reload --port 8080
```

---

## User Workflows

### Generating an Estimate

1. **Requirements** — upload a `.md` / `.txt` file or paste the text directly into the form.
2. **Estimation model** — the built-in Core & Satellites model is used by default. Uncheck "Use default model" to upload a custom `.md` file.
3. **GitHub repository** — optionally enter a public or private repo URL. For private repos, supply a Personal Access Token.
4. **Financial parameters** — set the manday rate and currency.
5. Click **Generate Estimate**.

The progress panel shows a live activity log and elapsed timer while Claude works. When complete, the report renders in-page.

### Refining with AI Chat

Once the report is displayed, a **"Refine with AI"** chat panel appears on the right:

- **Ask a question** — "Why is the Core 42 mandays?" — Claude explains the reasoning. The report is unchanged.
- **Request a change** — "Reduce QA to 5 mandays" or "Deactivate the DX satellite" — Claude calls the `produce_estimate` tool with updated values. The report refreshes live and the chat shows a diff summary (e.g., `QA: 8.0 → 5.0 mandays`).

`Enter` sends a message; `Shift+Enter` inserts a newline.

### Re-running the Estimation

In the result header, click **Re-run estimation** to open the re-run panel. You can:

- **Change the estimation model** — upload a new `.md` model file.
- **Change the requirements** — edit the requirements text inline or load a new file via the Requirements panel (see below).
- **Change both** — combine a new model with updated requirements in the same re-run.

The model file is optional — if omitted the current model is reused. GitHub analysis is always reused; no re-fetch is required.

### Saving and Managing Estimates

1. Click **Save** in the result header → enter a name → **Save draft**.
2. Navigate to [http://localhost:8000/history](http://localhost:8000/history) to see all saved estimates.
3. Click a card to open the full report.
4. From the detail view:
   - **Download .md** — saves the report file locally.
   - **Change** — opens the draft for editing (drafts only — see below).
   - **Finalize** — locks the estimate permanently. Finalized estimates cannot be modified or deleted.
   - **Delete** — removes the draft (not available for finalized estimates).

| Action | Draft | Final |
|:---|:---:|:---:|
| View report | ✓ | ✓ |
| Download .md | ✓ | ✓ |
| Change | ✓ | ✗ |
| Finalize | ✓ | — |
| Delete | ✓ | ✗ |

### Changing a Draft

Clicking **Change** on a draft in the History page opens it in an editing session on the main page:

- The **Estimation Report** is displayed immediately — no re-estimation needed.
- The **Refine with AI** chat panel is ready to use. Ask Claude to adjust any value; the report refreshes live.
- The **Requirements** panel (below the report header) shows the saved requirements. Click **Edit** to switch to an editable textarea where you can modify the text directly or click **Load new file…** to replace it entirely with a new `.md` file. Click **Preview** to return to the rendered view (a `●` indicator appears when the requirements have been modified).
- Click **Re-run estimation** to re-run Claude with the current or updated requirements and/or a new model file.
- Click **Update draft** to sync all changes (chat edits, re-run results) back to the saved draft file.

---

## AI Architecture

### Structured Output via Tool Use

Claude is called with `tool_choice={"type":"any"}` for initial estimates, which forces it to call the `produce_estimate` tool and return a fully structured JSON object. This guarantees a parseable, Pydantic-validated response with no free-form prose.

For chat refinements, `tool_choice={"type":"auto"}` is used so Claude can choose between:
- Responding with plain text (for explanations and questions)
- Calling `produce_estimate` (for changes), which triggers a full report regeneration

### Prompt Design

**System prompt** (initial estimate):
- Expert estimator persona with 10 strict rules
- Enforces complete entity enumeration, correct multiplier application, and SPIKE identification
- Instructs Claude to use GitHub data to distinguish existing vs. new components

**User prompt** — three delimited sections:
1. `## ESTIMATION MODEL` — full model markdown verbatim
2. `## PROJECT REQUIREMENTS` — requirements document
3. `## CODEBASE ANALYSIS` — (optional) repo summary string

**Chat system prompt**:
- Always includes the current `EstimateResult` as JSON in the system prompt
- Instructs Claude to call the tool only for changes, never for questions
- Conversation history (text only) provides continuity across turns

### GitHub Context Management

| Limit | Value |
|:---|:---|
| Max total characters | 80,000 |
| Max lines per file | 200 |
| Priority order | `*.md` → source files → configs |
| Skipped directories | `node_modules`, `.git`, `dist`, `build`, `vendor`, `__pycache__` |

Files exceeding the line cap are truncated with a `[truncated]` marker. If the total cap is reached, a `[Repository summary truncated]` notice is appended. GitHub fetch failures are non-blocking — a warning is added to the report but estimation proceeds.

### Financial Post-Processing

All financial computation happens **after** Claude returns the structured estimate, keeping the AI focused on manday estimation only:

```
core_cost       = core.total_mandays × manday_rate
satellite_costs = {sat: sat.total_mandays × manday_rate  for each active satellite}
grand_mandays   = core.total_mandays + Σ active satellite mandays
grand_cost      = grand_mandays × manday_rate
```

### Retry Logic

The initial Claude call retries up to 3 times with exponential backoff (2s, 4s) on API errors or validation failures.

---

## API Reference

### Estimation

| Method | Endpoint | Description |
|:---|:---|:---|
| `POST` | `/api/estimate` | Submit a new estimation job |
| `GET` | `/api/estimate/{job_id}/status` | Poll job status and progress message |
| `GET` | `/api/estimate/{job_id}/report` | Download the generated `.md` report |
| `GET` | `/api/estimate/{job_id}/context` | Return requirements, model text, and save metadata for a job |
| `POST` | `/api/estimate/{job_id}/chat` | Send a chat message to refine the estimate |
| `POST` | `/api/estimate/{job_id}/rerun` | Re-run with optional new model and/or requirements |

#### `POST /api/estimate` — multipart form fields

| Field | Type | Required | Default |
|:---|:---|:---:|:---|
| `requirements_file` | file | ✓ or text | — |
| `requirements_text` | string | ✓ or file | — |
| `estimation_model_file` | file | — | built-in model |
| `github_url` | string | — | — |
| `github_token` | string | — | env `GITHUB_TOKEN` |
| `manday_cost` | number | — | `500` |
| `currency` | string | — | `EUR` |

#### `POST /api/estimate/{job_id}/rerun` — multipart form fields

All fields are optional. At least one change (model or requirements) should be provided; omitted fields fall back to the job's current values.

| Field | Type | Description |
|:---|:---|:---|
| `rerun_model` | file | New estimation model `.md` file |
| `rerun_requirements_file` | file | New requirements file (overrides text field) |
| `rerun_requirements_text` | string | Updated requirements as plain text |

#### `POST /api/estimate/{job_id}/chat` — JSON body

```json
{ "message": "Reduce QA to 5 mandays and deactivate the DX satellite." }
```

Response includes `reply`, `estimate_updated` (bool), and `report_markdown` (new report if updated).

#### `GET /api/estimate/{job_id}/status` — response

```json
{ "status": "running", "progress_message": "Calling Claude API — this may take 30–90 seconds…" }
```

Status values: `pending` → `running` → `done` | `error`

### Saved Estimates

| Method | Endpoint | Description |
|:---|:---|:---|
| `POST` | `/api/saves` | Save the current estimate as a draft |
| `GET` | `/api/saves` | List all saved estimates (summary) |
| `GET` | `/api/saves/{save_id}` | Get full save detail including report markdown |
| `POST` | `/api/saves/{save_id}/open` | Load a draft into an in-memory job for editing; returns `job_id` |
| `PUT` | `/api/saves/{save_id}` | Update a draft with the current state of a job |
| `POST` | `/api/saves/{save_id}/finalize` | Finalize (lock) a draft |
| `DELETE` | `/api/saves/{save_id}` | Delete a draft (not allowed for finalized estimates) |

#### `POST /api/saves` — JSON body

```json
{ "job_id": "uuid", "name": "CRM Project v1.2" }
```

#### `PUT /api/saves/{save_id}` — JSON body

```json
{ "job_id": "uuid" }
```

Reads the current report, estimate data, and financials from the in-memory job and writes them to the save file. Returns the updated `SaveSummary`. Fails with `403` if the save is finalized.

#### `POST /api/saves/{save_id}/open` — response

```json
{ "job_id": "uuid", "save_id": "uuid", "name": "CRM Project v1.2" }
```

Creates a new in-memory job pre-populated with the saved estimate data. The returned `job_id` can be used immediately with the chat, rerun, and report endpoints.

---

## Data Persistence

Saves are stored as JSON files in the `saves/` directory (one file per estimate). No database is required.

```json
{
  "save_id": "uuid",
  "name": "CRM Project v1.2",
  "status": "draft",
  "created_at": "2026-02-28T10:00:00+00:00",
  "updated_at": "2026-02-28T11:30:00+00:00",
  "requirements_md": "...",
  "model_md": "...",
  "report_markdown": "...",
  "estimate_data": { ... },
  "financials_data": { ... }
}
```

`saves/*.json` and `reports/*.md` are gitignored. Both directories are auto-created on first use.

---

## Configuration

All settings are loaded from `.env` via `pydantic-settings`:

| Variable | Required | Default | Description |
|:---|:---:|:---|:---|
| `ANTHROPIC_API_KEY` | ✓ | — | Anthropic API key |
| `GITHUB_TOKEN` | — | `""` | GitHub PAT for private repos |
| `DEFAULT_MODEL_PATH` | — | `EstimateModel/Modello di Stima.md` | Path to built-in estimation model |
| `REPORTS_DIR` | — | `reports/` | Directory for generated report files |

---

## Requirements

- Python 3.11+
- [Anthropic API key](https://console.anthropic.com/)
- GitHub Personal Access Token (optional — only needed for private repositories)

### Python dependencies

```
fastapi, uvicorn[standard], anthropic, PyGithub,
pydantic, pydantic-settings, jinja2,
python-multipart, markdown2, python-dotenv, httpx
```

---

## License

Apache License 2.0 — see [LICENSE](LICENSE) for the full text.

Copyright 2026 Massimo Del Vecchio
