# NovaBrew Marketing Command Center

A multi-agent AI system that orchestrates marketing campaigns for NovaBrew, a D2C cold brew coffee brand. Built for the AutoPilot Hackathon Round 2.

## What It Does

One brief from the CMO triggers 6 AI agents that coordinate to: analyse trends, generate multi-channel content, enforce brand safety policies, publish to LinkedIn and Blog with AI-generated images, and notify the team on Slack. All in under 90 seconds.

## Architecture

- 6 AI Agents on Supervity Auto (Orchestrator + 5 Operators)
- Core Capability: Knowledge Base (RAG via Dropbox documents)
- Command Center: Next.js + FastAPI + PostgreSQL
- Integrations: Dropbox, LinkedIn, Blog API, Microsoft Outlook, Slack, AI Image Generation

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15, React 19, TailwindCSS, Radix UI |
| Backend | Python 3.11, FastAPI, SQLAlchemy, Alembic |
| Database | PostgreSQL 15 |
| Agent Platform | Supervity Auto |
| Infrastructure | Docker Compose |

## Setup

```bash
git clone https://github.com/OmPrakashMunda/AutoPilot-Hackathon-CC.git
cd AutoPilot-Hackathon-CC
cp .env.example .env
docker compose up --build -d
```

- App: http://localhost:3001
- API Docs: http://localhost:8001/api/docs

## Pages

- Dashboard — Campaign stats, agent status, quick actions
- Campaigns — Full history with published URLs and execution traces
- Workbench — Exception management (human-in-the-loop)
- AI Policies — Brand safety rules with Dropbox sync
- AI Insights — Agent performance and publishing stats
- AI Manager — Chat interface to trigger campaigns

## Team

Om Prakash Munda
