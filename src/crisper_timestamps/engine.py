"""CrisperWhisper model loading and transcription with word timestamps."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any

from crisper_timestamps.export import TranscriptResult, WordTiming

logger = logging.getLogger(__name__)

# Supported audio extensions (ffmpeg/soundfile via CrisperWhisper)
AUDIO_EXTENSIONS = {
    ".wav",
    ".mp3",
    ".m4a",
    ".flac",
    ".ogg",
    ".opus",
    ".webm",
    ".mp4",
    ".mkv",
    ".aac",
    ".wma",
}

# Model shorthands accepted by CrisperWhisper 2.0
MODEL_ALIASES = {
    "large": "large",
    "turbo": "turbo",
    "medium": "medium",
    "small": "small",
    "large_pro": "large_pro",
    "turbo_pro": "turbo_pro",
    "medium_pro": "medium_pro",
    "small_pro": "small_pro",
}


def resolve_backend(preferred: str = "auto") -> str:
    """
    Prefer ct2 on Linux when installed; on Windows always transformers
    (ct2 wheels are Linux-only).
    """
    if preferred not in ("auto", "ct2", "transformers"):
        raise ValueError(f"Unknown backend: {preferred}")

    if preferred == "transformers":
        return "transformers"
    if preferred == "ct2":
        return "ct2"

    # auto
    if sys.platform.startswith("linux"):
        try:
            import ctranslate2  # noqa: F401

            return "ct2"
        except ImportError:
            return "transformers"
    return "transformers"


def is_audio_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS


def collect_audio_files(paths: list[Path], recursive: bool = False) -> list[Path]:
    """Expand files/dirs into a sorted unique list of audio paths."""
    found: list[Path] = []
    for p in paths:
        p = p.expanduser().resolve()
        if p.is_file():
            if is_audio_file(p):
                found.append(p)
            else:
                raise FileNotFoundError(
                    f"Keine unterstützte Audiodatei: {p} "
                    f"(erlaubt: {', '.join(sorted(AUDIO_EXTENSIONS))})"
                )
        elif p.is_dir():
            pattern = "**/*" if recursive else "*"
            for child in sorted(p.glob(pattern)):
                if is_audio_file(child):
                    found.append(child.resolve())
        else:
            raise FileNotFoundError(f"Pfad existiert nicht: {p}")

    # unique preserve order
    seen: set[Path] = set()
    unique: list[Path] = []
    for f in found:
        if f not in seen:
            seen.add(f)
            unique.append(f)
    return unique


class TimestampEngine:
    """Thin wrapper: load once, transcribe many files with word timestamps."""

    def __init__(
        self,
        model: str = "turbo",
        *,
        backend: str = "auto",
        device: str = "auto",
        compute_type: str = "float16",
        language: str = "de",
        mode: str = "verbatim",
        longform_strategy: str = "continuation",
        diarize: bool = False,
    ) -> None:
        self.model_name = MODEL_ALIASES.get(model, model)
        self.backend = resolve_backend(backend)
        self.device = device
        self.compute_type = compute_type
        self.language = language
        self.mode = mode
        self.longform_strategy = longform_strategy
        self.diarize = diarize
        self._model: Any = None

    def load(self) -> None:
        if self._model is not None:
            return
        from crisperwhisper import CrisperWhisperModel

        kwargs: dict[str, Any] = {
            "backend": self.backend,
            "device": self.device,
            "compute_type": self.compute_type,
        }
        # Optional cache dir for converted models
        cache = os.environ.get("CRISPERWHISPER_CACHE")
        if cache:
            kwargs["cache_dir"] = cache

        print(
            f"[engine] Lade Modell '{self.model_name}' "
            f"(backend={self.backend}, device={self.device}, compute={self.compute_type}) …",
            flush=True,
        )
        self._model = CrisperWhisperModel(self.model_name, **kwargs)
        print(f"[engine] Bereit (backend={getattr(self._model, 'backend', self.backend)}).", flush=True)

    def transcribe_file(self, audio_path: Path) -> TranscriptResult:
        self.load()
        audio_path = audio_path.expanduser().resolve()
        if not is_audio_file(audio_path):
            raise FileNotFoundError(f"Keine Audiodatei: {audio_path}")

        print(f"[engine] Transkribiere: {audio_path.name}", flush=True)
        # Exact timestamps: word_timestamps=True, continuation longform.
        # No speculative decoding — docs warn it can slightly blur draft-token timings.
        result = self._model.transcribe(
            str(audio_path),
            language=self.language,
            mode=self.mode,
            word_timestamps=True,
            longform_strategy=self.longform_strategy,
            hallucination_mitigation=True,
            speculative_decoding=False,
        )

        words: list[WordTiming] = []
        raw_words = getattr(result, "words", None) or []
        for w in raw_words:
            word = getattr(w, "word", None)
            start = getattr(w, "start", None)
            end = getattr(w, "end", None)
            if word is None or start is None or end is None:
                # dict-like fallback
                if isinstance(w, dict):
                    word = w.get("word", "")
                    start = float(w.get("start", 0.0))
                    end = float(w.get("end", 0.0))
                else:
                    continue
            words.append(WordTiming(word=str(word), start=float(start), end=float(end)))

        if self.diarize:
            from crisper_timestamps.diarize import assign_speakers

            word_dicts = [word.to_dict() for word in words]
            try:
                from crisper_timestamps.diarize import run_diarization

                segments = run_diarization(audio_path)
            except Exception as exc:
                logger.warning("Diarisierung fehlgeschlagen; verwende speaker_unknown: %s", exc)
                segments = []
            words = [
                WordTiming(
                    word=str(word["word"]),
                    start=float(word["start"]),
                    end=float(word["end"]),
                    speaker=str(word["speaker"]),
                )
                for word in assign_speakers(word_dicts, segments)
            ]

        return TranscriptResult(
            text=str(getattr(result, "text", "") or ""),
            language=str(getattr(result, "language", self.language) or self.language),
            mode=str(getattr(result, "mode", self.mode) or self.mode),
            duration=_opt_float(getattr(result, "duration", None)),
            processing_time=_opt_float(getattr(result, "processing_time", None)),
            words=words,
            source=str(audio_path),
            model=self.model_name,
        )


def _opt_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
