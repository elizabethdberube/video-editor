#!/usr/bin/env python3
"""Render an edit plan (plan.json) into a finished 30fps CFR video (1920x1080
by default; vertical and square formats too).

Everything here is free to use in monetized YouTube videos: ffmpeg
(LGPL/GPL), OpenCV (Apache 2.0) and the YuNet face model (MIT) put no
conditions on the videos made with them, and nothing calls a paid service.

Every time in the plan is a per-clip source time (0 at that file's start),
never a project-timeline time -- see transcribe.py. The plan is a list of
segments, played in order:

    {"clip": "cam", "start": 4.1, "end": 10.9}
        A piece of one clip, its own audio. Optional "speed" (default 1,
        slow-mo below 1, fast-forward above -- audio tempo is chained across
        multiple atempo filters since ffmpeg rejects a single atempo outside
        0.5-2.0). Optional "zoom": {"factor": 1.3, "cx": 0.5, "cy": 0.4,
        "ease_in": 0.3, "ease_out": 0.3} for a punch-in -- eases from 1x to
        "factor" over ease_in seconds of the segment's own (post-speed)
        output duration, holds, eases back out over the last ease_out
        seconds. cx/cy (0-1, default centered) is the zoom target point.
    {"photo": "IMG_0887.HEIC", "duration": 1.5}
        A still with a slow push-in, silent.
    {"block": "phone", "video": [{"clip": "rec", "start": .., "end": .., "speed": ..}, ...],
     "audio": [{"clip": "old", "start": .., "end": .., "at": 0.0} | {"file": "vo.wav", "at": 0.0}]}
        Several video pieces played back to back, with separately placed
        audio on top (voiceover over a silent screen recording). "at" is the
        offset inside the block. The block's own clip audio is dropped.

Any segment can also take:
    "pip": {"clip": "rec", "start": 140, "speed": 1, "position": "right", "height": 0.75}
        Another clip inset over this one, running from its own source "start"
        for as long as the segment lasts (holds its last frame if it runs out).
        Silent. position: left/right/top-left/top-right/bottom-left/bottom-right.
        height: fraction of the frame (default 0.75 vertical, 0.32 otherwise).
    "fade_in" / "fade_out": seconds, picture from/to black and audio with it.
    "volume_db": gain on the segment's audio.
    "overlays": [{"graphic": "warning1.mov", "at": 37.2}]
        Transparent graphics from graphics.py (<work_dir>/graphics/), or
        any PNG with "duration". Plays once, from "at".
    "sfx": [{"file": "whoosh.wav", "at": 37.0, "volume_db": -6}]
        Sound effects from the shared pool (_editor/assets/sfx/, falling
        back to the work dir), mixed on top of the segment's audio.
    "broll": [{"photo": "receipts.jpg", "at": 59.0, "duration": 4},
              {"clip": "rec", "start": 196, "at": 44.0, "duration": 5}]
        Full-frame cutaways: the picture switches to a photo (slow push-in)
        or another clip (from its own source "start", in that clip's
        layout) while this segment's audio keeps playing. A clip cutaway can
        take the same "zoom" as a clip segment, e.g. to push in on a detail.
    "blur": [{"at": 55.45, "duration": 0.85, "x": 0.27, "y": 0.06, "w": 0.43, "h": 0.41}]
        Pixelate a rectangle (fractions of the frame) for a while -- for
        personal info that can't be cut, like a device ID label.
    "music": false
        Keep the background music silent during this segment (it ramps out
        and back in around it) -- e.g. clips that already have music baked in.

  Picture:
    "flip": "horizontal" | "vertical" | "both"
    "rotate": 90 | 180 | 270 (turns the source, e.g. sideways phone footage)
              or any other angle (tilts the frame, zoomed so no corners show)
    "stabilize": true | {"shakiness": 5, "smoothing": 15}   (clip segments)
        Two-pass vid.stab; the motion analysis is cached in <work_dir>/stab.
    "reverse": true      (clip segments, up to 30s; audio plays backwards too)
    "reframe": "auto" | 0-1   (clip segments with the default "fill" layout)
        Crop to fill the frame following the largest face (OpenCV YuNet,
        cached in <work_dir>/reframe.json), or at a fixed horizontal
        position. Mostly for landscape footage in a vertical Short.
    "transform": {"scale": 0.75, "x": 0.5, "y": 0.5, "rotate": -4,
                  "border": {"width": 12, "color": "white"},
                  "shadow": true | {"blur": 18, "opacity": 0.55, "offset": 16},
                  "background": "blur" | "black" | "#1d3557",
                  "enter": "slide_left|slide_right|slide_up|slide_down|pop|fade",
                  "exit": same names, "anim": 0.4}
        Shrink the picture into a card over a background, with border,
        drop shadow, tilt and an animated entrance/exit.
    "motion" (photos): "push_in" (default) | "pull_out" | "pan_left" |
        "pan_right" | "pan_up" | "pan_down" | "none"
  Look (applied to the footage, B-roll and PiP -- never to graphics):
    "enhance": true        auto light/colour fix (contrast, white balance, vibrance, light sharpen)
    "color": {"brightness": 0.03, "contrast": 1.1, "saturation": 1.2, "gamma": 1.0,
              "vibrance": 0.2, "temperature": 5500, "shadows": 0.5, "highlights": -0.3,
              "lut": "film.cube"}     (LUT files go in <work_dir>/luts)
    "sharpen": 0.5-1.5
    "filters": ["bw", "sepia", "vintage", "vignette", "blur", "grain", "invert",
                "warm", "cool", "vivid", "cinematic", "letterbox", "glow"]
  Joins:
    "transition": {"type": "fade", "duration": 0.5}
        Into this segment from the previous one (they overlap by the
        duration). Types: fade, dissolve, fadeblack, fadewhite, wipeleft/
        right/up/down, slideleft/right/up/down, smoothleft/right, circleopen/
        close, radial, zoomin, pixelize, hblur, distance. Any transition makes
        the join a re-encode instead of a stream copy.
    For overlays, sfx and broll, "at" on a clip segment is that clip's SOURCE time
    (so re-trimming the segment doesn't move the graphic off its moment);
    on a photo or block it's seconds into the segment. Anything that would
    start outside the segment is skipped with a warning.

Amazon reviews ("destination": "amazon") must include Liz's gifted-product
disclosure: a block whose audio is {"file": "@amazon_disclosure", "at": 0}
(the clip lives in _editor/assets/disclosure/amazon_gifted_disclosure.wav).
Render stops if the clip is missing on this computer or the plan lacks it.

Plan-level options:
    "format": "landscape" (1920x1080, default) | "vertical" (1080x1920, Shorts) | "square" (1080x1080)
    "defaults": {"enhance": true, ...}
        Settings applied to every segment unless the segment sets its own.
    "destination": "youtube" | "amazon"   -- required if "music" is set.
    "music": {"files": ["a.mp3", "b.mp3"], "level_lufs": -30, "crossfade": 2}
        A playlist under the video, crossfaded track to track and repeated
        if it runs short, ducked whenever someone talks. It starts at the
        first segment that allows music. Each track is gain-matched to
        level_lufs using its loudness from catalog_music.py's catalog
        (tracks not in the catalog fall back to "volume_db", default -20).
        Files are relative to music_dir in config.json. {"file": "x.mp3"}
        still works for a single track. Refused for Amazon videos: Liz's
        rule is music on YouTube videos only.
    "voice_level_lufs": -20
        Gain every segment's own audio (and block voiceover pieces) so they
        all sit at the same loudness before mixing. Each piece of 3s or more
        is measured on its own; shorter ones use their whole file's level.
        Measurements are cached in <work_dir>/loudness.json. Without it,
        sources recorded at different distances play several dB apart and
        music swamps the quiet ones.
    "voice_cleanup": true
        Rumble cut, noise reduction, a little presence and gentle
        compression on every clip's own audio and clip voiceover pieces
        (not music or sfx), and on voiceover files in blocks. A clip can opt
        out with "voice_cleanup": false.
    "captions": true, "transcripts": ["transcript.json", "../other/transcript.json"]
        Burn in captions from the word timings. Words are matched to plan
        clips by file stem (transcribe.py's default clip id), so audio from
        any clip (or a transcribed voiceover file) gets captioned wherever
        the plan uses it.

A clip can set "restore": true when its file was heavily compressed (e.g.
sent through WhatsApp): deblock + denoise at source size, lanczos upscale,
light sharpen. It can't bring back lost detail -- originals are always better.

"clips" maps short ids to files under footage_root. Each clip's "layout" is
"fill" (crop to 16:9, default) or "vertical" (phone screen centred over a
blurred copy of itself). "audio_track" picks the audio stream (default 0;
iPhone .MOVs also carry an unusable 4ch apac track as 0:a:1).

Segments render to <work_dir>/render/NNN.mp4 in one uniform format, then get
concatenated, music-mixed, captioned and loudness-normalised to -14 LUFS.

Usage:
    python tools/render.py --name video1
    python tools/render.py --name video1 --only 3      # re-render one segment, then re-join
    python tools/render.py --name video1 --preview     # fast 540p review copy -> <name>_preview.mp4
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import assets_dir, load, work_dir

W, H, FPS = 1920, 1080, 30
VIDEO_OUT = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
             "-pix_fmt", "yuv420p", "-r", str(FPS)]
AUDIO_OUT = ["-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2"]
FADE = 0.02  # short audio fades at every cut, so hard cuts don't click
PIP_MARGIN = 40
LOUDNORM = "I=-14:TP=-1.5:LRA=11"
# Rumble cut, noise reduction tuned to her iPhone audio's real floor (~-55
# dB), a little less boxiness, a little more presence, then a gentle gate
# that dips pauses by at most 12 dB. Measured on IMG_0895: voice-to-pause gap
# 29.3 dB -> 37.8 dB with speech level unchanged. A compressor was tried
# first and dropped: its makeup gain raised the pauses as much as the noise
# reduction lowered them (gap 29.2 dB), and loudnorm evens out levels anyway.
VOICE_CLEANUP = ("highpass=f=80,afftdn=nf=-60:nr=15:tn=1,"
                 "equalizer=f=250:t=q:w=1:g=-2,equalizer=f=3500:t=q:w=1.2:g=2,"
                 "agate=threshold=0.01:ratio=3:attack=5:release=250:range=0.25")


PEAK_GUARD = "alimiter=limit=0.5:attack=1:release=60:level=false"   # -6 dBFS
# Final ceiling after loudnorm. Measured on WhatsApp audio: guard + this ->
# -14.5 LUFS at -1.4 dBTP (without the guard, a final limiter alone made the
# encoded peaks worse, +0.8 dBTP).
FINAL_CEILING = "alimiter=limit=0.79:attack=5:release=80:level=false"


# Liz's gifted-product disclosure ("This company was kind enough to gift this
# item to me, so let's go ahead and try it out."), required in every Amazon
# review. Lives in the footage folder's shared assets, not the repo, so each
# computer needs its own copy -- render refuses Amazon plans without it.
DISCLOSURE = "@amazon_disclosure"


def disclosure_path() -> Path:
    return assets_dir("disclosure") / "amazon_gifted_disclosure.wav"


def audio_file(name: str, wd: Path) -> Path:
    """Block voiceover files: relative to the work dir, or the disclosure shortcut."""
    return disclosure_path() if name == DISCLOSURE else wd / name


def check_amazon_disclosure(plan):
    """Amazon reviews must play the gifted disclosure. Stop, with
    instructions, if the clip isn't on this computer or the plan forgot it."""
    if plan.get("destination") != "amazon":
        return
    path = disclosure_path()
    if not path.exists():
        sys.exit(f"Amazon review needs the gifted-product disclosure clip, but it isn't on this computer.\n"
                 f"Put it here: {path}\n(the 5s WAV of Liz saying 'This company was kind enough to gift "
                 f"this item to me, so let's go ahead and try it out.')")
    used = any(a.get("file") == DISCLOSURE for s in plan["segments"] for a in s.get("audio", []))
    if not used:
        sys.exit("Amazon review plan doesn't include the gifted disclosure. Add a block segment with "
                 f"\"audio\": [{{\"file\": \"{DISCLOSURE}\", \"at\": 0}}] -- normally right after her "
                 "intro names the product, before the demo.")


def voice_chain(clip: dict, cleanup: bool, level_db=None) -> str:
    """Speech processing for one clip's own audio: level-matching gain (from
    "voice_level_lufs", see set_voice_levels), then optional cleanup."""
    level_db = clip.get("_level_db") if level_db is None else level_db
    # The limiter right after the gain catches handling noise: on quiet phone
    # speech (-32 dB RMS) a +12 dB level gain pushed box crinkles and jar taps
    # to +11 dBFS, which nothing downstream could tame cleanly.
    chain = f"volume={level_db:.2f}dB,{PEAK_GUARD}," if level_db else ""
    if cleanup and clip.get("voice_cleanup", True):
        chain += VOICE_CLEANUP + ","
    return chain


MIN_LEVEL_SPAN = 3.0  # shorter pieces use their whole file's loudness; gating needs a few seconds


def measure_loudness(path: Path, track: int, wd: Path, start=None, end=None) -> float:
    """Integrated loudness (LUFS) of one audio track, or a range of it,
    cached in <work_dir>/loudness.json."""
    cache_file = wd / "loudness.json"
    cache = json.loads(cache_file.read_text(encoding="utf-8")) if cache_file.exists() else {}
    key = f"{path.name}|{track}|{start}|{end}|{path.stat().st_mtime_ns}"
    if key not in cache:
        rng = ["-ss", f"{start:.3f}", "-to", f"{end:.3f}"] if start is not None else []
        err = subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", *rng, "-i", str(path), "-map", f"0:a:{track}",
                              "-af", "ebur128", "-f", "null", "-"],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE).stderr.decode(errors="replace")
        summary = err[err.rindex("Integrated loudness"):]
        cache[key] = float(summary.split("I:")[1].split()[0])
        cache_file.write_text(json.dumps(cache, indent=2), encoding="utf-8")
    return cache[key]


def set_voice_levels(plan, clips, root, wd, target):
    """Gain every piece of speech to the same loudness before anything is
    mixed. Her sources differ a lot: on video2, old video -18.3 LUFS,
    IMG_0895 -22.4, IMG_0942 -29.5 as whole files, and inside the old video
    the hook, its setup narration and its sign-off sat at about -22, -27 and
    -17 dB. So each segment (or block audio piece) of MIN_LEVEL_SPAN or more
    is measured on its own; shorter ones fall back to their file's level."""
    for cid, c in clips.items():
        path, track = root / c["file"], c.get("audio_track", 0)
        if has_audio(path, track):
            lufs = measure_loudness(path, track, wd)
            if lufs > -60:  # silent tracks (e.g. her screen recordings) get no gain
                c["_level_db"] = target - lufs

    def level(c, path, track, start, end):
        if "_level_db" not in c:
            return None
        if end - start < MIN_LEVEL_SPAN:
            return c["_level_db"]
        lufs = measure_loudness(path, track, wd, start, end)
        return target - lufs if lufs > -60 else c["_level_db"]

    for seg in plan["segments"]:
        if "clip" in seg:
            c = clips[seg["clip"]]
            seg["_level_db"] = level(c, root / c["file"], c.get("audio_track", 0), seg["start"], seg["end"])
        for a in seg.get("audio", []):
            if "file" in a:
                a["_level_db"] = target - measure_loudness(audio_file(a["file"], wd), 0, wd)
            else:
                c = clips[a["clip"]]
                a["_level_db"] = level(c, root / c["file"], c.get("audio_track", 0), a["start"], a["end"])


def run(cmd, cwd=None):
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed:\n{' '.join(cmd)}\n{proc.stderr.decode(errors='replace')[-3000:]}")
    return proc


def has_audio(path: Path, track: int) -> bool:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", f"a:{track}",
                          "-show_entries", "stream=index", "-of", "csv=p=0", str(path)],
                         stdout=subprocess.PIPE).stdout.strip()
    return bool(out)


def probe_duration(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", str(path)], stdout=subprocess.PIPE).stdout
    return float(out.strip())


def n_inputs(cmd) -> int:
    return cmd.count("-i")


def layout_filter(layout: str, src: str, out: str, restore=False) -> str:
    """restore: the source was heavily compressed (e.g. sent over WhatsApp),
    so upscale with lanczos and add a light sharpen after; the deblock/denoise
    half runs before this, at source resolution (see RESTORE_PRE)."""
    flags, post = (":flags=lanczos", "," + RESTORE_POST) if restore else ("", "")
    if layout == "vertical":
        return (f"[{src}]split[bg][fg];"
                f"[bg]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                f"boxblur=40:2,eq=brightness=-0.12[bgb];"
                f"[fg]scale=-2:{H - 40}{flags}{post}[fgs];"
                f"[bgb][fgs]overlay=(W-w)/2:(H-h)/2,setsar=1[{out}]")
    return (f"[{src}]scale={W}:{H}:force_original_aspect_ratio=increase{flags},"
            f"crop={W}:{H}{post},setsar=1[{out}]")


# Clean-up for heavily compressed sources (clip option "restore": true).
# Chosen by side-by-side on 848x478 WhatsApp footage: crisper text/logos than
# a plain upscale; nlmeans looked almost the same but rendered 11x slower.
RESTORE_PRE = "deblock=filter=strong:block=8,hqdn3d=2:1.5:3:3"
RESTORE_POST = "unsharp=5:5:0.7:5:5:0"


def atempo_chain(speed: float) -> str:
    """atempo rejects a single value outside 0.5-2.0 (confirmed: ffmpeg
    errors 'out of range' even though its own docs claim up to 100) -- chain
    multiple instances to cover real slow-mo/fast-forward speeds."""
    filters, remaining = [], speed
    while remaining < 0.5:
        filters.append(0.5)
        remaining /= 0.5
    while remaining > 2.0:
        filters.append(2.0)
        remaining /= 2.0
    filters.append(remaining)
    return ",".join(f"atempo={f:.6f}" for f in filters)


def zoom_filter(zoom: dict, dur: float, src: str, out: str) -> str:
    """Punch-in via zoompan (crop's w/h are only evaluated once at filter
    init in this ffmpeg build -- confirmed by testing, so a time-varying
    crop size doesn't work; zoompan is the filter actually built for this,
    and photo_graph already relies on it for push-ins). d=1 so every
    output frame consumes the next real input frame -- motion keeps playing
    instead of freezing on one frame like a photo push-in does. Expressions
    use 'on' (output frame number), eased in/held/eased out in frames."""
    factor = zoom.get("factor", 1.3)
    cx, cy = zoom.get("cx", 0.5), zoom.get("cy", 0.5)
    ease_in = min(zoom.get("ease_in", 0.3), dur / 2)
    ease_out = min(zoom.get("ease_out", 0.3), dur / 2)
    total_f = max(round(dur * FPS), 1)
    in_f = max(round(ease_in * FPS), 1)
    out_f = max(total_f - round(ease_out * FPS), in_f)
    z = (f"if(lt(on,{in_f}),1+({factor}-1)*on/{in_f},"
         f"if(lt(on,{out_f}),{factor},"
         f"{factor}-({factor}-1)*(on-{out_f})/{max(total_f - out_f, 1)}))")
    x = f"min(max(iw*{cx}-(iw/zoom/2),0),iw-iw/zoom)"
    y = f"min(max(ih*{cy}-(ih/zoom/2),0),ih-ih/zoom)"
    return f"[{src}]zoompan=z='{z}':x='{x}':y='{y}':d=1:s={W}x{H}:fps={FPS}[{out}]"


# --- picture tools (flip/rotate/stabilize/reverse/reframe/transform/looks) ---

def even(x: float) -> int:
    return max(2, int(round(x / 2)) * 2)


def orient_filter(seg) -> str:
    """Flip and 90-degree rotation, applied to the source before layout so a
    sideways clip is reframed correctly. Returns ',filter,...' or ''."""
    f = []
    turn = {90: "transpose=clock", 180: "transpose=clock,transpose=clock",
            270: "transpose=cclock", -90: "transpose=cclock"}.get(seg.get("rotate"))
    if turn:
        f.append(turn)
    f += {"horizontal": ["hflip"], "vertical": ["vflip"], "both": ["hflip", "vflip"]}.get(seg.get("flip"), [])
    return "".join("," + x for x in f)


def tilt_filter(angle: float) -> str:
    """Rotate the whole frame by any angle, zoomed just enough that no black
    corners show."""
    import math
    a = math.radians(angle)
    k = abs(math.cos(a)) + abs(math.sin(a)) * max(W / H, H / W)
    return f"scale={even(W * k)}:{even(H * k)},rotate={a:.5f}:ow={W}:oh={H}"


def stab_file(seg, clips, root, wd) -> str:
    """Pass 1 of stabilisation: run vidstabdetect over exactly the frames the
    segment will use (same seek + retime chain, so frame numbers line up) and
    cache the motion file. Returns its path relative to the work dir, where
    segment renders run (avoids escaping the drive colon in the filter)."""
    c = clips[seg["clip"]]
    opts = seg["stabilize"] if isinstance(seg["stabilize"], dict) else {}
    span, speed = seg["end"] - seg["start"], seg.get("speed", 1.0)
    rel = (f"stab/{Path(c['file']).stem}_{seg['start']:.2f}_{seg['end']:.2f}_{speed}"
           f"_{opts.get('shakiness', 5)}.trf")
    if not (wd / rel).exists():
        (wd / "stab").mkdir(exist_ok=True)
        run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-ss", f"{seg['start']:.3f}", "-to", f"{seg['end']:.3f}",
             "-i", str(root / c["file"]), "-vf",
             f"{retime(span, speed)},vidstabdetect=shakiness={opts.get('shakiness', 5)}:accuracy=15:result={rel}",
             "-f", "null", "-"], cwd=wd)
    return rel


def stab_filter(seg, rel) -> str:
    opts = seg["stabilize"] if isinstance(seg["stabilize"], dict) else {}
    return (f",vidstabtransform=input={rel}:smoothing={opts.get('smoothing', 15)}:"
            f"zoom=0:optzoom=1:interpol=bicubic")


FACE_MODEL = "face_detection_yunet_2023mar.onnx"  # OpenCV zoo YuNet (MIT), in _editor/assets/models


def face_track(path: Path, start: float, end: float, wd: Path, rate=5) -> list:
    """Horizontal face position (0-1) over a clip range, sampled `rate` times
    a second, smoothed, cached in <work_dir>/reframe.json. OpenCV 5 dropped
    the Haar cascades, so this uses its YuNet detector. Frames with no face
    hold the last known position (0.5 until one is found)."""
    import cv2
    import numpy as np
    cache_file = wd / "reframe.json"
    cache = json.loads(cache_file.read_text(encoding="utf-8")) if cache_file.exists() else {}
    key = f"{path.name}|{start:.3f}|{end:.3f}|{rate}"
    if key in cache:
        return cache[key]
    model = assets_dir("models") / FACE_MODEL
    if not model.exists():
        sys.exit(f"auto reframe needs {model} (OpenCV zoo face_detection_yunet_2023mar.onnx)")
    w, h = 640, 360
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{start:.3f}", "-to", f"{end:.3f}", "-i", str(path),
                          "-vf", f"fps={rate},scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                         stdout=subprocess.PIPE).stdout
    frames = np.frombuffer(raw, dtype=np.uint8).reshape(-1, h, w, 3)
    det = cv2.FaceDetectorYN.create(str(model), "", (w, h))
    xs, last = [], None
    for f in frames:
        _, faces = det.detect(f)
        if faces is not None and len(faces):
            big = max(faces, key=lambda r: r[2] * r[3])
            last = float((big[0] + big[2] / 2) / w)
        xs.append(last)
    first = next((x for x in xs if x is not None), 0.5)
    xs = [first if x is None else x for x in xs]
    # median then exponential smoothing: no jitter, no snapping between faces
    med = [float(np.median(xs[max(0, i - 3):i + 4])) for i in range(len(xs))]
    out, s = [], med[0] if med else 0.5
    for x in med:
        s += 0.25 * (x - s)
        out.append(round(s, 4))
    cache[key] = out
    cache_file.write_text(json.dumps(cache), encoding="utf-8")
    return out


def reframe_filter(seg, c, root, wd, src: str, out: str) -> str:
    """Fill the frame by cropping, steering the crop to follow a face
    ("reframe": "auto") or holding a fixed horizontal position (0-1). Used
    when the source is wider than the output, e.g. landscape footage in a
    vertical Short."""
    speed = seg.get("speed", 1.0)
    cover = f"scale={W}:{H}:force_original_aspect_ratio=increase"
    if seg["reframe"] == "auto":
        rate = 5
        xs = face_track(root / c["file"], seg["start"], seg["end"], wd, rate)
        keys = [(i / rate / speed, x) for i, x in enumerate(xs)][::2]  # every 0.4s of source
        if not keys:
            keys = [(0.0, 0.5)]
        terms = []
        for (t0, x0), (t1, x1) in zip(keys, keys[1:]):
            slope = (x1 - x0) / (t1 - t0)
            terms.append(f"gte(t,{t0:.3f})*lt(t,{t1:.3f})*({x0:.4f}+{slope:.5f}*(t-{t0:.3f}))")
        terms.append(f"gte(t,{keys[-1][0]:.3f})*{keys[-1][1]:.4f}")
        cx = "+".join(terms)
    else:
        cx = f"{float(seg['reframe']):.4f}"
    return (f"[{src}]{cover},crop={W}:{H}:x='min(max(({cx})*iw-{W}/2,0),iw-{W})':y='(ih-{H})/2',"
            f"setsar=1[{out}]")


EASE_OUT = "(1-pow(1-min(1,max(0,t/{d})),3))"            # 0 -> 1 over the first d seconds
EASE_EXIT = "pow(min(1,max(0,(t-{s})/{d})),3)"            # 0 -> 1 over the last d seconds


def transform_graph(tf: dict, dur: float, src: str, out: str) -> str:
    """Shrink the picture into a card on a background, with optional border,
    drop shadow, tilt and slide/pop/fade entrance and exit."""
    s = tf.get("scale", 0.8)
    cx, cy = tf.get("x", 0.5), tf.get("y", 0.5)
    fw, fh = even(W * s), even(H * s)
    bw = tf.get("border", {}).get("width", 0) if isinstance(tf.get("border"), dict) else (12 if tf.get("border") else 0)
    bcol = tf.get("border", {}).get("color", "white") if isinstance(tf.get("border"), dict) else "white"
    d = tf.get("anim", 0.4)
    enter, exit_ = tf.get("enter"), tf.get("exit")
    bg = tf.get("background", "blur")

    g = f"[{src}]split[tfb][tff];"
    if bg == "blur":
        g += f"[tfb]boxblur=30:2,eq=brightness=-0.1[tbg];"
    else:
        g += f"[tfb]drawbox=c={bg}:t=fill[tbg];"
    g += f"[tff]scale={fw}:{fh},setsar=1"
    if bw:
        g += f",pad=iw+{2 * bw}:ih+{2 * bw}:{bw}:{bw}:{bcol}"
    g += ",format=rgba"
    if tf.get("rotate"):
        import math
        a = math.radians(tf["rotate"])
        g += f",rotate={a:.5f}:ow=rotw({a:.5f}):oh=roth({a:.5f}):c=none"
    if enter == "fade":
        g += f",fade=t=in:d={d}:alpha=1"
    if exit_ == "fade":
        g += f",fade=t=out:st={dur - d:.3f}:d={d}:alpha=1"
    if enter == "pop":
        # Scale inside a fixed transparent canvas: frames whose size changes
        # every frame crash/stop the pad, blur and overlay filters after this.
        import math
        cw, ch = fw + 2 * bw, fh + 2 * bw
        if tf.get("rotate"):
            a = abs(math.radians(tf["rotate"]))
            cw, ch = cw * math.cos(a) + ch * math.sin(a), cw * math.sin(a) + ch * math.cos(a)
        cw, ch = even(cw + 2), even(ch + 2)
        g += (f",scale=w='max(4,trunc(iw*(0.2+0.8*{EASE_OUT.format(d=d)})/2)*2)':h=-2:eval=frame,"
              f"pad=w={cw}:h={ch}:x=(ow-iw)/2:y=(oh-ih)/2:color=black@0:eval=frame")
    g += "[tcard];"

    # Slide offsets, added to the resting position.
    # ffmpeg's expression parser rejects a unary minus before "(", hence (0-(...)).
    reach = {"slide_left": ("(0-(X+w))", "0"), "slide_right": ("(W-X)", "0"),
             "slide_down": ("0", "(0-(Y+h))"), "slide_up": ("0", "(H-Y)")}
    X, Y = f"({W * cx:.1f}-w/2)", f"({H * cy:.1f}-h/2)"

    def offset(axis):
        parts = []
        if enter in reach:
            parts.append(f"{reach[enter][axis]}*(1-{EASE_OUT.format(d=d)})")
        if exit_ in reach:
            # exits leave the way the same-named entrance arrives from
            parts.append(f"{reach[exit_][axis]}*{EASE_EXIT.format(s=f'{dur - d:.3f}', d=d)}")
        return "+".join(parts) or "0"
    # X/Y inside the slide offsets mean the card's resting position; W/H/w/h
    # are overlay's own main/overlay sizes.
    xexpr = f"{X}+{offset(0)}".replace("(X+", f"({X}+").replace("-X)", f"-{X})")
    yexpr = f"{Y}+{offset(1)}".replace("(Y+", f"({Y}+").replace("-Y)", f"-{Y})")

    shadow = tf.get("shadow")
    if shadow:
        sh = shadow if isinstance(shadow, dict) else {}
        blur, op, off = sh.get("blur", 18), sh.get("opacity", 0.55), sh.get("offset", 16)
        m = blur * 3
        g += (f"[tcard]split[tc1][tc2];"
              f"[tc2]pad=iw+{2 * m}:ih+{2 * m}:{m}:{m}:color=black@0,"
              f"colorchannelmixer=rr=0:gg=0:bb=0:aa={op},gblur=sigma={blur}[tsh];"
              # the shadow is padded evenly, so centring it like the card lines them up
              f"[tbg][tsh]overlay=x='{xexpr}+{off}':y='{yexpr}+{off}':eval=frame[tbg2];"
              f"[tbg2][tc1]overlay=x='{xexpr}':y='{yexpr}':eval=frame,setsar=1[{out}]")
    else:
        g += f"[tbg][tcard]overlay=x='{xexpr}':y='{yexpr}':eval=frame,setsar=1[{out}]"
    return g


LOOKS = {
    "bw": "hue=s=0",
    "sepia": "colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131",
    "vintage": "curves=preset=vintage,vignette=angle=PI/5",
    "vignette": "vignette=angle=PI/4.5",
    "blur": "gblur=sigma=12",
    "grain": "noise=alls=10:allf=t+u",
    "invert": "negate",
    "warm": "colortemperature=temperature=4800",
    "cool": "colortemperature=temperature=8000",
    "vivid": "eq=contrast=1.1:saturation=1.35",
    "cinematic": "colorbalance=rs=-0.05:bs=0.07:rh=0.07:gh=0.02:bh=-0.06,eq=contrast=1.08:saturation=1.1",
    "letterbox": "drawbox=x=0:y=0:w=iw:h=ih*0.11:c=black:t=fill,drawbox=x=0:y=ih*0.89:w=iw:h=ih*0.11:c=black:t=fill",
    "glow": None,  # needs a split, built in look_graph
}
# Auto light/colour fix: gentle contrast stretch and white balance from the
# picture itself (normalize, smoothed over ~1s so it doesn't pump), a touch
# of vibrance and a light sharpen.
ENHANCE = "normalize=blackpt=black:whitept=white:smoothing=30:independence=0.6:strength=0.7,vibrance=intensity=0.12,unsharp=5:5:0.4"


def look_graph(seg, src: str, out: str) -> str:
    """Colour/light, sharpness and named looks, in that order."""
    f = []
    if seg.get("enhance"):
        f.append(ENHANCE)
    col = seg.get("color", {})
    eq = {k: col[k] for k in ("brightness", "contrast", "saturation", "gamma") if k in col}
    if eq:
        f.append("eq=" + ":".join(f"{k}={v}" for k, v in eq.items()))
    if "vibrance" in col:
        f.append(f"vibrance=intensity={col['vibrance']}")
    if "temperature" in col:
        f.append(f"colortemperature=temperature={col['temperature']}")
    if "shadows" in col or "highlights" in col:
        sh, hl = col.get("shadows", 0), col.get("highlights", 0)
        f.append(f"curves=all='0/0 0.25/{0.25 + 0.12 * sh:.3f} 0.75/{0.75 + 0.12 * hl:.3f} 1/1'")
    if "lut" in col:
        f.append(f"lut3d=luts/{col['lut']}")  # .cube files in <work_dir>/luts (renders run there)
    if seg.get("sharpen"):
        f.append(f"unsharp=5:5:{seg['sharpen']}:5:5:0")
    names = seg.get("filters", [])
    unknown = [n for n in names if n not in LOOKS]
    if unknown:
        sys.exit(f"unknown filter(s) {unknown}; available: {sorted(LOOKS)}")
    chain = ",".join(f + [LOOKS[n] for n in names if LOOKS[n]]) or "null"
    g = f"[{src}]{chain}"
    if "glow" in names:
        g += (f"[lk0];[lk0]format=gbrp,split[lk1][lk2];[lk2]gblur=sigma=20[lk3];"  # blend in RGB: in YUV, screen on the chroma planes turns everything pink
              f"[lk1][lk3]blend=all_mode=screen:all_opacity=0.35,format=yuv420p[{out}]")
    else:
        g += f"[{out}]"
    return g


def has_look(seg) -> bool:
    return any(k in seg for k in ("enhance", "color", "sharpen", "filters"))


def segment_duration(seg) -> float:
    if "photo" in seg:
        return seg["duration"]
    if "block" in seg:
        return sum((p["end"] - p["start"]) / p.get("speed", 1.0) for p in seg["video"])
    return (seg["end"] - seg["start"]) / seg.get("speed", 1.0)


# --- per-segment graphs: each appends inputs to cmd and returns a filtergraph
# --- that ends in [vb] (picture) and [ab] (audio), both exactly dur long.

def silence(cmd, dur) -> str:
    i = n_inputs(cmd)
    cmd += ["-f", "lavfi", "-t", f"{dur:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
    return f"[{i}:a]anull[ab]"


def retime(span: float, speed: float) -> str:
    """Frame-exact video for an input opened with -ss <start> -to <start+span>.
    Input seeking alone isn't exact on her VFR screen recordings: ffmpeg keeps
    the frame that *covers* the seek point (negative pts) and lets a few
    frames past -to through (decode order), which leaked a "Please select a
    member" pop-up and an App Store sheet into video1/video2. Trimming on the
    real timestamps drops both; fps start_time=0 then fills from exactly 0."""
    return f"trim=start=0:end={span:.3f},setpts=PTS/{speed},fps={FPS}:start_time=0"


MAX_REVERSE = 30.0  # reverse holds every frame in memory


def clip_graph(seg, clips, root, wd, cmd, dur, cleanup):
    c = clips[seg["clip"]]
    path = root / c["file"]
    speed = seg.get("speed", 1.0)
    track = c.get("audio_track", 0)
    i = n_inputs(cmd)
    cmd += ["-ss", f"{seg['start']:.3f}", "-to", f"{seg['end']:.3f}", "-i", str(path)]
    pre = "," + RESTORE_PRE if c.get("restore") else ""
    if seg.get("stabilize"):
        pre += stab_filter(seg, stab_file(seg, clips, root, wd))
    reverse = seg.get("reverse")
    if reverse and dur > MAX_REVERSE:
        sys.exit(f"reverse on {seg_label(seg)}: {dur:.1f}s is too long (max {MAX_REVERSE}s, it buffers every frame)")
    if reverse:
        pre += ",reverse"
    pre += orient_filter(seg)
    fc = f"[{i}:v]{retime(seg['end'] - seg['start'], speed)}{pre}[v0];"
    if seg.get("reframe") is not None and c.get("layout", "fill") == "fill":
        fc += reframe_filter(seg, c, root, wd, "v0", "v1")
    else:
        fc += layout_filter(c.get("layout", "fill"), "v0", "v1", c.get("restore", False))
    if "zoom" in seg:
        fc += ";" + zoom_filter(seg["zoom"], dur, "v1", "vb")
    else:
        fc += ";[v1]null[vb]"
    if has_audio(path, track):
        fc += (f";[{i}:a:{track}]{voice_chain(c, cleanup, seg.get('_level_db'))}{atempo_chain(speed)},"
               f"apad,atrim=end={dur:.3f}{',areverse' if reverse else ''}[ab]")
    else:
        fc += ";" + silence(cmd, dur)
    return fc


def still_png(name: str, root: Path, wd: Path) -> Path:
    """HEIC photos are tiled grids that ffmpeg reassembles itself, so they
    can't take a -vf in the same command; decode to PNG once and reuse."""
    src = root / name
    if src.suffix.lower() not in (".heic", ".heif"):
        return src
    png = wd / "stills" / (src.stem + ".png")
    if not png.exists():
        png.parent.mkdir(exist_ok=True)
        run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-i", str(src), "-frames:v", "1", str(png)])
    return png


PHOTO_MOTION = {  # zoompan z / x / y per "motion"; N = total frames
    "push_in":  ("1+0.06*on/N", "iw/2-iw/zoom/2", "ih/2-ih/zoom/2"),
    "pull_out": ("1.06-0.06*on/N", "iw/2-iw/zoom/2", "ih/2-ih/zoom/2"),
    "pan_left":  ("1.12", "(iw-iw/zoom)*(1-on/N)", "ih/2-ih/zoom/2"),
    "pan_right": ("1.12", "(iw-iw/zoom)*on/N", "ih/2-ih/zoom/2"),
    "pan_up":    ("1.12", "iw/2-iw/zoom/2", "(ih-ih/zoom)*(1-on/N)"),
    "pan_down":  ("1.12", "iw/2-iw/zoom/2", "(ih-ih/zoom)*on/N"),
    "none":      ("1", "0", "0"),
}


def photo_graph(seg, root, wd, cmd, dur):
    frames = round(dur * FPS)
    i = n_inputs(cmd)
    cmd += ["-i", str(still_png(seg["photo"], root, wd))]
    motion = seg.get("motion", "push_in")
    if motion not in PHOTO_MOTION:
        sys.exit(f"unknown photo motion {motion!r}; available: {sorted(PHOTO_MOTION)}")
    z, x, y = (e.replace("N", str(frames)) for e in PHOTO_MOTION[motion])
    fc = (f"[{i}:v]{orient_filter(seg)[1:] + ',' if orient_filter(seg) else ''}"
          f"scale={W * 2}:{H * 2}:force_original_aspect_ratio=increase,crop={W * 2}:{H * 2},"
          f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={W}x{H}:fps={FPS},setsar=1[vb]")
    return fc + ";" + silence(cmd, dur)


def block_graph(seg, clips, root, wd, cmd, dur, cleanup):
    parts, labels, layout = [], [], None
    for k, piece in enumerate(seg["video"]):
        c = clips[piece["clip"]]
        layout = layout or c.get("layout", "fill")
        speed = piece.get("speed", 1.0)
        i = n_inputs(cmd)
        cmd += ["-ss", f"{piece['start']:.3f}", "-to", f"{piece['end']:.3f}", "-i", str(root / c["file"])]
        parts.append(f"[{i}:v]{retime(piece['end'] - piece['start'], speed)},setsar=1[p{k}]")
        labels.append(f"[p{k}]")
    fc = ";".join(parts) + ";" + "".join(labels) + f"concat=n={len(labels)}:v=1:a=0{orient_filter(seg)}[cat];"
    fc += layout_filter(layout, "cat", "vb")

    # Silent bed for the whole block, then every audio piece mixed in at its offset.
    bed = n_inputs(cmd)
    cmd += ["-f", "lavfi", "-t", f"{dur:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
    mix = [f"[{bed}:a]"]
    for k, a in enumerate(seg.get("audio", [])):
        i = n_inputs(cmd)
        if "file" in a:
            cmd += ["-i", str(audio_file(a["file"], wd))]
            track, fades, voice = 0, "", voice_chain(a, cleanup)
        else:
            c = clips[a["clip"]]
            cmd += ["-ss", f"{a['start']:.3f}", "-to", f"{a['end']:.3f}", "-i", str(root / c["file"])]
            adur = a["end"] - a["start"]
            track, voice = c.get("audio_track", 0), voice_chain(c, cleanup, a.get("_level_db"))
            fades = f"afade=t=in:d={FADE},afade=t=out:st={adur - FADE:.3f}:d={FADE},"
        delay = int(a.get("at", 0) * 1000)
        fc += (f";[{i}:a:{track}]aresample=48000,aformat=channel_layouts=stereo,{voice}{fades}"
               f"adelay={delay}:all=1[a{k}]")
        mix.append(f"[a{k}]")
    fc += f";{''.join(mix)}amix=inputs={len(mix)}:duration=first:normalize=0[ab]"
    return fc


PIP_POS = {
    "right": ("W-w-{m}", "(H-h)/2"), "left": ("{m}", "(H-h)/2"),
    "top-right": ("W-w-{m}", "{m}"), "top-left": ("{m}", "{m}"),
    "bottom-right": ("W-w-{m}", "H-h-{m}"), "bottom-left": ("{m}", "H-h-{m}"),
}


def pip_graph(pip, clips, root, cmd, dur, under="vb") -> str:
    """Inset another clip over [under], output [vp]."""
    c = clips[pip["clip"]]
    speed = pip.get("speed", 1.0)
    vertical = c.get("layout") == "vertical"
    height = int(H * pip.get("height", 0.75 if vertical else 0.32)) // 2 * 2
    end = pip["start"] + dur * speed
    i = n_inputs(cmd)
    cmd += ["-ss", f"{pip['start']:.3f}", "-to", f"{end:.3f}", "-i", str(root / c["file"])]
    x, y = (s.format(m=PIP_MARGIN) for s in PIP_POS[pip.get("position", "right")])
    border = 6
    return (f";[{i}:v]{retime(end - pip['start'], speed)},"
            f"tpad=stop_mode=clone:stop_duration={dur:.3f},trim=end={dur:.3f},"
            f"scale=-2:{height - 2 * border},pad=iw+{2 * border}:ih+{2 * border}:{border}:{border}:white,"
            f"format=yuva420p,fade=t=in:d=0.2:alpha=1,fade=t=out:st={dur - 0.2:.3f}:d=0.2:alpha=1[pip];"
            f"[{under}][pip]overlay={x}:{y}:shortest=0:eof_action=pass[vp]")


def seg_time(seg, at: float) -> float:
    """Where "at" lands inside this segment's output (see docstring)."""
    if "clip" in seg:
        return (at - seg["start"]) / seg.get("speed", 1.0)
    return at


def placed_items(seg, key, dur, label):
    for item in seg.get(key, []):
        t = seg_time(seg, item["at"])
        if 0 <= t < dur:
            yield item, t
        else:
            print(f"  warning: {key} {item.get(label) or item.get('clip')} at {item['at']} falls outside "
                  f"{seg_label(seg)}, skipped", file=sys.stderr)


def blur_graph(seg, dur, vlabel) -> tuple[str, str]:
    """Pixelate + blur rectangles for a while (hide a label, a screen, a
    plate). x/y/w/h are fractions of the frame; "at" follows the overlays
    rule (clip SOURCE time on clip segments). Size the box with margin:
    hand-held things drift, so check every frame afterwards."""
    fc = ""
    for k, (r, t) in enumerate(placed_items(seg, "blur", dur, "note")):
        x, y = even(W * r["x"]), even(H * r["y"])
        w, h = even(W * r["w"]), even(H * r["h"])
        end = min(t + r["duration"], dur)
        px = r.get("pixel", 24)
        fc += (f";[{vlabel}]split[bm{k}][bs{k}];"
               f"[bs{k}]crop={w}:{h}:{x}:{y},scale={max(2, w // px)}:{max(2, h // px)},"
               f"scale={w}:{h}:flags=neighbor,boxblur=6:2[bb{k}];"
               f"[bm{k}][bb{k}]overlay={x}:{y}:enable='between(t,{t:.3f},{end:.3f})'[vbl{k}]")
        vlabel = f"vbl{k}"
    return fc, vlabel


def broll_graph(seg, clips, root, wd, cmd, dur, vlabel) -> tuple[str, str]:
    """Full-frame cutaways over the picture; the segment's audio carries on."""
    fc = ""
    for k, (b, t) in enumerate(placed_items(seg, "broll", dur, "photo")):
        d = min(b["duration"], dur - t)
        i = n_inputs(cmd)
        if "photo" in b:
            frames = round(d * FPS)
            cmd += ["-i", str(still_png(b["photo"], root, wd))]
            fc += (f";[{i}:v]scale={W * 2}:{H * 2}:force_original_aspect_ratio=increase,crop={W * 2}:{H * 2},"
                   f"zoompan=z='1+0.05*on/{frames}':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':"
                   f"d={frames}:s={W}x{H}:fps={FPS},setsar=1[by{k}]")
        else:
            c = clips[b["clip"]]
            speed = b.get("speed", 1.0)
            cmd += ["-ss", f"{b['start']:.3f}", "-to", f"{b['start'] + d * speed:.3f}",
                    "-i", str(root / c["file"])]
            restore = c.get("restore", False)
            fc += (f";[{i}:v]{retime(d * speed, speed)}{',' + RESTORE_PRE if restore else ''}[bx{k}];"
                   + layout_filter(c.get("layout", "fill"), f"bx{k}", f"by{k}", restore))
            if "zoom" in b:  # same punch-in as clip segments, e.g. push in on a detail
                fc += ";" + zoom_filter(b["zoom"], d, f"by{k}", f"byz{k}")
                fc += f";[byz{k}]null[bw{k}]"
            else:
                fc += f";[by{k}]null[bw{k}]"
        if "photo" in b:
            fc += f";[by{k}]null[bw{k}]"
        fc += (f";[bw{k}]trim=end={d:.3f},setpts=PTS-STARTPTS+{t:.3f}/TB[bz{k}];"
               f"[{vlabel}][bz{k}]overlay=0:0:eof_action=pass[vB{k}]")
        vlabel = f"vB{k}"
    return fc, vlabel


def overlays_graph(seg, wd, cmd, dur, vlabel) -> tuple[str, str]:
    fc = ""
    for k, (o, t) in enumerate(placed_items(seg, "overlays", dur, "graphic")):
        src = wd / "graphics" / o["graphic"]
        i = n_inputs(cmd)
        if src.suffix.lower() == ".png":
            cmd += ["-loop", "1", "-t", f"{o['duration']:.3f}", "-i", str(src)]
        else:
            cmd += ["-i", str(src)]
        fc += (f";[{i}:v]scale={W}:{H},format=yuva420p,setpts=PTS-STARTPTS+{t:.3f}/TB[g{k}];"
               f"[{vlabel}][g{k}]overlay=0:0:eof_action=pass[vo{k}]")
        vlabel = f"vo{k}"
    return fc, vlabel


def sfx_graph(seg, cfg_sfx_dir: Path, wd, cmd, dur) -> tuple[str, list]:
    fc, labels = "", []
    for k, (s, t) in enumerate(placed_items(seg, "sfx", dur, "file")):
        src = cfg_sfx_dir / s["file"]
        if not src.exists():
            src = wd / s["file"]
        i = n_inputs(cmd)
        cmd += ["-i", str(src)]
        fc += (f";[{i}:a]aresample=48000,aformat=channel_layouts=stereo,"
               f"volume={s.get('volume_db', 0)}dB,adelay={int(t * 1000)}:all=1[s{k}]")
        labels.append(f"[s{k}]")
    return fc, labels


def render_segment(seg, clips, root, wd, out: Path, cleanup: bool, sfx_dir: Path):
    dur = segment_duration(seg)
    cmd = ["ffmpeg", "-nostdin", "-y", "-v", "error"]
    if "photo" in seg:
        fc = photo_graph(seg, root, wd, cmd, dur)
    elif "block" in seg:
        fc = block_graph(seg, clips, root, wd, cmd, dur, cleanup)
    else:
        fc = clip_graph(seg, clips, root, wd, cmd, dur, cleanup)

    # Layers, bottom to top: segment picture (tilted / shrunk into a card),
    # B-roll cutaways, PiP, then the colour look over all footage, then
    # graphics on top so the look never tints them.
    vlabel = "vb"
    angle = seg.get("rotate")
    if angle and angle not in (90, 180, 270, -90) and "transform" not in seg:
        fc += f";[{vlabel}]{tilt_filter(angle)}[vt]"
        vlabel = "vt"
    if "transform" in seg:
        tf = dict(seg["transform"])
        if angle and angle not in (90, 180, 270, -90):
            tf.setdefault("rotate", angle)
        fc += ";" + transform_graph(tf, dur, vlabel, "vtf")
        vlabel = "vtf"
    zfc, vlabel = blur_graph(seg, dur, vlabel)
    fc += zfc
    bfc, vlabel = broll_graph(seg, clips, root, wd, cmd, dur, vlabel)
    fc += bfc
    if "pip" in seg:
        fc += pip_graph(seg["pip"], clips, root, cmd, dur, vlabel)
        vlabel = "vp"
    if has_look(seg):
        fc += ";" + look_graph(seg, vlabel, "vlk")
        vlabel = "vlk"
    ofc, vlabel = overlays_graph(seg, wd, cmd, dur, vlabel)
    fc += ofc

    fin, fout = seg.get("fade_in", 0), seg.get("fade_out", 0)
    # Square pixels on every segment: a flip/look segment came out 2672:2673,
    # which the transition join's concat refuses.
    vf = ["format=yuv420p", "setsar=1"]
    if fin:
        vf.append(f"fade=t=in:d={fin}")
    if fout:
        vf.append(f"fade=t=out:st={dur - fout:.3f}:d={fout}")
    fc += f";[{vlabel}]{','.join(vf)}[v]"

    fc += f";[ab]volume={seg.get('volume_db', 0)}dB[abv]"
    sfc, sfx_labels = sfx_graph(seg, sfx_dir, wd, cmd, dur)
    fc += sfc
    alabel = "abv"
    if sfx_labels:
        fc += f";[abv]{''.join(sfx_labels)}amix=inputs={len(sfx_labels) + 1}:duration=first:normalize=0[abs]"
        alabel = "abs"
    fc += (f";[{alabel}]afade=t=in:d={max(fin, FADE)},"
           f"afade=t=out:st={dur - max(fout, FADE):.3f}:d={max(fout, FADE)}[a]")
    run(cmd + ["-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-t", f"{dur:.3f}",
               *VIDEO_OUT, *AUDIO_OUT, str(out)], cwd=wd)


def seg_label(seg) -> str:
    if "photo" in seg:
        s = f"photo {seg['photo']} {seg['duration']}s"
    elif "block" in seg:
        s = f"block {seg['block']} ({len(seg['video'])} pieces, {len(seg.get('audio', []))} audio)"
    else:
        s = f"{seg['clip']} {seg['start']:.2f}-{seg['end']:.2f}"
    return s + (f" + pip {seg['pip']['clip']}" if "pip" in seg else "")


# --- captions

def load_words(plan, wd: Path) -> dict:
    """All transcript words, grouped by clip id (= source file stem)."""
    by_clip = {}
    for t in plan.get("transcripts", ["transcript.json"]):
        data = json.loads((wd / t).read_text(encoding="utf-8"))
        for w in data["words"]:
            by_clip.setdefault(w["clip"], []).append(w)
    return by_clip


def caption_words(plan, wd, offsets):
    """Every spoken word that survives the edit, placed on the output timeline."""
    words = load_words(plan, wd)
    clips = plan["clips"]
    placed = []

    def place(stem, src_start, src_end, out_start, speed):
        for w in words.get(stem, []):
            mid = (w["start"] + w["end"]) / 2
            if src_start <= mid < src_end:
                placed.append((out_start + (w["start"] - src_start) / speed,
                               out_start + (w["end"] - src_start) / speed, w["word"]))

    for seg, off in zip(plan["segments"], offsets):
        if "clip" in seg:
            place(Path(clips[seg["clip"]]["file"]).stem, seg["start"], seg["end"], off, seg.get("speed", 1.0))
        elif "block" in seg:
            for a in seg.get("audio", []):
                if "file" in a:
                    place(Path(a["file"]).stem, 0, 1e9, off + a.get("at", 0), 1.0)
                else:
                    place(Path(clips[a["clip"]]["file"]).stem, a["start"], a["end"], off + a.get("at", 0), 1.0)
    return sorted(placed)


def chunk_captions(words, max_words=4, max_chars=24, max_gap=0.35):
    """Short punchy chunks: break on punctuation, pauses, or length."""
    chunks, cur = [], []
    for w in words:
        if cur and (len(cur) >= max_words or w[0] - cur[-1][1] > max_gap
                    or len(" ".join(x[2] for x in cur + [w])) > max_chars):
            chunks.append(cur)
            cur = []
        cur.append(w)
        if w[2][-1:] in ".,?!":
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    out = []
    for k, ch in enumerate(chunks):
        start, end = ch[0][0], ch[-1][1]
        if k + 1 < len(chunks) and chunks[k + 1][0][0] - end < 0.25:
            end = chunks[k + 1][0][0]
        out.append((start, end, " ".join(x[2] for x in ch)))
    return out


def write_ass(chunks, path: Path):
    def ts(t):
        cs = int(round(t * 100))
        return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"

    lines = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
        "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Cap,Arial Black,64,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,"
        "0,0,0,0,100,100,0,0,1,5,2,2,80,80,90,1", "",
        "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    for start, end, text in chunks:
        lines.append(f"Dialogue: 0,{ts(start)},{ts(end)},Cap,,0,0,0,,{text}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# --- final mix

MUSIC_RAMP = 1.0  # seconds the music takes to duck out/in around "music": false segments


def music_catalog() -> dict:
    p = assets_dir("music") / "catalog.json"
    if not p.exists():
        return {}
    return {t["file"]: t for t in json.loads(p.read_text(encoding="utf-8"))}


def audio_graph(plan, cfg, inputs, spans) -> str:
    """Joined voice audio, plus ducked music for YouTube videos. Ends in [mix].
    spans: (start, end, music_allowed) per segment on the output timeline."""
    music = plan.get("music")
    allowed = [s for s in spans if s[2]]
    if not music or not allowed:
        return "[0:a]anull[mix]"
    if not cfg.get("music_dir"):
        sys.exit("plan has music but music_dir isn't set in config.json")
    total = spans[-1][1]
    start = allowed[0][0]
    needed = total - start
    xf = music.get("crossfade", 2.0)
    catalog = music_catalog()
    files = music.get("files") or [music["file"]]

    # Repeat the playlist until it covers the video, then crossfade it together.
    playlist, length = [], -xf
    while length < needed:
        f = files[len(playlist) % len(files)]
        path = Path(cfg["music_dir"]) / f
        playlist.append((f, path))
        length += probe_duration(path) - xf
    fc = "[0:a]asplit[voice][key]"
    labels = []
    for k, (f, path) in enumerate(playlist):
        i = n_inputs(inputs)
        inputs += ["-i", str(path)]
        lufs = catalog.get(f, {}).get("lufs")
        gain = music.get("level_lufs", -30) - lufs if lufs is not None else music.get("volume_db", -20)
        fc += f";[{i}:a]aresample=48000,aformat=channel_layouts=stereo,volume={gain:.2f}dB[m{k}]"
        labels.append(f"m{k}")
    cur = labels[0]
    for k, nxt in enumerate(labels[1:], 1):
        fc += f";[{cur}][{nxt}]acrossfade=d={xf}:c1=tri:c2=tri[x{k}]"
        cur = f"x{k}"

    # Silence the music through "music": false segments, ramping around them.
    gates = [f"max(0,min(1,max(({a:.3f}-t)/{MUSIC_RAMP},(t-{b:.3f})/{MUSIC_RAMP})))"
             for a, b, ok in spans if not ok and a > start]
    gate = f",volume='{'*'.join(gates)}':eval=frame" if gates else ""
    # The lead-in is real silent samples concatenated in front, not adelay:
    # on video2, crossfaded mp3s -> adelay(92.7s) -> apad -> atrim dropped the
    # delay entirely (music started at 0 and ran out ~200s), though each
    # filter behaves alone. Concat with anullsrc is sample-exact.
    i = n_inputs(inputs)
    inputs += ["-f", "lavfi", "-t", f"{start:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
    fc += (f";[{cur}]atrim=end={needed:.3f},asetpts=PTS-STARTPTS,"
           f"afade=t=in:d=1.5,afade=t=out:st={needed - 3:.3f}:d=3[bed];"
           f"[{i}:a][bed]concat=n=2:v=0:a=1{gate},apad,atrim=end={total:.3f},asetpts=PTS-STARTPTS[music];"
           f"[music][key]sidechaincompress=threshold=0.02:ratio=8:attack=20:release=400[ducked];"
           f"[voice][ducked]amix=inputs=2:duration=first:normalize=0[mix]")
    print(f"music: {' -> '.join(f for f, _ in playlist)} from {start:.1f}s"
          + (f", silent through {len(gates)} segment(s)" if gates else ""), file=sys.stderr)
    return fc


def finalise(plan, cfg, joined: Path, wd: Path, final: Path, captions: Path | None, spans, normalise=True):
    inputs = ["-i", str(joined)]
    agraph = audio_graph(plan, cfg, inputs, spans)

    if normalise:
        # Two-pass loudnorm on the final mix. Single-pass only approaches the
        # target (measured -16.6 LUFS for a -14 target on video1); measuring
        # first and applying one linear gain hits it. Costs ~30s on a 5 min
        # video (loudnorm works at 192kHz internally), so previews skip it.
        proc = subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", *inputs, "-filter_complex",
                               f"{agraph};[mix]loudnorm={LOUDNORM}:print_format=json[out]",
                               "-map", "[out]", "-f", "null", "-"],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        err = proc.stderr.decode(errors="replace")
        m = json.loads(err[err.rindex("{"):err.rindex("}") + 1])
        level = (f"loudnorm={LOUDNORM}:linear=true:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
                 f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:"
                 f"offset={m['target_offset']},aresample=48000,{FINAL_CEILING}")
    else:
        level = "anull"

    fc = f"{agraph};[mix]{level}[a]"
    if captions:
        # Relative filename (ffmpeg runs in wd) avoids escaping the drive colon;
        # fontsdir points libass at Windows fonts since there's no fontconfig.
        fc += f";[0:v]subtitles={captions.name}:fontsdir='C\\:/Windows/Fonts'[v]"
        vmap, vcodec = "[v]", VIDEO_OUT
    else:
        vmap, vcodec = "0:v", ["-c:v", "copy"]
    run(["ffmpeg", "-nostdin", "-y", "-v", "error", *inputs, "-filter_complex", fc,
         "-map", vmap, "-map", "[a]", *vcodec, *AUDIO_OUT, "-movflags", "+faststart", str(final)],
        cwd=wd)


FORMATS = {"landscape": (1920, 1080), "vertical": (1080, 1920), "square": (1080, 1080)}
XFADES = {"fade", "dissolve", "fadeblack", "fadewhite", "wipeleft", "wiperight", "wipeup", "wipedown",
          "slideleft", "slideright", "slideup", "slidedown", "circleopen", "circleclose", "radial",
          "smoothleft", "smoothright", "zoomin", "pixelize", "hblur", "distance"}


def join_segments(seg_files, segs, rdir: Path):
    """Join the rendered segments. Hard cuts are a stream copy; when any
    segment has a "transition" the join is re-encoded with xfade (video) and
    acrossfade (audio), which overlaps the two segments by its duration.
    Returns (joined path, [(start, end) per segment on the output timeline])."""
    lens = [probe_duration(f) for f in seg_files]
    joined = rdir / "joined.mp4"
    if not any(s.get("transition") for s in segs[1:]):
        listing = rdir / "concat.txt"
        listing.write_text("".join(f"file '{p.as_posix()}'\n" for p in seg_files), encoding="utf-8")
        run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-f", "concat", "-safe", "0",
             "-i", str(listing), "-c", "copy", str(joined)])
        spans, t = [], 0.0
        for d in lens:
            spans.append((t, t + d))
            t += d
        return joined, spans

    cmd = ["ffmpeg", "-nostdin", "-y", "-v", "error"]
    for f in seg_files:
        cmd += ["-i", str(f)]
    fc = [f"[{k}:v]setsar=1,format=yuv420p,fps={FPS},settb=AVTB[sv{k}]" for k in range(len(seg_files))]
    v, a, total = "sv0", "0:a", lens[0]
    spans = [(0.0, lens[0])]
    for k in range(1, len(seg_files)):
        tr = segs[k].get("transition")
        if tr:
            kind = tr.get("type", "fade") if isinstance(tr, dict) else "fade"
            d = min(tr.get("duration", 0.5) if isinstance(tr, dict) else 0.5, lens[k - 1] / 2, lens[k] / 2)
            if kind not in XFADES:
                sys.exit(f"unknown transition {kind!r}; available: {sorted(XFADES)}")
            off = total - d
            fc.append(f"[{v}][sv{k}]xfade=transition={kind}:duration={d:.3f}:offset={off:.3f}[xv{k}]")
            fc.append(f"[{a}][{k}:a]acrossfade=d={d:.3f}:c1=tri:c2=tri[xa{k}]")
            spans.append((off, off + lens[k]))
            total += lens[k] - d
        else:
            fc.append(f"[{v}][{a}][sv{k}][{k}:a]concat=n=2:v=1:a=1[xv{k}][xa{k}]")
            spans.append((total, total + lens[k]))
            total += lens[k]
        v, a = f"xv{k}", f"xa{k}"
    run(cmd + ["-filter_complex", ";".join(fc), "-map", f"[{v}]", "-map", f"[{a}]",
               *VIDEO_OUT, *AUDIO_OUT, str(joined)])
    return joined, spans


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True, help="video name (work dir under footage_root/_editor/work)")
    ap.add_argument("--plan", default="plan.json")
    ap.add_argument("--only", type=int, action="append", help="re-render only these segment numbers")
    ap.add_argument("--out", help="output file (default <work_dir>/<name>.mp4)")
    ap.add_argument("--preview", action="store_true",
                    help="fast 960x540 review render into render_preview/, output <name>_preview.mp4")
    args = ap.parse_args()

    cfg = load()
    root = cfg["footage_root"]
    wd = work_dir(args.name)
    plan = json.loads((wd / args.plan).read_text(encoding="utf-8"))

    global W, H, VIDEO_OUT, PIP_MARGIN
    fmt = plan.get("format", "landscape")
    if fmt not in FORMATS:
        sys.exit(f"unknown format {fmt!r}; available: {sorted(FORMATS)}")
    W, H = FORMATS[fmt]
    if args.preview:
        W, H, PIP_MARGIN = W // 2, H // 2, 20
        VIDEO_OUT = ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
                     "-pix_fmt", "yuv420p", "-r", str(FPS)]
    # Plan-wide defaults (e.g. {"enhance": true}); a segment's own keys win.
    for seg in plan["segments"]:
        for k, v in plan.get("defaults", {}).items():
            seg.setdefault(k, v)
    check_amazon_disclosure(plan)
    if plan.get("music") and plan.get("destination") != "youtube":
        sys.exit(f"plan has music but destination is {plan.get('destination')!r}: background music "
                 f"is only for YouTube videos, never Amazon. Set \"destination\": \"youtube\" or drop \"music\".")
    clips = plan["clips"]
    cleanup = plan.get("voice_cleanup", False)
    if plan.get("voice_level_lufs") is not None:
        set_voice_levels(plan, clips, root, wd, plan["voice_level_lufs"])
    sfx_dir = assets_dir("sfx")
    rdir = wd / ("render_preview" if args.preview else "render")
    rdir.mkdir(exist_ok=True)

    seg_files = []
    for i, seg in enumerate(plan["segments"]):
        out = rdir / f"{i:03d}.mp4"
        seg_files.append(out)
        if args.only and i not in args.only and out.exists():
            continue
        print(f"[{i + 1}/{len(plan['segments'])}] {seg_label(seg)}", file=sys.stderr)
        render_segment(seg, clips, root, wd, out, cleanup, sfx_dir)

    # Segment positions come from the rendered files, not the plan (frame
    # rounding adds up), minus any transition overlaps.
    joined, positions = join_segments(seg_files, plan["segments"], rdir)
    offsets = [a for a, _ in positions]
    spans = [(a, b, seg.get("music", True)) for (a, b), seg in zip(positions, plan["segments"])]

    captions = None
    if plan.get("captions"):
        chunks = chunk_captions(caption_words(plan, wd, offsets))
        captions = wd / "captions.ass"
        write_ass(chunks, captions)
        print(f"{len(chunks)} caption chunks", file=sys.stderr)

    final = Path(args.out) if args.out else wd / f"{args.name}{'_preview' if args.preview else ''}.mp4"
    steps = [x for x in ["music" if plan.get("music") else "", "captions" if captions else "",
                         "" if args.preview else "loudness -14 LUFS"] if x]
    print("final mix: " + (", ".join(steps) or "join only"), file=sys.stderr)
    finalise(plan, cfg, joined, wd, final.resolve(), captions, spans, normalise=not args.preview)
    print(f"wrote {final}")


if __name__ == "__main__":
    main()
