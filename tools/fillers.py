#!/usr/bin/env python3
"""Find filler sounds ("um", "uh", "ah", throat-clears) to cut.

Parakeet mostly leaves fillers out of the transcript, so they hide in the
gaps between words. This scans every gap for a burst that is loud compared
to the room (voiced sound, not silence), and also lists any filler words the
transcript did catch. It only reports; the edit decision (cut, and how to
hide the jump) stays with whoever writes the plan.

Each finding is (clip, start, end) in that clip's source time -- cut from
the end of the word before to the start of the word after, so no real word
is clipped.

Usage:
    python tools/fillers.py --name youtube1
    python tools/fillers.py --name youtube1 --clip "WhatsApp Video 2026-10-22 at 5.05.16 PM"
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import load, work_dir

FILLER_WORDS = {"um", "umm", "uh", "uhh", "ah", "ahh", "er", "erm", "hmm", "mm", "mhm"}
SR = 16000
WIN = 800  # 50ms


def db(x):
    return 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12)


def clip_audio(path: Path) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:a:0", "-ac", "1",
                          "-ar", str(SR), "-f", "f32le", "-"], stdout=subprocess.PIPE).stdout
    return np.frombuffer(raw, dtype=np.float32)


def find(words, audio, min_gap=0.25, min_voiced=0.15, above_room=15.0):
    """Gaps whose loud (voiced) part lasts >= min_voiced seconds, more than
    above_room dB over the clip's room tone (10th percentile of gap levels)."""
    import librosa
    levels = [db(audio[i:i + WIN]) for p, q in zip(words, words[1:])
              for i in range(int(p["end"] * SR), int(q["start"] * SR) - WIN, WIN)]
    room = float(np.percentile(levels, 10)) if levels else -60.0
    out = []
    for p, q in zip(words, words[1:]):
        a, b = p["end"], q["start"]
        if b - a < min_gap:
            continue
        seg = audio[int(a * SR):int(b * SR)]
        lv = np.array([db(seg[i:i + WIN]) for i in range(0, len(seg) - WIN, WIN // 2)])
        loud = lv > room + above_room
        voiced_s = loud.sum() * (WIN / 2) / SR
        if voiced_s < min_voiced:
            continue
        burst = np.concatenate([seg[i * WIN // 2:i * WIN // 2 + WIN] for i in np.where(loud)[0]])
        flat = float(librosa.feature.spectral_flatness(y=burst).mean())
        # Voice-like (um/ah/throat) is low-flatness; clicks and bumps are noisy/high.
        kind = "voiced filler (um/ah/throat-clear?)" if flat < 0.02 else "noise (handling/click?)"
        out.append({"start": round(a, 2), "end": round(b, 2), "voiced_s": round(voiced_s, 2),
                    "peak_db": round(float(lv.max()), 1), "flatness": round(flat, 3), "kind": kind,
                    "context": f"...{p['word']} [ ] {q['word']}..."})
    for w in words:
        if w["word"].lower().strip(".,!?") in FILLER_WORDS:
            out.append({"start": w["start"], "end": w["end"], "kind": "filler word in transcript",
                        "context": w["word"]})
    return sorted(out, key=lambda r: r["start"]), room


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--clip", help="clip id (file stem); default: every clip in transcript.json")
    args = ap.parse_args()
    root = load()["footage_root"]
    t = json.loads((work_dir(args.name) / "transcript.json").read_text(encoding="utf-8"))
    for c in t["clips"]:
        if args.clip and c["id"] != args.clip:
            continue
        words = [w for w in t["words"] if w["clip"] == c["id"]]
        found, room = find(words, clip_audio(root / c["file"]))
        print(f"== {c['id']}  (room tone {room:.1f} dB, {len(found)} candidates)")
        for r in found:
            extra = f"voiced {r['voiced_s']}s peak {r['peak_db']} flat {r['flatness']}" if "voiced_s" in r else ""
            print(f"  {r['start']:7.2f}-{r['end']:7.2f}  {r['kind']:38s} {extra}  {r['context']}")


if __name__ == "__main__":
    main()
