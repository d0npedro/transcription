# CrisperWhisper Timestamps

Idiotensicheres Tool: **exakte Wort-Timestamps** aus Audio mit
[CrisperWhisper 2.0](https://github.com/nyrahealth/CrisperWhisper)
(~30 ms mittlere Boundary-Fehler auf gelesener Sprache).

## Examples

See **[`examples/`](examples/)** for:

- single-file CLI recipes
- album layout (`01 WAV Masters` → `NN Timestamps`)
- handoff consumers (Python / TypeScript)
- checked-in fixtures (export shape only, no large WAVs)

```powershell
.\.venv\Scripts\python.exe examples\03-handoff-consumer\consume_handoff.py `
  examples\02-album-layout\mock-project\06 Timestamps\handoff.json
```

## Schnellstart (Windows)

1. **Python 3.10+** installieren ([python.org](https://www.python.org/downloads/), „Add to PATH“)
2. Optional: **ffmpeg** im PATH (für MP3/M4A; WAV/FLAC gehen ohne)
3. Audio-Datei(en) in den Ordner **`input/`** legen
4. **`START.bat`** doppelklicken

### Album-Pipeline wiederholen (empfohlen)

Gleicher Qualitätsstandard wie beim Referenz-Lauf (*Noch ein Bier bis zum Mond*):

```powershell
# Ein Befehl: findet "01 WAV Masters", schreibt Timestamps + Handoff, deployed ins Projekt
.\repeat.ps1 -Project "F:\Downloads\Noch ein Bier bis zum Mond" -Profile album

# Oder Doppelklick / Drag&Drop
.\REPEAT.bat "F:\Pfad\Zum\AlbumProjekt"
```

| Profil | Sprache | Mode | Modell | Einsatz |
|--------|---------|------|--------|---------|
| **`album`** | en | intended | turbo | Music Masters (Default) |
| **`album-hq`** | en | intended | medium | bessere Lyrics, langsamer |
| **`speech-de`** | de | verbatim | turbo | Interviews DE |
| **`speech-en`** | en | verbatim | turbo | Interviews EN |

**Quality-Lock (nicht abschaltbar ohne `--unlock`):**

- `word_timestamps=true` — exakte Wortzeiten
- `longform_strategy=continuation` — beste Longform-Timestamps
- `speculative_decoding=false` — keine Timing-Verwischung
- Exporte: json + tsv + srt + vtt + txt
- immer `handoff.json` + `HANDOFF.md`
- Deploy: `NN Timestamps` im Projekt (existierendes `* Timestamps` wird wiederverwendet)

Ergebnis liegt in **`output/`** (Arbeitskopie) und im **Projektordner**:

| Datei | Inhalt |
|-------|--------|
| `*.json` | Volltext + exakte Wort-Timestamps (`start`/`end` in Sekunden) |
| `*.tsv` | Tabelle `start end word` (Excel/Sheets) |
| `*.srt` / `*.vtt` | Untertitel aus den Wortzeiten |
| `*.txt` | Nur Transkript |

## CLI

```powershell
# Setup (einmalig)
.\setup.ps1

# Eine Datei
.\transcribe.ps1 input\meeting.wav

# Ordner, Englisch, größeres Modell
.\transcribe.ps1 input -l en -m medium

# Direkt
.\.venv\Scripts\python.exe -m crisper_timestamps audio.wav -o output
```

### Wichtige Flags

| Flag | Default | Bedeutung |
|------|---------|-----------|
| `-m / --model` | `turbo` | `turbo` (schnell) · `medium` · `large` (beste Qualität) · `small` |
| `-l / --language` | `de` | ISO-639-1 Sprachcode |
| `--mode` | `verbatim` | `verbatim` = inkl. Filler; `intended` = bereinigt |
| `--formats` | `json,tsv,srt,vtt,txt` | Exportformate |
| `-j / --jobs` | `1` | Parallele Dateien (Process-Pool; nur bei multi-GPU/CPU sinnvoll) |
| `--longform-strategy` | `continuation` | Beste Timestamps; `chunked_lcs` parallelisierbar, etwas ungenauer an Chunk-Grenzen |
| `--diarize` | aus | Sprecherzuordnung mit optionalem pyannote.audio |

### Optionale Sprechererkennung

```powershell
pip install -e ".[diarize]"
$env:HF_TOKEN = "hf_..."  # alternativ CRISPER_HF_TOKEN
timestamps interview.wav --diarize
```

Vor dem ersten Lauf müssen die Nutzungsbedingungen des
`pyannote/speaker-diarization-3.1`-Modells auf Hugging Face akzeptiert werden.
Falls pyannote fehlt oder die Diarisierung fehlschlägt, bleibt der ASR-Lauf
erfolgreich und alle Wörter erhalten `speaker_unknown`.

## Genauigkeit der Timestamps

- Immer `word_timestamps=True` (Viterbi auf Cross-Attention)
- Default **`continuation`**-Longform (nahtlose >30 s Audio, globale Sekunden)
- **Kein** Speculative Decoding (laut Upstream kann Draft-Attention Timings leicht verwaschen)

## Backend

| Plattform | Backend |
|-----------|---------|
| **Windows** (dieses Setup) | `transformers` + PyTorch CUDA 12.8 (RTX etc.) |
| Linux + NVIDIA | optional `pip install -e ".[ct2]"` → ~4× schneller |

`setup.ps1` / `START.bat` holen automatisch `torch` von `https://download.pytorch.org/whl/cu128`. Ohne NVIDIA-Treiber läuft CPU (langsamer).

Modellgewichte: Non-Commercial Research License (Nyra). Inference-Code MIT.
Siehe [CrisperWhisper License](https://github.com/nyrahealth/CrisperWhisper#license).

## Handoff (Übergabe an ein anderes Projekt)

Nach jedem Lauf entstehen im Output-Ordner:

| Datei | Zweck |
|-------|--------|
| **`handoff.json`** | Maschinenlesbares Manifest (Entry-Point für Importer) |
| **`HANDOFF.md`** | Copy-Befehle, Schema, Track-Index, XML-Markup-Block |

```powershell
# Handoff nur neu bauen (bestehende *.json)
.\.venv\Scripts\python.exe -m crisper_timestamps.handoff output\noch-ein-bier-bis-zum-mond `
  --id noch-ein-bier-bis-zum-mond `
  --source "F:\Downloads\Noch ein Bier bis zum Mond\01 WAV Masters" `
  --language en --mode intended --model turbo

# Direkt in ein anderes Projekt kopieren
.\.venv\Scripts\python.exe -m crisper_timestamps `
  "F:\path\to\audio" -o output\job1 --handoff-to "D:\OtherProject\assets\timestamps\job1"
```

**XML-Markup** (steht auch in `HANDOFF.md` / Workflow-Report):

```xml
<timestamp-handoff schema="crisper-timestamps.handoff/v1" id="…">
  <output_dir>…</output_dir>
  <entry>handoff.json</entry>
  <tracks>…</tracks>
  <words>…</words>
</timestamp-handoff>
```

Consumer laden `handoff.json` → `tracks[].artifacts.json` → `words[{word,start,end}]`.

## Grok-Workflow

```
/workflow extract-timestamps {"audio":"input/meeting.wav"}
/workflow extract-timestamps {"audio_dir":"input","language":"en","model":"turbo","handoff_id":"my-job"}
/workflow extract-timestamps {"audio_dir":"input","handoff_to":"D:/OtherProject/assets/timestamps/run1"}
```

Args: `audio` | `audio_dir`, optional `language`, `model`, `mode`, `out_dir`, `jobs`, **`handoff_to`**, **`handoff_id`**.

Siehe `.grok/workflows/extract-timestamps.rhai`.

## Projektstruktur

```
transcription/
  START.bat                 # Doppelklick-Start
  setup.ps1 / transcribe.ps1
  input/                    # Audio rein
  output/                   # JSON/TSV/SRT/VTT raus
  src/crisper_timestamps/   # CLI + Engine + Export
  .grok/workflows/          # Grok Build Workflow
```
