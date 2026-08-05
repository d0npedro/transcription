# Example 01 — Single file

## Goal

Transcribe one audio file with exact word timestamps and full export set.

## Command

```powershell
# from repo root
.\setup.ps1   # once

.\.venv\Scripts\python.exe -m crisper_timestamps "C:\path\to\interview.wav" `
  -l de `
  --mode verbatim `
  -m turbo `
  -o output\example-single
```

Or:

```powershell
.\transcribe.ps1 "C:\path\to\interview.wav" -l de
```

## Expected outputs

Under `output\example-single\` (stem = audio filename without extension):

| File | Role |
|------|------|
| `{stem}.json` | `text` + `words[{word,start,end}]` |
| `{stem}.tsv` | spreadsheet |
| `{stem}.srt` / `{stem}.vtt` | subtitles |
| `{stem}.txt` | plain text |
| `handoff.json` / `HANDOFF.md` | package for other projects |

## Sample shape

See [`../fixtures/sample-track/`](../fixtures/sample-track/) for a checked-in example of those files (no audio).

## Speech vs album

| Use case | Flags |
|----------|--------|
| German interview | `-l de --mode verbatim` |
| English interview | `-l en --mode verbatim` |
| Song / album vocals | prefer `.\repeat.ps1 -Profile album` (intended + en) |
