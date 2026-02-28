from __future__ import annotations
import json
import time
import logging
from anthropic import Anthropic, APIError
from app.models.estimate import EstimateResult

logger = logging.getLogger(__name__)

PRODUCE_ESTIMATE_TOOL = {
    "name": "produce_estimate",
    "description": (
        "Produce a structured software project estimate following the Core & Satellites model. "
        "Return every field — set active=false for satellites that are not needed, but always include them."
    ),
    "input_schema": {
        "type": "object",
        "required": ["project_name", "project_summary", "core", "satellites", "overall_reasoning", "roles", "plan_phases"],
        "properties": {
            "project_name": {"type": "string"},
            "project_summary": {"type": "string", "description": "2-3 sentence executive summary of the project"},
            "overall_reasoning": {"type": "string", "description": "High-level explanation of estimation choices"},
            "core": {
                "type": "object",
                "required": [
                    "data_entities", "api_integrations", "business_logic_mandays",
                    "scalability_tier", "scalability_multiplier", "spikes",
                    "base_fcu_mandays", "total_mandays", "reasoning"
                ],
                "properties": {
                    "data_entities": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["name", "operations", "mandays"],
                            "properties": {
                                "name": {"type": "string"},
                                "operations": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "e.g. ['Create','Read','Update','Delete']"
                                },
                                "mandays": {"type": "number"}
                            }
                        }
                    },
                    "api_integrations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["name", "direction", "complexity", "mandays"],
                            "properties": {
                                "name": {"type": "string"},
                                "direction": {"type": "string", "enum": ["inbound", "outbound", "bidirectional"]},
                                "complexity": {"type": "string", "enum": ["simple", "moderate", "complex"]},
                                "mandays": {"type": "number"}
                            }
                        }
                    },
                    "business_logic_mandays": {"type": "number"},
                    "scalability_tier": {"type": "string", "enum": ["low", "medium", "high"]},
                    "scalability_multiplier": {"type": "number"},
                    "spikes": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["description", "mandays"],
                            "properties": {
                                "description": {"type": "string"},
                                "mandays": {"type": "number"}
                            }
                        }
                    },
                    "base_fcu_mandays": {"type": "number", "description": "Sum before scalability multiplier"},
                    "total_mandays": {"type": "number", "description": "(base_fcu_mandays * scalability_multiplier) + sum(spike mandays)"},
                    "reasoning": {"type": "string"}
                }
            },
            "roles": {
                "type": "array",
                "description": "All human roles required. Map every manday from Core and active Satellites to a named role. Sum of all role mandays must equal grand total mandays.",
                "items": {
                    "type": "object",
                    "required": ["role", "mandays", "description"],
                    "properties": {
                        "role": {"type": "string", "description": "e.g. 'Backend Developer', 'Project Manager', 'Solution Architect', 'QA Engineer', 'UX Designer'"},
                        "mandays": {"type": "number"},
                        "description": {"type": "string", "description": "What this role does on this specific project"}
                    }
                }
            },
            "plan_phases": {
                "type": "array",
                "description": "Sequential project phases. Weeks are 1-indexed. Phases may overlap. Allocate mandays to roles per phase.",
                "items": {
                    "type": "object",
                    "required": ["name", "start_week", "end_week", "roles"],
                    "properties": {
                        "name": {"type": "string"},
                        "start_week": {"type": "integer", "description": "1-indexed week when phase starts"},
                        "end_week": {"type": "integer", "description": "Inclusive week when phase ends"},
                        "roles": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["role", "mandays"],
                                "properties": {
                                    "role": {"type": "string"},
                                    "mandays": {"type": "number", "description": "Mandays allocated to this role in this phase"}
                                }
                            }
                        }
                    }
                }
            },
            "satellites": {
                "type": "object",
                "required": ["pm_orchestration", "dedicated_business_analysis", "solution_architecture", "cybersecurity", "digital_experience", "quality_assurance"],
                "properties": {
                    "pm_orchestration": {
                        "type": "object",
                        "required": ["active", "justification", "project_size", "base_fte_per_month", "project_months", "team_factor", "total_mandays"],
                        "properties": {
                            "active": {"type": "boolean"},
                            "justification": {"type": "string"},
                            "project_size": {"type": "string", "enum": ["small", "medium", "large"]},
                            "base_fte_per_month": {"type": "number"},
                            "project_months": {"type": "number"},
                            "team_factor": {"type": "number"},
                            "total_mandays": {"type": "number"}
                        }
                    },
                    "dedicated_business_analysis": {
                        "type": "object",
                        "description": "Dedicated BA satellite (NEW in V2): active when the client lacks ready requirements or needs active stakeholder management.",
                        "required": ["active", "justification", "fte_dedicated", "duration_months", "total_mandays"],
                        "properties": {
                            "active": {"type": "boolean"},
                            "justification": {"type": "string"},
                            "fte_dedicated": {"type": "number", "description": "FTE dedicated (e.g. 0.5 or 1.0)"},
                            "duration_months": {"type": "number"},
                            "total_mandays": {"type": "number"}
                        }
                    },
                    "solution_architecture": {
                        "type": "object",
                        "required": ["active", "justification", "external_systems_count", "environment_complexity", "finops_months", "total_mandays"],
                        "properties": {
                            "active": {"type": "boolean"},
                            "justification": {"type": "string"},
                            "external_systems_count": {"type": "integer"},
                            "environment_complexity": {"type": "string", "enum": ["simple", "standard", "complex"]},
                            "finops_months": {"type": "number"},
                            "total_mandays": {"type": "number"}
                        }
                    },
                    "cybersecurity": {
                        "type": "object",
                        "required": ["active", "justification", "sensitivity_tier", "security_gates_count", "compliance_addons", "total_mandays"],
                        "properties": {
                            "active": {"type": "boolean"},
                            "justification": {"type": "string"},
                            "sensitivity_tier": {"type": "string", "enum": ["basic", "standard", "critical"]},
                            "security_gates_count": {"type": "integer"},
                            "compliance_addons": {"type": "array", "items": {"type": "string"}},
                            "total_mandays": {"type": "number"}
                        }
                    },
                    "digital_experience": {
                        "type": "object",
                        "required": ["active", "justification", "user_journey_complexity", "accessibility_required", "total_mandays"],
                        "properties": {
                            "active": {"type": "boolean"},
                            "justification": {"type": "string"},
                            "user_journey_complexity": {"type": "string", "enum": ["simple", "transactional", "expert"]},
                            "accessibility_required": {"type": "boolean"},
                            "total_mandays": {"type": "number"}
                        }
                    },
                    "quality_assurance": {
                        "type": "object",
                        "required": ["active", "justification", "verification_points", "criticality_tier", "performance_testing", "total_mandays"],
                        "properties": {
                            "active": {"type": "boolean"},
                            "justification": {"type": "string"},
                            "verification_points": {"type": "integer"},
                            "criticality_tier": {"type": "integer", "enum": [1, 2, 3]},
                            "performance_testing": {"type": "boolean"},
                            "total_mandays": {"type": "number"}
                        }
                    }
                }
            }
        }
    }
}


def build_system_prompt(model_md: str) -> str:
    return f"""You are an expert software project estimator. \
Follow the ESTIMATION MODEL below as the primary methodology reference.

STRICT RULES (structural — always apply):
1. Enumerate EVERY data entity that requires CRUD operations — do not bundle them.
2. List EVERY external API integration separately with direction and complexity.
3. Apply scalability multipliers and formulas EXACTLY as defined in the ESTIMATION MODEL below.
4. Only activate satellites that are GENUINELY needed — justify each with a concrete reason.
5. Flag every technology unknown or legacy integration as a SPIKE with a specific manday cost.
6. When a GitHub codebase is provided, distinguish clearly between existing (no cost) and new components.
7. Return ONLY the tool call — no prose outside the structured output.
8. Use realistic manday estimates: simple CRUD entity ≈ 1–3 md; complex integration ≈ 3–8 md.
9. Produce a complete `roles` list mapping ALL mandays from Core and active Satellites to named roles. Sum must equal grand total.
10. Produce a `plan_phases` list as a realistic sequential weekly schedule. Mandays per role across phases must match role totals.

## ESTIMATION MODEL

{model_md}"""


def build_user_prompt(requirements_md: str, repo_summary: str | None) -> str:
    parts = ["## PROJECT REQUIREMENTS\n\n" + requirements_md]
    if repo_summary:
        parts.append("## CODEBASE ANALYSIS\n\n" + repo_summary)
    return "\n\n---\n\n".join(parts)


def call_claude(
    api_key: str,
    model_md: str,
    requirements_md: str,
    repo_summary: str | None = None,
    claude_model: str = "claude-opus-4-6",
    max_retries: int = 3,
) -> EstimateResult:
    client = Anthropic(api_key=api_key)
    system_prompt = build_system_prompt(model_md)
    user_prompt = build_user_prompt(requirements_md, repo_summary)

    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            logger.info("Claude API call attempt %d/%d", attempt, max_retries)
            response = client.messages.create(
                model=claude_model,
                max_tokens=8192,
                system=system_prompt,
                tools=[PRODUCE_ESTIMATE_TOOL],
                tool_choice={"type": "any"},
                messages=[{"role": "user", "content": user_prompt}],
            )

            # Extract tool_use block
            tool_use_block = next(
                (block for block in response.content if block.type == "tool_use"),
                None,
            )
            if tool_use_block is None:
                raise ValueError("Claude did not return a tool_use block")

            raw_input = tool_use_block.input
            return EstimateResult.model_validate(raw_input)

        except (APIError, ValueError, Exception) as exc:
            last_error = exc
            logger.warning("Attempt %d failed: %s", attempt, exc)
            if attempt < max_retries:
                wait = 2 ** attempt
                logger.info("Retrying in %d seconds…", wait)
                time.sleep(wait)

    raise RuntimeError(f"Claude API failed after {max_retries} attempts: {last_error}") from last_error


# ── Chat refinement ────────────────────────────────────────────────────────────

def _diff_estimates(old: EstimateResult, new: EstimateResult) -> str:
    lines = []
    if abs(old.core.total_mandays - new.core.total_mandays) > 0.01:
        lines.append(f"- **Core**: {old.core.total_mandays:.1f} → {new.core.total_mandays:.1f} mandays")

    sat_pairs = [
        ("PM & Orchestration",       old.satellites.pm_orchestration,    new.satellites.pm_orchestration),
        ("Solution Architecture",    old.satellites.solution_architecture, new.satellites.solution_architecture),
        ("Cybersecurity",            old.satellites.cybersecurity,        new.satellites.cybersecurity),
        ("Digital Experience",       old.satellites.digital_experience,   new.satellites.digital_experience),
        ("Quality Assurance",        old.satellites.quality_assurance,    new.satellites.quality_assurance),
    ]
    for name, o, n in sat_pairs:
        if o.active != n.active:
            lines.append(f"- **{name}**: {'activated' if n.active else 'deactivated'}")
        elif o.active and n.active and abs(o.total_mandays - n.total_mandays) > 0.01:
            lines.append(f"- **{name}**: {o.total_mandays:.1f} → {n.total_mandays:.1f} mandays")

    if not lines:
        return "I've applied the requested changes to the estimate."
    return "Done. Here's what changed:\n\n" + "\n".join(lines)


def chat_with_claude(
    api_key: str,
    message: str,
    chat_history: list[dict],
    current_estimate: EstimateResult,
    claude_model: str = "claude-opus-4-6",
) -> tuple[str, EstimateResult | None]:
    """
    Returns (reply_text, updated_estimate_or_None).
    chat_history is a list of {"role": "user"|"assistant", "content": str}.
    Uses tool_choice=auto: Claude decides whether to update the estimate or just reply.
    """
    client = Anthropic(api_key=api_key)

    system = f"""You are an expert software estimation assistant helping the user refine a project estimate built on the Core & Satellites model.

The user may ask you to:
- Explain any estimation choice or assumption
- Override specific manday values for entities, integrations, or satellites
- Add/remove data entities, API integrations, or SPIKEs
- Activate or deactivate satellite services
- Change the scalability tier

RULES:
- When the user requests a CHANGE: call the `produce_estimate` tool with the COMPLETE updated estimate (all fields). Recompute base_fcu_mandays and total_mandays correctly after any change.
- When the user asks a QUESTION or wants EXPLANATION: reply with plain text — do NOT call the tool.
- When updating the estimate, also update `roles` and `plan_phases` to reflect the changes.
- Be concise and precise.

## Current Estimate
```json
{current_estimate.model_dump_json(indent=2)}
```"""

    messages = list(chat_history) + [{"role": "user", "content": message}]

    response = client.messages.create(
        model=claude_model,
        max_tokens=4096,
        system=system,
        tools=[PRODUCE_ESTIMATE_TOOL],
        tool_choice={"type": "auto"},
        messages=messages,
    )

    reply_text = ""
    updated_estimate: EstimateResult | None = None

    for block in response.content:
        if block.type == "text":
            reply_text += block.text
        elif block.type == "tool_use":
            try:
                updated_estimate = EstimateResult.model_validate(block.input)
            except Exception as exc:
                logger.warning("Chat tool call returned an incomplete estimate, ignoring: %s", exc)

    # If only a tool call was returned (no prose), generate a diff summary
    if updated_estimate is not None and not reply_text.strip():
        reply_text = _diff_estimates(current_estimate, updated_estimate)

    return reply_text.strip(), updated_estimate
