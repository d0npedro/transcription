"""
Repeatable quality-locked pipeline.

Same quality characteristics as the proven album run:
  - word_timestamps=True
  - longform_strategy=continuation
  - speculative_decoding=False
  - full export set + handoff.json / HANDOFF.md
  - optional deploy into a numbered project folder (e.g. 06 Timestamps)
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
import time
import traceback
from pathlib import Path
from typing import Any

from crisper_timestamps import __version__
from crisper_timestamps.engine import TimestampEngine, collect_audio_files
from crisper_timestamps.export import write_all
from crisper_timestamps.handoff import write_handoff
from crisper_timestamps.profiles import list_profiles, load_profile, profile_summary, resolve_run_config

_NUM_NAME = re.compile(r"^(\d{2})\s+(.+)$")


def find_audio_dir(project_root: Path, candidates: list[str]) -> Path | None:
    project_root = project_root.resolve()
    for name in candidates:
        p = project_root / name
        if p.is_dir():
            return p
    # loose match: any dir containing "wav" and "master"
    for child in sorted(project_root.iterdir()):
        if not child.is_dir():
            continue
        low = child.name.lower()
        if "wav" in low and "master" in low:
            return child
    return None


def resolve_deploy_dir(
    project_root: Path,
    *,
    folder_name: str = "Timestamps",
    number_prefix: bool = True,
    prefer_existing_named: str | None = "Timestamps",
    force_name: str | None = None,
) -> Path:
    """
    Pick deploy path under project_root.

    - force_name: exact folder name if set
    - else reuse existing '* Timestamps' / '* <prefer_existing_named>'
    - else next free NN <folder_name>
    """
    project_root = project_root.resolve()
    if force_name:
        return project_root / force_name

    if prefer_existing_named:
        for child in sorted(project_root.iterdir()):
            if child.is_dir() and prefer_existing_named.lower() in child.name.lower():
                return child

    if not number_prefix:
        return project_root / folder_name

    used: set[int] = set()
    for child in project_root.iterdir():
        if not child.is_dir():
            continue
        m = _NUM_NAME.match(child.name)
        if m:
            used.add(int(m.group(1)))

    n = 1
    while n in used:
        n += 1
    return project_root / f"{n:02d} {folder_name}"


def run_pipeline(
    *,
    audio_paths: list[Path],
    work_output: Path,
    cfg: dict[str, Any],
    handoff_id: str | None = None,
    source_meta: Path | None = None,
    deploy_to: Path | None = None,
    recursive: bool = False,
    diarize: bool = False,
) -> dict[str, Any]:
    """Transcribe → export → handoff → optional deploy. Returns summary dict."""
    files = collect_audio_files(audio_paths, recursive=recursive)
    if not files:
        raise FileNotFoundError("Keine Audiodateien gefunden.")

    work_output = work_output.expanduser().resolve()
    work_output.mkdir(parents=True, exist_ok=True)

    formats = list(cfg.get("formats") or ["json", "tsv", "srt", "vtt", "txt"])
    engine = TimestampEngine(
        model=str(cfg["model"]),
        backend=str(cfg.get("backend", "auto")),
        device=str(cfg.get("device", "auto")),
        compute_type=str(cfg.get("compute_type", "float16")),
        language=str(cfg["language"]),
        mode=str(cfg["mode"]),
        longform_strategy=str(cfg.get("longform_strategy", "continuation")),
        diarize=diarize,
    )

    print("=" * 64)
    print("  REPEAT PIPELINE — quality-locked timestamps")
    print("=" * 64)
    print(f"  profile : {cfg.get('profile_id')} — {cfg.get('profile_title')}")
    print(f"  files   : {len(files)}")
    print(f"  model   : {cfg['model']}")
    print(f"  language: {cfg['language']}")
    print(f"  mode    : {cfg['mode']}")
    print(f"  longform: {cfg.get('longform_strategy')}  speculative: {cfg.get('speculative_decoding')}")
    print(f"  work out: {work_output}")
    if deploy_to:
        print(f"  deploy  : {deploy_to}")
    print("=" * 64)
    for note in cfg.get("notes") or []:
        print(f"  note: {note}")

    t0 = time.perf_counter()
    results: list[dict[str, Any]] = []
    for i, audio in enumerate(files, start=1):
        print(f"\n=== [{i}/{len(files)}] {audio.name} ===", flush=True)
        t1 = time.perf_counter()
        try:
            result = engine.transcribe_file(audio)
            written = write_all(result, work_output, audio.stem, formats=formats)
            elapsed = time.perf_counter() - t1
            info = {
                "source": str(audio),
                "word_count": len(result.words),
                "duration": result.duration,
                "processing_time": result.processing_time,
                "wall_time": elapsed,
                "outputs": {k: str(v) for k, v in written.items()},
            }
            results.append(info)
            print(
                f"  → {len(result.words)} Wörter | "
                f"Audio {result.duration or '?'}s | {elapsed:.1f}s",
                flush=True,
            )
        except Exception as exc:
            print(f"  FEHLER: {exc}", flush=True)
            traceback.print_exc()
            results.append({"source": str(audio), "error": str(exc)})

    ok = sum(1 for r in results if "error" not in r)
    fail = len(results) - ok
    elapsed = time.perf_counter() - t0

    handoff_paths: dict[str, Path] = {}
    if cfg.get("write_handoff", True):
        handoff_paths = write_handoff(
            work_output,
            handoff_id=handoff_id or work_output.name,
            source_path=source_meta,
            model=str(cfg["model"]),
            language=str(cfg["language"]),
            mode=str(cfg["mode"]),
            project_hint=str(deploy_to) if deploy_to else None,
            extra={
                "profile_id": cfg.get("profile_id"),
                "quality_lock": {
                    "word_timestamps": True,
                    "speculative_decoding": False,
                    "longform_strategy": cfg.get("longform_strategy"),
                    "hallucination_mitigation": cfg.get("hallucination_mitigation"),
                },
                "pipeline_version": __version__,
            },
        )

    final_dir = work_output
    if deploy_to is not None:
        deploy_to = deploy_to.expanduser().resolve()
        deploy_to.mkdir(parents=True, exist_ok=True)
        for item in work_output.iterdir():
            target = deploy_to / item.name
            if item.is_dir():
                if target.exists():
                    shutil.rmtree(target)
                shutil.copytree(item, target)
            else:
                shutil.copy2(item, target)
        # Rewrite handoff paths to live inside the project
        handoff_paths = write_handoff(
            deploy_to,
            handoff_id=handoff_id or deploy_to.name,
            source_path=source_meta,
            model=str(cfg["model"]),
            language=str(cfg["language"]),
            mode=str(cfg["mode"]),
            project_hint=str(deploy_to),
            extra={
                "profile_id": cfg.get("profile_id"),
                "pipeline_version": __version__,
                "deployed_from": str(work_output),
            },
        )
        final_dir = deploy_to
        print(f"\n  Deployed → {deploy_to}", flush=True)

    words_total = sum(int(r.get("word_count") or 0) for r in results if "error" not in r)
    summary = {
        "ok": ok,
        "fail": fail,
        "elapsed_s": elapsed,
        "work_output": str(work_output),
        "final_dir": str(final_dir),
        "handoff_json": str(handoff_paths.get("handoff_json", "")),
        "handoff_md": str(handoff_paths.get("handoff_md", "")),
        "total_words": words_total,
        "profile_id": cfg.get("profile_id"),
        "results": results,
    }

    print("\n" + "=" * 64)
    print(f"  Fertig: {ok} OK, {fail} Fehler, {elapsed:.1f}s")
    print(f"  Wörter : {words_total}")
    print(f"  Final  : {final_dir}")
    if handoff_paths.get("handoff_json"):
        print(f"  Handoff: {handoff_paths['handoff_json']}")
        print(f"           {handoff_paths.get('handoff_md')}")
    print("=" * 64)
    return summary


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="timestamps-repeat",
        description=(
            "Wiederholbarer Timestamp-Lauf mit Qualitätsprofil "
            "(exakte Wortzeiten, continuation, kein Speculative Decoding, Handoff)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Beispiele:\n"
            "  timestamps-repeat --project \"F:\\Albums\\Mein Album\" --profile album\n"
            "  timestamps-repeat --audio-dir masters --project . --profile album --language en\n"
            "  timestamps-repeat --list-profiles\n"
        ),
    )
    p.add_argument(
        "--project",
        type=Path,
        default=None,
        help="Album-/Projektordner (sucht z.B. '01 WAV Masters', deployed 'NN Timestamps')",
    )
    p.add_argument(
        "--audio-dir",
        type=Path,
        default=None,
        help="Audio-Ordner (sonst Auto-Detect unter --project)",
    )
    p.add_argument(
        "--audio",
        type=Path,
        nargs="*",
        default=None,
        help="Einzelne Audiodatei(en) statt Ordner",
    )
    p.add_argument(
        "--profile",
        default="album",
        help=f"Qualitätsprofil (default: album). Verfügbar: {', '.join(list_profiles()) or '…'}",
    )
    p.add_argument("--list-profiles", action="store_true", help="Profile auflisten und beenden")
    p.add_argument(
        "-o",
        "--work-output",
        type=Path,
        default=None,
        help="Arbeits-Output (default: ./output/<handoff-id>)",
    )
    p.add_argument(
        "--deploy",
        choices=("auto", "none", "path"),
        default="auto",
        help="auto=in Projektordner deployen wenn --project gesetzt; none=nur work-output",
    )
    p.add_argument(
        "--deploy-path",
        type=Path,
        default=None,
        help="Expliziter Deploy-Pfad (setzt deploy=path)",
    )
    p.add_argument("--handoff-id", default=None, help="ID für handoff.json")
    p.add_argument("-l", "--language", default=None, help="Override Sprache (Profil-Default)")
    p.add_argument("-m", "--model", default=None, help="Override Modell")
    p.add_argument("--mode", choices=("verbatim", "intended"), default=None)
    p.add_argument("-j", "--jobs", type=int, default=None)
    p.add_argument("-r", "--recursive", action="store_true")
    p.add_argument(
        "--diarize",
        action="store_true",
        help="Sprecher mit optionalem pyannote.audio erkennen",
    )
    p.add_argument(
        "--unlock",
        action="store_true",
        help="Erlaubt Quality-Lock-Overrides (nicht empfohlen)",
    )
    p.add_argument("-v", "--version", action="version", version=f"%(prog)s {__version__}")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_profiles:
        for pid in list_profiles():
            print(profile_summary(pid))
            print()
        return 0

    try:
        cfg = resolve_run_config(
            args.profile,
            overrides={
                "language": args.language,
                "model": args.model,
                "mode": args.mode,
                "jobs": args.jobs,
            },
            unlock=args.unlock,
        )
    except FileNotFoundError as exc:
        print(f"FEHLER: {exc}", file=sys.stderr)
        return 2

    project = args.project.expanduser().resolve() if args.project else None
    audio_paths: list[Path] = []

    if args.audio:
        audio_paths = list(args.audio)
    elif args.audio_dir:
        audio_paths = [args.audio_dir]
    elif project:
        candidates = list((cfg.get("project") or {}).get("audio_dir_candidates") or [])
        found = find_audio_dir(project, candidates)
        if not found:
            print(
                f"FEHLER: Kein Audio-Ordner unter {project}.\n"
                f"  Kandidaten: {', '.join(candidates)}\n"
                f"  Oder: --audio-dir \"…\"",
                file=sys.stderr,
            )
            return 2
        audio_paths = [found]
        print(f"[pipeline] Audio-Ordner: {found}")
    else:
        print(
            "FEHLER: Bitte --project, --audio-dir oder --audio angeben.\n"
            "  Beispiel: timestamps-repeat --project \"F:\\Albums\\Mein Album\" --profile album",
            file=sys.stderr,
        )
        return 2

    # handoff id / work output
    if args.handoff_id:
        hid = args.handoff_id
    elif project:
        hid = project.name
    else:
        hid = audio_paths[0].name if audio_paths else "run"
    # slug-ish
    hid = re.sub(r"[^\w\-]+", "-", hid.strip(), flags=re.UNICODE).strip("-").lower() or "run"

    root = Path(__file__).resolve().parents[2]
    work_output = (
        args.work_output.expanduser().resolve()
        if args.work_output
        else (root / "output" / hid)
    )

    deploy_to: Path | None = None
    if args.deploy_path:
        deploy_to = args.deploy_path
    elif args.deploy == "auto" and project:
        proj_cfg = cfg.get("project") or {}
        deploy_to = resolve_deploy_dir(
            project,
            folder_name=str(proj_cfg.get("deploy_folder_name") or "Timestamps"),
            number_prefix=bool(proj_cfg.get("deploy_number_prefix", True)),
            prefer_existing_named=proj_cfg.get("prefer_existing_named") or "Timestamps",
        )
    elif args.deploy == "path" and args.deploy_path:
        deploy_to = args.deploy_path

    source_meta = audio_paths[0] if len(audio_paths) == 1 else audio_paths[0]

    try:
        summary = run_pipeline(
            audio_paths=audio_paths,
            work_output=work_output,
            cfg=cfg,
            handoff_id=hid,
            source_meta=source_meta,
            deploy_to=deploy_to,
            recursive=args.recursive,
            diarize=args.diarize,
        )
    except FileNotFoundError as exc:
        print(f"FEHLER: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"FEHLER: {exc}", file=sys.stderr)
        traceback.print_exc()
        return 1

    return 0 if summary["fail"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
