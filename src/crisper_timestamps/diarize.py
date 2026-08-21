"""Speaker assignment from diarization segments."""

from __future__ import annotations

UNKNOWN_SPEAKER = "speaker_unknown"


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
