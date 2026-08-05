# Examples

Self-contained samples for **crisper-timestamps** — no large audio binaries in git.

| Example | What it shows |
|---------|----------------|
| [`01-single-file/`](01-single-file/) | One track: full export set + how to run CLI |
| [`02-album-layout/`](02-album-layout/) | Album folder layout (`01 WAV Masters` → `06 Timestamps`) |
| [`03-handoff-consumer/`](03-handoff-consumer/) | Load `handoff.json` in Python / TypeScript |
| [`fixtures/sample-track/`](fixtures/sample-track/) | Minimal real-shaped JSON/TSV/SRT/VTT/TXT |
| [`commands.ps1`](commands.ps1) | Copy-paste PowerShell recipes |

## Quick recipes

### A) Single file (speech DE)

```powershell
# from repo root after .\setup.ps1
.\.venv\Scripts\python.exe -m crisper_timestamps path\to\clip.wav `
  -l de --mode verbatim -m turbo -o output\my-clip
```

### B) Album project (quality-locked, same as reference release)

```powershell
.\repeat.ps1 -Project "F:\Albums\My Album" -Profile album
# expects e.g.  "01 WAV Masters"  under the project
# writes/reuses  "NN Timestamps"  + handoff.json
```

### C) Rebuild handoff only

```powershell
.\.venv\Scripts\python.exe -m crisper_timestamps.handoff output\my-batch `
  --id my-batch --language en --mode intended --model turbo
```

### D) Copy package into another app

```powershell
Copy-Item -Recurse -Force "path\to\NN Timestamps\*" "D:\OtherApp\assets\timestamps\my-batch\"
```

Then open `handoff.json` (see example 03).

## Quality lock (do not weaken for “same quality”)

See [../QUALITY.md](../QUALITY.md):

- `word_timestamps=true`
- `longform_strategy=continuation`
- `speculative_decoding=false`
- always write `handoff.json` + `HANDOFF.md`

## Note on audio

Git does **not** ship WAV masters. Put your own files under `input/` or your album’s `01 WAV Masters/`.  
The fixtures under `fixtures/` are **export samples** (text + timestamps only).
