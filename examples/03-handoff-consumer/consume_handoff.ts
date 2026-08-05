/**
 * Sketch: load a co-located handoff.json and read relative track JSON paths.
 * Run with:  npx tsx examples/03-handoff-consumer/consume_handoff.ts path/to/handoff.json
 */
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";

type Word = { word: string; start: number; end: number };
type Track = {
  stem?: string;
  word_count?: number;
  artifacts_relative?: { json?: string };
  artifacts?: { json?: string };
};
type Handoff = {
  schema?: string;
  id?: string;
  summary?: { track_count?: number; total_words?: number };
  tracks?: Track[];
};

const handoffPath = process.argv[2];
if (!handoffPath) {
  console.error("Usage: consume_handoff.ts path/to/handoff.json");
  process.exit(2);
}

const handoff = JSON.parse(readFileSync(handoffPath, "utf8")) as Handoff;
const base = dirname(handoffPath);
console.log(`id=${handoff.id} schema=${handoff.schema}`);
console.log(
  `tracks=${handoff.summary?.track_count} words=${handoff.summary?.total_words}`,
);

for (const track of handoff.tracks ?? []) {
  const wc = track.word_count ?? 0;
  if (!wc) continue;
  const rel = track.artifacts_relative?.json;
  if (!rel) continue;
  const data = JSON.parse(readFileSync(join(base, rel), "utf8")) as {
    words?: Word[];
    text?: string;
  };
  console.log(`[${track.stem}] ${(data.words ?? []).length} words`);
  for (const w of (data.words ?? []).slice(0, 3)) {
    console.log(`  ${w.start.toFixed(3)}-${w.end.toFixed(3)}  ${w.word}`);
  }
}
