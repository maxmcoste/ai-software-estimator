from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field


class DataEntity(BaseModel):
    name: str
    operations: list[str] = Field(description="CRUD operations, e.g. ['Create','Read','Update','Delete']")
    mandays: float


class ApiIntegration(BaseModel):
    name: str
    direction: str = Field(description="'inbound' or 'outbound'")
    complexity: str = Field(description="'simple', 'moderate', or 'complex'")
    mandays: float


class Spike(BaseModel):
    description: str
    mandays: float


class CoreEstimate(BaseModel):
    data_entities: list[DataEntity]
    api_integrations: list[ApiIntegration]
    business_logic_mandays: float
    scalability_tier: str = Field(description="'low', 'medium', or 'high'")
    scalability_multiplier: float
    spikes: list[Spike]
    base_fcu_mandays: float
    total_mandays: float
    reasoning: str


class PmOrchestration(BaseModel):
    active: bool
    justification: str
    project_size: str = Field(description="'small', 'medium', or 'large'")
    base_fte_per_month: float
    project_months: float
    team_factor: float
    total_mandays: float


class SolutionArchitecture(BaseModel):
    active: bool
    justification: str
    external_systems_count: int
    environment_complexity: str = Field(description="'simple', 'standard', or 'complex'")
    finops_months: float
    total_mandays: float


class Cybersecurity(BaseModel):
    active: bool
    justification: str
    sensitivity_tier: str = Field(description="'basic', 'standard', or 'critical'")
    security_gates_count: int
    compliance_addons: list[str]
    total_mandays: float


class DigitalExperience(BaseModel):
    active: bool
    justification: str
    user_journey_complexity: str = Field(description="'simple', 'transactional', or 'expert'")
    accessibility_required: bool
    total_mandays: float


class QualityAssurance(BaseModel):
    active: bool
    justification: str
    verification_points: int
    criticality_tier: int = Field(description="1, 2, or 3")
    performance_testing: bool
    total_mandays: float


class DedicatedBusinessAnalysis(BaseModel):
    active: bool
    justification: str
    fte_dedicated: float = Field(description="FTE dedicated, e.g. 0.5 or 1.0")
    duration_months: float
    total_mandays: float


def _default_dedicated_ba() -> "DedicatedBusinessAnalysis":
    return DedicatedBusinessAnalysis(
        active=False,
        justification="Not applicable with this estimation model.",
        fte_dedicated=0.0,
        duration_months=0.0,
        total_mandays=0.0,
    )


class Satellites(BaseModel):
    pm_orchestration: PmOrchestration
    dedicated_business_analysis: DedicatedBusinessAnalysis = Field(
        default_factory=_default_dedicated_ba
    )
    solution_architecture: SolutionArchitecture
    cybersecurity: Cybersecurity
    digital_experience: DigitalExperience
    quality_assurance: QualityAssurance


class RoleEstimate(BaseModel):
    role: str
    mandays: float
    description: str = ""


class PhaseRole(BaseModel):
    role: str
    mandays: float


class PlanPhase(BaseModel):
    name: str
    start_week: int
    end_week: int
    roles: list[PhaseRole]


class EstimateResult(BaseModel):
    project_name: str
    project_summary: str
    core: CoreEstimate
    satellites: Satellites
    overall_reasoning: str = ""
    roles: list[RoleEstimate] = []
    plan_phases: list[PlanPhase] = []


class FinancialSummary(BaseModel):
    manday_cost: float
    currency: str
    core_mandays: float
    core_cost: float
    pm_mandays: float
    pm_cost: float
    ba_mandays: float = 0.0
    ba_cost: float = 0.0
    sa_mandays: float
    sa_cost: float
    cyber_mandays: float
    cyber_cost: float
    dx_mandays: float
    dx_cost: float
    qa_mandays: float
    qa_cost: float
    grand_mandays: float
    grand_cost: float
