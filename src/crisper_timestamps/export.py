"""Export word timestamps to JSON, SRT, VTT, TSV."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence


@dataclass(frozen=True)
class WordTiming:
    word: str
    start: float
    end: float
    speaker: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"word": self.word, "start": self.start, "end": self.end}
        if self.speaker is not None:
            data["speaker"] = self.speaker
        return data


@dataclass
class TranscriptResult:
    text: str
    language: str
    mode: str
    duration: float | None
    processing_time: float | None
    words: list[WordTiming]
    source: str
    model: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "model": self.model,
            "text": self.text,
            "language": self.language,
            "mode": self.mode,
            "duration": self.duration,
            "processing_time": self.processing_time,
            "words": [w.to_dict() for w in self.words],
            "word_count": len(self.words),
        }


def _fmt_ts(seconds: float, *, vtt: bool = False) -> str:
    """Format seconds as SRT (comma) or VTT (dot) timestamp."""
    if seconds < 0:
        seconds = 0.0
    ms_total = int(round(seconds * 1000))
    hours, rem = divmod(ms_total, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, ms = divmod(rem, 1000)
    sep = "." if vtt else ","
    return f"{hours:02d}:{minutes:02d}:{secs:02d}{sep}{ms:03d}"


def words_to_cues(
    words: Sequence[WordTiming],
    *,
    max_chars: int = 42,
    max_duration: float = 5.0,
    max_gap: float = 0.6,
) -> list[tuple[float, float, str]]:
    """Group words into subtitle cues (start, end, text)."""
    if not words:
        return []

    cues: list[tuple[float, float, str]] = []
    buf: list[WordTiming] = [words[0]]

    def flush() -> None:
        nonlocal buf
        if not buf:
            return
        text = " ".join(w.word.strip() for w in buf if w.word.strip())
        if text:
            cues.append((buf[0].start, buf[-1].end, text))
        buf = []

    for w in words[1:]:
        gap = w.start - buf[-1].end
        candidate = " ".join(x.word.strip() for x in buf + [w] if x.word.strip())
        duration = w.end - buf[0].start
        if gap > max_gap or len(candidate) > max_chars or duration > max_duration:
            flush()
            buf = [w]
        else:
            buf.append(w)
    flush()
    return cues


def write_json(result: TranscriptResult, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def write_tsv(words: Iterable[WordTiming], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["start\tend\tword"]
    for w in words:
        # Escape tabs/newlines in word text
        word = w.word.replace("\t", " ").replace("\n", " ").replace("\r", "")
        lines.append(f"{w.start:.3f}\t{w.end:.3f}\t{word}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_srt(words: Sequence[WordTiming], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    cues = words_to_cues(words)
    blocks: list[str] = []
    for i, (start, end, text) in enumerate(cues, start=1):
        blocks.append(
            f"{i}\n{_fmt_ts(start)} --> {_fmt_ts(end)}\n{text}\n"
        )
    path.write_text("\n".join(blocks), encoding="utf-8")
    return path


def write_vtt(words: Sequence[WordTiming], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    cues = words_to_cues(words)
    lines = ["WEBVTT", ""]
    for start, end, text in cues:
        lines.append(f"{_fmt_ts(start, vtt=True)} --> {_fmt_ts(end, vtt=True)}")
        lines.append(text)
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_all(
    result: TranscriptResult,
    out_dir: Path,
    stem: str,
    *,
    formats: Sequence[str] = ("json", "tsv", "srt", "vtt", "txt"),
) -> dict[str, Path]:
    """Write requested formats; returns map format -> path."""
    out_dir.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}
    fmt_set = {f.lower().strip() for f in formats}

    if "json" in fmt_set:
        written["json"] = write_json(result, out_dir / f"{stem}.json")
    if "tsv" in fmt_set:
        written["tsv"] = write_tsv(result.words, out_dir / f"{stem}.tsv")
    if "srt" in fmt_set:
        written["srt"] = write_srt(result.words, out_dir / f"{stem}.srt")
    if "vtt" in fmt_set:
        written["vtt"] = write_vtt(result.words, out_dir / f"{stem}.vtt")
    if "txt" in fmt_set:
        p = out_dir / f"{stem}.txt"
        p.write_text(result.text + ("\n" if result.text else ""), encoding="utf-8")
        written["txt"] = p
    return written
