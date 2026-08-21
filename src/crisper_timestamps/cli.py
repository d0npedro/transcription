"""CLI: exact word timestamps from audio via CrisperWhisper 2.0."""

from __future__ import annotations

import argparse
import sys
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from crisper_timestamps import __version__
from crisper_timestamps.engine import (
    AUDIO_EXTENSIONS,
    TimestampEngine,
    collect_audio_files,
)
from crisper_timestamps.export import write_all
from crisper_timestamps.handoff import write_handoff

DEFAULT_INPUT = Path(__file__).resolve().parents[2] / "input"
DEFAULT_OUTPUT = Path(__file__).resolve().parents[2] / "output"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="timestamps",
        description=(
            "Extrahiert exakte Wort-Timestamps aus Audio mit CrisperWhisper 2.0.\n"
            "Einfach: Audio in den Ordner 'input/' legen und START.bat doppelklicken."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"Unterstützte Formate: {', '.join(sorted(AUDIO_EXTENSIONS))}",
    )
    p.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Audiodatei(en) oder Ordner. Default: ./input/",
    )
    p.add_argument(
        "-o",
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Ausgabeordner (default: {DEFAULT_OUTPUT})",
    )
    p.add_argument(
        "-m",
        "--model",
        default="turbo",
        help="Modell: turbo (schnell, default) | medium | large | small | *_pro",
    )
    p.add_argument(
        "-l",
        "--language",
        default="de",
        help="Sprachcode ISO-639-1 (default: de). z.B. en, de, fr",
    )
    p.add_argument(
        "--mode",
        choices=("verbatim", "intended"),
        default="verbatim",
        help="verbatim = exakt Gesprochenes inkl. Filler; intended = bereinigt",
    )
    p.add_argument(
        "--backend",
        choices=("auto", "ct2", "transformers"),
        default="auto",
        help="Inference-Backend (Windows: transformers; Linux GPU: ct2 empfohlen)",
    )
    p.add_argument(
        "--device",
        default="auto",
        help="Device: auto | cuda | cpu",
    )
    p.add_argument(
        "--compute-type",
        default="float16",
        help="float16 (GPU default) | int8_float16 | float32",
    )
    p.add_argument(
        "--formats",
        default="json,tsv,srt,vtt,txt",
        help="Komma-getrennte Formate: json,tsv,srt,vtt,txt",
    )
    p.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="Ordner rekursiv durchsuchen",
    )
    p.add_argument(
        "-j",
        "--jobs",
        type=int,
        default=1,
        help=(
            "Parallele Dateien (Process-Pool). Default 1 = ein Modell auf der GPU. "
            "Nur sinnvoll bei mehreren GPUs oder reinem CPU-Betrieb."
        ),
    )
    p.add_argument(
        "--longform-strategy",
        choices=("continuation", "chunked_lcs", "token_lcs"),
        default="continuation",
        help="Longform: continuation = beste Timestamps (default); *_lcs = parallelisierbar",
    )
    p.add_argument(
        "--diarize",
        action="store_true",
        help="Sprecher mit optionalem pyannote.audio erkennen",
    )
    p.add_argument(
        "--handoff-id",
        default=None,
        help="ID/Slug für handoff.json (default: Output-Ordnername)",
    )
    p.add_argument(
        "--handoff-to",
        type=Path,
        default=None,
        help="Zielordner in einem anderen Projekt — kopiert das gesamte Output-Package dorthin",
    )
    p.add_argument(
        "--no-handoff",
        action="store_true",
        help="Kein handoff.json / HANDOFF.md schreiben",
    )
    p.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return p


def _worker(payload: dict) -> dict:
    """Process-pool worker: load model in child and transcribe one file."""
    audio = Path(payload["audio"])
    engine = TimestampEngine(
        model=payload["model"],
        backend=payload["backend"],
        device=payload["device"],
        compute_type=payload["compute_type"],
        language=payload["language"],
        mode=payload["mode"],
        longform_strategy=payload["longform_strategy"],
        diarize=payload["diarize"],
    )
    result = engine.transcribe_file(audio)
    formats = payload["formats"]
    out_dir = Path(payload["output"])
    written = write_all(result, out_dir, audio.stem, formats=formats)
    return {
        "source": str(audio),
        "word_count": len(result.words),
        "text_preview": (result.text[:120] + "…") if len(result.text) > 120 else result.text,
        "outputs": {k: str(v) for k, v in written.items()},
        "duration": result.duration,
        "processing_time": result.processing_time,
    }


def run_sequential(
    files: list[Path],
    engine: TimestampEngine,
    out_dir: Path,
    formats: list[str],
) -> list[dict]:
    results: list[dict] = []
    for i, audio in enumerate(files, start=1):
        print(f"\n=== [{i}/{len(files)}] {audio.name} ===", flush=True)
        t0 = time.perf_counter()
        try:
            result = engine.transcribe_file(audio)
            written = write_all(result, out_dir, audio.stem, formats=formats)
            elapsed = time.perf_counter() - t0
            info = {
                "source": str(audio),
                "word_count": len(result.words),
                "text_preview": (result.text[:120] + "…")
                if len(result.text) > 120
                else result.text,
                "outputs": {k: str(v) for k, v in written.items()},
                "duration": result.duration,
                "processing_time": result.processing_time,
                "wall_time": elapsed,
            }
            results.append(info)
            print(
                f"  → {len(result.words)} Wörter | "
                f"Audio {result.duration or '?'}s | "
                f"{elapsed:.1f}s Wandzeit",
                flush=True,
            )
            for fmt, path in written.items():
                print(f"  → {fmt}: {path}", flush=True)
        except Exception as exc:
            print(f"  FEHLER: {exc}", flush=True)
            traceback.print_exc()
            results.append({"source": str(audio), "error": str(exc)})
    return results


def run_parallel(files: list[Path], args: argparse.Namespace, formats: list[str]) -> list[dict]:
    """Parallel process-pool (one model load per worker — use carefully)."""
    results: list[dict] = []
    payloads = [
        {
            "audio": str(f),
            "model": args.model,
            "backend": args.backend,
            "device": args.device,
            "compute_type": args.compute_type,
            "language": args.language,
            "mode": args.mode,
            "longform_strategy": args.longform_strategy,
            "diarize": args.diarize,
            "formats": formats,
            "output": str(args.output),
        }
        for f in files
    ]
    print(f"[parallel] {args.jobs} Worker für {len(files)} Dateien …", flush=True)
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        futures = {pool.submit(_worker, p): p["audio"] for p in payloads}
        for fut in as_completed(futures):
            src = futures[fut]
            try:
                info = fut.result()
                results.append(info)
                print(
                    f"  OK {Path(src).name}: {info['word_count']} Wörter",
                    flush=True,
                )
            except Exception as exc:
                print(f"  FEHLER {src}: {exc}", flush=True)
                results.append({"source": src, "error": str(exc)})
    return results


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    paths = list(args.paths) if args.paths else [DEFAULT_INPUT]
    if not args.paths and not DEFAULT_INPUT.exists():
        DEFAULT_INPUT.mkdir(parents=True, exist_ok=True)

    try:
        files = collect_audio_files(paths, recursive=args.recursive)
    except FileNotFoundError as exc:
        print(f"FEHLER: {exc}", file=sys.stderr)
        return 2

    if not files:
        print(
            "Keine Audiodateien gefunden.\n"
            f"  Lege Dateien in: {DEFAULT_INPUT.resolve()}\n"
            f"  Oder: timestamps pfad\\zu\\audio.wav\n"
            f"  Formate: {', '.join(sorted(AUDIO_EXTENSIONS))}",
            file=sys.stderr,
        )
        return 2

    formats = [f.strip().lower() for f in args.formats.split(",") if f.strip()]
    args.output = args.output.expanduser().resolve()
    args.output.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("  CrisperWhisper — exakte Wort-Timestamps")
    print("=" * 60)
    print(f"  Dateien : {len(files)}")
    print(f"  Modell  : {args.model}")
    print(f"  Sprache : {args.language}")
    print(f"  Mode    : {args.mode}")
    print(f"  Output  : {args.output}")
    print(f"  Formate : {', '.join(formats)}")
    print("=" * 60)

    t0 = time.perf_counter()
    if args.jobs > 1 and len(files) > 1:
        results = run_parallel(files, args, formats)
    else:
        engine = TimestampEngine(
            model=args.model,
            backend=args.backend,
            device=args.device,
            compute_type=args.compute_type,
            language=args.language,
            mode=args.mode,
            longform_strategy=args.longform_strategy,
            diarize=args.diarize,
        )
        results = run_sequential(files, engine, args.output, formats)

    ok = sum(1 for r in results if "error" not in r)
    fail = len(results) - ok
    elapsed = time.perf_counter() - t0

    if not args.no_handoff:
        # Source path: single file or common parent of batch
        if len(paths) == 1:
            source_meta = paths[0]
        else:
            source_meta = paths[0].parent if paths else None
        try:
            handoff_paths = write_handoff(
                args.output,
                handoff_id=args.handoff_id,
                source_path=source_meta,
                model=args.model,
                language=args.language,
                mode=args.mode,
                copy_to=args.handoff_to,
            )
            print("\n  Handoff:")
            for key, path in handoff_paths.items():
                print(f"    {key}: {path}")
        except Exception as exc:
            print(f"\n  WARNUNG: Handoff fehlgeschlagen: {exc}", flush=True)
            traceback.print_exc()

    print("\n" + "=" * 60)
    print(f"  Fertig: {ok} OK, {fail} Fehler, {elapsed:.1f}s gesamt")
    print(f"  Ergebnisse: {args.output}")
    if not args.no_handoff:
        print(f"  Handoff:    {args.output / 'handoff.json'}")
        print(f"              {args.output / 'HANDOFF.md'}")
    print("=" * 60)
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
