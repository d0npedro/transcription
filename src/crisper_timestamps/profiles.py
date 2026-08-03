"""Quality profiles — frozen settings that define repeatable runs."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

# Keys that callers may override without breaking the quality lock
OVERRIDABLE = frozenset(
    {
        "model",
        "language",
        "mode",
        "backend",
        "device",
        "compute_type",
        "jobs",
    }
)

# Quality lock fields — never weakened by casual flags
LOCKED_KEYS = frozenset(
    {
        "word_timestamps",
        "speculative_decoding",
        "longform_strategy",
        "hallucination_mitigation",
        "formats",
        "write_handoff",
    }
)


def profiles_dir() -> Path:
    """Return filesystem path to bundled profiles (dev-friendly)."""
    # Prefer package resources; fall back to sibling dir next to this file
    here = Path(__file__).resolve().parent / "profiles"
    if here.is_dir():
        return here
    raise FileNotFoundError("profiles/ package data missing")


def list_profiles() -> list[str]:
    return sorted(p.stem for p in profiles_dir().glob("*.json"))


def _load_raw(profile_id: str) -> dict[str, Any]:
    path = profiles_dir() / f"{profile_id}.json"
    if not path.is_file():
        known = ", ".join(list_profiles()) or "(none)"
        raise FileNotFoundError(
            f"Unbekanntes Profil '{profile_id}'. Verfügbar: {known}"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def load_profile(profile_id: str) -> dict[str, Any]:
    """
    Load profile with optional 'extends' merge.
    Child defaults/quality_lock/project overlay parent.
    """
    raw = _load_raw(profile_id)
    if "extends" in raw:
        parent = load_profile(str(raw["extends"]))
        merged = deepcopy(parent)
        for key in ("defaults", "quality_lock", "project"):
            if key in raw and isinstance(raw[key], dict):
                base = merged.get(key) or {}
                base = deepcopy(base)
                base.update(raw[key])
                merged[key] = base
        for key in ("id", "title", "description", "notes"):
            if key in raw:
                merged[key] = raw[key]
        return merged
    return raw


def resolve_run_config(
    profile_id: str,
    *,
    overrides: dict[str, Any] | None = None,
    unlock: bool = False,
) -> dict[str, Any]:
    """
    Merge profile defaults + quality_lock + safe overrides into a flat run config.

    Quality lock always wins over overrides unless unlock=True
    (still keeps word_timestamps=True and speculative_decoding=False as hard floor).
    """
    profile = load_profile(profile_id)
    cfg: dict[str, Any] = {}
    cfg.update(profile.get("defaults") or {})
    lock = dict(profile.get("quality_lock") or {})
    cfg.update(lock)

    overrides = overrides or {}
    for k, v in overrides.items():
        if v is None:
            continue
        if k in LOCKED_KEYS and not unlock:
            continue
        if k in OVERRIDABLE or unlock:
            cfg[k] = v

    # Hard floor — never disable exact timestamps or enable speculative (timing drift)
    cfg["word_timestamps"] = True
    cfg["speculative_decoding"] = False
    if not unlock:
        cfg["longform_strategy"] = lock.get("longform_strategy", "continuation")
        cfg["hallucination_mitigation"] = lock.get("hallucination_mitigation", True)
        cfg["formats"] = list(lock.get("formats") or ["json", "tsv", "srt", "vtt", "txt"])
        cfg["write_handoff"] = True

    cfg["profile_id"] = profile.get("id", profile_id)
    cfg["profile_title"] = profile.get("title", profile_id)
    cfg["project"] = profile.get("project") or {}
    cfg["notes"] = profile.get("notes") or []
    return cfg


def profile_summary(profile_id: str) -> str:
    p = load_profile(profile_id)
    d = p.get("defaults") or {}
    q = p.get("quality_lock") or {}
    lines = [
        f"{p.get('id')}: {p.get('title')}",
        f"  {p.get('description', '')}",
        f"  model={d.get('model')} language={d.get('language')} mode={d.get('mode')}",
        f"  lock: longform={q.get('longform_strategy')} "
        f"speculative={q.get('speculative_decoding')} "
        f"formats={','.join(q.get('formats') or [])}",
    ]
    return "\n".join(lines)
