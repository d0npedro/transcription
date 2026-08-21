"""Speaker assignment from diarization segments."""

from __future__ import annotations

import inspect
import os
from pathlib import Path

UNKNOWN_SPEAKER = "speaker_unknown"
DIARIZATION_MODEL = "pyannote/speaker-diarization-3.1"


def _pipeline_from_pretrained(Pipeline, model: str, token: str | None):
    """Load pyannote pipeline with a Hugging Face token kwarg compatible across versions."""
    if token is None:
        return Pipeline.from_pretrained(model)

    params = inspect.signature(Pipeline.from_pretrained).parameters
    if "token" in params:
        return Pipeline.from_pretrained(model, token=token)
    if "use_auth_token" in params:
        return Pipeline.from_pretrained(model, use_auth_token=token)
    return Pipeline.from_pretrained(model)


def run_diarization(audio_path: Path, *, hf_token: str | None = None) -> list[dict]:
    """Run optional pyannote speaker diarization and return normalized segments."""
    from pyannote.audio import Pipeline

    token = hf_token or os.environ.get("HF_TOKEN") or os.environ.get("CRISPER_HF_TOKEN")
    pipeline = _pipeline_from_pretrained(Pipeline, DIARIZATION_MODEL, token)
    output = pipeline(str(audio_path.expanduser().resolve()))
    annotation = getattr(output, "speaker_diarization", output)

    return [
        {"id": str(speaker), "start": float(turn.start), "end": float(turn.end)}
        for turn, _track, speaker in annotation.itertracks(yield_label=True)
    ]


def _overlap(start_a: float, end_a: float, start_b: float, end_b: float) -> float:
    return max(0.0, min(end_a, end_b) - max(start_a, start_b))


def assign_speakers(words: list[dict], segments: list[dict]) -> list[dict]:
    """Assign each word to the diarization segment with maximum time overlap."""
    result: list[dict] = []
    for word in words:
        word_start = float(word["start"])
        word_end = float(word["end"])
        best_speaker = UNKNOWN_SPEAKER
        best_overlap = 0.0
        for segment in segments:
            overlap = _overlap(word_start, word_end, float(segment["start"]), float(segment["end"]))
            speaker_id = segment["id"]
            if overlap > best_overlap or (overlap == best_overlap and overlap > 0 and speaker_id < best_speaker):
                best_overlap = overlap
                best_speaker = speaker_id
        enriched = dict(word)
        enriched["speaker"] = best_speaker
        result.append(enriched)
    return result
