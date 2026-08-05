"""Ensure shipped examples stay valid against real handoff consumer code."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from crisper_timestamps.handoff import SCHEMA_ID, discover_tracks, write_handoff

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "examples" / "fixtures" / "sample-track"
MOCK_HANDOFF = (
    ROOT
    / "examples"
    / "02-album-layout"
    / "mock-project"
    / "06 Timestamps"
    / "handoff.json"
)
CONSUMER = ROOT / "examples" / "03-handoff-consumer" / "consume_handoff.py"


def test_fixture_tracks_discoverable():
    tracks = discover_tracks(FIXTURES)
    assert len(tracks) >= 2
    with_words = [t for t in tracks if t["word_count"] > 0]
    empty = [t for t in tracks if t["word_count"] == 0]
    assert with_words, "expected at least one non-empty sample track"
    assert empty, "expected instrumental empty track example"


def test_write_handoff_from_fixtures(tmp_path: Path):
    # Copy fixtures then run real handoff writer
    dest = tmp_path / "out"
    dest.mkdir()
    for p in FIXTURES.glob("*"):
        if p.is_file() and p.name not in ("handoff.json", "HANDOFF.md"):
            (dest / p.name).write_bytes(p.read_bytes())
    written = write_handoff(
        dest,
        handoff_id="test-examples",
        model="turbo",
        language="en",
        mode="intended",
    )
    data = json.loads(written["handoff_json"].read_text(encoding="utf-8"))
    assert data["schema"] == SCHEMA_ID
    assert data["summary"]["track_count"] == 2
    assert data["summary"]["total_words"] == 13


def test_shipped_mock_handoff_and_consumer():
    assert MOCK_HANDOFF.is_file(), "commit mock-project handoff.json"
    data = json.loads(MOCK_HANDOFF.read_text(encoding="utf-8"))
    assert data["schema"].startswith("crisper-timestamps.handoff")
    assert data["summary"]["track_count"] >= 1

    proc = subprocess.run(
        [sys.executable, str(CONSUMER), str(MOCK_HANDOFF)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "Sample Intro" in proc.stdout or "sample" in proc.stdout.lower()
    assert "words" in proc.stdout.lower() or "13" in proc.stdout
