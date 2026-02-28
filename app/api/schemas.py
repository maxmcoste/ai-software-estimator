from pydantic import BaseModel, ConfigDict
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


class PhaseRoleSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    role: str
    mandays: float


class PlanPhaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str
    start_week: int
    end_week: int
    roles: list[PhaseRoleSchema]


class RoleEstimateSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    role: str
    mandays: float
    description: str = ""


class PlanResponse(BaseModel):
    roles: list[RoleEstimateSchema]
    plan_phases: list[PlanPhaseSchema]


class SaveDetail(SaveSummary):
    report_markdown: str
    requirements_md: str
    roles: list[RoleEstimateSchema] = []
    plan_phases: list[PlanPhaseSchema] = []


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    estimate_updated: bool
    report_markdown: Optional[str] = None


class OpenSaveResponse(BaseModel):
    job_id: str
    save_id: str
    name: str


class UpdateSaveRequest(BaseModel):
    job_id: str


class JobContextResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    requirements_md: str
    model_md: str
    save_id: Optional[str] = None
    save_name: Optional[str] = None
