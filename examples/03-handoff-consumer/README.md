# Example 03 — Handoff consumer

After a pipeline run, another app should treat **`handoff.json`** as the entry point.

## Markup block (for PRs / agents)

```xml
<timestamp-handoff schema="crisper-timestamps.handoff/v1" id="my-batch">
  <output_dir>path/to/NN Timestamps</output_dir>
  <entry>handoff.json</entry>
  <tracks>…</tracks>
  <words>…</words>
</timestamp-handoff>
```

## Python

```powershell
.\.venv\Scripts\python.exe examples\03-handoff-consumer\consume_handoff.py `
  examples\02-album-layout\mock-project\06 Timestamps\handoff.json
```

## TypeScript (sketch)

See `consume_handoff.ts` — load JSON, iterate `tracks`, open relative `artifacts_relative.json`.

## Contract

- Schema id: `crisper-timestamps.handoff/v1`
- Per track: `word_count`, `artifacts.json` (or `artifacts_relative.json` when co-located)
- Word object: `{ "word": string, "start": number, "end": number }` (seconds)
