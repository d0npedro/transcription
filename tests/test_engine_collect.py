"""Tests for audio discovery (no model)."""

from pathlib import Path

import pytest

from crisper_timestamps.engine import collect_audio_files, is_audio_file, resolve_backend


def test_is_audio_file(tmp_path: Path):
    wav = tmp_path / "a.wav"
    wav.write_bytes(b"RIFF")
    assert is_audio_file(wav)
    txt = tmp_path / "a.txt"
    txt.write_text("x")
    assert not is_audio_file(txt)


def test_collect_from_dir(tmp_path: Path):
    (tmp_path / "a.wav").write_bytes(b"x")
    (tmp_path / "b.mp3").write_bytes(b"x")
    (tmp_path / "c.txt").write_text("nope")
    files = collect_audio_files([tmp_path])
    names = {f.name for f in files}
    assert names == {"a.wav", "b.mp3"}


def test_collect_missing_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        collect_audio_files([tmp_path / "missing.wav"])


def test_resolve_backend_auto_windows():
    # On Windows we always prefer transformers for auto
    import sys

    if sys.platform == "win32":
        assert resolve_backend("auto") == "transformers"
    assert resolve_backend("transformers") == "transformers"
