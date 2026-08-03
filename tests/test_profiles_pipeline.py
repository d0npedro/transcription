"""Tests for quality profiles and deploy path resolution (no model)."""

from __future__ import annotations

from pathlib import Path

import pytest

from crisper_timestamps.pipeline import find_audio_dir, resolve_deploy_dir
from crisper_timestamps.profiles import list_profiles, load_profile, resolve_run_config


def test_list_profiles_contains_album():
    ids = list_profiles()
    assert "album" in ids
    assert "speech-de" in ids
    assert "album-hq" in ids


def test_album_quality_lock():
    cfg = resolve_run_config("album")
    assert cfg["word_timestamps"] is True
    assert cfg["speculative_decoding"] is False
    assert cfg["longform_strategy"] == "continuation"
    assert cfg["write_handoff"] is True
    assert cfg["language"] == "en"
    assert cfg["mode"] == "intended"
    assert "json" in cfg["formats"]


def test_overrides_cannot_break_lock():
    cfg = resolve_run_config(
        "album",
        overrides={
            "language": "de",
            "speculative_decoding": True,  # must be ignored
            "longform_strategy": "chunked_lcs",  # must be ignored
        },
    )
    assert cfg["language"] == "de"
    assert cfg["speculative_decoding"] is False
    assert cfg["longform_strategy"] == "continuation"


def test_album_hq_extends_album():
    p = load_profile("album-hq")
    assert p["defaults"]["model"] == "medium"
    assert p["quality_lock"]["word_timestamps"] is True


def test_find_audio_and_deploy(tmp_path: Path):
    (tmp_path / "01 WAV Masters").mkdir()
    (tmp_path / "02 Metadata").mkdir()
    found = find_audio_dir(tmp_path, ["01 WAV Masters", "wav"])
    assert found is not None
    assert found.name == "01 WAV Masters"

    # next free number
    d1 = resolve_deploy_dir(tmp_path, prefer_existing_named=None)
    assert d1.name == "03 Timestamps"

    # reuse existing Timestamps
    (tmp_path / "06 Timestamps").mkdir()
    d2 = resolve_deploy_dir(tmp_path, prefer_existing_named="Timestamps")
    assert d2.name == "06 Timestamps"
