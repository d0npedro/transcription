let meta = #{
    name: "extract-timestamps",
    description: "CrisperWhisper Timestamps + Handoff-Package (handoff.json / HANDOFF.md) fuer andere Projekte",
    when_to_use: "Audio → Wort-Timestamps mit portabler Uebergabe (handoff). Args: audio|audio_dir, optional handoff_to.",
    phases: [
        #{ title: "Env-Check", detail: "Python, ffmpeg, Package, Target parallel" },
        #{ title: "Setup", detail: "venv + pip install falls noetig" },
        #{ title: "Transcribe", detail: "CrisperWhisper word timestamps + auto-handoff" },
        #{ title: "Verify", detail: "JSON-Timestamps + handoff.json pruefen" },
        #{ title: "Handoff", detail: "Manifest/Markup finalisieren, optional in Zielprojekt kopieren" },
    ],
};

let check_schema = #{
    "type": "object",
    "required": ["ok", "detail"],
    "properties": #{
        "ok": #{ "type": "boolean" },
        "detail": #{ "type": "string" },
        "path": #{ "type": "string" },
    },
};

let files_schema = #{
    "type": "object",
    "required": ["files"],
    "properties": #{
        "files": #{
            "type": "array",
            "maxItems": 64,
            "items": #{ "type": "string" },
        },
        "count": #{ "type": "integer" },
        "detail": #{ "type": "string" },
    },
};

let run_schema = #{
    "type": "object",
    "required": ["success", "detail"],
    "properties": #{
        "success": #{ "type": "boolean" },
        "detail": #{ "type": "string" },
        "exit_code": #{ "type": "integer" },
        "outputs": #{
            "type": "array",
            "maxItems": 128,
            "items": #{ "type": "string" },
        },
        "handoff_json": #{ "type": "string" },
        "handoff_md": #{ "type": "string" },
        "copied_to": #{ "type": "string" },
    },
};

let verdict_schema = #{
    "type": "object",
    "required": ["file", "real", "reason", "word_count"],
    "properties": #{
        "file": #{ "type": "string" },
        "real": #{ "type": "boolean" },
        "reason": #{ "type": "string" },
        "word_count": #{ "type": "integer" },
        "monotonic": #{ "type": "boolean" },
        "evidence": #{ "type": "string" },
    },
};

let handoff_schema = #{
    "type": "object",
    "required": ["success", "detail", "handoff_json", "handoff_md", "markup"],
    "properties": #{
        "success": #{ "type": "boolean" },
        "detail": #{ "type": "string" },
        "handoff_json": #{ "type": "string" },
        "handoff_md": #{ "type": "string" },
        "copied_to": #{ "type": "string" },
        "markup": #{ "type": "string" },
        "track_count": #{ "type": "integer" },
        "total_words": #{ "type": "integer" },
    },
};

// --- args ---
let audio = ();
let audio_dir = ();
let language = "de";
let model = "turbo";
let mode = "verbatim";
let out_dir = "output";
let jobs = 1;
let handoff_to = ();
let handoff_id = ();
let workspace = "D:\\Projects\\transcription";

if args != () {
    if args.audio != () { audio = args.audio; }
    if args.audio_dir != () { audio_dir = args.audio_dir; }
    if args.language != () { language = args.language; }
    if args.model != () { model = args.model; }
    if args.mode != () { mode = args.mode; }
    if args.out_dir != () { out_dir = args.out_dir; }
    if args.jobs != () { jobs = args.jobs; }
    if args.handoff_to != () { handoff_to = args.handoff_to; }
    if args.handoff_id != () { handoff_id = args.handoff_id; }
    if args.workspace != () { workspace = args.workspace; }
}

if audio == () && audio_dir == () {
    pause("verification", "Pass args.audio oder args.audio_dir. Optional: handoff_to (Zielprojekt-Pfad), handoff_id, language, model, mode, out_dir.");
}

let target = if audio != () { audio } else { audio_dir };
log("Target=" + target + " model=" + model + " lang=" + language + " out=" + out_dir);
if handoff_to != () {
    log("handoff_to=" + handoff_to);
}

// =====================================================================
phase("Env-Check");
// =====================================================================
let env_jobs = [];

let p_py = "Check Python 3.10+ on Windows. Run python --version or py -3 --version via run_terminal_command. ";
p_py += "ok=true only if >= 3.10. detail=version string. path=executable.";
env_jobs.push(#{ prompt: p_py, label: "check:python", capability_mode: "execute", output_schema: check_schema });

let p_ff = "Check ffmpeg on PATH (ffmpeg -version). ok=true if runs; ok=false acceptable for WAV/FLAC. detail=first line.";
env_jobs.push(#{ prompt: p_ff, label: "check:ffmpeg", capability_mode: "execute", output_schema: check_schema });

let p_pkg = "In workspace " + workspace + " check imports. Prefer .venv\\Scripts\\python.exe. ";
p_pkg += "Run: <py> -c \"import crisper_timestamps, crisperwhisper; from crisper_timestamps.handoff import write_handoff; print('ok')\". ";
p_pkg += "ok=true only if import succeeds.";
env_jobs.push(#{ prompt: p_pkg, label: "check:package", capability_mode: "execute", output_schema: check_schema });

let p_tgt = "Verify audio target exists: " + target + ". Use Test-Path / list_dir. ";
p_tgt += "File: ok if audio suffix. Dir: ok if exists. detail + path absolute.";
env_jobs.push(#{ prompt: p_tgt, label: "check:target", capability_mode: "execute", output_schema: check_schema });

let env_results = parallel(env_jobs);
log("Env checks returned: " + env_results.len().to_string());

let package_ok = false;
if env_results.len() >= 3 {
    let pr = env_results[2];
    if pr != () && pr.success && pr.output.ok == true { package_ok = true; }
}
let target_ok = false;
if env_results.len() >= 4 {
    let tr = env_results[3];
    if tr != () && tr.success && tr.output.ok == true { target_ok = true; }
}
if !target_ok {
    pause("verification", "Audio-Ziel nicht gefunden: " + target);
}

// =====================================================================
phase("Setup");
// =====================================================================
if !package_ok {
    log("Installing package…");
    let setup_prompt = "";
    setup_prompt += "Install project at " + workspace + ". Use run_terminal_command. ";
    setup_prompt += "cd there; python -m venv .venv if needed; .venv\\Scripts\\python -m pip install -U pip; ";
    setup_prompt += ".venv\\Scripts\\python -m pip install -e . ; ";
    setup_prompt += "optional CUDA torch: pip install --upgrade torch --index-url https://download.pytorch.org/whl/cu128 ; ";
    setup_prompt += "verify: import crisper_timestamps, crisperwhisper, handoff. success=true only if import ok.";
    let setup_r = agent(setup_prompt, #{ label: "setup:install", capability_mode: "all", output_schema: run_schema });
    if setup_r == () || !setup_r.success || setup_r.output.success != true {
        let msg = "Setup failed";
        if setup_r != () && setup_r.success && setup_r.output.detail != () { msg = setup_r.output.detail; }
        pause("infra", "Installation fehlgeschlagen: " + msg);
    }
    log("Setup OK");
} else {
    log("Package ready — skip install");
}

// =====================================================================
phase("Transcribe");
// =====================================================================
let disc = "";
disc += "List audio files under: " + target + " (workspace " + workspace + "). ";
disc += "Extensions: wav mp3 m4a flac ogg opus webm mp4 mkv aac wma. ";
disc += "Single file → one entry. Return files[] paths (max 64). Do not transcribe.";
let disc_r = agent(disc, #{ label: "discover:audio", capability_mode: "execute", output_schema: files_schema });

let audio_files = [];
if disc_r != () && disc_r.success && disc_r.output.files != () {
    for f in disc_r.output.files { audio_files.push(f); }
}
if audio_files.len() == 0 {
    pause("verification", "Keine Audiodateien unter " + target);
}
log("Discovered " + audio_files.len().to_string() + " file(s)");

let jobs_str = jobs.to_string();
let tx = "";
tx += "Run timestamp CLI in " + workspace + ". ";
tx += "Command base: .\\.venv\\Scripts\\python.exe -m crisper_timestamps ";
tx += "-l " + language + " -m " + model + " --mode " + mode + " -o " + out_dir + " -j " + jobs_str + " ";
if handoff_id != () {
    tx += "--handoff-id " + handoff_id + " ";
}
if handoff_to != () {
    tx += "--handoff-to \"" + handoff_to + "\" ";
}
tx += "Pass all audio paths (or the directory). Files:\n";
for f in audio_files {
    tx += " - " + f + "\n";
}
tx += "CLI writes handoff.json + HANDOFF.md automatically. Long timeout (60+ min for albums). ";
tx += "success=true if exit 0. Set handoff_json/handoff_md to written paths. outputs=artifact list. ";
tx += "If handoff_to set, set copied_to.";

let tx_r = agent(tx, #{ label: "transcribe:run", capability_mode: "all", output_schema: run_schema });
if tx_r == () || !tx_r.success || tx_r.output.success != true {
    let msg = "Transcription failed";
    if tx_r != () && tx_r.success && tx_r.output.detail != () { msg = tx_r.output.detail; }
    pause("infra", "Transkription fehlgeschlagen: " + msg);
}
log("Transcription + handoff write OK");

// =====================================================================
phase("Verify");
// =====================================================================
let vjobs = [];
// handoff manifest check
let vh = "";
vh += "Verify handoff package under " + out_dir + " in workspace " + workspace + ". ";
vh += "Read handoff.json and HANDOFF.md with read_file. ";
vh += "Require schema starts with crisper-timestamps.handoff, tracks array present, summary.total_words is int. ";
vh += "real=true only with quoted evidence from handoff.json. file=path to handoff.json. word_count=summary.total_words.";
vjobs.push(#{ prompt: vh, label: "verify:handoff", capability_mode: "read-only", output_schema: verdict_schema });

// up to 12 track JSON checks
let max_v = audio_files.len();
if max_v > 12 { max_v = 12; }
let vi = 0;
for f in audio_files {
    if vi >= max_v { break; }
    let vp = "";
    vp += "Verify timestamp JSON for audio " + f + " under " + out_dir + " (" + workspace + "). ";
    vp += "Use list_dir/read_file. Need words[{word,start,end}], monotonic starts, word_count match. ";
    vp += "Empty words is OK for instrumentals (still real=true if JSON valid). ";
    vp += "real=true only with evidence. file=json path. word_count from file.";
    vjobs.push(#{ prompt: vp, label: "verify:track:" + vi.to_string(), capability_mode: "read-only", output_schema: verdict_schema });
    vi += 1;
}

let verdicts = parallel(vjobs);
let confirmed = 0;
let failed_v = 0;
for v in verdicts {
    if v != () && v.success && v.output.real == true {
        confirmed += 1;
    } else {
        failed_v += 1;
    }
}
log("Verify: " + confirmed.to_string() + "/" + verdicts.len().to_string() + " OK");

// =====================================================================
phase("Handoff");
// =====================================================================
let hp = "";
hp += "Finalize portable handoff for other projects. Workspace: " + workspace + ". out_dir: " + out_dir + ". ";
hp += "1) Ensure handoff.json + HANDOFF.md exist (regenerate if missing): ";
hp += ".\\.venv\\Scripts\\python.exe -m crisper_timestamps.handoff \"" + out_dir + "\" ";
if handoff_id != () { hp += "--id " + handoff_id + " "; }
hp += "--source \"" + target + "\" --model " + model + " --language " + language + " --mode " + mode + " ";
if handoff_to != () {
    hp += "--to \"" + handoff_to + "\" ";
}
hp += "2) Read HANDOFF.md and extract the <timestamp-handoff>...</timestamp-handoff> XML block into markup field. ";
hp += "3) success=true if handoff.json readable. handoff_json/handoff_md = absolute paths. ";
hp += "copied_to = dest if copied. track_count and total_words from handoff summary. detail=short status.";

let ho = agent(hp, #{ label: "handoff:finalize", capability_mode: "all", output_schema: handoff_schema });

let markup = "";
let hj = "";
let hm = "";
let copied = "";
let track_count = audio_files.len();
let total_words = 0;
let handoff_ok = false;

if ho != () && ho.success && ho.output.success == true {
    handoff_ok = true;
    if ho.output.markup != () { markup = ho.output.markup; }
    if ho.output.handoff_json != () { hj = ho.output.handoff_json; }
    if ho.output.handoff_md != () { hm = ho.output.handoff_md; }
    if ho.output.copied_to != () { copied = ho.output.copied_to; }
    if ho.output.track_count != () { track_count = ho.output.track_count; }
    if ho.output.total_words != () { total_words = ho.output.total_words; }
}

if !handoff_ok {
    pause("infra", "Handoff-Finalisierung fehlgeschlagen — handoff.json fehlt oder unlesbar unter " + out_dir);
}

// Compose final report for workflow UI
let report = "";
report += "# extract-timestamps + handoff\n\n";
report += "- target: " + target + "\n";
report += "- model: " + model + " language: " + language + " mode: " + mode + "\n";
report += "- out_dir: " + out_dir + "\n";
report += "- verified: " + confirmed.to_string() + "/" + verdicts.len().to_string() + "\n";
report += "- tracks: " + track_count.to_string() + " words: " + total_words.to_string() + "\n";
report += "- handoff_json: " + hj + "\n";
report += "- handoff_md: " + hm + "\n";
if copied != "" {
    report += "- copied_to: " + copied + "\n";
}
report += "\n## Output-Übergabe Markup\n\n";
report += "```xml\n";
if markup != "" {
    report += markup + "\n";
} else {
    report += "<timestamp-handoff schema=\"crisper-timestamps.handoff/v1\">\n";
    report += "  <output_dir>" + out_dir + "</output_dir>\n";
    report += "  <entry>handoff.json</entry>\n";
    report += "</timestamp-handoff>\n";
}
report += "```\n\n";
report += "Anderes Projekt: Ordner kopieren oder `handoff.json` laden (siehe HANDOFF.md).\n";

let report_path = write_scratch_file("report.md", report);
log("Handoff ready: " + hj);

complete(#{
    summary: "Timestamps + Handoff: " + track_count.to_string() + " tracks, " + total_words.to_string() + " words",
    path: report_path,
    report: report,
    out_dir: out_dir,
    handoff_json: hj,
    handoff_md: hm,
    handoff_markup: markup,
    copied_to: copied,
    verified: confirmed,
    track_count: track_count,
    total_words: total_words,
    model: model,
    language: language,
    mode: mode,
});
