"""Unified job store.

Local dev  → reads/writes data/jobs.json as a plain file.
Render/CI  → reads/writes data/jobs.json via GitHub API
            (set GITHUB_TOKEN + GITHUB_REPO env vars).

Provides the same interface as bot/db.py so callers can swap freely.
"""
import base64
import json
import os
import time
from datetime import date
from pathlib import Path
from urllib.parse import urlparse, urlunparse


def _norm(url: str) -> str:
    if not url:
        return url
    p = urlparse(url)
    return urlunparse((p.scheme, p.netloc, p.path, "", "", ""))

import requests

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO  = os.getenv("GITHUB_REPO", "juliaonmoon/job-search-bot")
DATA_FILE    = "data/jobs.json"
LOCAL_PATH   = Path(__file__).parent.parent / DATA_FILE

USE_GITHUB   = bool(GITHUB_TOKEN)

# In-memory cache so we don't hammer the GitHub API on every request
_cache: dict = {"data": None, "sha": None, "ts": 0.0}
CACHE_TTL = 30  # seconds


# ── GitHub helpers ────────────────────────────────────────────────────────────

def _gh_headers() -> dict:
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }


def _gh_load() -> dict:
    """Load from GitHub; return raw store dict."""
    now = time.time()
    if _cache["data"] is not None and now - _cache["ts"] < CACHE_TTL:
        return _cache["data"]

    r = requests.get(
        f"https://api.github.com/repos/{GITHUB_REPO}/contents/{DATA_FILE}",
        headers=_gh_headers(), timeout=10,
    )
    if r.status_code == 404:
        store = {"next_id": 1, "jobs": []}
    else:
        r.raise_for_status()
        body = r.json()
        _cache["sha"] = body["sha"]
        store = json.loads(base64.b64decode(body["content"]))

    _cache["data"] = store
    _cache["ts"] = now
    return store


def _gh_save(store: dict, message: str = "Update jobs") -> bool:
    """Write store dict back to GitHub (retries on SHA conflict)."""
    for _ in range(3):
        # Refresh SHA before each attempt
        r = requests.get(
            f"https://api.github.com/repos/{GITHUB_REPO}/contents/{DATA_FILE}",
            headers=_gh_headers(), timeout=10,
        )
        sha = r.json().get("sha") if r.ok else None

        content = base64.b64encode(
            json.dumps(store, indent=2, ensure_ascii=False).encode()
        ).decode()
        payload: dict = {"message": message, "content": content}
        if sha:
            payload["sha"] = sha

        w = requests.put(
            f"https://api.github.com/repos/{GITHUB_REPO}/contents/{DATA_FILE}",
            headers=_gh_headers(), json=payload, timeout=15,
        )
        if w.ok:
            _cache["sha"] = w.json()["content"]["sha"]
            _cache["data"] = store
            _cache["ts"] = time.time()
            return True
        if w.status_code == 409:
            time.sleep(1)
            continue
        break
    return False


# ── Local file helpers ────────────────────────────────────────────────────────

def _local_load() -> dict:
    LOCAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    if LOCAL_PATH.exists():
        return json.loads(LOCAL_PATH.read_text(encoding="utf-8"))
    return {"next_id": 1, "jobs": []}


def _local_save(store: dict) -> None:
    LOCAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOCAL_PATH.write_text(
        json.dumps(store, indent=2, ensure_ascii=False), encoding="utf-8"
    )


# ── Routing ───────────────────────────────────────────────────────────────────

def _load() -> dict:
    return _gh_load() if USE_GITHUB else _local_load()


def _save(store: dict, message: str = "Update jobs") -> None:
    if USE_GITHUB:
        _gh_save(store, message)
    else:
        _local_save(store)


# ── Public API (mirrors bot/db.py) ────────────────────────────────────────────

def init_db():
    """No-op — store is created on first write."""
    if not USE_GITHUB and not LOCAL_PATH.exists():
        _save({"next_id": 1, "jobs": []})


def add_job(title, company, location, url, source,
            jd_snippet="", salary_text="", score=0,
            jd_full="", daily_batch="", date_posted="") -> bool:
    """Add a job if URL not already present. Returns True if new."""
    store = _load()
    url = _norm(url)
    if any(_norm(j["url"]) == url for j in store["jobs"]):
        return False
    job = {
        "id":           store["next_id"],
        "title":        title,
        "company":      company,
        "location":     location or "",
        "url":          url,
        "source":       source,
        "status":       "found",
        "date_found":   date.today().isoformat(),
        "date_posted":  date_posted,
        "date_applied": None,
        "notes":        None,
        "contact":      None,
        "follow_up":    None,
        "persona":      None,
        "jd_snippet":   jd_snippet,
        "salary_text":  salary_text,
        "score":        score,
        "jd_full":      jd_full,
        "tailor_output": None,
        "cover_output":  None,
        "daily_batch":  daily_batch,
    }
    store["jobs"].append(job)
    store["next_id"] += 1
    _save(store, f"Add job: {title} at {company}")
    return True


def get_job(job_id: int) -> dict | None:
    store = _load()
    for j in store["jobs"]:
        if j["id"] == job_id:
            return dict(j)
    return None


def update_status(job_id: int, status: str, notes=None, contact=None, follow_up=None):
    store = _load()
    for j in store["jobs"]:
        if j["id"] == job_id:
            j["status"] = status
            if status == "applied":
                j["date_applied"] = date.today().isoformat()
            if notes is not None:
                j["notes"] = notes
            if contact is not None:
                j["contact"] = contact
            if follow_up is not None:
                j["follow_up"] = follow_up
            break
    _save(store, f"Status → {status} (job {job_id})")


def save_tailor(job_id: int, tailor_output: str, persona: str | None = None):
    store = _load()
    for j in store["jobs"]:
        if j["id"] == job_id:
            j["tailor_output"] = tailor_output
            if persona:
                j["persona"] = persona
            break
    _save(store, f"Tailor saved (job {job_id})")


def save_cover(job_id: int, cover_output: str):
    store = _load()
    for j in store["jobs"]:
        if j["id"] == job_id:
            j["cover_output"] = cover_output
            break
    _save(store, f"Cover saved (job {job_id})")


def list_jobs(status: str | None = None, limit: int = 200) -> list[dict]:
    store = _load()
    jobs = store["jobs"]
    if status:
        jobs = [j for j in jobs if j.get("status") == status]
    jobs = sorted(jobs, key=lambda j: (-(j.get("score") or 0), j.get("date_found") or ""))
    return [dict(j) for j in jobs[:limit]]


def get_stats() -> dict:
    store = _load()
    counts: dict = {}
    for j in store["jobs"]:
        s = j.get("status", "found")
        counts[s] = counts.get(s, 0) + 1
    return counts
