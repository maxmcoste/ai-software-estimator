from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.models.estimate import EstimateResult, FinancialSummary

_TEMPLATE_DIR = Path(__file__).parent.parent / "templates"


def _get_jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=select_autoescape(disabled_extensions=("j2",)),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def generate_report(
    estimate: EstimateResult,
    financials: FinancialSummary,
    report_path: Path,
    github_warning: str = "",
) -> None:
    env = _get_jinja_env()
    template = env.get_template("report_template.md.j2")
    rendered = template.render(
        estimate=estimate,
        financials=financials,
        github_warning=github_warning,
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )
    report_path.write_text(rendered, encoding="utf-8")
