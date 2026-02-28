from __future__ import annotations
import logging
from pathlib import Path
from typing import Annotated, Optional

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.api.schemas import EstimateJobResponse, JobStatusResponse
from app.core import estimator
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
