from pydantic import BaseModel
from typing import Optional


class EstimateJobResponse(BaseModel):
    job_id: str


class JobStatusResponse(BaseModel):
    status: str
    progress_message: str
    error_detail: Optional[str] = None


class SaveRequest(BaseModel):
    job_id: str
    name: str


class SaveSummary(BaseModel):
    save_id: str
    name: str
    status: str
    created_at: str
    updated_at: str
    project_name: str
    grand_mandays: float
    grand_cost: float
    currency: str


class SaveDetail(SaveSummary):
    report_markdown: str
    requirements_md: str


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    estimate_updated: bool
    report_markdown: Optional[str] = None
