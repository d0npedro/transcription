"""Mock-only tests for optional pyannote diarization."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from crisper_timestamps.cli import build_parser as build_cli_parser
from crisper_timestamps.diarize import run_diarization
from crisper_timestamps.engine import TimestampEngine
from crisper_timestamps.pipeline import build_parser as build_pipeline_parser


class _Turn:
    def __init__(self, start: float, end: float) -> None:
        self.start = start
        self.end = end


class _Annotation:
    def itertracks(self, *, yield_label: bool):
        assert yield_label is True
        yield _Turn(0.0, 1.25), "track-0", "SPEAKER_00"
        yield _Turn(1.25, 2.5), "track-1", "SPEAKER_01"


def test_run_diarization_uses_pyannote_pipeline_and_env_token(monkeypatch, tmp_path: Path):
    audio = tmp_path / "clip.wav"
    audio.touch()
    loaded_pipeline = Mock(return_value=_Annotation())
    pipeline_type = Mock()
    pipeline_type.from_pretrained.return_value = loaded_pipeline
    monkeypatch.setitem(sys.modules, "pyannote", SimpleNamespace(audio=SimpleNamespace(Pipeline=pipeline_type)))
    monkeypatch.setitem(sys.modules, "pyannote.audio", SimpleNamespace(Pipeline=pipeline_type))
    monkeypatch.setenv("CRISPER_HF_TOKEN", "secret")

    segments = run_diarization(audio)

    pipeline_type.from_pretrained.assert_called_once_with(
        "pyannote/speaker-diarization-3.1",
        use_auth_token="secret",
    )
    loaded_pipeline.assert_called_once_with(str(audio.resolve()))
    assert segments == [
        {"id": "SPEAKER_00", "start": 0.0, "end": 1.25},
        {"id": "SPEAKER_01", "start": 1.25, "end": 2.5},
    ]


def _fake_asr_result():
    return SimpleNamespace(
        text="hello world",
        language="en",
        mode="verbatim",
        duration=2.0,
        processing_time=0.1,
        words=[
            {"word": "hello", "start": 0.0, "end": 0.5},
            {"word": "world", "start": 1.0, "end": 1.5},
        ],
    )


def test_engine_labels_words_when_diarization_enabled(tmp_path: Path):
    audio = tmp_path / "clip.wav"
    audio.touch()
    engine = TimestampEngine(diarize=True)
    engine._model = Mock()
    engine._model.transcribe.return_value = _fake_asr_result()
    segments = [
        {"id": "speaker_00", "start": 0.0, "end": 0.75},
        {"id": "speaker_01", "start": 0.75, "end": 2.0},
    ]

    with patch("crisper_timestamps.diarize.run_diarization", return_value=segments):
        result = engine.transcribe_file(audio)

    assert [word.speaker for word in result.words] == ["speaker_00", "speaker_01"]
    assert result.to_dict()["words"][0]["speaker"] == "speaker_00"


def test_engine_diarization_failure_warns_and_keeps_asr(tmp_path: Path, caplog):
    audio = tmp_path / "clip.wav"
    audio.touch()
    engine = TimestampEngine(diarize=True)
    engine._model = Mock()
    engine._model.transcribe.return_value = _fake_asr_result()

    with patch("crisper_timestamps.diarize.run_diarization", side_effect=RuntimeError("offline")):
        result = engine.transcribe_file(audio)

    assert [word.speaker for word in result.words] == ["speaker_unknown", "speaker_unknown"]
    assert "Diarisierung fehlgeschlagen" in caplog.text


def test_cli_and_pipeline_accept_diarize_flag():
    assert build_cli_parser().parse_args(["--diarize"]).diarize is True
    assert build_pipeline_parser().parse_args(["--diarize"]).diarize is True
