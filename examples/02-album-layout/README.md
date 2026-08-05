# Example 02 — Album project layout

## Layout (recommended)

```
My Album/
  01 WAV Masters/          ← put masters here (wav/flac/…)
    01 - Track One.wav
    02 - Track Two.wav
  02 Metadata/
  …
  06 Timestamps/           ← created/updated by the pipeline
    handoff.json
    HANDOFF.md
    01 - Track One.json
    01 - Track One.tsv
    …
```

The pipeline **auto-detects** audio folders named like:

- `01 WAV Masters`
- `WAV Masters`
- `wav` / `audio` / `masters`

and deploys to an existing `* Timestamps` folder or the next free `NN Timestamps`.

## Command

```powershell
.\repeat.ps1 -Project "F:\Downloads\My Album" -Profile album
```

Higher quality (slower):

```powershell
.\repeat.ps1 -Project "F:\Downloads\My Album" -Profile album-hq
```

## Mock tree (no real audio)

This folder contains a **skeleton** under `mock-project/` so you can see names only:

```
mock-project/
  01 WAV Masters/.gitkeep
  06 Timestamps/   ← sample handoff + one track fixture (copied from fixtures)
```

Run against a real project with your own WAVs; do not expect the mock masters to transcribe.

## Profile defaults (`album`)

| Setting | Value |
|---------|--------|
| language | `en` |
| mode | `intended` |
| model | `turbo` |
| longform | `continuation` |
| speculative | `false` |
