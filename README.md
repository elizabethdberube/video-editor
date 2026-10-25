# Video-Editor

A local, free YouTube editing pipeline for the eggheadfixers channel (DIY
repair tutorials and reviews). Everything runs on your own PC — no paid
software, no cloud editing services.

## How it works

1. **Transcribe** your raw footage (Parakeet, a free speech-to-text model) to
   get word-level timestamps.
2. **Claude makes the editorial decisions** — what to cut, which B-roll to
   use, where to punch in, what graphics to add — and writes them into a
   `plan.json` file for that video.
3. **Scripts carry out the plan**: `render.py` turns `plan.json` into an
   actual video using ffmpeg. You never hand-edit video directly; you review
   a fast low-res preview and give notes, and the plan gets updated.

Every plan is anchored to *source time* — seconds into the original clip —
so re-ordering or re-cutting never breaks graphics, B-roll, or sound effects
tied to a moment.

## Layout

- `tools/` — the pipeline scripts (this repo, version-controlled).
- `config.json` (not committed — copy `config.example.json`) — points the
  tools at your footage location, which differs per machine.
- Your footage root gets a `_editor/` folder added next to it:
  - `_editor/work/<video>/` — transcripts, plans, rendered output for one video.
  - `_editor/assets/` — shared, reusable stuff: free fonts, emoji/icons, sound
    effects, pulled in by `fetch_assets.py` with license info recorded.
- `.claude/skills/youtube-edit/` — everything Claude has learned so far:
  tool quirks, real measurements, and your editing taste. Read automatically
  whenever Claude works in this repo.

## Setup notes

- Needs **Node >=22** on PATH for `graphics.py` (it shells out to
  `npx hyperframes`). If your default `node` is older, install a current one
  (e.g. `winget install OpenJS.NodeJS.LTS` on Windows, or `nvm install 22`).
  HyperFrames has an optional paid cloud tier — this pipeline only ever uses
  its local rendering, never `hyperframes cloud`/`lambda`/`auth`.

## What's built so far

- `transcribe.py` — speech-to-text with word timestamps
- `render.py` — turns a plan into a finished video
- `fetch_assets.py` — free emoji, fonts, and sound effects (all license-checked)
- `thumbnail.py` — generates thumbnail candidates from your footage
- `graphics.py` — renders a motion-graphic callout (icon + text) to a
  transparent overlay, for `render.py` to composite over footage
- `speakers.py` — identifies who's speaking per segment via voiceprints
  (two-speaker footage only; not yet verified on real hardware)
- `fillers.py` — finds "um", "ah" and throat-clears between words (the
  speech-to-text usually leaves them out) so they can be cut
- `catalog_music.py` — measures BPM/LUFS/energy/brightness/vocals for a
  folder of background music (point `music_dir` in `config.json` at it
  once you have one)

`render.py` also supports, all set in `plan.json` (see its docstring):

- slow-motion/fast-forward (`"speed"`) and punch-in zooms (`"zoom"`)
- **picture-in-picture** (`"pip"`): inset a second clip, e.g. the phone
  screen recording beside you demoing the device
- **fades** to/from black (`"fade_in"`, `"fade_out"`) and per-segment volume
  (`"volume_db"`)
- **background music** (`"music"`) that dips automatically while you talk.
  YouTube videos only: the plan must say `"destination": "youtube"`, and
  Amazon videos never get music.
- **B-roll cutaways** (`"broll"`): cut to a photo or another clip while
  you keep talking
- **voice levelling** (`"voice_level_lufs"`): evens out clips recorded at
  different distances so every section plays at the same volume
- **music playlists** (`"music": {"files": [...]}`), crossfaded and
  volume-matched using `catalog_music.py`'s measurements, and
  `"music": false` on any segment that already has its own music
- **graphics overlays** (`"overlays"`): put the transparent callouts that
  `graphics.py` makes on top of a segment, at a moment in the source clip
- **sound effects** (`"sfx"`): whooshes, pops, etc. from `_editor/assets/sfx/`
  (download them with `fetch_assets.py sfx`), placed at a moment in the clip
- **voice cleanup** (`"voice_cleanup": true`): cuts rumble and background
  noise, adds a little clarity, and dips the pauses between sentences
- burned-in captions (`"captions": true`) built from the transcript. Off
  by default, and not used on this channel's videos.

It can also change the picture, look and joins (full option list in
`render.py`'s docstring):

- **size and position** of the picture as a card, with **border**, **drop
  shadow**, **tilt** and **slide/pop/fade animations** in and out
- **flip**, **rotate** (sideways footage or any tilt angle), **reverse**
- **video stabilization** for shaky handheld shots
- **auto reframe**: crop follows your face, mainly for vertical Shorts
  (`"format": "vertical"`; square works too)
- **colour and light enhancement** (one-switch auto fix, or brightness,
  contrast, saturation, warmth, shadows/highlights, LUTs) and **sharpness**
- **filters**: black & white, sepia, vintage, vignette, blur, grain,
  invert, warm, cool, vivid, cinematic, letterbox, glow
- **transitions** between clips: fade, dissolve, wipes, slides, zoom and more
- **photo motion**: push in, pull out, pan left/right/up/down

Every tool used is free and fine for monetized YouTube videos (ffmpeg,
OpenCV, and OpenCV's MIT-licensed YuNet face model, which auto reframe needs
in `_editor/assets/models/face_detection_yunet_2023mar.onnx`).

**Quick preview:** `python tools/render.py --name video1 --preview` renders
a small 960×540 copy (`video1_preview.mp4`) about 3× faster than a full
render (about 1 minute vs about 3½ for a 5-minute video on the Windows
laptop), so you can review a cut before the full render. Its loudness isn't
normalised, so it may play a bit quieter or louder than the final.

## Where things go

- **Background music:** put tracks in the folder set as `music_dir` in
  `config.json` (on the Windows laptop:
  `C:\Users\eliza\Videos\YouTube\_music`). Use only music you're
  allowed to use on YouTube, such as the YouTube Audio Library.
- **Finished videos:** `<footage root>\_editor\work\<video>\<video>.mp4`.

## Windows setup (no NVIDIA GPU)

1. `winget install Python.Python.3.12` and `winget install Gyan.FFmpeg`
2. `python -m venv .venv`
3. `.venv\Scripts\python -m pip install torch --index-url https://download.pytorch.org/whl/cpu`
   (don't add torchaudio)
4. `.venv\Scripts\python -m pip install -r requirements-windows.txt`
5. Copy `config.example.json` to `config.json` and set `footage_root_windows`
   (and `music_dir`).

If Windows says "An Application Control policy has blocked this file", that's
Smart App Control rejecting a brand-new package build. Pin an older version in
`requirements-windows.txt` rather than turning Smart App Control off.

Still to come: automatic pause-trimming, punch-ins, pacing checks, and a few
other tools — see the skill file for the full list and current status.
