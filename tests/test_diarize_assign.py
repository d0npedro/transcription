"""Tests for speaker assignment from diarization segments."""

from __future__ import annotations

from crisper_timestamps.diarize import assign_speakers


def test_assigns_by_max_overlap():
    words = [{"word": "a", "start": 0.0, "end": 0.5}, {"word": "b", "start": 1.0, "end": 1.5}]
    segs = [
        {"id": "speaker_00", "start": 0.0, "end": 0.8},
        {"id": "speaker_01", "start": 0.8, "end": 2.0},
    ]
    out = assign_speakers(words, segs)
    assert out[0]["speaker"] == "speaker_00"
    assert out[1]["speaker"] == "speaker_01"


def test_no_overlap_unknown():
    words = [{"word": "x", "start": 9.0, "end": 9.2}]
    out = assign_speakers(words, [])
    assert out[0]["speaker"] == "speaker_unknown"


def test_zero_overlap_with_segments_unknown():
    """Word outside all diarization segments must stay speaker_unknown."""
    words = [{"word": "x", "start": 9.0, "end": 9.2}]
    segs = [
        {"id": "speaker_00", "start": 0.0, "end": 1.0},
        {"id": "speaker_01", "start": 2.0, "end": 3.0},
    ]
    out = assign_speakers(words, segs)
    assert out[0]["speaker"] == "speaker_unknown"


def test_tie_prefers_lexicographically_smaller_id():
    words = [{"word": "t", "start": 0.0, "end": 1.0}]
    segs = [
        {"id": "speaker_01", "start": 0.0, "end": 1.0},
        {"id": "speaker_00", "start": 0.0, "end": 1.0},
    ]
    out = assign_speakers(words, segs)
    assert out[0]["speaker"] == "speaker_00"
