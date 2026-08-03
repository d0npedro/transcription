"""Tests for handoff package generation."""

from __future__ import annotations

import json
from pathlib import Path

from crisper_timestamps.handoff import (
    SCHEMA_ID,
    build_handoff,
    render_handoff_md,
    write_handoff,
)


def _seed_track(out: Path, stem: str, words: list[dict], text: str = "hello") -> None:
    payload = {
        "source": f"F:/audio/{stem}.wav",
        "model": "turbo",
        "text": text,
        "language": "en",
        "mode": "intended",
        "duration": 12.5,
        "processing_time": 1.0,
        "words": words,
        "word_count": len(words),
    }
    (out / f"{stem}.json").write_text(json.dumps(payload), encoding="utf-8")
    (out / f"{stem}.tsv").write_text("start\tend\tword\n0.0\t0.5\thello\n", encoding="utf-8")
    (out / f"{stem}.txt").write_text(text + "\n", encoding="utf-8")


def test_write_handoff_creates_manifest_and_markup(tmp_path: Path):
    out = tmp_path / "batch"
    out.mkdir()
    _seed_track(
        out,
        "01 - Intro",
        [{"word": "Hey", "start": 0.1, "end": 0.4}, {"word": "there", "start": 0.4, "end": 0.8}],
        text="Hey there",
    )
    _seed_track(out, "02 - Empty", [], text="")

    written = write_handoff(
        out,
        handoff_id="demo-album",
        source_path=r"F:\Masters",
        model="turbo",
        language="en",
        mode="intended",
        project_hint=r"D:\OtherApp\assets\timestamps\demo-album",
    )
    assert written["handoff_json"].is_file()
    assert written["handoff_md"].is_file()

    data = json.loads(written["handoff_json"].read_text(encoding="utf-8"))
    assert data["schema"] == SCHEMA_ID
    assert data["id"] == "demo-album"
    assert data["summary"]["track_count"] == 2
    assert data["summary"]["tracks_with_words"] == 1
    assert data["summary"]["total_words"] == 2
    assert data["tracks"][0]["artifacts_relative"]["json"] == "01 - Intro.json"
    assert "copy_to_other_project" in data["import"]
    assert "powershell" in data["import"]["copy_to_other_project"]

    md = written["handoff_md"].read_text(encoding="utf-8")
    assert "<timestamp-handoff" in md
    assert "handoff.json" in md
    assert "demo-album" in md


def test_copy_to_other_project(tmp_path: Path):
    src = tmp_path / "out"
    dest = tmp_path / "other-project" / "timestamps"
    src.mkdir(parents=True)
    _seed_track(src, "track-a", [{"word": "a", "start": 0.0, "end": 0.2}])

    written = write_handoff(src, handoff_id="x", copy_to=dest)
    assert written["copied_to"] == dest.resolve()
    assert (dest / "handoff.json").is_file()
    assert (dest / "track-a.json").is_file()
    assert (dest / "HANDOFF.md").is_file()


def test_build_and_render_roundtrip(tmp_path: Path):
    out = tmp_path / "o"
    out.mkdir()
    _seed_track(out, "t", [{"word": "x", "start": 1.0, "end": 1.2}])
    h = build_handoff(out, handoff_id="t1")
    md = render_handoff_md(h)
    assert "Word-Schema" in md
    assert h["tracks"][0]["word_count"] == 1
