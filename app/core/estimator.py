from __future__ import annotations
import uuid
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from app.models.estimate import EstimateResult, FinancialSummary

logger = logging.getLogger(__name__)

# In-memory job store
_JOBS: dict[str, "Job"] = {}


@dataclass
class Job:
    job_id: str
    status: str = "pending"          # pending | running | done | error
    progress_message: str = "Waiting to start…"
    report_path: Optional[Path] = None
    error_detail: Optional[str] = None


def create_job() -> Job:
    job_id = str(uuid.uuid4())
    job = Job(job_id=job_id)
    _JOBS[job_id] = job
    return job


def get_job(job_id: str) -> Optional[Job]:
    return _JOBS.get(job_id)


def update_job(job_id: str, **kwargs) -> None:
    job = _JOBS.get(job_id)
    if job is None:
        return
    for key, value in kwargs.items():
        setattr(job, key, value)


def _compute_financials(result: EstimateResult, manday_cost: float, currency: str) -> FinancialSummary:
    s = result.satellites

    def sat_md(sat) -> float:
        return sat.total_mandays if sat.active else 0.0

    core_md = result.core.total_mandays
    pm_md = sat_md(s.pm_orchestration)
    sa_md = sat_md(s.solution_architecture)
    cyber_md = sat_md(s.cybersecurity)
    dx_md = sat_md(s.digital_experience)
    qa_md = sat_md(s.quality_assurance)

    grand_md = core_md + pm_md + sa_md + cyber_md + dx_md + qa_md

    return FinancialSummary(
        manday_cost=manday_cost,
        currency=currency,
        core_mandays=core_md,
        core_cost=round(core_md * manday_cost, 2),
        pm_mandays=pm_md,
        pm_cost=round(pm_md * manday_cost, 2),
        sa_mandays=sa_md,
        sa_cost=round(sa_md * manday_cost, 2),
        cyber_mandays=cyber_md,
        cyber_cost=round(cyber_md * manday_cost, 2),
        dx_mandays=dx_md,
        dx_cost=round(dx_md * manday_cost, 2),
        qa_mandays=qa_md,
        qa_cost=round(qa_md * manday_cost, 2),
        grand_mandays=round(grand_md, 2),
        grand_cost=round(grand_md * manday_cost, 2),
    )


def run_estimation(
    job_id: str,
    requirements_md: str,
    model_md: str,
    github_url: str,
    github_token: str,
    manday_cost: float,
    currency: str,
    reports_dir: Path,
    api_key: str,
) -> None:
    """Synchronous estimation runner — called inside a BackgroundTasks thread."""
    from app.core import claude_client, github_client, report_generator

    try:
        update_job(job_id, status="running", progress_message="Starting estimation…")

        # Optional GitHub fetch
        repo_summary: str | None = None
        repo_warning: str = ""
        if github_url:
            update_job(job_id, progress_message="Fetching GitHub repository…")
            repo_summary, repo_warning = github_client.fetch_repo_summary(github_url, github_token)
            if repo_warning:
                logger.warning("GitHub warning for job %s: %s", job_id, repo_warning)

        # Call Claude
        update_job(job_id, progress_message="Calling Claude API — this may take 30–90 seconds…")
        result: EstimateResult = claude_client.call_claude(
            api_key=api_key,
            model_md=model_md,
            requirements_md=requirements_md,
            repo_summary=repo_summary or None,
        )

        # Financial post-processing
        update_job(job_id, progress_message="Computing financials…")
        financials = _compute_financials(result, manday_cost, currency)

        # Generate report
        update_job(job_id, progress_message="Generating report…")
        reports_dir.mkdir(parents=True, exist_ok=True)
        report_path = reports_dir / f"{job_id}.md"
        report_generator.generate_report(
            estimate=result,
            financials=financials,
            report_path=report_path,
            github_warning=repo_warning,
        )

        update_job(job_id, status="done", progress_message="Report ready.", report_path=report_path)
        logger.info("Job %s completed successfully.", job_id)

    except Exception as exc:
        logger.exception("Job %s failed: %s", job_id, exc)
        update_job(job_id, status="error", error_detail=str(exc), progress_message="Estimation failed.")
