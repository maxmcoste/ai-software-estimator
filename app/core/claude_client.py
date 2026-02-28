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
        "required": ["project_name", "project_summary", "core", "satellites", "overall_reasoning"],
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
            "satellites": {
                "type": "object",
                "required": ["pm_orchestration", "solution_architecture", "cybersecurity", "digital_experience", "quality_assurance"],
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


def build_system_prompt() -> str:
    return """You are an expert software project estimator specializing in the Core & Satellites model for the post-GenAI era.

STRICT RULES:
1. Enumerate EVERY data entity that requires CRUD operations — do not bundle them.
2. List EVERY external API integration separately with direction and complexity.
3. Apply scalability multipliers exactly as specified in the model: low=1.0x, medium=1.3x, high=1.8x.
4. Only activate satellites that are GENUINELY needed for this project — justify each with a concrete reason.
5. Flag every technology unknown or legacy integration as a SPIKE with a specific manday cost.
6. When a GitHub codebase is provided, distinguish clearly between existing components (no cost) and new components to build.
7. Base FCU mandays = sum of all data entity mandays + sum of API integration mandays + business_logic_mandays.
8. Total core mandays = (base_fcu_mandays × scalability_multiplier) + sum of all spike mandays.
9. Return ONLY the tool call — no prose, no explanation outside the structured output.
10. Use realistic manday estimates: a simple CRUD entity ≈ 1-3 mandays; a complex integration ≈ 3-8 mandays."""


def build_user_prompt(model_md: str, requirements_md: str, repo_summary: str | None) -> str:
    parts = [
        "## ESTIMATION MODEL\n\n" + model_md,
        "## PROJECT REQUIREMENTS\n\n" + requirements_md,
    ]
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
    system_prompt = build_system_prompt()
    user_prompt = build_user_prompt(model_md, requirements_md, repo_summary)

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
