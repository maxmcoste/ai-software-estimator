from __future__ import annotations
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

SAVES_DIR = Path("saves")


def _path(save_id: str) -> Path:
    return SAVES_DIR / f"{save_id}.json"


def create_save(
    name: str,
    requirements_md: str,
    model_md: str,
    report_markdown: str,
    estimate_data: dict,
    financials_data: dict,
) -> dict:
    SAVES_DIR.mkdir(exist_ok=True)
    save_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    data = {
        "save_id": save_id,
        "name": name,
        "status": "draft",
        "created_at": now,
        "updated_at": now,
        "requirements_md": requirements_md,
        "model_md": model_md,
        "report_markdown": report_markdown,
        "estimate_data": estimate_data,
        "financials_data": financials_data,
    }
    _path(save_id).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return data


def get_save(save_id: str) -> Optional[dict]:
    p = _path(save_id)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def list_saves() -> list[dict]:
    SAVES_DIR.mkdir(exist_ok=True)
    saves = []
    for f in sorted(SAVES_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            saves.append({
                "save_id":      data["save_id"],
                "name":         data["name"],
                "status":       data["status"],
                "created_at":   data["created_at"],
                "updated_at":   data["updated_at"],
                "project_name": data["estimate_data"].get("project_name", ""),
                "grand_mandays": data["financials_data"].get("grand_mandays", 0),
                "grand_cost":   data["financials_data"].get("grand_cost", 0),
                "currency":     data["financials_data"].get("currency", ""),
            })
        except Exception:
            continue
    return saves


def finalize_save(save_id: str) -> Optional[dict]:
    data = get_save(save_id)
    if data is None:
        return None
    if data["status"] == "final":
        return data
    data["status"] = "final"
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    _path(save_id).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return data


def update_save(save_id: str, report_markdown: str, estimate_data: dict, financials_data: dict) -> Optional[dict]:
    """Update an existing draft save. Returns None if not found or finalized."""
    data = get_save(save_id)
    if data is None or data["status"] == "final":
        return None
    data["report_markdown"] = report_markdown
    data["estimate_data"] = estimate_data
    data["financials_data"] = financials_data
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    _path(save_id).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return data


def delete_save(save_id: str) -> bool:
    """Delete only if draft. Returns True on success."""
    data = get_save(save_id)
    if data is None:
        return False
    if data["status"] == "final":
        return False
    _path(save_id).unlink()
    return True
