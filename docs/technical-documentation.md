# NovaBrew Command Center — Technical Documentation

## System Overview

The NovaBrew Command Center is a multi-agent marketing automation system. A user types a campaign brief, and 6 AI agents coordinate to research, write, validate, publish, and report — all governed by brand safety policies.

---

## Architecture

```
User (CMO)
    |
    v
[Command Center UI] — Next.js 15, React 19, TailwindCSS
    |
    | POST /api/ai/chat
    v
[FastAPI Backend] — Python 3.11, SQLAlchemy, PostgreSQL
    |
    | Supervity Streaming API
    v
[Supervity Auto Platform] — 6 AI Agents
    |
    |--- Dropbox (docs, policies, logs)
    |--- LinkedIn (publish posts)
    |--- Blog API (publish articles)
    |--- Microsoft Outlook (email notifications)
    |--- Slack (real-time alerts)
    |--- AI Image Generation (campaign visuals)
```

---

## Agent Architecture

| Agent | Role | Integrations |
|-------|------|-------------|
| Orchestrator | Coordinates all agents, manages flow | Outlook, Slack, Dropbox |
| Trend Analyser | Scores topic relevance | Dropbox |
| Content Adapter | Writes channel-adapted content + generates image | Dropbox, AI Image Gen |
| Brand Safety Checker | Validates content against policies | Dropbox |
| Social Scheduler | Publishes to LinkedIn, Blog; drafts email | LinkedIn, Blog API, Outlook |
| Knowledge Base | RAG — retrieves brand docs for grounding | Dropbox |

---

## Execution Flow

1. User submits brief via AI Manager chat
2. Backend calls Supervity streaming API with Orchestrator workflow ID
3. Orchestrator executes steps sequentially:
   - Step 1: Trend Analysis (relevance scoring)
   - Step 2: Content Creation (multi-channel + image)
   - Step 3: Brand Safety Check (policy enforcement)
   - Step 4: Publishing (LinkedIn, Blog, Email)
   - Step 5: Exception Handling (flag violations)
   - Step 6: Notification (Slack, Outlook, Dropbox log)
4. Backend parses SSE response, stores campaign + traces in PostgreSQL
5. Frontend displays results in chat, campaigns page, and insights

---

## API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | /api/ai/chat | Trigger campaign or query knowledge base |
| GET | /api/ai/campaigns | List all campaigns |
| GET | /api/ai/campaigns/{id} | Campaign details with execution trace |
| GET | /api/ai/campaigns/sync | Fetch runs from Supervity |
| GET | /api/ai/workbench | List pending exceptions |
| POST | /api/ai/workbench/{id}/resolve | Approve/reject exception |
| GET | /api/ai/policies | List brand safety policies |
| POST | /api/ai/policies | Create policy (syncs to Dropbox) |
| DELETE | /api/ai/policies/{id} | Remove policy |
| GET | /api/ai/insights | Aggregated metrics |
| POST | /api/ai/knowledge | Direct knowledge base query |

---

## Data Flow

### Campaign Data
- Stored in PostgreSQL `campaigns` table
- Result JSON contains full Supervity response (activity runs, outputs)
- Execution traces stored in `execution_traces` table

### Policies
- Stored in PostgreSQL `policies` table
- Synced to Dropbox as CSV files on create/update/delete
- Brand Safety Checker reads from Dropbox at runtime

### Exceptions
- Extracted from Orchestrator's Step 5 output
- Stored in `campaign_exceptions` table
- Displayed in Workbench page with approve/reject actions

---

## Supervity API Integration

- Endpoint: `POST /api/v1/workflow-runs/execute/stream`
- Auth: Bearer token (Keycloak)
- Format: multipart/form-data
- Response: Server-Sent Events (SSE) stream
- Backend parses SSE to extract: runId, activity runs, step outputs, final result

Additional APIs used:
- `GET /api/v1/workflow-runs` — list past runs
- `GET /api/v1/workflow-runs/:runId` — run details
- `GET /api/v1/user-forms` — pending human reviews
- `POST /api/v1/user-forms/:id/submit` — submit review decision

---

## Intent Detection

The chat endpoint routes messages based on keywords:
- Campaign keywords (create, launch, campaign, publish) → Orchestrator
- Knowledge keywords (what is, brand voice, ingredients) → Knowledge Base agent
- Insights keywords (show insights, metrics, performance) → Local DB query
- Everything else → Help response

---

## Brand Safety System

Policies are enforced at two levels:
1. Dropbox CSV files (read by Brand Safety Checker agent at runtime)
2. PostgreSQL table (managed via Command Center UI)

When a policy is created/updated in the UI:
- Saved to PostgreSQL
- Synced to Dropbox via Dropbox API
- Next campaign run reads the updated file

Policy types: banned_term, brand_voice_rule, posting_limit

---

## Infrastructure

```
Docker Compose (3 services):
- postgres:15-alpine (port 5432)
- backend (FastAPI, port 8001)
- frontend (Next.js, port 3001)
```

Database migrations managed by Alembic. Tables:
- campaigns, campaign_exceptions, execution_traces, policies
- audit_logs, items, settings (from template)

---

## Key Design Decisions

1. SSE streaming over polling — Supervity's execute endpoint is synchronous (blocks until complete). Streaming returns results as they happen.

2. Local DB + Supervity API — Campaign results stored locally for fast UI rendering. Supervity API used for sync and human review forms.

3. Dynamic policies via Dropbox — Policies editable from UI, synced to Dropbox CSV. Agents read fresh files every run. No redeployment needed.

4. Exception routing — Flagged content never publishes. Routes to Workbench for human decision. Slack notification ensures visibility.

5. Image generation on Auto — Built-in capability, no external API needed. Image URL passed through Content Adapter to Social Scheduler.
