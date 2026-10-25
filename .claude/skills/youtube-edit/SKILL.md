---
name: youtube-edit
description: Personal knowledge for Liz's automated YouTube editing pipeline (eggheadfixers channel) - tool gotchas, real measurements, and her editing taste. Use whenever working in the Video-Editor repo or editing her footage.
---

# youtube-edit

Personal skill for building and operating Liz's local YouTube editing pipeline.
Update this file in the same turn whenever she gives feedback — don't let it go stale.
Keep it general: one-off details of a single video don't belong here (she asked
for the notes from a one-time sponsored video to be removed, 2026-10-24).

## Project facts

- Repo: `/home/taytay/Video-Editor` (GitHub: `elizabethdberube/Video-Editor`, renamed
  from `AI-Video-Editor` 2026-10-23). Codebase lives here, version-controlled.
  This deviates from her original spec of putting tools inside
  `[footage_root]\_editor\tools` — we keep the *code* in this git repo instead, and
  only per-video *work files* (transcripts, plans, proxies) go under
  `<footage_root>/_editor/work/<video>`, so raw footage folders stay untouched and
  the tools stay version-controlled. Confirm this split still works for her once
  she's seen it in practice.
- Channel: eggheadfixers (youtube.com/c/eggheadfixers) — DIY tutorials and reviews
  (fix-it / repair content), not interview-style. Spec's "follow the speaker"
  punch-in rules are secondary here; B-roll of the actual repair/device and
  screen-recording inserts likely matter more than speaker tracking.
- Style goal (her words): "quirky, fast moving and very informative" — inspired by
  other creators generally, not her own back-catalog (she has no past raw+final
  footage to learn from; default editing rules + ongoing review notes are the only
  taste signal for now).
- Third machine (set up 2026-10-23): Windows 11 laptop, user `eliza`, i7-1365U,
  Intel Iris Xe, **no NVIDIA GPU**, 31GB RAM, **Smart App Control on**. Repo at
  `C:\Users\eliza\Video-Editor`, venv `.venv` (Python 3.12.10, CPU torch, NeMo
  3.0.0), ffmpeg 9.0.2 via winget. Footage at
  `C:\Users\eliza\OneDrive\Desktop\YouTube` (OneDrive Desktop). Liz chose to run
  the full pipeline CPU-only here. Measured: Parakeet on CPU transcribed a
  32s clip in 3.6s, so CPU transcription is fine for her short clips.
  Smart App Control blocks DLLs from brand-new wheels (onnx 1.23.2, pyarrow
  26, torchaudio CPU) with "An Application Control policy has blocked this
  file". Fix by pinning an older release (see requirements-windows.txt), never
  by turning SAC off (it can't be turned back on without reinstalling Windows).
  A newly opened shell may still need ffmpeg on PATH
  (`%LOCALAPPDATA%\Microsoft\WinGet\Links`).
- Dev split: this Linux box has **no NVIDIA GPU, no CUDA** — used for writing code,
  non-GPU testing (ffmpeg logic, OpenCV, librosa) and real ffprobe measurements only.
  GPU/CPU-heavy work (NeMo/Parakeet transcription, TitaNet, renders) is written here
  but actually *run and measured* by Liz elsewhere. **Correction:** the original
  brief's "RTX GPU, 12GB VRAM, OOM above 17min" detail was unfilled template
  boilerplate, not a verified fact about her hardware — don't restate it as
  confirmed. The actual machine in use (see "Third machine" above) has no NVIDIA
  GPU at all and runs everything CPU-only, which has been fine for her short
  clips so far. Loop: I write + reason about a tool here, she runs it elsewhere,
  pastes back real console output/errors, I fix based on that — never assume
  NeMo/CPU/CUDA behavior without real pasted output.
- `config.json` (gitignored) holds `footage_root` (Linux path) and
  `footage_root_windows` (Windows path); `tools/config.py` picks the right one by
  `platform.system()`. `config.example.json` is the committed template.
  `music_dir` on the Windows laptop is `<footage_root>/_music`.

## Her footage: what to expect

- **iPhone clips (.MOV)**: 1920x1080 h264, **variable frame rate** (~30fps
  nominal, fractional avg_frame_rate). render.py's CFR conversion is not
  optional. Some are tagged rotation=-180 (shot upside down); ffmpeg
  autorotates them correctly.
- **iPhone audio has two tracks**: `0:a:0` is normal AAC stereo 48kHz — use
  this one. `0:a:1` is a 4-channel `apac` spatial-audio track ffprobe can't
  even name; never feed it to NeMo. Always `-map 0:a:0` explicitly.
- **Photos are HEIC** (iPhone). See the ffmpeg-on-Windows gotcha below.
- **Phone screen recordings** (RecordIt, ~884x1920 HEVC, VFR, often a silent
  audio track): very sparse frames while the screen is static, which breaks
  naive cuts (see the exact-cuts rule below). They are where personal info
  and error pop-ups hide.
- **OneDrive duplicates**: files like `IMG_xxxx(1).MOV` can be byte-different
  but stream-identical copies — compare with `ffmpeg -f streamhash` before
  treating one as new footage.
- **Speech levels vary a lot between setups** (camera distance): measured
  sources 7-11 dB apart, so use `"voice_level_lufs"` in plans.
- Older published videos of hers may have music baked in: ask, and give those
  segments `"music": false` so two songs never play at once (keep any
  voiceover lifted from them in one continuous piece so the baked music
  doesn't jump at cuts).

## Architecture correction: no project timeline, per-clip source time only

Liz confirmed (2026-10-23): a typical video is cut from **many independent
clips and photos**, not one continuous take. So `transcript.json` (and every
downstream file — shots, drops, sections, broll) must never flatten onto one
offset/global timeline. Each clip keeps its own source time, 0 at that file's
start, and every reference to a time must carry the clip id alongside it —
`(clip_id, start, end)`, never a bare float. `transcribe.py` was rewritten
accordingly: `transcript.json` has a `clips` list (`id`, `file`, `duration`)
and `words` tagged with `clip`; `--offset` was removed, replaced by `--clip-id`
(defaults to the filename stem). The `.srt` preview is the one place that
still concatenates clips onto a display timeline, purely for human review —
editing tools must use the per-clip source time in the JSON, never the SRT's
times.

## Rule: free tools only, usable in monetized YouTube videos (Liz, 2026-10-24)

"all tools should be free and I should be able to use them for youtube
videos". Before adding any tool, library, model, font, music, sfx or
preset: it must be free, and its license must allow use in monetized
YouTube videos. ffmpeg (LGPL/GPL), OpenCV (Apache 2.0), YuNet face model
(MIT), Google Fonts (OFL), Freesound CC0 qualify. No paid tiers, trials,
watermarking tools, "personal use only" assets, or cloud services. If a
license needs a credit (OpenMoji CC BY-SA), tell her the credit line.

## Rule: every Amazon review includes the gifted-product disclosure (Liz, 2026-10-25)

Her words: "use it in every amazon review. You need to disclose that the
item was gifted to you and the clip does that." The clip is her voice
saying: "This company was kind enough to gift this item to me, so let's go
ahead and try it out." (5.1s WAV.)

- **Where it lives:** `<footage_root>/_editor/assets/disclosure/amazon_gifted_disclosure.wav`
  (on the Windows laptop: `C:\Users\eliza\Videos\YouTube\_editor\assets\disclosure\`).
  It is NOT in the git repo, so each computer needs its own copy.
- **First step of every Amazon review, before planning anything:** check
  that file exists. If it doesn't, stop and ask her to add it, and tell her
  the exact path for that computer. Don't build the edit without it.
  (render.py enforces the same thing: `check_amazon_disclosure` refuses an
  Amazon plan if the clip is missing or no segment uses it.)
- **How to use it:** a block segment whose audio is
  `{"file": "@amazon_disclosure", "at": 0}`, over a clean product shot
  from that review (no personal info, no prices/offers on screen). Default
  placement: right after her intro names the product, before the demo --
  the line ends "so let's go ahead and try it out", and disclosures belong
  early. Only once per video.
- The source was a webcam recording (WIN_20261025_10_19_14_Pro.mp4). If the
  clip ever needs re-making, trim to the sentence (0.10-5.35s there).
- **YouTube reviews: don't add this clip** (Liz, 2026-10-25: "I can say it
  myself in youtube"). She discloses gifts/sponsorships in her own words
  while filming and uses YouTube's paid-promotion box. When editing a
  YouTube review: never cut her disclosure line (gifted, sent to me,
  sponsored, partnered, etc.) -- keep it early in the cut. If the
  transcript has no disclosure at all, say so when handing the video over
  (don't block the edit). Background: the FTC says the platform box alone
  isn't enough; an in-video statement is what counts.

## Naming: name each video after the product (Liz, 2026-10-25)

"for future videos can you try to name them after the product". Use the
product name, lowercase, words joined by hyphens, then `_amazon` or
`_youtube`: e.g. `vosker-v150-security-camera_amazon`,
`saian-pumpkin-spice-mask_amazon`. Use it as the render `--name` so the
work folder and the finished file (`<name>.mp4`) match. Take the product
name from the packaging/label in the footage (speech-to-text mishears brand
names -- "cyan" was Saian, "F150" was V150). No spaces or special characters.

## Amazon review content rules (applied 2026-10-24/25, she approved each)

- At least 2 minutes; otherwise as long as looks best. No background music.
- Cut price / subscription-cost talk and on-screen prices or offers ("$9.99",
  "1 month free", "5 free songs" -> cover with B-roll), and purchase-option
  talk ("two-pack, or buy them individually"). Amazon's review guidelines
  (as quoted on seller forums -- the official page kept erroring) exclude
  pricing, availability and ordering options.
- No copyrighted music: cut song demos (and lyrics/song titles on screens)
  and devices' own promo videos (their voiceover + music).
- Cut sponsor-sounding phrases ("brought to you by"); keep one call to
  action, at the end. Free samples are fine for her to accept.
- Plus the gifted disclosure rule above.
- A YouTube review can be turned into an Amazon version from the same
  source + plan: drop music, add the disclosure, apply the cuts above. A
  finished YouTube render can't -- its music is baked in; ask for the
  original clip.

## Rule: edit out personal information, always (Liz, 2026-10-23)

Her words: "edit out any passwords or emails or address any personal
information like that". This applies to every video, without being asked,
and to every edit before it's handed over.

- **What counts:** passwords (typed or visible), email addresses (including
  the Apple ID on App Store install sheets and account/login screens), home
  or mailing addresses, phone numbers, verification/2FA codes, device
  pairing/share codes and anything else that grants access, payment or
  card details, full names of family members, house numbers, street signs
  or mail visible in shots, license plates, and notifications popping up
  on a screen recording. Her first name "Liz" is fine: she says it on camera.
- **Where it hides:** screen recordings above all (sign-up/login, App Store
  install sheets, pairing screens, settings, notification banners), device
  screens filmed in footage, paperwork/mail/packages in B-roll, and photos.
- **Before rendering:** scan every screen-recording range and on-screen
  device the plan uses with dense frame sheets (1 fps minimum, 10 fps
  around anything suspicious) and read them. Don't assume a range is clean
  because the obvious part (e.g. login) was skipped -- an App Store install
  sheet showing her email once shipped in a cut until she spotted it.
- **Prefer cutting over blurring.** A cut can't fail; a blur on something
  that moves or animates (sheets sliding in, scrolling) easily misses frames.
  If it must stay visible, blur or box it and check every frame.
- **Find exact frame ranges, then check every frame at each join.** Get
  the first/last affected frame from real frame timestamps (showinfo on a
  -copyts -fps_mode passthrough decode), including faint fade-in/out
  frames, and cut a little outside them. Input -ss/-to alone was NOT frame
  exact on her VFR screen recordings: ffmpeg kept the frame covering the
  start point and let frames past -to through, leaking a sheet frame and
  whole pop-ups. render.py's `retime()` now trims on real timestamps for
  every clip/piece/PiP/B-roll (verified: a leaking piece ended on 5 pop-up
  frames before, clean after). Still inspect the finished video frame by
  frame across each join.
- Tell her what was found and removed. The raw files still contain it, so
  mention that if she shares raw footage.

**Also cut app error/warning pop-ups** (Liz, 2026-10-23: "it flashes please
select a member twice. I would like to edit those pops out"). Treat error
toasts like "Please select a member" as mistakes to hide, not content. Ask
before assuming neutral ones ("Loading...", "Successfully connected") also
go -- she didn't mention those and they were left in. Check PiP and B-roll
sources too (a PiP once ran into a pop-up). Detect toasts by the mean
brightness of the toast spot on a light UI (white form ~255, a toast pulls
it under 200) and look at every flagged frame -- menus, calendars and
spinners also trip it.

## Editorial principle: pick and choose, don't dump everything in

Liz confirmed (2026-10-23): a video's raw folder does not have to end up fully
used. Gathering/transcribing a clip or photo is not a commitment to include
it — I (Claude) am expected to pick and choose what actually serves the edit,
same as any editor would, not force every file in the folder into the final
cut. Treat "many clips and photos available" as a pool to select from, not a
checklist to exhaust.

## Editorial principle: prefer graphics for YouTube, but ask first

Liz confirmed (2026-10-23, her call: "update it so it uses graphics where
possible if its a youtube video. have it prompt to ask"):

- Since every video here is for YouTube, **default toward a motion graphic**
  when a moment explains a physical/technical idea (how something works,
  what a part does, a before/after, a number/spec) — graphics are the
  default tool for that job here, not just one option among several. The
  existing guardrail still applies: if an idea genuinely won't draw cleanly,
  cut back to the speaker instead of forcing a bad graphic.
- **Before adding a graphic to a plan, ask her in chat first** — don't
  silently decide a moment gets a graphic and render it. This is specific to
  graphics; it does not change the general workflow (she reviews low-res
  previews and gives notes on the rest of the edit). Surface the candidate
  moment, what the graphic would show, and let her confirm/adjust before
  `graphics.py` gets run for real.

## render.py: speed changes and punch-in zoom (added 2026-10-23, her call: "does it have the ability to zoom in and out on a frame? do slow motion or speed it up?")

- **Speed was already supported but had a real bug**, caught by testing
  before shipping: `atempo={speed}` directly on a single filter -- ffmpeg's
  `atempo` hard-rejects anything outside 0.5-2.0 (confirmed: a real
  slow-mo render at 0.3x failed with "Value 0.300000 ... out of range").
  Fixed with `atempo_chain()`, which decomposes any speed into a chain of
  per-filter factors each within range (e.g. 0.3x -> atempo=0.5,atempo=0.6).
  Verified for real: 0.3x and 3.0x renders of real footage both now succeed.
- **Punch-in zoom is new** (`"zoom": {"factor", "cx", "cy", "ease_in",
  "ease_out"}` on a clip segment). First attempt used `crop` with
  time-varying `w`/`h` expressions referencing `t` and an `eval=frame`
  option copied from memory of other filters (`scale` has that option,
  `crop` does not) -- **wrong on two counts**, caught by testing: `crop`
  has no `eval` option at all, and more importantly **`crop`'s `w`/`h` are
  only evaluated once at filter init in this ffmpeg build, not per-frame**
  (only `x`/`y` re-evaluate per frame) -- a `t`-dependent `h` alone fails
  with "Error when evaluating the expression", isolated with a minimal
  standalone ffmpeg command before touching the real code. Correct
  approach, and what the original brief actually specified: `zoompan`
  (already used for photo push-ins elsewhere in this file), with `d=1` so
  every output frame consumes the next real input frame -- motion keeps
  playing through the zoom instead of freezing like a photo push-in does.
  **Verified visually, not just by exit code**: rendered a zoom on real
  footage, pulled frames at the start/mid/end, confirmed wide -> genuinely
  zoomed-in -> wide, with real hand/body motion visibly continuing at each
  point (proves it isn't frozen on one frame). Quick 0.01s punch-ins work
  well to hide jump cuts on a static talking head.

## render.py: PiP, fades, music, captions, B-roll, levelling (added 2026-10-23)

- `"pip"` on any segment insets another clip (own source start, silent,
  white border, 0.2s alpha fade in/out, holds last frame if the source runs
  out). Put it where the frame is empty (check a frame first).
- `"fade_in"`/`"fade_out"` (picture to/from black + audio) and `"volume_db"`
  per segment. Every cut still gets the 20ms anti-click audio fade.
- Plan-level `"music"`: a playlist (`"files"`) from `music_dir`, crossfaded,
  gain-matched to `level_lufs` from catalog_music's catalog, ducked by
  `sidechaincompress` keyed on the voice, 1.5s fade in / 3s fade out, starts
  at the first segment allowing music; per-segment `"music": false` ramps it
  out for 1s. Refused unless `"destination": "youtube"` (see taste log).
  Measured: -33 LUFS music sits ~18 dB under her levelled voice; ducking
  takes it down a further 5-8.5 dB while she talks.
- `"voice_level_lufs"` levels each segment of 3s+ on its own (cached in
  `<work>/loudness.json`): speech spread across sections 10 dB -> 1.9 dB.
  Skips silent tracks (screen recordings) so they aren't boosted ~70 dB.
- `"broll"` full-frame cutaways (photo push-in or clip; segment audio
  continues).
- `"captions": true` burns in short (<=4 word) chunks in Arial Black via an
  .ass file + `subtitles` filter (she doesn't want captions -- see taste log).
  libass on Windows needs `fontsdir='C\:/Windows/Fonts'`, and ffmpeg runs
  with cwd = work dir so the .ass path has no drive colon to escape.
  Segment offsets come from the rendered files' real durations, not plan
  maths, because frame rounding drifts.
- `"overlays"` (graphics.py ProRes 4444 or PNG+duration) and `"sfx"` per
  segment; `"at"` is clip SOURCE time on clip segments, seconds-in on
  photo/block segments; out-of-range items warn and skip. Verified timing
  frame by frame and by subtracting audio tracks. Test-asset gotcha: ffmpeg
  `drawbox` doesn't write alpha, so a drawbox in a yuva test graphic comes
  out invisible -- not a render.py bug.
- **graphics.py can't run on the Windows laptop yet**: Node there is v20
  (nvm4w), HyperFrames needs >=22, and no fonts/emoji are fetched. Freesound
  sfx also needs `freesound_api_key` in config.json, not set up.
- `"voice_cleanup": true` (plan-level; clip opt-out). Her iPhone audio is
  already clean (noise floor ~-54 dB), so gains are modest: voice-to-pause
  gap 29.3 -> 37.8 dB, mostly from the gentle gate. A first version with a
  compressor did nothing (29.2 dB) because makeup gain lifted pauses as much
  as NR lowered them -- always measure the gap (speech RMS minus pause RMS),
  not absolute levels, since loudnorm rescales. She hasn't given feedback on
  how it sounds yet.
- `--preview`: half resolution, ultrafast, separate render_preview/ dir, and
  skips loudnorm (which was ~30s of every render; it works at 192kHz
  internally). A 5-min video: full ~3.3 min, preview ~1 min on the laptop.
- **ffmpeg gotcha (real)**: crossfaded mp3s -> `adelay` (92.7s) -> `apad`
  -> `atrim` silently lost the delay (music started at 0 and ran out early),
  though each filter behaves alone and short synthetic tests pass. Fixed by
  concatenating real anullsrc silence in front. Also: atrim/trim positional
  args map to start, then `starti` (an alias of start) per
  `ffmpeg -h filter=atrim`, not start/end -- always write `end=` explicitly.
  Verify music by subtracting the voice-only joined.mp4 from the preview mix
  (preview skips loudnorm, so it's exact).
- Lost once: a `git pull` that reset to a rewritten origin/main wiped this
  work while it was uncommitted, and it was re-merged on top of the
  atempo_chain/zoom version. Commit render.py changes promptly.

## render.py picture/look/transition toolkit (added 2026-10-24)

Her request: size, flip, rotate, border, shadow, auto reframe, reverse,
animation, effects/filters, sharpness, stabilization, colour and light
enhancement (speed, ducking, audio fades already existed). All in
render.py's docstring, plus xfade transitions and vertical/square formats.
Verified on her footage in a scratch plan:
- reverse: first frame matched source's last (diff 1.2 vs 20.4).
- stabilize (vid.stab two-pass, .trf cached in <work>/stab): on a mildly
  shaky handheld clip, jitter 0.40 -> 0.27 px, drift -22%. Modest; expect
  more on genuinely shaky footage.
- auto reframe to vertical: face off-centre 0.01-0.04 of frame width vs
  0.47-0.53 for a centre crop (which cut her off in 32/32 and 15/28
  frames). Her talking-head framing puts her at x~0.33, so a centre crop is
  never safe for her Shorts.
- transitions: output length exactly sum(segments) - overlaps.
- all 13 filters + enhance checked on one frame side by side.
Gotchas found building it (all fixed in code):
- OpenCV 5 dropped Haar cascades (no cv2.CascadeClassifier); face finding
  uses cv2.FaceDetectorYN + the YuNet onnx in _editor/assets/models.
- ffmpeg expressions reject a unary minus before "(": write (0-(...)).
- A frame size that changes per frame (scale eval=frame for "pop")
  crashes ffmpeg (0xC0000374) or errors downstream: pad back to a fixed
  canvas right after.
- "screen" blend in YUV shifts chroma -> everything turns pink. Blend in
  RGB (format=gbrp).
- Segments need setsar=1 (one came out 2672:2673) and the xfade join needs
  every input on the same timebase (settb=AVTB) or concat/xfade refuse.
- Segment renders run with cwd=<work_dir> so stab/ and luts/ paths are
  relative (no drive-colon escaping in filter args).

## catalog_music.py (new, 2026-10-23, her call: she wants to be able to
provide a music folder eventually and have the pipeline catalog it)

- Reads `config.json`'s `music_dir`, measures BPM (`librosa.beat.beat_track`),
  integrated LUFS (`pyloudnorm`), energy swing (90th-10th percentile of
  short-term RMS in dB -- how much a track swings between quiet/loud
  sections), brightness (mean spectral centroid, Hz), and vocals via
  transcribing each track and checking for 50+ words (reuses
  `transcribe.py`'s functions directly) -- matches her original spec for this
  tool exactly.
- Writes `<footage_root>/_editor/assets/music/catalog.json` with an
  absolute `source_path` back into `music_dir` -- **never writes into
  music_dir itself**, since that's her own external folder, not ours to
  modify (same boundary as raw footage folders).
- Verified on a synthetic 120 BPM click (117.5 BPM detected) and on her real
  music folder (vocals detection via NeMo works on CPU; all six tracks came
  back instrumental). Tracks with big energy swings (~14 dB) are distracting
  under talking; steady ones sit better.
- `--skip-vocals` flag skips the NeMo step entirely for a fast catalog pass.

## Tool gotchas (confirmed or carried over from Liz's own prior experience)

- **transcribe.py**: pass audio to NeMo as a numpy float32 array, never a path —
  path-based input makes NeMo leave a temp manifest file open, which crashes on
  Windows (her finding, not yet independently re-verified by us this round).
  Switch Parakeet to local attention (`rel_pos_local_attn`, context `[128,128]`)
  above ~10 min of audio as a precaution; the "OOMs around 17min on a 12GB card"
  rationale is unverified boilerplate (see "Dev split" correction above) — revisit
  this threshold once a long clip is actually run somewhere and OOM behavior (or
  lack of it) is observed for real. Always extract the explicit AAC track
  (`-map 0:a:0`), see footage notes above.
- **fetch_assets.py** (new, 2026-10-23): pulls free, no-permission-needed assets
  into `<footage_root>/_editor/assets/<kind>/`, each with a `manifest.json`
  recording source/license/attribution so nothing gets used blind.
  - `emoji` subcommand: bulk-downloads the OpenMoji SVG-color set (one-time,
    skips re-download if already present) — **confirmed working for real**:
    4,495 svgs + a 4,565-entry tag/annotation metadata file, searchable via
    `--search <tags...>` (e.g. `--search tool wrench warning` surfaced wrench,
    screwdriver, toolbox, hammer-and-wrench, warning, check-mark — good fit
    for repair-tutorial callouts). License is **CC-BY-SA 4.0, attribution
    required** (not plain CC-BY as I first assumed — checked the actual
    LICENSE.txt in the repo rather than guessing) — need an attribution line
    in the video description whenever an OpenMoji asset is used in a video.
  - `sfx` subcommand: searches Freesound restricted to CC0 only (no
    attribution ever owed) and downloads the HQ preview mp3 (the full
    original download needs an OAuth login, not just an API key — the
    preview avoids that and is fine for SFX use). **Not yet run for real** —
    needs `freesound_api_key` in `config.json`; Liz has to create that
    Freesound account/key herself (I can't create third-party accounts on
    her behalf) at https://freesound.org/apiv2/apply/.
  - Background **music fetching was explicitly descoped** (2026-10-23, her
    call) — skip it, don't build a Pixabay/music source into this tool.
  - `fonts` subcommand (added 2026-10-23, her call: "add the last two things
    to the plan"): downloads font families straight from the `google/fonts`
    GitHub repo (tries `ofl/` then `apache/` then `ufl/` license folders),
    no API key. **Confirmed working for real** — fetched Montserrat, Oswald,
    Bebas Neue, verified as valid TrueType files with their `OFL.txt`
    alongside. SIL Open Font License: free for commercial use, **no
    attribution required** (OFL only requires the license text travel with
    the font file, not credit in the video) — unlike OpenMoji above, nothing
    needs to go in the description for fonts. Variable fonts download as a
    single `FamilyName[axis].ttf` (e.g. `Montserrat[wght].ttf`) — fine for
    drawtext, but prefer a fixed-weight static file (like Bebas Neue's
    `BebasNeue-Regular.ttf`) for thumbnail/caption work to avoid relying on
    the variable font defaulting to the right weight.
- **thumbnail.py** (new, 2026-10-23, her call: "add the last two things to
  the plan"): auto-picks a few candidate frames from a clip (Laplacian
  sharpness + HSV saturation as a cheap "looks interesting" proxy — a
  starting heuristic, not a substitute for actually looking at the
  candidates), overlays bold title text via ffmpeg `drawtext` using a font
  from `fetch_assets.py fonts`, outputs 1280x720 PNGs (YouTube thumbnail
  spec) to `<work>/thumbnails/`. **Confirmed working for real** on her
  footage: produced 3 real candidates; visually inspected one —
  "IS IT WORTH IT?" in bold white Bebas Neue with a black border, clearly
  legible over a real frame. Not yet in the original 11-tool list; this is
  net-new scope she asked to add.
- **graphics.py** (new, 2026-10-23, her call: "add TitaNet and HyperFrames"):
  renders a callout graphic (icon + bold text, animates in/out) to a
  transparent ProRes 4444 MOV via HyperFrames (HTML+GSAP -> video), for
  `render.py` to composite over footage. **Confirmed working for real,
  pixel-checked**: rendered a "CHECK THE FUSE FIRST" callout with a
  warning-triangle OpenMoji icon and Bebas Neue text, `ffprobe` confirms
  `prores`/`yuva444p12le`, and I sampled actual RGBA pixel values —
  background alpha=0 (fully transparent), badge alpha=255 (fully opaque),
  soft partial alpha at the drop-shadow edge. Not a guess from docs; actually
  measured. **Requires Node >=22 on PATH** (`npx hyperframes` fails/needs a
  real Node on this box's default v12 -- used `nvm use 22`; Windows setup
  needs its own Node >=22, e.g. `winget install OpenJS.NodeJS.LTS`, not yet
  verified there). HyperFrames itself is a HeyGen product with an optional
  cloud tier (`hyperframes cloud`/`lambda`/`auth`) — **never use those**,
  only local rendering (`init`, `render`, `check`), to keep this free/local
  per her original requirement.
- **speakers.py** (new, 2026-10-23, her call): TitaNet voiceprints per
  pause-bounded segment, numpy 2-means (no sklearn dependency), labels the
  cluster nearest a `--reference-clip` solo-you clip as "me". **Partially
  verified**: segment-grouping (splits correctly on >0.5s pauses) and the
  k-means math (cleanly separates synthetic well-separated clusters) checked
  locally with real assertions. The NeMo-facing calls
  (`EncDecSpeakerLabelModel.from_pretrained(...)`, `.get_embedding(path)`)
  are **unverified** — written from documentation, same position
  `transcribe.py` was in before Windows corrected some of its assumptions.
  Only makes sense for two-speaker footage — her content is mostly solo
  DIY/review narration (see "Channel" above), so check whether a given video
  actually has two speakers before running this; forcing a 2-way split on
  one voice just clusters noise into a meaningless split.
- **Free source map for future reference** (not yet built into tooling beyond
  emoji/sfx above): YouTube Audio Library is the only source structurally
  immune to Content ID claims (YouTube clears it directly) but has no API —
  can't be automated, only used manually. Pixabay (music/sfx/images, API key,
  no attribution) and Freesound (CC0 filter is the safe subset) are
  API-automatable. OpenMoji/Twemoji are open-source bulk packs, not
  per-query search.
- **Transitions are built** (xfade, see toolkit above) — a filter, so zero
  licensing risk. Deliberately steered away from downloaded "transition
  pack" overlay clips (glitch/light-leak stock footage): those read as
  wedding/vlog template style, which clashes with the "quirky, fast,
  informative" DIY-tutorial feel. Default to plain cuts/fades unless Liz asks
  for a specific look.
- **ffmpeg on Windows**: `drawtext` segfaults without fontconfig — always pass
  `fontfile='C\:/Windows/Fonts/arial.ttf'`. HEIC stills are tile grids that
  ffmpeg 9 stitches as a stream group, so `-vf` on a HEIC input errors
  ("Simple and complex filtering cannot be used together") — decode to PNG
  first (render.py caches them in `<work>/stills`). Windows python can't open
  `/c/...` git-bash paths — use `C:/...`.
- **loudnorm** single-pass missed -14 by 2.6 LU; render.py does two-pass
  (lands -14.3 to -14.7, capped by the -1.5 dBTP ceiling).
- Don't read frame rate from `ffprobe -read_intervals` pts — packets come in
  decode order (B-frames), so 30fps looks like 15. Count packets / duration.

## Editing taste log

- **OpenMoji icons need a credit** (license verified 2026-10-23 on their
  GitHub: CC BY-SA 4.0, not CC-BY as fetch_assets.py's docstring said --
  fixed). Any video using one gets this line in its description: "Emoji
  designed by OpenMoji – the open-source emoji and icon project. License:
  CC BY-SA 4.0". Tell Liz whenever an edit uses one. Fonts (OFL) and
  Freesound CC0 sfx need no credit.
- **Background music: YouTube videos only, never Amazon videos** (Liz's rule,
  2026-10-23). She makes videos for both destinations, so before adding music
  (from `music_dir`) know which one a video is for — if it isn't clear, ask
  her rather than guessing. An Amazon cut gets voice/clip audio only.
  render.py enforces it: a plan with `"music"` must also say
  `"destination": "youtube"` or the render stops.
- **Music sources**: prefer YouTube Audio Library tracks (named artist files
  like "Nico Staf - ..." / "Riot - ..." in `_music`). Files with generic
  names (`Track.mp3`, `Track (1).mp3`...) have unknown provenance — ask her
  where they came from before using them.
- She has asked for **"talking throughout and background music"** on a
  YouTube review: fill the length with her real speech (cutaways, B-roll and
  PiP for visuals), keep silent stretches to brief photo transitions, and
  keep music ~15-20 dB under her voice.
- **No captions** (Liz, 2026-10-23, right after I built burned-in
  captions): "I dont want captions". Keep `"captions"` off in plans; the
  feature stays in render.py, off by default, but don't add it unless she
  asks. No reason given; ask before assuming it also covers title text.
- When she gives a length target (e.g. ~5 min) and a tight cut comes out
  shorter, she has preferred padding with real content over cutting short.
  Unconfirmed whether that's a general rule.
- Channel branding to keep using: "Egghead Reviews" intro sting at the top,
  "Hello my fellow eggheads" greeting, "From one egghead to another egghead,
  this is Liz signing out" sign-off. Right now the sting and sign-off only
  exist as clips inside one of her older published videos in the footage
  folder; ask her for standalone copies if a new video needs them.
- Steer away from flashy downloaded transition packs (glitch/light-leak
  overlays); plain crossfades/cuts fit the DIY-tutorial tone better. Not yet
  directly confirmed by Liz — my own editorial judgment call when she asked
  about free transitions (2026-10-23); flag this one for her to correct if
  she actually wants a punchier look.
- (fill in as Liz gives review notes on real cuts. Log each confirmed
  preference with the reasoning, not just the verdict.)

## Open questions / unconfirmed

- Whether the git-repo-for-code / footage-root-for-work-files split (above) is
  actually fine with her, or she wants tools physically inside
  `_editor\tools` on the footage root too (e.g. for use on a totally different
  machine without this git repo cloned).
- `transcribe(audio=[numpy_array], timestamps=True)` is **confirmed working**
  (NeMo 3.0.0, CPU, real clips 2026-10-23: correct per-clip times).
  `change_attention_model(...)` for audio over 10 min has still never been
  run.
