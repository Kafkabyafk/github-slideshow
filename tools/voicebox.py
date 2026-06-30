#!/usr/bin/env python3
"""voicebox — Kokoro-ready .txt -> .wav/.mp3 (+ sentence timeline JSON).

Synthesizes the text per line in parallel with the Kokoro engine (kokoro-onnx),
captures each segment's exact duration, stitches one audio file, and writes a
sentence-level timeline that lyricbox.py turns into a read-along player.

Input should be Kokoro-ready (one sentence per line). Pass --prep to run
textprep.py automatically on a raw file first.

Usage:
    python voicebox.py chapter.kokoro.txt --voice af_heart --out out/chapter
    python voicebox.py reading.raw.txt --prep --voice af_heart --out out/reading
"""
import argparse, json, os, time
import multiprocessing as mp
import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = os.path.join(HERE, "models", "kokoro.int8.onnx")
VOICES = os.path.join(HERE, "models", "voices-v1.0.bin")
SR = 24000

_args = None
_k = None


def _init(model, voices):
    global _k
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    from kokoro_onnx import Kokoro
    _k = Kokoro(model, voices)


def _synth(task):
    idx, text, voice, speed, outdir = task
    s, _ = _k.create(text, voice=voice, speed=speed, lang="en-us")
    s = np.asarray(s, dtype=np.float32)
    np.save(os.path.join(outdir, f"c{idx:05d}.npy"), s)
    return idx, len(s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--out", required=True, help="output path prefix, e.g. out/reading")
    ap.add_argument("--voice", default="af_heart")
    ap.add_argument("--speed", type=float, default=1.0)
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2)))
    ap.add_argument("--gap-sentence", type=float, default=0.18)
    ap.add_argument("--gap-paragraph", type=float, default=0.45)
    ap.add_argument("--mp3-bitrate", default="32k")
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--voices", default=VOICES)
    ap.add_argument("--prep", action="store_true", help="run textprep on a raw input first")
    a = ap.parse_args()

    raw = open(a.input).read()
    if a.prep:
        from textprep import to_kokoro_lines
        raw = to_kokoro_lines(raw)

    lines = raw.splitlines()
    chunks = []  # (idx, text, big_gap)
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        chunks.append((len(chunks), line.strip(), nxt.strip() == ""))
    print(f"chunks: {len(chunks)}  voice={a.voice}  workers={a.workers}", flush=True)

    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    tmp = a.out + "_chunks"
    os.makedirs(tmp, exist_ok=True)
    tasks = [(idx, t, a.voice, a.speed, tmp) for idx, t, _ in chunks]

    t0, done = time.time(), 0
    with mp.get_context("spawn").Pool(a.workers, initializer=_init, initargs=(a.model, a.voices)) as pool:
        for _ in pool.imap_unordered(_synth, tasks, chunksize=2):
            done += 1
            if done % 25 == 0 or done == len(tasks):
                print(f"  {done}/{len(tasks)}  ({time.time()-t0:.0f}s)", flush=True)

    sent_gap = np.zeros(int(SR * a.gap_sentence), np.float32)
    para_gap = np.zeros(int(SR * a.gap_paragraph), np.float32)
    pieces, timings, cur = [], [], 0.0
    for idx, text, big in chunks:
        s = np.load(os.path.join(tmp, f"c{idx:05d}.npy"))
        start = cur
        pieces.append(s); cur += len(s) / SR
        timings.append({"i": idx, "t": text, "start": round(start, 3), "end": round(cur, 3)})
        gap = para_gap if big else sent_gap
        pieces.append(gap); cur += len(gap) / SR

    full = np.concatenate(pieces)
    sf.write(a.out + ".wav", full, SR)
    json.dump({"voice": a.voice, "sr": SR, "duration": round(len(full) / SR, 3), "lines": timings},
              open(a.out + ".timings.json", "w"), ensure_ascii=False)
    import subprocess
    subprocess.run(["ffmpeg", "-y", "-i", a.out + ".wav", "-ac", "1", "-ar", str(SR),
                    "-codec:a", "libmp3lame", "-b:a", a.mp3_bitrate, a.out + ".mp3"],
                   check=True, capture_output=True)
    print(f"DONE  {len(full)/SR/60:.1f} min audio  compute {(time.time()-t0)/60:.1f} min")
    print(f"  {a.out}.wav  {a.out}.mp3  {a.out}.timings.json")


if __name__ == "__main__":
    main()
