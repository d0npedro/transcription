# Handoff: `sample-fixture`

> Schema: `crisper-timestamps.handoff/v1` · created `2026-08-05T12:16:54.598600+00:00`

## Übergabe in ein anderes Projekt

Dieser Ordner ist **portable**. Nimm den kompletten Output-Ordner mit:

| Datei | Zweck |
|-------|--------|
| `handoff.json` | Maschinenlesbares Manifest (Entry-Point) |
| `HANDOFF.md` | Diese Anleitung |
| `*.json` | Transkript + exakte Wort-Timestamps (`start`/`end` in Sekunden) |
| `*.tsv` | Tabelle `start\tend\tword` |
| `*.srt` / `*.vtt` | Untertitel |
| `*.txt` | Nur Fließtext |

### PowerShell (kopieren)

```powershell
New-Item -ItemType Directory -Force -Path "examples/02-album-layout/mock-project/06 Timestamps" | Out-Null; Copy-Item -Recurse -Force "D:\Projects\transcription\examples\fixtures\sample-track\*" "examples/02-album-layout/mock-project/06 Timestamps\"
```

### Bash

```bash
mkdir -p "examples/02-album-layout/mock-project/06 Timestamps" && cp -R "D:\Projects\transcription\examples\fixtures\sample-track/." "examples/02-album-layout/mock-project/06 Timestamps/"
```

### Python Consumer (minimal)

```python
import json
from pathlib import Path
handoff = json.loads(Path(r'D:\Projects\transcription\examples\fixtures\sample-track/handoff.json').read_text(encoding='utf-8'))
for track in handoff['tracks']:
    if track['word_count'] == 0:
        continue
    data = json.loads(Path(track['artifacts']['json']).read_text(encoding='utf-8'))
    for w in data['words']:
        print(track['stem'], w['start'], w['end'], w['word'])

```

## Word-Schema

```json
{
  "type": "object",
  "required": [
    "word",
    "start",
    "end"
  ],
  "properties": {
    "word": {
      "type": "string",
      "description": "Token text (may include punctuation)"
    },
    "start": {
      "type": "number",
      "description": "Start time in seconds from audio start"
    },
    "end": {
      "type": "number",
      "description": "End time in seconds from audio start"
    }
  }
}
```

## Run

- **output_dir:** `D:\Projects\transcription\examples\fixtures\sample-track`
- **model:** `turbo`
- **language:** `en`
- **mode:** `intended`
- **summary:** 2 tracks · 1 with words · 1 empty · 13 total words
- **source:** `examples/fixtures/audio-not-included`

## Track-Index

| # | stem | words | duration | json |
|---|------|------:|---------:|------|
| 1 | `01 - Sample Intro` | 13 | 12.5 | `01 - Sample Intro.json` |
| 2 | `02 - Instrumental` | 0 | 180.0 | `02 - Instrumental.json` |

## Markup-Block (für Chat / PR)

```xml
<timestamp-handoff schema="crisper-timestamps.handoff/v1" id="sample-fixture">
  <output_dir>D:\Projects\transcription\examples\fixtures\sample-track</output_dir>
  <entry>handoff.json</entry>
  <tracks>2</tracks>
  <words>13</words>
  <model>turbo</model>
  <language>en</language>
</timestamp-handoff>
```

Ein anderes Projekt kann diesen Block parsen und `output_dir` / `handoff.json` als Source of Truth laden.
