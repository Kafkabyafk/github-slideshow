# Readings → Audio Suite — Handoff

**What this is (read this first).** There is **no magic tool registry**. "pdf2txt",
"voicebox", and "lyricbox" are **plain Python scripts** in this folder, driving
**open-source engines** (Tesseract OCR, PyMuPDF, Kokoro-82M via `kokoro-onnx`,
ffmpeg). Nothing here depends on a hosted service or a special MCP server. If you
can run Python, you can run the whole pipeline. It was built to turn course
readings (PDFs, including scanned/copy-protected ones) into narrated audio and an
optional synced read-along.

## The pipeline

```
PDF ──pdf2txt──▶ <name>.raw.txt ──textprep──▶ <name>.kokoro.txt ──voicebox──▶ .wav/.mp3 + .timings.json ──lyricbox──▶ .readalong.html
        (OCR)         (de-noise)      (normalize, 1 sentence/line)      (Kokoro TTS)                         (karaoke player)
```

There is also a **manual proofread** step that a human/Claude does between
`textprep` and `voicebox`: open the page images and the generated text side by
side, fix OCR errors, and delete junk the scripts can't know is junk (running
headers, footnote markers, table grids, figure captions). The scripts get you
~95% there; the eyeball pass gets the last 5%.

## One-time setup

```bash
cd tools
bash setup.sh          # installs tesseract, ffmpeg, python deps; downloads Kokoro model (~120MB) from GitHub
```

The Kokoro weights come from the `kokoro-onnx` **GitHub release** (not HuggingFace),
because some sandboxes block HuggingFace. Models land in `tools/models/`.

## The tools

### `pdf2txt.py` — PDF → raw text (OCR)
Renders each page to an image and OCRs it, so it works on scanned / no-text-layer
PDFs (the "around the copyright problem" path).
```bash
python pdf2txt.py reading.pdf --out out/                 # one file -> out/reading.raw.txt
python pdf2txt.py "Week2/" --out out/                     # every PDF in a folder
python pdf2txt.py reading.pdf --prefer-text               # use embedded text layer if clean (faster)
```

### `textprep.py` — raw text → Kokoro-ready text
One sentence per line (keeps every chunk under Kokoro's **510-token** limit, since
`KPipeline` splits on newlines), with numbers/symbols/abbreviations spelled out so
the misaki G2P never guesses. **Do your manual proofread on the `.kokoro.txt`.**
```bash
python textprep.py out/reading.raw.txt out/reading.kokoro.txt
```

### `voicebox.py` — Kokoro-ready text → audio (+ timeline)
Parallel Kokoro synthesis per sentence; stitches one `.wav`/`.mp3` and writes a
sentence-level `.timings.json`.
```bash
python voicebox.py out/reading.kokoro.txt --voice af_heart --out out/reading
python voicebox.py out/reading.raw.txt --prep --voice af_heart --out out/reading   # prep+synth in one go
```
Voices: `af_heart` (default, warm female), `af_bella`, `af_nicole`, `am_michael`,
`am_onyx`, … (American `a`, British `b`). Flags: `--speed`, `--workers`,
`--mp3-bitrate`, `--gap-sentence`, `--gap-paragraph`.

### `lyricbox.py` — text + audio → read-along player
Bundles the timeline + mp3 into ONE offline HTML that highlights and auto-scrolls
each sentence as it plays (tap a line to seek). Audio is embedded → single file,
works in mobile Safari/Chrome.
```bash
python lyricbox.py out/reading --title "Lake 2010"        # -> out/reading.readalong.html
```

## Batch a week (e.g. IR101 Week 2)

```bash
mkdir -p out
python pdf2txt.py "Week2/" --out out/                      # all PDFs -> *.raw.txt
for f in out/*.raw.txt; do
  b="out/$(basename "$f" .raw.txt)"
  python textprep.py "$f" "$b.kokoro.txt"                  # then PROOFREAD each .kokoro.txt
  python voicebox.py "$b.kokoro.txt" --voice af_heart --out "$b"
  python lyricbox.py "$b" || true
done
mkdir -p "IR101 Week2" && cp out/*.mp3 out/*.wav "IR101 Week2"/ && zip -r "IR101 Week2.zip" "IR101 Week2"
```

## Performance / budget notes

- **No GPU** in the web container → Kokoro int8 runs ~0.6× realtime per core and
  **saturates all cores**, so more workers ≠ much faster once cores are full.
  Budget ≈ **render time ≈ total audio length** (a 50-min reading ≈ ~50 min).
- OCR and textprep are cheap and **parallelize across readings** (one process or
  one agent per PDF).
- RAM: each Kokoro worker ≈ ~0.6 GB; 4 workers fits comfortably in <4 GB.

## Environment gotchas (so the next session isn't surprised)

- This runs in an **ephemeral cloud container**: `/tmp` scratch and installed pip
  packages **do not persist**. The durable copy is **this `tools/` folder in the
  git repo**. Re-run `setup.sh` at the start of each session to reinstall engines
  + model.
- **HuggingFace may be blocked**; GitHub is not — hence the model download URL.
- The container **cannot see your local Desktop**. Hand files in by uploading to
  chat, pushing to the repo, or via a connected Google Drive folder.
