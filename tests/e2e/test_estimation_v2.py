"""
End-to-end test: estimation with Modello di Stima V2.

Makes a single real Claude API call (shared across the entire module via a
module-scoped fixture) and validates that the EstimateResult is:

  1. Schema-compliant (Pydantic parsed cleanly, all enums valid)
  2. Consistent with V2 Core math  (base_fcu * multiplier + spikes == total)
  3. Includes the BA Refinement component from V2 (base_fcu >= raw FCU sum)
  4. Responds correctly to explicit satellite on/off signals in the requirements
  5. Produces roles whose sum equals the grand total mandays
  6. Produces a timeline where every phase has valid week bounds and the
     per-role mandays across all phases match the role list totals

Run:
    pip install -r requirements-dev.txt
    pytest tests/e2e/test_estimation_v2.py -v
"""

import math
import os
from collections import defaultdict
from pathlib import Path

import pytest

from app.core.claude_client import call_claude
from app.models.estimate import EstimateResult

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MODEL_V2_PATH = Path("EstimateModel/Modello di Stima V2.md")

# Scalability multipliers as defined in the V2 model (and the default model)
EXPECTED_MULTIPLIERS = {"low": 1.0, "medium": 1.3, "high": 1.8}

# Acceptable relative tolerance for floating-point math checks (5 %)
REL_TOL = 0.05
ABS_TOL = 0.5   # mandays — absolute floor to absorb Claude's rounding

# ---------------------------------------------------------------------------
# Requirements fixture
#
# Carefully worded to pin down:
#   - scalability tier explicitly → LOW (< 1 000 users/month)
#   - exactly 3 named data entities with full CRUD
#   - exactly 2 named API integrations
#   - Cybersecurity satellite explicitly requested
#   - Quality Assurance satellite explicitly requested
#   - Digital Experience satellite explicitly excluded
#   - Dedicated BA satellite explicitly excluded (requirements are ready)
# ---------------------------------------------------------------------------

REQUIREMENTS = """\
## Internal Task Management API

Build a REST API for an internal team task management tool.

### Scale
- Maximum 50 concurrent users, internal company use only.
- Expected traffic: well under 1 000 requests/month.
- **Scalability tier: LOW.**

### Data Entities — full CRUD required for each
1. **Task** — Create, Read, Update, Delete
2. **User** — Create, Read, Update
3. **Project** — Create, Read, Update, Delete

### External API Integrations
1. **Slack webhook** (outbound, simple) — notify the team on task status changes.
2. **Google OAuth2** (inbound, moderate) — user authentication.

### Business Logic
- Assign tasks to users; task priority system (low / medium / high).
- Mark tasks complete or incomplete.

### Quality & Security Requirements
- Unit and integration test suite required.
  → **Activate the Quality Assurance satellite.**
- Basic OWASP security hardening required.
  → **Activate the Cybersecurity satellite.**

### Explicitly excluded satellites
- No frontend or UX design needed.
  → **Digital Experience satellite: NOT needed.**
- Requirements are ready — no stakeholder facilitation needed.
  → **Dedicated Business Analysis satellite: NOT needed.**

### Technology
- Python FastAPI + PostgreSQL, standard single-cloud deployment.
- No legacy integrations or unknown technologies.
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def is_close(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def grand_total_mandays(result: EstimateResult) -> float:
    """Core + every active satellite."""
    sat = result.satellites
    return result.core.total_mandays + sum(
        s.total_mandays
        for s in [
            sat.pm_orchestration,
            sat.dedicated_business_analysis,
            sat.solution_architecture,
            sat.cybersecurity,
            sat.digital_experience,
            sat.quality_assurance,
        ]
        if s.active
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def api_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        pytest.skip("ANTHROPIC_API_KEY not set — skipping e2e tests")
    return key


@pytest.fixture(scope="module")
def model_v2() -> str:
    if not MODEL_V2_PATH.exists():
        pytest.skip(f"Model file not found: {MODEL_V2_PATH}")
    return MODEL_V2_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def estimate(api_key: str, model_v2: str) -> EstimateResult:
    """Single Claude API call, reused by all tests in this module."""
    return call_claude(
        api_key=api_key,
        model_md=model_v2,
        requirements_md=REQUIREMENTS,
    )


# ---------------------------------------------------------------------------
# 1. Schema compliance
# ---------------------------------------------------------------------------

class TestSchemaCompliance:
    """Output must parse cleanly and all enum values must be valid."""

    def test_is_estimate_result(self, estimate: EstimateResult):
        assert isinstance(estimate, EstimateResult)

    def test_project_name_not_empty(self, estimate: EstimateResult):
        assert estimate.project_name.strip()

    def test_project_summary_not_empty(self, estimate: EstimateResult):
        assert estimate.project_summary.strip()

    def test_has_at_least_three_data_entities(self, estimate: EstimateResult):
        assert len(estimate.core.data_entities) >= 3, (
            f"Expected ≥3 data entities (Task, User, Project); "
            f"got {[e.name for e in estimate.core.data_entities]}"
        )

    def test_has_at_least_two_api_integrations(self, estimate: EstimateResult):
        assert len(estimate.core.api_integrations) >= 2, (
            f"Expected ≥2 integrations (Slack, Google OAuth2); "
            f"got {[a.name for a in estimate.core.api_integrations]}"
        )

    def test_scalability_tier_enum(self, estimate: EstimateResult):
        assert estimate.core.scalability_tier in EXPECTED_MULTIPLIERS

    def test_api_direction_enum(self, estimate: EstimateResult):
        valid = {"inbound", "outbound", "bidirectional"}
        for a in estimate.core.api_integrations:
            assert a.direction in valid, (
                f"Integration '{a.name}' has invalid direction '{a.direction}'"
            )

    def test_api_complexity_enum(self, estimate: EstimateResult):
        valid = {"simple", "moderate", "complex"}
        for a in estimate.core.api_integrations:
            assert a.complexity in valid, (
                f"Integration '{a.name}' has invalid complexity '{a.complexity}'"
            )

    def test_entity_mandays_positive(self, estimate: EstimateResult):
        for e in estimate.core.data_entities:
            assert e.mandays > 0, f"Entity '{e.name}' has non-positive mandays"

    def test_integration_mandays_positive(self, estimate: EstimateResult):
        for a in estimate.core.api_integrations:
            assert a.mandays > 0, f"Integration '{a.name}' has non-positive mandays"

    def test_satellite_enum_pm_project_size(self, estimate: EstimateResult):
        assert estimate.satellites.pm_orchestration.project_size in {"small", "medium", "large"}

    def test_satellite_enum_sa_env_complexity(self, estimate: EstimateResult):
        assert estimate.satellites.solution_architecture.environment_complexity in {
            "simple", "standard", "complex"
        }

    def test_satellite_enum_cyber_sensitivity(self, estimate: EstimateResult):
        assert estimate.satellites.cybersecurity.sensitivity_tier in {
            "basic", "standard", "critical"
        }

    def test_satellite_enum_dx_journey(self, estimate: EstimateResult):
        assert estimate.satellites.digital_experience.user_journey_complexity in {
            "simple", "transactional", "expert"
        }

    def test_satellite_enum_qa_criticality(self, estimate: EstimateResult):
        assert estimate.satellites.quality_assurance.criticality_tier in {1, 2, 3}


# ---------------------------------------------------------------------------
# 2. V2 Core math
# ---------------------------------------------------------------------------

class TestV2CoreMath:
    """
    V2 formula:
        Stima_Core = ((Base_FCU + BA_Refinement_15%) × Scalability) + Spike

    In the schema:
        base_fcu_mandays  = the value *before* the scalability multiplier
                            (may include the 15 % BA refinement)
        total_mandays     = (base_fcu_mandays × scalability_multiplier) + Σspikes
    """

    def test_scalability_tier_is_low(self, estimate: EstimateResult):
        """Requirements explicitly declare LOW scalability."""
        assert estimate.core.scalability_tier == "low", (
            f"Requirements declare LOW scalability, "
            f"got '{estimate.core.scalability_tier}'"
        )

    def test_scalability_multiplier_matches_tier(self, estimate: EstimateResult):
        tier = estimate.core.scalability_tier
        expected = EXPECTED_MULTIPLIERS[tier]
        assert is_close(estimate.core.scalability_multiplier, expected), (
            f"Tier '{tier}' → expected multiplier {expected}, "
            f"got {estimate.core.scalability_multiplier}"
        )

    def test_core_total_mandays_formula(self, estimate: EstimateResult):
        """total_mandays == (base_fcu × multiplier) + Σspike.mandays"""
        spike_sum = sum(s.mandays for s in estimate.core.spikes)
        expected = (
            estimate.core.base_fcu_mandays * estimate.core.scalability_multiplier
            + spike_sum
        )
        assert is_close(estimate.core.total_mandays, expected), (
            f"Core math inconsistent: "
            f"base_fcu={estimate.core.base_fcu_mandays}, "
            f"multiplier={estimate.core.scalability_multiplier}, "
            f"spikes={spike_sum:.2f}, "
            f"expected total={expected:.2f}, "
            f"got total={estimate.core.total_mandays:.2f}"
        )

    def test_base_fcu_not_less_than_raw_sum(self, estimate: EstimateResult):
        """
        V2 adds BA Refinement (+15 %) on top of raw FCU before scaling.
        base_fcu_mandays must be >= raw sum (entities + APIs + business logic).
        """
        raw = (
            sum(e.mandays for e in estimate.core.data_entities)
            + sum(a.mandays for a in estimate.core.api_integrations)
            + estimate.core.business_logic_mandays
        )
        assert estimate.core.base_fcu_mandays >= raw - ABS_TOL, (
            f"base_fcu ({estimate.core.base_fcu_mandays:.2f}) is less than "
            f"raw FCU sum ({raw:.2f}). "
            f"With V2's BA Refinement (+15 %), base_fcu should be >= raw sum."
        )

    def test_base_fcu_positive(self, estimate: EstimateResult):
        assert estimate.core.base_fcu_mandays > 0

    def test_core_total_positive(self, estimate: EstimateResult):
        assert estimate.core.total_mandays > 0


# ---------------------------------------------------------------------------
# 3. Satellite activation
# ---------------------------------------------------------------------------

class TestSatelliteActivation:
    """
    The requirements explicitly activate Cybersecurity and QA,
    and explicitly deactivate Digital Experience and Dedicated BA.
    """

    def test_cybersecurity_active(self, estimate: EstimateResult):
        assert estimate.satellites.cybersecurity.active, (
            "Cybersecurity satellite must be active — "
            "requirements explicitly request OWASP hardening"
        )

    def test_quality_assurance_active(self, estimate: EstimateResult):
        assert estimate.satellites.quality_assurance.active, (
            "QA satellite must be active — "
            "requirements explicitly request a test suite"
        )

    def test_digital_experience_inactive(self, estimate: EstimateResult):
        assert not estimate.satellites.digital_experience.active, (
            "Digital Experience satellite must be inactive — "
            "requirements explicitly exclude frontend/UX"
        )

    def test_dedicated_ba_inactive(self, estimate: EstimateResult):
        assert not estimate.satellites.dedicated_business_analysis.active, (
            "Dedicated BA satellite must be inactive — "
            "requirements state they are already ready"
        )

    def test_active_satellite_mandays_positive(self, estimate: EstimateResult):
        sat = estimate.satellites
        for name, s in [
            ("cybersecurity", sat.cybersecurity),
            ("quality_assurance", sat.quality_assurance),
        ]:
            assert s.total_mandays > 0, (
                f"Satellite '{name}' is active but reports 0 mandays"
            )

    def test_inactive_satellite_mandays_zero(self, estimate: EstimateResult):
        sat = estimate.satellites
        for name, s in [
            ("digital_experience", sat.digital_experience),
            ("dedicated_business_analysis", sat.dedicated_business_analysis),
        ]:
            assert s.total_mandays == 0.0, (
                f"Inactive satellite '{name}' should have 0 mandays, "
                f"got {s.total_mandays}"
            )

    def test_active_satellites_have_justification(self, estimate: EstimateResult):
        sat = estimate.satellites
        for name, s in [
            ("cybersecurity", sat.cybersecurity),
            ("quality_assurance", sat.quality_assurance),
        ]:
            assert s.justification.strip(), (
                f"Active satellite '{name}' has no justification text"
            )

    def test_qa_has_verification_points(self, estimate: EstimateResult):
        assert estimate.satellites.quality_assurance.verification_points > 0


# ---------------------------------------------------------------------------
# 4. Roles consistency
# ---------------------------------------------------------------------------

class TestRolesConsistency:
    """Sum of all role.mandays must equal the grand total mandays."""

    def test_roles_list_not_empty(self, estimate: EstimateResult):
        assert len(estimate.roles) > 0, "No roles defined in the estimate"

    def test_role_names_not_empty(self, estimate: EstimateResult):
        for r in estimate.roles:
            assert r.role.strip(), "Found a role with an empty name"

    def test_role_mandays_positive(self, estimate: EstimateResult):
        for r in estimate.roles:
            assert r.mandays > 0, f"Role '{r.role}' has non-positive mandays"

    def test_roles_sum_equals_grand_total(self, estimate: EstimateResult):
        grand = grand_total_mandays(estimate)
        roles_sum = sum(r.mandays for r in estimate.roles)
        assert is_close(roles_sum, grand), (
            f"Roles sum ({roles_sum:.2f}) != grand total ({grand:.2f}), "
            f"diff = {abs(roles_sum - grand):.2f} md"
        )


# ---------------------------------------------------------------------------
# 5. Timeline validity
# ---------------------------------------------------------------------------

class TestTimeline:
    """
    plan_phases must be present with valid 1-indexed week bounds,
    and per-role mandays across phases must match the role list totals.
    """

    def test_plan_phases_not_empty(self, estimate: EstimateResult):
        assert len(estimate.plan_phases) > 0, "No plan phases defined"

    def test_phase_names_not_empty(self, estimate: EstimateResult):
        for p in estimate.plan_phases:
            assert p.name.strip(), "Found a plan phase with an empty name"

    def test_phase_weeks_valid(self, estimate: EstimateResult):
        for p in estimate.plan_phases:
            assert p.start_week >= 1, (
                f"Phase '{p.name}': start_week {p.start_week} must be >= 1"
            )
            assert p.end_week >= p.start_week, (
                f"Phase '{p.name}': end_week {p.end_week} < start_week {p.start_week}"
            )

    def test_phase_role_mandays_positive(self, estimate: EstimateResult):
        for p in estimate.plan_phases:
            for pr in p.roles:
                assert pr.mandays > 0, (
                    f"Phase '{p.name}', role '{pr.role}': non-positive mandays"
                )

    def test_phase_role_totals_match_role_list(self, estimate: EstimateResult):
        """
        For every role that appears in both the roles list and plan phases,
        the sum of phase allocations must match the role list total.
        """
        phase_sums: dict[str, float] = defaultdict(float)
        for p in estimate.plan_phases:
            for pr in p.roles:
                phase_sums[pr.role] += pr.mandays

        role_totals = {r.role: r.mandays for r in estimate.roles}

        for role_name, phase_total in phase_sums.items():
            if role_name not in role_totals:
                continue  # role appears only in phases — not a hard error
            assert is_close(phase_total, role_totals[role_name]), (
                f"Role '{role_name}': "
                f"phase sum {phase_total:.2f} != role total {role_totals[role_name]:.2f}"
            )
