"""Unit tests for export helpers (no model download)."""

from __future__ import annotations

import json
from pathlib import Path

from crisper_timestamps.export import (
    TranscriptResult,
    WordTiming,
    words_to_cues,
    write_all,
    write_json,
    write_srt,
    write_tsv,
    write_vtt,
)


def _sample_words() -> list[WordTiming]:
    return [
        WordTiming("Hallo", 0.00, 0.35),
        WordTiming("Welt", 0.40, 0.80),
        WordTiming("das", 1.50, 1.70),
        WordTiming("ist", 1.75, 1.95),
        WordTiming("ein", 2.00, 2.15),
        WordTiming("Test", 2.20, 2.60),
    ]


def test_words_to_cues_splits_on_gap():
    cues = words_to_cues(_sample_words(), max_gap=0.6)
    assert len(cues) == 2
    assert cues[0][2] == "Hallo Welt"
    assert cues[1][2] == "das ist ein Test"


def test_write_json_roundtrip(tmp_path: Path):
    result = TranscriptResult(
        text="Hallo Welt",
        language="de",
        mode="verbatim",
        duration=3.0,
        processing_time=0.5,
        words=_sample_words()[:2],
        source="x.wav",
        model="turbo",
    )
    path = write_json(result, tmp_path / "out.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["word_count"] == 2
    assert data["words"][0]["word"] == "Hallo"
    assert abs(data["words"][0]["start"] - 0.0) < 1e-9


def test_write_tsv_and_srt_vtt(tmp_path: Path):
    words = _sample_words()
    tsv = write_tsv(words, tmp_path / "a.tsv")
    lines = tsv.read_text(encoding="utf-8").strip().splitlines()
    assert lines[0] == "start\tend\tword"
    assert "Hallo" in lines[1]

    srt = write_srt(words, tmp_path / "a.srt")
    srt_text = srt.read_text(encoding="utf-8")
    assert "-->" in srt_text
    assert "," in srt_text  # SRT uses comma for ms

    vtt = write_vtt(words, tmp_path / "a.vtt")
    vtt_text = vtt.read_text(encoding="utf-8")
    assert vtt_text.startswith("WEBVTT")
    assert "." in vtt_text.splitlines()[2]  # VTT uses dot


def test_write_all(tmp_path: Path):
    result = TranscriptResult(
        text="Hallo",
        language="de",
        mode="verbatim",
        duration=1.0,
        processing_time=0.1,
        words=_sample_words()[:1],
        source="x.wav",
        model="turbo",
    )
    written = write_all(result, tmp_path, "clip", formats=("json", "tsv", "txt"))
    assert set(written) == {"json", "tsv", "txt"}
    assert (tmp_path / "clip.txt").read_text(encoding="utf-8").startswith("Hallo")
