from __future__ import annotations
import logging
from pathlib import Path
from typing import Annotated, Optional

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.api.schemas import (
    EstimateJobResponse, JobStatusResponse,
    ChatRequest, ChatResponse,
    SaveRequest, SaveSummary, SaveDetail,
    OpenSaveResponse, UpdateSaveRequest, JobContextResponse,
    PlanResponse, RoleEstimateSchema, PlanPhaseSchema,
)
from app.core import estimator, saves as saves_store
from app.core import claude_client, report_generator
from app.dependencies import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


@router.post("/estimate", response_model=EstimateJobResponse)
async def create_estimate(
    background_tasks: BackgroundTasks,
    requirements_file: Annotated[Optional[UploadFile], File()] = None,
    requirements_text: Annotated[Optional[str], Form()] = None,
    estimation_model_file: Annotated[Optional[UploadFile], File()] = None,
    github_url: Annotated[str, Form()] = "",
    github_token: Annotated[str, Form()] = "",
    manday_cost: Annotated[float, Form()] = 500.0,
    currency: Annotated[str, Form()] = "EUR",
):
    settings = get_settings()

    # Resolve requirements
    if requirements_file and requirements_file.filename:
        requirements_md = (await requirements_file.read()).decode("utf-8", errors="replace")
    elif requirements_text and requirements_text.strip():
        requirements_md = requirements_text.strip()
    else:
        raise HTTPException(status_code=422, detail="Provide either requirements_file or requirements_text.")

    # Resolve estimation model
    if estimation_model_file and estimation_model_file.filename:
        model_md = (await estimation_model_file.read()).decode("utf-8", errors="replace")
    else:
        model_path: Path = settings.DEFAULT_MODEL_PATH
        if not model_path.exists():
            raise HTTPException(status_code=500, detail=f"Default estimation model not found at {model_path}")
        model_md = model_path.read_text(encoding="utf-8")

    # Resolve GitHub token
    effective_token = github_token or settings.GITHUB_TOKEN

    job = estimator.create_job()

    background_tasks.add_task(
        estimator.run_estimation,
        job_id=job.job_id,
        requirements_md=requirements_md,
        model_md=model_md,
        github_url=github_url,
        github_token=effective_token,
        manday_cost=manday_cost,
        currency=currency,
        reports_dir=settings.REPORTS_DIR,
        api_key=settings.ANTHROPIC_API_KEY,
    )

    return EstimateJobResponse(job_id=job.job_id)


@router.get("/estimate/{job_id}/status", response_model=JobStatusResponse)
async def get_status(job_id: str):
    job = estimator.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatusResponse(
        status=job.status,
        progress_message=job.progress_message,
        error_detail=job.error_detail,
    )


@router.post("/saves", response_model=SaveSummary)
async def create_save(req: SaveRequest):
    job = estimator.get_job(req.job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "done" or job.estimate_result is None:
        raise HTTPException(status_code=409, detail="Estimation not complete")
    if job.report_path is None or not job.report_path.exists():
        raise HTTPException(status_code=500, detail="Report file missing")

    report_md = job.report_path.read_text(encoding="utf-8")
    data = saves_store.create_save(
        name=req.name.strip() or job.estimate_result.project_name,
        requirements_md=job.requirements_md,
        model_md=job.model_md,
        report_markdown=report_md,
        estimate_data=job.estimate_result.model_dump(),
        financials_data=job.financials.model_dump(),
    )
    return SaveSummary(**{k: data[k] for k in ("save_id", "name", "status", "created_at", "updated_at")},
                       project_name=data["estimate_data"].get("project_name", ""),
                       grand_mandays=data["financials_data"]["grand_mandays"],
                       grand_cost=data["financials_data"]["grand_cost"],
                       currency=data["financials_data"]["currency"])


@router.get("/saves", response_model=list[SaveSummary])
async def list_saves():
    return [SaveSummary(**s) for s in saves_store.list_saves()]


@router.get("/saves/{save_id}", response_model=SaveDetail)
async def get_save(save_id: str):
    data = saves_store.get_save(save_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Save not found")
    estimate_data = data.get("estimate_data", {})
    return SaveDetail(
        **{k: data[k] for k in ("save_id", "name", "status", "created_at", "updated_at",
                                 "report_markdown", "requirements_md")},
        project_name=estimate_data.get("project_name", ""),
        grand_mandays=data["financials_data"]["grand_mandays"],
        grand_cost=data["financials_data"]["grand_cost"],
        currency=data["financials_data"]["currency"],
        roles=estimate_data.get("roles", []),
        plan_phases=estimate_data.get("plan_phases", []),
    )


@router.post("/saves/{save_id}/finalize", response_model=SaveSummary)
async def finalize_save(save_id: str):
    data = saves_store.finalize_save(save_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Save not found")
    return SaveSummary(
        **{k: data[k] for k in ("save_id", "name", "status", "created_at", "updated_at")},
        project_name=data["estimate_data"].get("project_name", ""),
        grand_mandays=data["financials_data"]["grand_mandays"],
        grand_cost=data["financials_data"]["grand_cost"],
        currency=data["financials_data"]["currency"],
    )


@router.delete("/saves/{save_id}")
async def delete_save(save_id: str):
    ok = saves_store.delete_save(save_id)
    if not ok:
        data = saves_store.get_save(save_id)
        if data is None:
            raise HTTPException(status_code=404, detail="Save not found")
        raise HTTPException(status_code=403, detail="Finalized estimates cannot be deleted")
    return {"deleted": True}


@router.post("/saves/{save_id}/open", response_model=OpenSaveResponse)
async def open_save(save_id: str):
    """Load a saved estimate into an in-memory job so it can be edited via chat."""
    from app.models.estimate import EstimateResult, FinancialSummary

    data = saves_store.get_save(save_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Save not found")

    settings = get_settings()

    estimate_result = EstimateResult(**data["estimate_data"])
    financials = FinancialSummary(**data["financials_data"])

    job = estimator.create_job()

    # Write the saved report markdown to a file so the report endpoint works
    settings.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = settings.REPORTS_DIR / f"{job.job_id}.md"
    report_path.write_text(data["report_markdown"], encoding="utf-8")

    estimator.update_job(
        job.job_id,
        status="done",
        progress_message="Report ready.",
        report_path=report_path,
        estimate_result=estimate_result,
        financials=financials,
        requirements_md=data.get("requirements_md", ""),
        model_md=data.get("model_md", ""),
        save_id=save_id,
    )

    return OpenSaveResponse(job_id=job.job_id, save_id=save_id, name=data["name"])


@router.put("/saves/{save_id}", response_model=SaveSummary)
async def update_save(save_id: str, req: UpdateSaveRequest):
    """Update an existing draft with the current state of a job."""
    job = estimator.get_job(req.job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "done" or job.estimate_result is None:
        raise HTTPException(status_code=409, detail="Estimation not complete")
    if job.report_path is None or not job.report_path.exists():
        raise HTTPException(status_code=500, detail="Report file missing")

    report_md = job.report_path.read_text(encoding="utf-8")
    data = saves_store.update_save(
        save_id=save_id,
        report_markdown=report_md,
        estimate_data=job.estimate_result.model_dump(),
        financials_data=job.financials.model_dump(),
    )
    if data is None:
        raise HTTPException(status_code=404, detail="Save not found or already finalized")

    return SaveSummary(
        **{k: data[k] for k in ("save_id", "name", "status", "created_at", "updated_at")},
        project_name=data["estimate_data"].get("project_name", ""),
        grand_mandays=data["financials_data"]["grand_mandays"],
        grand_cost=data["financials_data"]["grand_cost"],
        currency=data["financials_data"]["currency"],
    )


@router.get("/estimate/{job_id}/plan", response_model=PlanResponse)
async def get_job_plan(job_id: str):
    """Return roles and plan phases for a completed job."""
    job = estimator.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "done" or job.estimate_result is None:
        raise HTTPException(status_code=409, detail="Estimation not complete")
    return PlanResponse(
        roles=job.estimate_result.roles,
        plan_phases=job.estimate_result.plan_phases,
    )


@router.get("/estimate/{job_id}/context", response_model=JobContextResponse)
async def get_job_context(job_id: str):
    """Return requirements, model text, and save metadata for a completed job."""
    job = estimator.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    save_name = None
    if job.save_id:
        save_data = saves_store.get_save(job.save_id)
        if save_data:
            save_name = save_data["name"]

    return JobContextResponse(
        requirements_md=job.requirements_md,
        model_md=job.model_md,
        save_id=job.save_id,
        save_name=save_name,
    )


@router.post("/estimate/{job_id}/rerun", response_model=EstimateJobResponse)
async def rerun_estimate(
    background_tasks: BackgroundTasks,
    job_id: str,
    rerun_model: Annotated[Optional[UploadFile], File()] = None,
    rerun_requirements_file: Annotated[Optional[UploadFile], File()] = None,
    rerun_requirements_text: Annotated[Optional[str], Form()] = None,
):
    job = estimator.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status not in ("done", "error"):
        raise HTTPException(status_code=409, detail="Cannot re-run a job that is still running")

    settings = get_settings()

    # Model: new upload or fall back to existing
    if rerun_model and rerun_model.filename:
        model_md = (await rerun_model.read()).decode("utf-8", errors="replace")
    else:
        model_md = job.model_md

    # Requirements: file override > text override > existing
    if rerun_requirements_file and rerun_requirements_file.filename:
        new_requirements_md = (await rerun_requirements_file.read()).decode("utf-8", errors="replace")
    elif rerun_requirements_text and rerun_requirements_text.strip():
        new_requirements_md = rerun_requirements_text.strip()
    else:
        new_requirements_md = job.requirements_md

    manday_cost = job.financials.manday_cost if job.financials else 500.0
    currency    = job.financials.currency    if job.financials else "EUR"

    # Reset job state; update model and requirements in place
    estimator.update_job(
        job_id,
        status="pending",
        progress_message="Waiting to start…",
        error_detail=None,
        estimate_result=None,
        financials=None,
        model_md=model_md,
        requirements_md=new_requirements_md,
        chat_history=[],
    )

    background_tasks.add_task(
        estimator.run_estimation,
        job_id=job_id,
        requirements_md=new_requirements_md,
        model_md=model_md,
        github_url="",
        github_token="",
        manday_cost=manday_cost,
        currency=currency,
        reports_dir=settings.REPORTS_DIR,
        api_key=settings.ANTHROPIC_API_KEY,
        cached_repo_summary=job.repo_summary,   # reuse existing GitHub analysis
    )

    return EstimateJobResponse(job_id=job_id)


@router.post("/estimate/{job_id}/chat", response_model=ChatResponse)
def chat(job_id: str, req: ChatRequest):
    """Sync endpoint — FastAPI runs it in a thread pool automatically."""
    job = estimator.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "done":
        raise HTTPException(status_code=409, detail="Estimation not complete yet")
    if job.estimate_result is None:
        raise HTTPException(status_code=500, detail="Estimate data not available for chat")

    settings = get_settings()

    reply, updated_estimate = claude_client.chat_with_claude(
        api_key=settings.ANTHROPIC_API_KEY,
        message=req.message,
        chat_history=job.chat_history,
        current_estimate=job.estimate_result,
    )

    # Append to history as plain text (current estimate is always in the system prompt)
    job.chat_history.append({"role": "user", "content": req.message})
    job.chat_history.append({"role": "assistant", "content": reply})

    report_markdown = None
    if updated_estimate is not None:
        new_financials = estimator._compute_financials(
            updated_estimate,
            job.financials.manday_cost,
            job.financials.currency,
        )
        report_path = settings.REPORTS_DIR / f"{job_id}.md"
        report_generator.generate_report(
            estimate=updated_estimate,
            financials=new_financials,
            report_path=report_path,
        )
        estimator.update_job(job_id, estimate_result=updated_estimate, financials=new_financials)
        report_markdown = report_path.read_text(encoding="utf-8")

    return ChatResponse(reply=reply, estimate_updated=updated_estimate is not None, report_markdown=report_markdown)


@router.get("/estimate/{job_id}/report")
async def get_report(job_id: str):
    job = estimator.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "done":
        raise HTTPException(status_code=409, detail=f"Report not ready (status: {job.status})")
    if job.report_path is None or not job.report_path.exists():
        raise HTTPException(status_code=500, detail="Report file missing")
    return FileResponse(
        path=str(job.report_path),
        media_type="text/markdown",
        filename=f"estimate-{job_id[:8]}.md",
        headers={"Content-Disposition": f"attachment; filename=estimate-{job_id[:8]}.md"},
    )
