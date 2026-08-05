#!/usr/bin/env python3
"""Minimal consumer: load handoff.json and print word rows from track JSONs."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(
            "Usage: consume_handoff.py path/to/handoff.json",
            file=sys.stderr,
        )
        return 2

    handoff_path = Path(argv[1]).expanduser().resolve()
    if not handoff_path.is_file():
        print(f"Not found: {handoff_path}", file=sys.stderr)
        return 2

    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    schema = handoff.get("schema", "")
    if not str(schema).startswith("crisper-timestamps.handoff"):
        print(f"Warning: unexpected schema {schema!r}", file=sys.stderr)

    base = handoff_path.parent
    summary = handoff.get("summary") or {}
    print(f"id={handoff.get('id')} schema={schema}")
    print(
        f"tracks={summary.get('track_count')} "
        f"with_words={summary.get('tracks_with_words')} "
        f"total_words={summary.get('total_words')}"
    )
    print("-" * 60)

    for track in handoff.get("tracks") or []:
        stem = track.get("stem") or track.get("id")
        wc = int(track.get("word_count") or 0)
        if wc == 0:
            print(f"[{stem}] (empty / instrumental)")
            continue

        rel = (track.get("artifacts_relative") or {}).get("json")
        abs_json = (track.get("artifacts") or {}).get("json")
        json_path = (base / rel) if rel else (Path(abs_json) if abs_json else None)
        if json_path is None or not json_path.is_file():
            print(f"[{stem}] missing json artifact", file=sys.stderr)
            continue

        data = json.loads(json_path.read_text(encoding="utf-8"))
        words = data.get("words") or []
        print(f"[{stem}] {len(words)} words — {data.get('text', '')[:80]!r}")
        for w in words[:5]:
            print(f"  {w['start']:7.3f}-{w['end']:7.3f}  {w['word']}")
        if len(words) > 5:
            print(f"  … +{len(words) - 5} more")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
