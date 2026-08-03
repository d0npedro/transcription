"""Handoff package: machine + human markup to drop timestamps into another project."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_ID = "crisper-timestamps.handoff/v1"
SCHEMA_VERSION = 1

# Word-level payload every consumer should expect in *.json
WORD_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["word", "start", "end"],
    "properties": {
        "word": {"type": "string", "description": "Token text (may include punctuation)"},
        "start": {"type": "number", "description": "Start time in seconds from audio start"},
        "end": {"type": "number", "description": "End time in seconds from audio start"},
    },
}

TRACK_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["source", "model", "text", "language", "mode", "words", "word_count"],
    "properties": {
        "source": {"type": "string"},
        "model": {"type": "string"},
        "text": {"type": "string"},
        "language": {"type": "string"},
        "mode": {"type": "string", "enum": ["verbatim", "intended", "forced_align"]},
        "duration": {"type": ["number", "null"]},
        "processing_time": {"type": ["number", "null"]},
        "words": {"type": "array", "items": WORD_SCHEMA},
        "word_count": {"type": "integer"},
    },
}


def _slug(text: str) -> str:
    s = text.strip().lower()
    s = re.sub(r"[^\w\s\-]+", "", s, flags=re.UNICODE)
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "handoff"


def _rel_or_abs(path: Path, base: Path) -> str:
    try:
        return str(path.resolve().relative_to(base.resolve())).replace("\\", "/")
    except ValueError:
        return str(path.resolve())


def discover_tracks(output_dir: Path) -> list[dict[str, Any]]:
    """Scan output_dir for per-track JSON sidecars and related artifacts."""
    output_dir = output_dir.resolve()
    tracks: list[dict[str, Any]] = []
    for json_path in sorted(output_dir.glob("*.json")):
        if json_path.name in ("handoff.json", "manifest.json"):
            continue
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict) or "words" not in data:
            continue

        stem = json_path.stem
        artifacts: dict[str, str] = {"json": str(json_path.resolve())}
        for ext in ("tsv", "srt", "vtt", "txt"):
            p = output_dir / f"{stem}.{ext}"
            if p.is_file():
                artifacts[ext] = str(p.resolve())

        words = data.get("words") or []
        text = str(data.get("text") or "")
        preview = text if len(text) <= 160 else text[:157] + "…"
        tracks.append(
            {
                "id": _slug(stem),
                "stem": stem,
                "source_audio": data.get("source"),
                "duration": data.get("duration"),
                "word_count": int(data.get("word_count") or len(words)),
                "text": text,
                "text_preview": preview,
                "language": data.get("language"),
                "mode": data.get("mode"),
                "model": data.get("model"),
                "artifacts": artifacts,
                "artifacts_relative": {
                    k: _rel_or_abs(Path(v), output_dir) for k, v in artifacts.items()
                },
            }
        )
    return tracks


def build_handoff(
    output_dir: Path,
    *,
    handoff_id: str | None = None,
    source_path: str | Path | None = None,
    model: str | None = None,
    language: str | None = None,
    mode: str | None = None,
    project_hint: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    tracks = discover_tracks(output_dir)
    with_words = [t for t in tracks if t["word_count"] > 0]
    total_words = sum(t["word_count"] for t in tracks)

    # Infer meta from first non-empty track
    sample = next((t for t in tracks if t.get("model")), tracks[0] if tracks else {})
    hid = handoff_id or _slug(output_dir.name)

    out_abs = str(output_dir)
    dest_placeholder = project_hint or "<ZIEL-PROJEKT>/assets/timestamps/" + hid

    handoff: dict[str, Any] = {
        "schema": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "id": hid,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "generator": "crisper-timestamps",
        "source": {
            "path": str(source_path) if source_path else None,
            "type": "directory" if source_path and Path(str(source_path)).is_dir() else (
                "file" if source_path else None
            ),
        },
        "run": {
            "model": model or sample.get("model"),
            "language": language or sample.get("language"),
            "mode": mode or sample.get("mode"),
        },
        "output_dir": out_abs,
        "output_dir_uri": Path(out_abs).as_uri(),
        "tracks": tracks,
        "summary": {
            "track_count": len(tracks),
            "tracks_with_words": len(with_words),
            "tracks_empty": len(tracks) - len(with_words),
            "total_words": total_words,
        },
        "word_schema": WORD_SCHEMA,
        "track_json_schema": TRACK_JSON_SCHEMA,
        "import": {
            "recommended_artifact": "json",
            "entry_file": "handoff.json",
            "human_readme": "HANDOFF.md",
            "primary_paths": {
                "handoff_json": str((output_dir / "handoff.json").resolve()),
                "handoff_md": str((output_dir / "HANDOFF.md").resolve()),
                "output_dir": out_abs,
            },
            "copy_to_other_project": {
                "powershell": (
                    f'New-Item -ItemType Directory -Force -Path "{dest_placeholder}" | Out-Null; '
                    f'Copy-Item -Recurse -Force "{out_abs}\\*" "{dest_placeholder}\\"'
                ),
                "cmd": f'xcopy /E /I /Y "{out_abs}" "{dest_placeholder}"',
                "bash": f'mkdir -p "{dest_placeholder}" && cp -R "{out_abs}/." "{dest_placeholder}/"',
            },
            "consumer_snippet_python": (
                "import json\n"
                "from pathlib import Path\n"
                f"handoff = json.loads(Path(r'{out_abs}/handoff.json').read_text(encoding='utf-8'))\n"
                "for track in handoff['tracks']:\n"
                "    if track['word_count'] == 0:\n"
                "        continue\n"
                "    data = json.loads(Path(track['artifacts']['json']).read_text(encoding='utf-8'))\n"
                "    for w in data['words']:\n"
                "        print(track['stem'], w['start'], w['end'], w['word'])\n"
            ),
            "consumer_snippet_ts": (
                "import handoff from './handoff.json';\n"
                "for (const track of handoff.tracks) {\n"
                "  if (!track.word_count) continue;\n"
                "  // load track.artifacts.json next to this handoff\n"
                "}\n"
            ),
        },
    }
    if extra:
        handoff["extra"] = extra
    return handoff


def render_handoff_md(handoff: dict[str, Any]) -> str:
    """Human-readable markup for pasting into PRs / other repos."""
    sid = handoff.get("id", "handoff")
    summary = handoff.get("summary") or {}
    run = handoff.get("run") or {}
    imp = handoff.get("import") or {}
    copy = imp.get("copy_to_other_project") or {}
    out_dir = handoff.get("output_dir", "")
    tracks = handoff.get("tracks") or []

    lines: list[str] = []
    lines.append(f"# Handoff: `{sid}`")
    lines.append("")
    lines.append(f"> Schema: `{handoff.get('schema')}` · created `{handoff.get('created_at')}`")
    lines.append("")
    lines.append("## Übergabe in ein anderes Projekt")
    lines.append("")
    lines.append("Dieser Ordner ist **portable**. Nimm den kompletten Output-Ordner mit:")
    lines.append("")
    lines.append("| Datei | Zweck |")
    lines.append("|-------|--------|")
    lines.append("| `handoff.json` | Maschinenlesbares Manifest (Entry-Point) |")
    lines.append("| `HANDOFF.md` | Diese Anleitung |")
    lines.append("| `*.json` | Transkript + exakte Wort-Timestamps (`start`/`end` in Sekunden) |")
    lines.append("| `*.tsv` | Tabelle `start\\tend\\tword` |")
    lines.append("| `*.srt` / `*.vtt` | Untertitel |")
    lines.append("| `*.txt` | Nur Fließtext |")
    lines.append("")
    lines.append("### PowerShell (kopieren)")
    lines.append("")
    lines.append("```powershell")
    lines.append(copy.get("powershell") or f'Copy-Item -Recurse -Force "{out_dir}\\*" "<ZIEL>\\"')
    lines.append("```")
    lines.append("")
    lines.append("### Bash")
    lines.append("")
    lines.append("```bash")
    lines.append(copy.get("bash") or f'cp -R "{out_dir}/." "<ZIEL>/"')
    lines.append("```")
    lines.append("")
    lines.append("### Python Consumer (minimal)")
    lines.append("")
    lines.append("```python")
    lines.append(imp.get("consumer_snippet_python") or "# see handoff.json import.consumer_snippet_python")
    lines.append("```")
    lines.append("")
    lines.append("## Word-Schema")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(handoff.get("word_schema") or WORD_SCHEMA, indent=2, ensure_ascii=False))
    lines.append("```")
    lines.append("")
    lines.append("## Run")
    lines.append("")
    lines.append(f"- **output_dir:** `{out_dir}`")
    lines.append(f"- **model:** `{run.get('model')}`")
    lines.append(f"- **language:** `{run.get('language')}`")
    lines.append(f"- **mode:** `{run.get('mode')}`")
    lines.append(
        f"- **summary:** {summary.get('track_count', 0)} tracks · "
        f"{summary.get('tracks_with_words', 0)} with words · "
        f"{summary.get('tracks_empty', 0)} empty · "
        f"{summary.get('total_words', 0)} total words"
    )
    src = (handoff.get("source") or {}).get("path")
    if src:
        lines.append(f"- **source:** `{src}`")
    lines.append("")
    lines.append("## Track-Index")
    lines.append("")
    lines.append("| # | stem | words | duration | json |")
    lines.append("|---|------|------:|---------:|------|")
    for i, t in enumerate(tracks, start=1):
        rel = (t.get("artifacts_relative") or {}).get("json", "")
        dur = t.get("duration")
        dur_s = f"{float(dur):.1f}" if isinstance(dur, (int, float)) else "—"
        lines.append(
            f"| {i} | `{t.get('stem')}` | {t.get('word_count', 0)} | {dur_s} | `{rel}` |"
        )
    lines.append("")
    lines.append("## Markup-Block (für Chat / PR)")
    lines.append("")
    lines.append("```xml")
    lines.append(f'<timestamp-handoff schema="{SCHEMA_ID}" id="{sid}">')
    lines.append(f"  <output_dir>{out_dir}</output_dir>")
    lines.append(f"  <entry>handoff.json</entry>")
    lines.append(f"  <tracks>{summary.get('track_count', 0)}</tracks>")
    lines.append(f"  <words>{summary.get('total_words', 0)}</words>")
    lines.append(f"  <model>{run.get('model')}</model>")
    lines.append(f"  <language>{run.get('language')}</language>")
    lines.append("</timestamp-handoff>")
    lines.append("```")
    lines.append("")
    lines.append(
        "Ein anderes Projekt kann diesen Block parsen und `output_dir` / `handoff.json` "
        "als Source of Truth laden."
    )
    lines.append("")
    return "\n".join(lines)


def write_handoff(
    output_dir: Path,
    *,
    handoff_id: str | None = None,
    source_path: str | Path | None = None,
    model: str | None = None,
    language: str | None = None,
    mode: str | None = None,
    project_hint: str | None = None,
    copy_to: Path | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Path]:
    """Write handoff.json + HANDOFF.md; optionally copy whole package to another project."""
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    handoff = build_handoff(
        output_dir,
        handoff_id=handoff_id,
        source_path=source_path,
        model=model,
        language=language,
        mode=mode,
        project_hint=str(copy_to) if copy_to else project_hint,
        extra=extra,
    )
    md = render_handoff_md(handoff)

    json_path = output_dir / "handoff.json"
    md_path = output_dir / "HANDOFF.md"
    json_path.write_text(
        json.dumps(handoff, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    md_path.write_text(md, encoding="utf-8")

    written: dict[str, Path] = {
        "handoff_json": json_path,
        "handoff_md": md_path,
    }

    if copy_to is not None:
        dest = Path(copy_to).expanduser().resolve()
        dest.mkdir(parents=True, exist_ok=True)
        # Refresh copy commands with real dest before re-write? already set via project_hint
        for item in output_dir.iterdir():
            target = dest / item.name
            if item.is_dir():
                if target.exists():
                    shutil.rmtree(target)
                shutil.copytree(item, target)
            else:
                shutil.copy2(item, target)
        written["copied_to"] = dest

    return written


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="crisper-timestamps-handoff",
        description="Erzeugt handoff.json + HANDOFF.md aus einem Output-Ordner.",
    )
    p.add_argument(
        "output_dir",
        type=Path,
        help="Ordner mit *.json Timestamp-Exports",
    )
    p.add_argument("--id", dest="handoff_id", default=None, help="Handoff-ID / Slug")
    p.add_argument("--source", default=None, help="Original-Audio-Pfad (Meta)")
    p.add_argument("--model", default=None)
    p.add_argument("--language", default=None)
    p.add_argument("--mode", default=None)
    p.add_argument(
        "--to",
        dest="copy_to",
        type=Path,
        default=None,
        help="Zielordner in einem anderen Projekt (kopiert gesamtes Package)",
    )
    p.add_argument(
        "--project-hint",
        default=None,
        help="Pfad-Platzhalter für Copy-Snippets (ohne echte Kopie)",
    )
    args = p.parse_args(argv)

    if not args.output_dir.is_dir():
        print(f"FEHLER: kein Ordner: {args.output_dir}", file=sys.stderr)
        return 2

    written = write_handoff(
        args.output_dir,
        handoff_id=args.handoff_id,
        source_path=args.source,
        model=args.model,
        language=args.language,
        mode=args.mode,
        project_hint=args.project_hint,
        copy_to=args.copy_to,
    )
    for k, v in written.items():
        print(f"{k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
