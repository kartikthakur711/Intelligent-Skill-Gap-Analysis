"""Small, file-backed learning progress store for local/single-instance use."""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path


SCHEMA_VERSION = 1
MAX_STORE_BYTES = 5 * 1024 * 1024
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")


class ProgressStoreError(ValueError):
    """Raised when progress data is invalid or cannot be safely updated."""


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _profile_id(profile: str) -> str:
    label = " ".join(str(profile).split()).casefold()
    if not label or len(label) > 80:
        raise ProgressStoreError("Choose a progress profile between 1 and 80 characters.")
    return _digest(label)


def _plan_id(job_title: str, roadmap, normalize_skill) -> str:
    payload = {
        "job": " ".join(str(job_title).split()).casefold(),
        "skills": [normalize_skill(skill) for skill in roadmap if normalize_skill(skill)],
    }
    return _digest(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))


def _empty_store():
    return {"schema_version": SCHEMA_VERSION, "profiles": {}}


def _validate_store(data):
    if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION:
        raise ProgressStoreError("Progress file has an unsupported format; it was left unchanged.")
    profiles = data.get("profiles")
    if not isinstance(profiles, dict):
        raise ProgressStoreError("Progress file is invalid; it was left unchanged.")
    for profile_id, profile in profiles.items():
        if not _HASH_RE.fullmatch(profile_id) or not isinstance(profile, dict):
            raise ProgressStoreError("Progress file is invalid; it was left unchanged.")
        plans = profile.get("plans")
        if not isinstance(plans, dict):
            raise ProgressStoreError("Progress file is invalid; it was left unchanged.")
        for plan_id, record in plans.items():
            if (
                not _HASH_RE.fullmatch(plan_id)
                or not isinstance(record, dict)
                or not isinstance(record.get("completed_skills"), list)
                or not all(isinstance(skill, str) for skill in record["completed_skills"])
                or not isinstance(record.get("updated_at"), str)
            ):
                raise ProgressStoreError("Progress file is invalid; it was left unchanged.")
    return data


def _read_store(path: Path):
    if not path.exists():
        return _empty_store()
    try:
        if path.stat().st_size > MAX_STORE_BYTES:
            raise ProgressStoreError("Progress file is too large; it was left unchanged.")
        with path.open("r", encoding="utf-8") as handle:
            return _validate_store(json.load(handle))
    except ProgressStoreError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProgressStoreError("Progress file could not be read safely; it was left unchanged.") from exc


def load_progress(path, profile, job_title, roadmap, normalize_skill):
    """Return the completed roadmap labels for one profile and plan."""
    store = _read_store(Path(path))
    record = store["profiles"].get(_profile_id(profile), {}).get("plans", {}).get(
        _plan_id(job_title, roadmap, normalize_skill), {}
    )
    completed = set(record.get("completed_skills", []))
    return [skill for skill in roadmap if normalize_skill(skill) in completed]


def summarize_progress(path):
    """Summarize saved records without returning profile or plan identifiers."""
    store = _read_store(Path(path))
    records = [
        record
        for profile in store["profiles"].values()
        for record in profile["plans"].values()
    ]
    timestamps = [record["updated_at"] for record in records if record["updated_at"]]
    return {
        "saved_plan_count": len(records),
        "completed_step_count": sum(len(record["completed_skills"]) for record in records),
        "last_updated": max(timestamps, default=None),
    }


def save_progress(path, profile, job_title, roadmap, completed_skills, normalize_skill):
    """Atomically save completion state without storing the profile label."""
    target = Path(path)
    profile_id = _profile_id(profile)
    plan_id = _plan_id(job_title, roadmap, normalize_skill)
    allowed = {normalize_skill(skill) for skill in roadmap if normalize_skill(skill)}
    completed = sorted({normalize_skill(skill) for skill in completed_skills} & allowed)
    store = _read_store(target)
    profile_record = store["profiles"].setdefault(profile_id, {"plans": {}})
    profile_record["plans"][plan_id] = {
        "completed_skills": completed,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    temporary_path = None
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=target.parent,
            prefix=f".{target.name}.", suffix=".tmp", delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            json.dump(store, handle, ensure_ascii=False, separators=(",", ":"))
            handle.flush()
            os.fsync(handle.fileno())
        if temporary_path.stat().st_size > MAX_STORE_BYTES:
            raise ProgressStoreError("Progress data is too large to save.")
        os.replace(temporary_path, target)
    except ProgressStoreError:
        raise
    except OSError as exc:
        raise ProgressStoreError("Progress could not be saved. Check the storage location and permissions.") from exc
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
