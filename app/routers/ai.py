# app/routers/ai.py
"""
AI Router — Full Supervity API integration.

Uses the complete Supervity API:
- POST /workflow-runs/execute — Trigger agents (non-streaming)
- GET /workflow-runs/:runId — Poll for results
- GET /workflow-runs — List all runs (campaign history)
- GET /workflow-runs/dashboard/:workflowId — Run stats
- GET /user-forms — List pending human approvals
- GET /user-forms/:formId — Get approval details
- POST /user-forms/:formId/submit — Submit approval decision
- POST /workflow-runs/cancel — Cancel running campaigns
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..models.campaign import Campaign, CampaignException, ExecutionTrace
from ..security import get_current_user

log = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI"])

# =============================================================================
# CONFIGURATION
# =============================================================================

SUPERVITY_BASE_URL = "https://auto-workflow-api.supervity.ai/api/v1"
SUPERVITY_TOKEN = "eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJCOVg3RVFFWE8td25ucjBJd3Vjbm5vQWlVcWdDM1JpNzh2aGMxMG9xTmJnIn0.eyJleHAiOjE3ODYxNjY3OTIsImlhdCI6MTc3ODM5MDc5MywianRpIjoiMGM2N2Y2MTktZDk3YS00ZjdhLTkwNWYtNGEyMDkwZGZmMDhlIiwiaXNzIjoiaHR0cHM6Ly9hdXRvLXNzby5zdXBlcnZpdHkuYWkvYXV0aC9yZWFsbXMvdGVjaGZvcmNlIiwiYXVkIjoiYWNjb3VudCIsInN1YiI6IjFiZDQxYjA5LTc5NWEtNGFiNS05NDY2LTIzYTJmMjdhZGE5MCIsInR5cCI6IkJlYXJlciIsImF6cCI6ImJvdC1tYWtlciIsInNpZCI6IjQyYjRmYWZlLTEwYzMtNGQ5Zi04NzEyLTk2ZGZkZmJlZGFmZSIsImFsbG93ZWQtb3JpZ2lucyI6WyJodHRwczovL2F1dG8uc3VwZXJ2aXR5LmFpIiwiKiJdLCJyZWFsbV9hY2Nlc3MiOnsicm9sZXMiOlsiZGVmYXVsdC1yb2xlcy10ZWNoZm9yY2UiLCJvZmZsaW5lX2FjY2VzcyIsInVtYV9hdXRob3JpemF0aW9uIl19LCJyZXNvdXJjZV9hY2Nlc3MiOnsiYWNjb3VudCI6eyJyb2xlcyI6WyJtYW5hZ2UtYWNjb3VudCIsIm1hbmFnZS1hY2NvdW50LWxpbmtzIiwidmlldy1wcm9maWxlIl19fSwic2NvcGUiOiJvcGVuaWQgcHJvZmlsZSBlbWFpbCIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwibmFtZSI6Ik9tIFByYWthc2ggTXVuZGEiLCJwcmVmZXJyZWRfdXNlcm5hbWUiOiJvbS5wcmFrYXNoMjYzMDRAZ21haWwuY29tIiwiZ2l2ZW5fbmFtZSI6Ik9tIFByYWthc2giLCJmYW1pbHlfbmFtZSI6Ik11bmRhIiwiZW1haWwiOiJvbS5wcmFrYXNoMjYzMDRAZ21haWwuY29tIn0.Z6JI37AB0IUPjhYu5QYBjQD4WJdPOJ1YZMXQP-UM3dNv_toyB8VsDzFNhISfpIG-Ov75i_6k9hCY0Jeh-F6Z6kmmlba8zdgtMSY6a525ffsHNBoKRuwwXCKVRyd9-BqdoYbVLmz6DgGZPtCtCDHPMzZjNLtMMunc_fgqzHNlNbqx-1F1wvi7-PO6UtEy1HEU-sXioO4REqkeHF56IASUn2975azxafuvVgsET-4BR_VfcAGBSaHJV4X2EDMLKH5RdVLqyLC-6y0DxhAFwg3hhCLbXWXBqNBz-XZyDoq-12t4PKW974eBksadxWDq4Pqvp-H6xKHfmVwKBEyR-V9reg"

# Workflow IDs
ORCHESTRATOR_WORKFLOW_ID = "019e31a4-a6bd-7000-ba76-fa56ee9f8d76"
KNOWLEDGE_BASE_WORKFLOW_ID = "019e305f-892a-7000-818c-9c38819db084"


# =============================================================================
# SCHEMAS
# =============================================================================


class ChatRequest(BaseModel):
    brief: str = ""
    message: str = ""
    channels: str = "linkedin, email, blog"
    product_focus: str = "NovaBrew Focus"
    urgency: str = "high"
    history: list = []
    context: dict = {}


class KnowledgeQuery(BaseModel):
    query: str


class CancelRequest(BaseModel):
    run_id: str


# =============================================================================
# SUPERVITY API CLIENT
# =============================================================================


def _get_headers():
    return {
        "Authorization": f"Bearer {SUPERVITY_TOKEN}",
        "x-source": "v1",
    }


def _get_json_headers():
    return {
        "Authorization": f"Bearer {SUPERVITY_TOKEN}",
        "Content-Type": "application/json",
    }


def _parse_sse_to_result(raw_text: str) -> dict:
    """
    Parse Supervity SSE stream into a structured result.
    Extracts: runId, status, activityRuns with outputs.
    """
    lines = raw_text.split("\n")
    current_event = None
    result = {"status": "unknown", "runId": "", "activityRuns": [], "outputs": {}}

    for line in lines:
        if line.startswith("event: "):
            current_event = line[7:].strip()
        elif line.startswith("data: ") and current_event:
            data_str = line[6:].strip()
            if not data_str or data_str == '{"content":"ping"}':
                continue

            try:
                data = json.loads(data_str)
            except json.JSONDecodeError:
                continue

            # Extract workflow run info (contains runId)
            if current_event == "workflow-run":
                content = data.get("content", {})
                if isinstance(content, dict):
                    if content.get("workflowRunId"):
                        result["runId"] = content["workflowRunId"]
                    if content.get("status"):
                        result["status"] = content["status"]

            # Extract completed step outputs
            elif current_event == "activity-run":
                content = data.get("content", {})
                if isinstance(content, dict) and content.get("status") == "completed" and content.get("kind") == "step":
                    step_id = content.get("stepId", "")
                    outputs = content.get("outputs", {})
                    output_str = outputs.get("output", "")
                    
                    # Try to parse step output for exceptions
                    if output_str and "exception" in step_id.lower():
                        try:
                            step_data = json.loads(output_str)
                            exceptions = step_data.get("exceptions", [])
                            if exceptions:
                                result["exceptions"] = exceptions
                        except json.JSONDecodeError:
                            pass
                    
                    result["activityRuns"].append({
                        "stepId": step_id,
                        "stepName": content.get("stepId", "").replace("_", " ").title(),
                        "status": "completed",
                        "kind": "step",
                        "outputs": outputs,
                        "startedAt": "",
                        "completedAt": "",
                    })

            # Extract final result
            elif current_event == "result":
                if data.get("success"):
                    workflow_run = data.get("workflowRun", {})
                    result["runId"] = workflow_run.get("id", result["runId"])
                    result["status"] = workflow_run.get("status", "completed")
                    # Use activity runs from final result if available
                    if workflow_run.get("activityRuns"):
                        result["activityRuns"] = workflow_run["activityRuns"]

    return result


async def supervity_execute(workflow_id: str, inputs: dict) -> dict:
    """
    Execute a workflow using the streaming endpoint.
    Parses the SSE stream and returns the final result with runId and outputs.
    """
    form_data = {"workflowId": workflow_id}
    for key, value in inputs.items():
        form_data[f"inputs[{key}]"] = str(value)

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{SUPERVITY_BASE_URL}/workflow-runs/execute/stream",
            headers=_get_headers(),
            data=form_data,
        )

    if response.status_code != 200:
        log.error(f"Supervity execute error: {response.status_code} — {response.text[:300]}")
        raise HTTPException(status_code=502, detail=f"Agent execution failed: {response.status_code}")

    # Parse SSE response to extract runId and final result
    return _parse_sse_to_result(response.text)


async def supervity_get_run(run_id: str) -> dict:
    """
    Get workflow run details by ID.
    Returns full run object with status, outputs, activity runs.
    """
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            f"{SUPERVITY_BASE_URL}/workflow-runs/{run_id}",
            headers=_get_json_headers(),
        )

    if response.status_code != 200:
        log.error(f"Supervity get run error: {response.status_code}")
        return {"status": "unknown", "error": response.text[:200]}

    return response.json()


async def supervity_poll_until_complete(run_id: str, max_wait: int = 120, interval: int = 3) -> dict:
    """
    Poll a workflow run until it reaches a terminal state.
    Returns the final run object.
    """
    elapsed = 0
    while elapsed < max_wait:
        run = await supervity_get_run(run_id)
        status = run.get("status", "unknown")

        if status in ("completed", "failed", "cancelled"):
            return run
        if status == "waiting":
            # Human review required — return immediately
            return run

        await asyncio.sleep(interval)
        elapsed += interval

    return {"status": "timeout", "runId": run_id, "error": f"Run did not complete within {max_wait}s"}


async def supervity_list_runs(workflow_id: str = None, page: int = 1, limit: int = 20) -> dict:
    """List workflow runs, optionally filtered by workflow ID."""
    params = {"page": page, "limit": limit}
    if workflow_id:
        params["workflowId"] = workflow_id

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            f"{SUPERVITY_BASE_URL}/workflow-runs",
            headers=_get_json_headers(),
            params=params,
        )

    if response.status_code != 200:
        return {"runs": [], "error": response.text[:200]}

    return response.json()


async def supervity_get_dashboard(workflow_id: str) -> dict:
    """Get dashboard counts for a workflow."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            f"{SUPERVITY_BASE_URL}/workflow-runs/dashboard/{workflow_id}",
            headers=_get_json_headers(),
        )

    if response.status_code != 200:
        return {}

    return response.json()


async def supervity_list_user_forms(page: int = 1, limit: int = 20, search: str = "") -> dict:
    """List pending human review forms (approvals)."""
    params = {"page": page, "limit": limit}
    if search:
        params["search"] = search

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            f"{SUPERVITY_BASE_URL}/user-forms",
            headers=_get_json_headers(),
            params=params,
        )

    if response.status_code != 200:
        return {"forms": [], "items": []}

    return response.json()


async def supervity_get_user_form(form_id: str) -> dict:
    """Get a specific human review form."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            f"{SUPERVITY_BASE_URL}/user-forms/{form_id}",
            headers=_get_json_headers(),
        )

    if response.status_code != 200:
        raise HTTPException(status_code=404, detail="Review form not found")

    return response.json()


async def supervity_submit_form(form_id: str, decision: str, comments: str = "") -> dict:
    """Submit a human review decision. Resumes agent execution."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            f"{SUPERVITY_BASE_URL}/user-forms/{form_id}/submit",
            headers=_get_json_headers(),
            json={"decision": decision, "comments": comments},
        )

    if response.status_code != 200:
        raise HTTPException(status_code=400, detail=f"Failed to submit review: {response.text[:200]}")

    return response.json()


async def supervity_cancel_runs(run_ids: list = None, workflow_id: str = None) -> dict:
    """Cancel active workflow runs."""
    body = {}
    if run_ids:
        body["runIds"] = run_ids
    if workflow_id:
        body["workflowId"] = workflow_id

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            f"{SUPERVITY_BASE_URL}/workflow-runs/cancel",
            headers=_get_json_headers(),
            json=body,
        )

    return response.json() if response.status_code == 200 else {"error": response.text[:200]}


# =============================================================================
# INTENT DETECTION
# =============================================================================

CAMPAIGN_KEYWORDS = [
    "create a campaign", "launch a campaign", "generate content",
    "write a post", "create content", "campaign about", "campaign for",
    "campaign around", "publish", "post about", "draft a",
    "marketing campaign", "social media campaign", "content for",
    "promote", "announce", "world coffee day",
    "launch trending", "create a post",
]

KNOWLEDGE_KEYWORDS = [
    "what is novabrew", "what are the", "tell me about",
    "brand voice", "product details", "ingredients",
    "banned", "competitor", "posting rules", "guidelines",
    "novabrew focus", "novabrew classic", "novabrew lite", "novabrew nitro",
    "starter pack", "price", "pricing",
]

INSIGHTS_KEYWORDS = [
    "show insights", "campaign insights", "show me insights",
    "how many campaigns", "performance", "metrics", "stats",
    "recent activity", "show recent",
]


def detect_intent(message: str) -> str:
    """Detect user intent: campaign, knowledge, insights, or help."""
    msg = message.lower()
    if any(kw in msg for kw in CAMPAIGN_KEYWORDS):
        return "campaign"
    if any(kw in msg for kw in KNOWLEDGE_KEYWORDS):
        return "knowledge"
    if any(kw in msg for kw in INSIGHTS_KEYWORDS):
        return "insights"
    return "help"


# =============================================================================
# ENDPOINTS — AI CHAT (Main Entry Point)
# =============================================================================


@router.post("/chat")
async def ai_chat(request: ChatRequest, db: Session = Depends(get_db)):
    """
    Main entry point for the AI Manager chat.
    - Campaign briefs → executes Orchestrator, polls for result
    - Knowledge questions → queries Knowledge Base agent
    - Insights requests → returns campaign stats
    - General questions → returns helpful info
    """
    message = request.brief or request.message
    if not message:
        raise HTTPException(status_code=400, detail="Either 'brief' or 'message' is required")

    intent = detect_intent(message)

    # =========================================================================
    # HELP — General questions
    # =========================================================================
    if intent == "help":
        return {
            "response": (
                "I'm the **NovaBrew AI** — your marketing command center assistant.\n\n"
                "Here's what I can do:\n\n"
                "☕ **Create campaigns** — \"Create a campaign about World Coffee Day\"\n"
                "📚 **Answer brand questions** — \"What is NovaBrew Focus?\", \"What are the banned terms?\"\n"
                "📊 **Show insights** — \"Show me campaign insights\"\n\n"
                "I orchestrate 5 AI agents: Trend Analyser, Content Adapter, Brand Safety Checker, "
                "Social Scheduler, and the Knowledge Base. Just tell me what you need!"
            )
        }

    # =========================================================================
    # KNOWLEDGE — Query the Knowledge Base agent
    # =========================================================================
    if intent == "knowledge":
        try:
            result = await supervity_execute(
                KNOWLEDGE_BASE_WORKFLOW_ID,
                {"query": message},
            )

            # Extract answer from the LAST completed step's output
            answer = ""
            for activity in reversed(result.get("activityRuns", [])):
                outputs = activity.get("outputs", {})
                output_str = outputs.get("output", "")
                if output_str and output_str.strip():
                    try:
                        parsed = json.loads(output_str)
                        # Look for answer-like fields
                        answer = (
                            parsed.get("answer", "") or
                            parsed.get("response", "") or
                            parsed.get("result", "") or
                            parsed.get("synthesis", "") or
                            parsed.get("output", "")
                        )
                        if not answer and isinstance(parsed, dict):
                            # If it's a dict without known keys, check if it looks like a file download step
                            if "processed_files" in parsed or "step" in parsed:
                                continue  # Skip intermediate steps
                            answer = json.dumps(parsed, indent=2)
                    except json.JSONDecodeError:
                        # Raw text answer
                        if len(output_str) > 20 and "processed_files" not in output_str:
                            answer = output_str
                    if answer:
                        break

            if answer:
                return {"response": f"📚 **From NovaBrew Knowledge Base:**\n\n{answer}"}
            return {"response": "I searched the knowledge base but couldn't find a specific answer. Try rephrasing your question."}
        except Exception as e:
            log.error(f"Knowledge Base query failed: {e}")
            return {"response": f"Knowledge Base query failed: {str(e)}"}

    # =========================================================================
    # INSIGHTS — Return campaign stats
    # =========================================================================
    if intent == "insights":
        from sqlalchemy import func
        from ..models.campaign import Campaign as CampaignModel

        total = db.query(CampaignModel).count()
        completed = db.query(CampaignModel).filter(CampaignModel.status == "completed").count()
        failed = db.query(CampaignModel).filter(CampaignModel.status == "failed").count()
        avg_duration = db.query(func.avg(CampaignModel.duration_ms)).scalar() or 0

        recent = (
            db.query(CampaignModel)
            .order_by(CampaignModel.created_at.desc())
            .limit(5)
            .all()
        )

        response = "📊 **Campaign Insights:**\n\n"
        response += f"**Total campaigns:** {total}\n"
        response += f"**Completed:** {completed} | **Failed:** {failed}\n"
        response += f"**Avg duration:** {round(avg_duration/1000, 1)}s\n"

        if recent:
            response += "\n**Recent campaigns:**\n"
            for c in recent:
                status_icon = "✅" if c.status == "completed" else "❌" if c.status == "failed" else "⏳"
                response += f"- {status_icon} {c.brief[:50]}... ({round((c.duration_ms or 0)/1000, 1)}s)\n"

        if total == 0:
            response = "📊 No campaigns have been run yet. Try: \"Create a campaign about World Coffee Day\""

        return {"response": response}

    # =========================================================================
    # CAMPAIGN — Execute the Orchestrator
    # =========================================================================
    start_time = time.time()
    campaign_id = f"nb-{uuid.uuid4().hex[:8]}-{datetime.now().strftime('%Y%m%d')}"

    # Store campaign locally
    campaign = Campaign(
        campaign_id=campaign_id,
        brief=message,
        channels=request.channels,
        product_focus=request.product_focus,
        urgency=request.urgency,
        status="running",
        created_at=datetime.now(timezone.utc),
    )
    db.add(campaign)
    db.commit()

    try:
        # Execute the Orchestrator (streaming — returns complete result)
        run = await supervity_execute(
            ORCHESTRATOR_WORKFLOW_ID,
            {
                "brief": message,
                "channels": request.channels,
                "product_focus": request.product_focus,
                "urgency": request.urgency,
            },
        )

        duration_ms = (time.time() - start_time) * 1000
        run_id = run.get("runId", "")
        run_status = run.get("status", "unknown")
        activity_runs = run.get("activityRuns", [])

        # Update campaign
        campaign.status = run_status
        campaign.result_json = json.dumps(run)
        campaign.duration_ms = duration_ms

        # Store execution trace from activity runs
        for i, activity in enumerate(activity_runs):
            if activity.get("kind") == "step":
                trace = ExecutionTrace(
                    campaign_id=campaign_id,
                    step_number=i + 1,
                    agent_name=activity.get("stepName", "Unknown"),
                    status=activity.get("status", "unknown"),
                    duration_ms=_calc_duration(activity),
                    output_summary=activity.get("stepDescription", ""),
                )
                db.add(trace)

        db.commit()

        # Build chat response
        response_text = _build_chat_response(campaign_id, run_status, run, duration_ms)

        return {
            "response": response_text,
            "campaign_id": campaign_id,
            "run_id": run_id,
            "status": run_status,
            "duration_ms": round(duration_ms),
        }

    except Exception as e:
        campaign.status = "failed"
        campaign.result_json = json.dumps({"error": str(e)})
        db.commit()
        log.error(f"Campaign execution failed: {e}")
        return {
            "response": f"❌ Campaign execution failed: {str(e)}\n\nPlease try again.",
            "campaign_id": campaign_id,
            "status": "failed",
        }


# =============================================================================
# ENDPOINTS — CAMPAIGNS
# =============================================================================


@router.get("/campaigns")
async def list_campaigns(page: int = 1, limit: int = 20, db: Session = Depends(get_db)):
    """List all campaigns from local DB with full result data."""
    campaigns = (
        db.query(Campaign)
        .order_by(Campaign.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return {
        "campaigns": [
            {
                "campaign_id": c.campaign_id,
                "brief": c.brief,
                "status": c.status,
                "channels": c.channels,
                "product_focus": c.product_focus,
                "duration_ms": c.duration_ms,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "result": _extract_campaign_result(c.result_json),
            }
            for c in campaigns
        ],
        "total": db.query(Campaign).count(),
    }


@router.get("/campaigns/sync")
async def sync_campaigns_from_supervity():
    """Fetch all past runs from Supervity for the Orchestrator workflow."""
    data = await supervity_list_runs(workflow_id=ORCHESTRATOR_WORKFLOW_ID, page=1, limit=20)
    return data


@router.get("/campaigns/run/{run_id}")
async def get_run_from_supervity(run_id: str):
    """Fetch full run details directly from Supervity API."""
    run = await supervity_get_run(run_id)
    return run


@router.get("/campaigns/{campaign_id}")
async def get_campaign(campaign_id: str, db: Session = Depends(get_db)):
    """Get full details of a specific campaign."""
    campaign = db.query(Campaign).filter(Campaign.campaign_id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    traces = (
        db.query(ExecutionTrace)
        .filter(ExecutionTrace.campaign_id == campaign_id)
        .order_by(ExecutionTrace.step_number)
        .all()
    )

    return {
        "campaign_id": campaign.campaign_id,
        "brief": campaign.brief,
        "status": campaign.status,
        "channels": campaign.channels,
        "product_focus": campaign.product_focus,
        "duration_ms": campaign.duration_ms,
        "created_at": campaign.created_at.isoformat() if campaign.created_at else None,
        "result": _extract_campaign_result(campaign.result_json),
        "execution_trace": [
            {
                "step": t.step_number,
                "agent": t.agent_name,
                "status": t.status,
                "duration_ms": t.duration_ms,
                "output_summary": t.output_summary,
            }
            for t in traces
        ],
    }


@router.post("/campaigns/cancel")
async def cancel_campaign(request: CancelRequest):
    """Cancel a running campaign."""
    result = await supervity_cancel_runs(run_ids=[request.run_id])
    return result


# =============================================================================
# ENDPOINTS — WORKBENCH (Human-in-Command)
# =============================================================================


@router.get("/workbench")
async def list_pending_reviews(page: int = 1, limit: int = 20, search: str = "", db: Session = Depends(get_db)):
    """
    List pending exceptions from BOTH:
    1. Supervity Human Review forms (native platform)
    2. Local campaign_exceptions table (from orchestrator responses)
    """
    all_exceptions = []

    # Source 1: Supervity user-forms
    try:
        data = await supervity_list_user_forms(page=page, limit=limit, search=search)
        forms = data.get("forms", data.get("items", []))
        for f in forms:
            all_exceptions.append({
                "id": f.get("id", f.get("formId", "")),
                "campaign_id": f.get("workflowRunId", f.get("runId", "")),
                "type": "human_review",
                "channel": "system",
                "severity": "block",
                "content_preview": f.get("workflowStepName", "Approval Required"),
                "violation_detail": f"Review required for: {f.get('workflowName', 'Unknown workflow')}",
                "suggestion": "Review the form and approve or reject",
                "status": f.get("status", "pending"),
                "created_at": f.get("createdAt"),
                "resolved_at": f.get("updatedAt") if f.get("status") != "pending" else None,
                "source": "supervity",
            })
    except Exception as e:
        log.warning(f"Failed to fetch Supervity user-forms: {e}")

    # Source 2: Local campaign_exceptions table
    from ..models.campaign import CampaignException
    local_exceptions = (
        db.query(CampaignException)
        .order_by(CampaignException.created_at.desc())
        .limit(limit)
        .all()
    )
    for e in local_exceptions:
        all_exceptions.append({
            "id": e.exception_id,
            "campaign_id": e.campaign_id,
            "type": e.exception_type,
            "channel": e.channel,
            "severity": e.severity,
            "content_preview": e.content_preview,
            "violation_detail": e.violation_detail,
            "suggestion": e.suggestion,
            "status": e.status,
            "created_at": e.created_at.isoformat() if e.created_at else None,
            "resolved_at": e.resolved_at.isoformat() if e.resolved_at else None,
            "source": "local",
        })

    # Sort by created_at descending
    all_exceptions.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    pending = sum(1 for e in all_exceptions if e.get("status") in ("pending", "pending_review"))

    return {
        "exceptions": all_exceptions[:limit],
        "total": len(all_exceptions),
        "pending": pending,
    }


@router.get("/workbench/{form_id}")
async def get_review_form(form_id: str):
    """Get a specific human review form with full context."""
    form = await supervity_get_user_form(form_id)
    return form


@router.post("/workbench/{form_id}/resolve")
async def resolve_review(form_id: str, decision: str = "approve", comments: str = "", db: Session = Depends(get_db)):
    """
    Submit a review decision.
    - For Supervity forms: calls /user-forms/:id/submit (resumes agent)
    - For local exceptions: updates status in DB
    """
    from ..models.campaign import CampaignException

    # Try local DB first
    local_exc = db.query(CampaignException).filter(CampaignException.exception_id == form_id).first()
    if local_exc:
        from datetime import datetime, timezone
        if decision == "approve":
            local_exc.status = "approved_override"
        elif decision == "edit_approve":
            local_exc.status = "approved_edited"
        elif decision == "reject":
            local_exc.status = "rejected"
        local_exc.resolved_by = "admin"
        local_exc.resolution_note = comments
        local_exc.resolved_at = datetime.now(timezone.utc)
        db.commit()
        return {
            "id": form_id,
            "status": local_exc.status,
            "message": f"Exception {decision}d successfully.",
        }

    # Try Supervity user-forms
    try:
        result = await supervity_submit_form(form_id, decision, comments)
        return {
            "id": form_id,
            "status": f"{decision}d",
            "message": f"Review {decision}d. Agent execution resumed.",
            "result": result,
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Exception not found: {str(e)}")


# =============================================================================
# ENDPOINTS — INSIGHTS (Dashboard & Stats)
# =============================================================================


@router.get("/insights")
async def get_insights(db: Session = Depends(get_db)):
    """
    Get aggregated insights combining Supervity dashboard data + local DB.
    """
    # Get dashboard stats from Supervity
    dashboard = await supervity_get_dashboard(ORCHESTRATOR_WORKFLOW_ID)

    # Get recent runs from Supervity
    recent_runs = await supervity_list_runs(workflow_id=ORCHESTRATOR_WORKFLOW_ID, page=1, limit=10)

    # Get pending reviews count
    reviews = await supervity_list_user_forms(page=1, limit=1)
    pending_count = reviews.get("pagination", {}).get("total", 0)

    # Local DB stats (execution traces)
    from sqlalchemy import func
    from ..models.campaign import Campaign as CampaignModel, ExecutionTrace as TraceModel

    total_campaigns = db.query(CampaignModel).count()
    completed = db.query(CampaignModel).filter(CampaignModel.status == "completed").count()
    failed = db.query(CampaignModel).filter(CampaignModel.status == "failed").count()
    avg_duration = db.query(func.avg(CampaignModel.duration_ms)).scalar() or 0

    # Agent performance from local traces
    agent_stats = (
        db.query(
            TraceModel.agent_name,
            func.avg(TraceModel.duration_ms).label("avg_duration"),
            func.count(TraceModel.id).label("total_calls"),
        )
        .group_by(TraceModel.agent_name)
        .all()
    )

    # Recent campaigns from local DB
    recent_campaigns = (
        db.query(CampaignModel)
        .order_by(CampaignModel.created_at.desc())
        .limit(10)
        .all()
    )

    return {
        "campaigns": {
            "total": total_campaigns,
            "completed": completed,
            "failed": failed,
            "success_rate": round((completed / total_campaigns * 100) if total_campaigns > 0 else 0, 1),
            "avg_duration_ms": round(avg_duration, 0),
        },
        "exceptions": {
            "total": pending_count,
            "pending": pending_count,
            "resolved": 0,
            "by_type": [],
        },
        "supervity_dashboard": dashboard,
        "agent_performance": [
            {
                "agent": name,
                "avg_duration_ms": round(avg_dur, 0) if avg_dur else 0,
                "total_calls": total,
            }
            for name, avg_dur, total in agent_stats
        ],
        "recent_campaigns": [
            {
                "campaign_id": c.campaign_id,
                "brief": c.brief[:100],
                "status": c.status,
                "duration_ms": c.duration_ms,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in recent_campaigns
        ],
        "publishing": _get_publishing_stats(db),
    }


@router.get("/insights/trace/{campaign_id}")
def get_execution_trace(campaign_id: str, db: Session = Depends(get_db)):
    """Get execution trace for a campaign from local DB."""
    traces = (
        db.query(ExecutionTrace)
        .filter(ExecutionTrace.campaign_id == campaign_id)
        .order_by(ExecutionTrace.step_number)
        .all()
    )
    return {
        "campaign_id": campaign_id,
        "trace": [
            {
                "step": t.step_number,
                "agent": t.agent_name,
                "status": t.status,
                "duration_ms": t.duration_ms,
                "output_summary": t.output_summary,
            }
            for t in traces
        ],
    }


# =============================================================================
# ENDPOINTS — KNOWLEDGE BASE
# =============================================================================


@router.post("/knowledge")
async def query_knowledge_base(request: KnowledgeQuery):
    """Query the NovaBrew Knowledge Base agent directly."""
    result = await supervity_execute(
        KNOWLEDGE_BASE_WORKFLOW_ID,
        {"query": request.query},
    )

    # Extract answer from activity runs
    answer = ""
    for activity in result.get("activityRuns", []):
        outputs = activity.get("outputs", {})
        output_str = outputs.get("output", "")
        if output_str:
            try:
                parsed = json.loads(output_str)
                answer = parsed.get("answer", parsed.get("response", output_str))
            except json.JSONDecodeError:
                answer = output_str
            break

    return {"answer": answer, "run_id": result.get("runId", ""), "status": result.get("status", "")}


# =============================================================================
# HELPERS
# =============================================================================


def _calc_duration(activity: dict) -> float:
    """Calculate duration from activity run timestamps."""
    started = activity.get("startedAt", "")
    completed = activity.get("completedAt", "")
    if started and completed:
        try:
            start_dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(completed.replace("Z", "+00:00"))
            return (end_dt - start_dt).total_seconds() * 1000
        except (ValueError, TypeError):
            pass
    return 0


def _get_publishing_stats(db: Session) -> dict:
    """Extract publishing stats from all campaign results."""
    campaigns = db.query(Campaign).all()
    
    channel_stats: dict = {}
    recent_failures: list = []

    for c in campaigns:
        if not c.result_json:
            continue
        try:
            data = json.loads(c.result_json)
        except json.JSONDecodeError:
            continue

        # Look through activity runs for publish results
        for activity in data.get("activityRuns", []):
            if activity.get("kind") != "step":
                continue
            outputs = activity.get("outputs", {})
            output_str = outputs.get("output", "")
            if not output_str:
                continue
            try:
                step_data = json.loads(output_str)
            except json.JSONDecodeError:
                continue

            publish_results = step_data.get("publish_results", step_data.get("schedule", []))
            if not isinstance(publish_results, list):
                continue

            for pr in publish_results:
                if not isinstance(pr, dict):
                    continue
                ch = pr.get("channel", "unknown")
                status = pr.get("status", "unknown")
                error = pr.get("error")

                if ch not in channel_stats:
                    channel_stats[ch] = {"channel": ch, "published": 0, "failed": 0, "total": 0}

                channel_stats[ch]["total"] += 1
                if status in ("published", "drafted", "simulated", "queued"):
                    channel_stats[ch]["published"] += 1
                elif status == "failed":
                    channel_stats[ch]["failed"] += 1
                    recent_failures.append({
                        "channel": ch,
                        "error": error or "Unknown error",
                        "campaign_id": c.campaign_id,
                    })

    return {
        "by_channel": list(channel_stats.values()),
        "recent_failures": recent_failures[-5:],  # Last 5 failures
    }


def _extract_campaign_result(result_json: str | None) -> dict | None:
    """Extract published URLs and execution trace from stored campaign result."""
    if not result_json:
        return None

    try:
        data = json.loads(result_json)
    except json.JSONDecodeError:
        return None

    result = {
        "topic": "",
        "published": [],
        "execution_trace": [],
        "summary": {},
    }

    # Strategy: Look at the LAST step's output — it contains the final structured report
    activity_runs = data.get("activityRuns", [])
    step_runs = [a for a in activity_runs if a.get("kind") == "step"]
    
    # Check if campaign was aborted (look for abort indicators in step outputs)
    is_aborted = False
    abort_reason = ""
    for activity in step_runs:
        outputs = activity.get("outputs", {})
        output_str = outputs.get("output", "")
        step_id = activity.get("stepId", "")
        if output_str and ("abort" in output_str.lower() or "aborted" in output_str.lower() or "Relevance score" in output_str and "failed" in output_str.lower()):
            is_aborted = True
            abort_reason = output_str.strip()
            break
        if "abort" in step_id.lower():
            is_aborted = True
            abort_reason = output_str.strip() if output_str else "Campaign aborted by Orchestrator"
            break

    if is_aborted:
        result["status"] = "aborted"
        result["abort_reason"] = abort_reason
    
    # Parse from last step backwards to find the structured JSON report
    for activity in reversed(step_runs):
        outputs = activity.get("outputs", {})
        output_str = outputs.get("output", "")
        if not output_str or not output_str.strip().startswith("{"):
            continue

        try:
            step_data = json.loads(output_str)
        except json.JSONDecodeError:
            continue

        # Found structured output — extract everything
        if "published" in step_data or "campaign_id" in step_data:
            # Topic
            result["topic"] = step_data.get("topic", step_data.get("campaign_id", ""))
            
            # Published items
            for pub in step_data.get("published", []):
                if isinstance(pub, dict):
                    result["published"].append({
                        "channel": pub.get("channel", "unknown"),
                        "url": pub.get("destination", pub.get("details", pub.get("url", ""))),
                        "status": pub.get("status", "unknown"),
                        "error": pub.get("error", pub.get("details", "")) if pub.get("status") == "failed" else None,
                    })

            # Exceptions
            result["exceptions"] = step_data.get("exceptions", [])

            # Execution trace
            trace_data = step_data.get("execution_trace", {})
            steps = trace_data.get("steps", []) if isinstance(trace_data, dict) else trace_data
            for i, step in enumerate(steps):
                if isinstance(step, dict):
                    result["execution_trace"].append({
                        "step": i + 1,
                        "agent": step.get("name", step.get("id", "Unknown")),
                        "status": step.get("status", "unknown"),
                        "duration_ms": int(step.get("duration_seconds", 0) * 1000),
                    })

            # Summary/metrics
            result["summary"] = step_data.get("metrics", step_data.get("summary", {}))
            break

    # Fallback: build execution trace from activity run timestamps if not found
    if not result["execution_trace"]:
        for i, activity in enumerate(step_runs):
            result["execution_trace"].append({
                "step": i + 1,
                "agent": activity.get("stepName", activity.get("stepId", "Unknown")),
                "status": activity.get("status", "unknown"),
                "duration_ms": _calc_duration(activity),
            })

    # Extract topic from Step 1 if not found
    if not result["topic"] and step_runs:
        first_output = step_runs[0].get("outputs", {}).get("output", "")
        if "Campaign ID:" in first_output:
            # Parse "Campaign ID: nb-xxx" from plain text
            parts = first_output.split("Campaign ID:")
            if len(parts) > 1:
                result["topic"] = parts[1].strip().split(",")[0].strip()

    return result


def _build_chat_response(campaign_id: str, status: str, run: dict, duration_ms: float) -> str:
    """Build a formatted chat response from the run result."""
    activity_runs = run.get("activityRuns", [])
    step_runs = [a for a in activity_runs if a.get("kind") == "step"]

    # Try to get structured data from the last step (Step 6 has the full report)
    final_data = {}
    for activity in reversed(step_runs):
        output_str = activity.get("outputs", {}).get("output", "")
        if output_str and output_str.strip().startswith("{"):
            try:
                final_data = json.loads(output_str)
                break
            except json.JSONDecodeError:
                continue

    if status == "completed":
        topic = final_data.get("campaign_id", campaign_id)
        published = final_data.get("published", [])
        exceptions = final_data.get("exceptions", [])
        metrics = final_data.get("metrics", {})

        response = f"✅ Campaign **{campaign_id}** completed!\n\n"
        response += f"**Duration:** {round(duration_ms/1000, 1)}s\n"
        response += f"**Steps executed:** {len(step_runs)}\n"

        if metrics:
            response += f"**Variants:** {metrics.get('variants_generated', '?')} generated, "
            response += f"{metrics.get('approved', '?')} approved, "
            response += f"{metrics.get('flagged', 0)} flagged\n"

        if published:
            response += "\n**Published:**\n"
            for pub in published:
                ch = pub.get("channel", "?")
                st = pub.get("status", "?")
                dest = pub.get("destination", pub.get("details", ""))
                if st in ("success", "published"):
                    # Convert LinkedIn URN to URL
                    if "urn:li:share:" in dest:
                        url = f"https://www.linkedin.com/feed/update/{dest}"
                        response += f"- ✅ **{ch}**: [View on LinkedIn]({url})\n"
                    elif "blog.omprakash.me" in dest:
                        response += f"- ✅ **{ch}**: [{dest}]({dest})\n"
                    else:
                        response += f"- ✅ **{ch}**: {dest}\n"
                elif st == "drafted":
                    response += f"- 📧 **{ch}**: Draft created in Outlook\n"
                elif st == "simulated":
                    response += f"- 📋 **{ch}**: Queued for posting\n"
                elif st == "failed":
                    response += f"- ❌ **{ch}**: Failed — {pub.get('details', dest)}\n"

        if exceptions:
            response += f"\n⚠️ **{len(exceptions)} exception(s)** routed to Workbench:\n"
            for exc in exceptions:
                response += f"- {exc.get('channel', '?')}: {exc.get('violation_detail', exc.get('type', 'Unknown'))}\n"

        if not published and not metrics:
            # Fallback: show step summaries from plain text outputs
            response += "\n**Steps:**\n"
            for activity in step_runs:
                step_id = activity.get("stepId", "?")
                output = activity.get("outputs", {}).get("output", "")
                if output and len(output) < 200:
                    response += f"- {output}\n"

        return response

    elif status == "waiting":
        return f"⏸️ Campaign **{campaign_id}** is waiting for human approval.\n\nCheck the **Workbench** page to review."

    elif status == "failed":
        # Check if aborted due to low relevance
        for activity in step_runs:
            output = activity.get("outputs", {}).get("output", "")
            if "abort" in output.lower() or "relevance" in output.lower():
                return f"🚫 Campaign **{campaign_id}** was **aborted**.\n\n**Reason:** {output}\n\n**Duration:** {round(duration_ms/1000, 1)}s"
        return f"❌ Campaign **{campaign_id}** failed.\n\n**Duration:** {round(duration_ms/1000, 1)}s"

    elif status == "timeout":
        return f"⏱️ Campaign **{campaign_id}** is still running (exceeded timeout).\n\nCheck Insights page for status."

    else:
        # Check for abort in step outputs
        for activity in step_runs:
            output = activity.get("outputs", {}).get("output", "")
            if "abort" in output.lower() or "Aborted" in output:
                return f"🚫 Campaign **{campaign_id}** was **aborted**.\n\n**Reason:** {output}\n\n**Duration:** {round(duration_ms/1000, 1)}s"
        return f"Campaign **{campaign_id}** — status: {status}\n\n**Duration:** {round(duration_ms/1000, 1)}s"
