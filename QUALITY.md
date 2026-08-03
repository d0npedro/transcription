# Quality lock — wiederholbarer Timestamp-Prozess

Referenzlauf: **Noch ein Bier bis zum Mond** (35 WAV Masters → `06 Timestamps`).

## Was „gleiche Qualität“ bedeutet

| Merkmal | Wert | Warum |
|---------|------|--------|
| Engine | CrisperWhisper 2.0 | Exakte Wortgrenzen (~30 ms) |
| `word_timestamps` | **immer an** | Kernprodukt |
| `longform_strategy` | **`continuation`** | Beste Naht-/Timing-Qualität >30 s |
| `speculative_decoding` | **aus** | Draft-Attention kann Timings verwischen |
| `hallucination_mitigation` | an | Loop-Repair |
| Exporte | json, tsv, srt, vtt, txt | Consumer + Untertitel |
| Handoff | `handoff.json` + `HANDOFF.md` | Portabel in andere Projekte |
| Deploy | `NN Timestamps` im Album-Root | Projektstruktur 01…0N |

## Profile

| ID | language | mode | model |
|----|----------|------|-------|
| `album` | en | intended | turbo |
| `album-hq` | en | intended | medium |
| `speech-de` | de | verbatim | turbo |
| `speech-en` | en | verbatim | turbo |

Sprache ist **kritisch**: falsche Sprache → oft leere Chunks (gesehen bei DE auf EN-Vocals).

## Wiederholen

```powershell
# Standard (wie Referenz-Album)
.\repeat.ps1 -Project "F:\Downloads\Noch ein Bier bis zum Mond" -Profile album

# Höhere Modellqualität
.\repeat.ps1 -Project "F:\Albums\X" -Profile album-hq

# Nur Audio-Ordner, kein Projekt-Deploy
.\repeat.ps1 -AudioDir "D:\takes" -Profile speech-de -NoDeploy
```

CLI:

```text
timestamps-repeat --project "F:\Album" --profile album
timestamps-repeat --list-profiles
```

## Nicht ändern ohne guten Grund

- Quality-Lock nur mit `--unlock` umgehbar (Pipeline).
- Hard floor im Code: `word_timestamps=True`, `speculative_decoding=False` immer.

## Handoff-Markup

Jedes Deploy enthält:

```xml
<timestamp-handoff schema="crisper-timestamps.handoff/v1" id="…">
  <output_dir>…\NN Timestamps</output_dir>
  <entry>handoff.json</entry>
</timestamp-handoff>
```
