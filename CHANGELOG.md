# Changelog

## [1.0.0] — 2026-08-03

Initial release: CrisperWhisper word-level timestamps with quality-locked repeat pipeline.

### Features
- CLI `timestamps` / `crisper-timestamps` — exact word timestamps (JSON, TSV, SRT, VTT, TXT)
- Quality lock: `word_timestamps`, `continuation` longform, no speculative decoding
- Handoff package: `handoff.json` + `HANDOFF.md` + XML markup for other projects
- Repeat pipeline: `timestamps-repeat`, `REPEAT.bat`, `repeat.ps1`
- Profiles: `album`, `album-hq`, `speech-de`, `speech-en`
- Auto-detect album layout (`01 WAV Masters` → `NN Timestamps`)
- Grok workflow: `.grok/workflows/extract-timestamps.rhai`
- Windows setup: `START.bat`, `setup.ps1` (incl. CUDA torch)

### Proven on
- Album *Noch ein Bier bis zum Mond* (35 WAV masters → handoff + project deploy)
