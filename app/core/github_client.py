from __future__ import annotations
import re
import logging
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

SKIP_DIRS = {"node_modules", ".git", "dist", "build", "vendor", "__pycache__", ".next", "coverage"}
MAX_FILE_LINES = 200
MAX_TOTAL_CHARS = 80_000

# Priority: docs first, then source, then configs
PRIORITY_EXTENSIONS = [
    ".md", ".rst", ".txt",
    ".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".java", ".rb", ".rs", ".cs", ".cpp", ".c",
    ".json", ".yaml", ".yml", ".toml", ".env.example",
]


def _parse_github_url(url: str) -> tuple[str, str, str]:
    """Return (owner, repo, branch). Branch defaults to 'main'."""
    url = url.rstrip("/")
    # Support https://github.com/owner/repo or https://github.com/owner/repo/tree/branch
    match = re.match(
        r"https?://github\.com/([^/]+)/([^/]+)(?:/tree/([^/]+))?",
        url,
    )
    if not match:
        raise ValueError(f"Cannot parse GitHub URL: {url}")
    owner, repo, branch = match.group(1), match.group(2), match.group(3) or "main"
    repo = repo.removesuffix(".git")
    return owner, repo, branch


def _extension_priority(path: str) -> int:
    for i, ext in enumerate(PRIORITY_EXTENSIONS):
        if path.endswith(ext):
            return i
    return len(PRIORITY_EXTENSIONS)


def _should_skip(path: str) -> bool:
    parts = path.split("/")
    return any(part in SKIP_DIRS for part in parts)


def _fetch_tree_via_api(owner: str, repo: str, branch: str, token: str) -> list[dict]:
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
    with httpx.Client(timeout=30) as client:
        resp = client.get(url, headers=headers)
        resp.raise_for_status()
    data = resp.json()
    return [item for item in data.get("tree", []) if item.get("type") == "blob"]


def _fetch_file_content(owner: str, repo: str, path: str, branch: str, token: str) -> str:
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
    with httpx.Client(timeout=15) as client:
        resp = client.get(url, headers=headers)
        resp.raise_for_status()
    lines = resp.text.splitlines()
    if len(lines) > MAX_FILE_LINES:
        lines = lines[:MAX_FILE_LINES]
        lines.append(f"[truncated after {MAX_FILE_LINES} lines]")
    return "\n".join(lines)


def fetch_repo_summary(github_url: str, token: str = "") -> tuple[str, str]:
    """
    Fetch a codebase summary string and an optional warning message.
    Returns (summary, warning). warning is empty string on success.
    """
    try:
        owner, repo, branch = _parse_github_url(github_url)
    except ValueError as exc:
        return "", str(exc)

    try:
        blobs = _fetch_tree_via_api(owner, repo, branch, token)
    except Exception as exc:
        logger.warning("GitHub tree fetch failed: %s", exc)
        return "", f"GitHub fetch failed: {exc}"

    # Filter and sort by priority
    blobs = [b for b in blobs if not _should_skip(b["path"])]
    blobs.sort(key=lambda b: _extension_priority(b["path"]))

    sections: list[str] = [f"# Repository: {owner}/{repo} (branch: {branch})\n"]
    total_chars = len(sections[0])

    for blob in blobs:
        path = blob["path"]
        try:
            content = _fetch_file_content(owner, repo, path, branch, token)
        except Exception as exc:
            logger.debug("Skipping %s: %s", path, exc)
            continue

        chunk = f"\n## {path}\n```\n{content}\n```\n"
        if total_chars + len(chunk) > MAX_TOTAL_CHARS:
            sections.append(f"\n[Repository summary truncated at {MAX_TOTAL_CHARS} characters]")
            break
        sections.append(chunk)
        total_chars += len(chunk)

    return "".join(sections), ""
