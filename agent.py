"""
Space Shorts Agent — generates a unique space/science YouTube Short end to end:
script (Groq LLM with model fallbacks) -> voiceover + word-synced captions
(edge-tts) -> vertical video with procedural space background + ambient bed
(ffmpeg) -> upload (YouTube Data API).

Run locally:        python agent.py
Build but skip upload:  DRY_RUN=1 python agent.py     (PowerShell: $env:DRY_RUN=1)
"""

import glob
import json
import logging
import os
import random
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime

from dotenv import load_dotenv
import groq
from groq import Groq

from captions import generate_voiceover_with_captions
from topics import TOPICS
from upload import upload_video

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("agent")

# ── Config (override via .env) ───────────────────────────────────────────────
DRY_RUN = os.getenv("DRY_RUN", "").lower() in ("1", "true", "yes")
VIDEO_SECONDS = int(os.getenv("VIDEO_SECONDS", "60"))
HISTORY_FILE = "history.json"
HISTORY_KEEP = 20

# Primary model first (override via GROQ_MODEL); the rest are fallbacks so a
# rate limit, outage, or model decommission never kills the daily run.
GROQ_MODELS = list(dict.fromkeys([
    os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "openai/gpt-oss-120b",
]))

# ~170 spoken wpm at rate +8%: 150 words stays safely under the 60s cap.
MAX_SPOKEN_WORDS = 150

# Red flags for an unattended public channel: if the LLM drifts here, the
# script is regenerated rather than published (word-boundary matched).
CONTENT_RED_FLAGS = (
    "vaccine", "covid", "election", "president", "politician",
    "suicide", "murder", "terrorist",
)

# A handful of energetic English voices; one is picked per run for variety.
VOICES = [
    "en-US-GuyNeural",
    "en-US-AndrewNeural",
    "en-US-BrianNeural",
    "en-US-ChristopherNeural",
    "en-GB-RyanNeural",
]


def get_groq_client():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Add it to .env locally, or to the "
            "GROQ_API_KEY repository secret in CI "
            "(create a key at https://console.groq.com/keys)."
        )
    return Groq(api_key=api_key)


def require_config():
    """Fail fast with actionable messages before any expensive work."""
    problems = []
    if not os.getenv("GROQ_API_KEY"):
        problems.append(
            "GROQ_API_KEY missing — create one at https://console.groq.com/keys"
        )
    if not DRY_RUN:
        for f in ("client_secrets.json", "token.json"):
            if not os.path.exists(f):
                problems.append(f"{f} missing — run: python authorize.py")
    if problems:
        raise RuntimeError("Configuration problems: " + "; ".join(problems))


# ── ffmpeg discovery ─────────────────────────────────────────────────────────
def ffmpeg_bin():
    """Use a system ffmpeg if present (CI/Linux), else the bundled ffmpeg.exe."""
    found = shutil.which("ffmpeg")
    if found:
        return found
    local = os.path.join(os.path.dirname(__file__), "ffmpeg.exe")
    if os.path.exists(local):
        return local
    raise RuntimeError("ffmpeg not found on PATH and ffmpeg.exe is missing.")


# ── History (de-duplication; committed back to the repo from CI) ─────────────
def load_history():
    try:
        with open(HISTORY_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history[-HISTORY_KEEP:], f, indent=2)


def pick_topic(history):
    """Prefer a topic we haven't used recently; fall back to any if exhausted."""
    used = {h["topic"] for h in history}
    fresh = [t for t in TOPICS if t not in used]
    return random.choice(fresh or TOPICS)


# ── Script generation ────────────────────────────────────────────────────────
SYSTEM_PROMPT = (
    "You are a YouTube Shorts script writer specializing in space and science "
    "facts. Content must be strictly family-friendly: no politics, no medical "
    "claims, no conspiracy theories, nothing unverified stated as fact. "
    "Respond ONLY with JSON in this exact shape:\n"
    '{"title": "punchy <=60 char title, no hashtags, no angle brackets", '
    '"hook": "max 12 words; a shocking claim, stat, or direct second-person '
    "stake in the FIRST 8 words. BANNED openers: Did you know, Have you ever, "
    "Imagine, What if, Welcome. Good examples: You would not survive 3 seconds "
    'on Neptune. / A teaspoon of this star outweighs a mountain.", '
    '"facts": "3-4 short punchy facts, conversational, building on the hook", '
    '"cta": "one short line that raises a follow-up question or circles back '
    'to the hook so the video loops seamlessly; never like-and-subscribe '
    'boilerplate"}\n'
    "The whole spoken script (hook + facts + cta) must be under 130 words."
)


def sanitize_text(text):
    """Strip characters YouTube rejects (angle brackets) and tidy whitespace."""
    return " ".join(text.replace("<", "").replace(">", "").split())


def content_red_flags(text):
    """Return red-flag terms present in `text` (word-boundary matched)."""
    lowered = text.lower()
    return [t for t in CONTENT_RED_FLAGS
            if re.search(rf"\b{re.escape(t)}\b", lowered)]


def spoken_text(script):
    return f"{script['hook']} {script['facts']} {script['cta']}"


def generate_script(history):
    log.info("🤖 Generating script...")
    topic = pick_topic(history)
    log.info("📌 Topic: %s", topic)

    recent_titles = [h["title"] for h in history[-10:]]
    avoid = (
        f"\nAvoid titles similar to these recent ones: {recent_titles}"
        if recent_titles else ""
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Write a YouTube Shorts script specifically about: {topic}. "
                f"Make it exciting and mind-blowing.{avoid}"
            ),
        },
    ]

    client = get_groq_client()
    last_err = None
    attempt = 0
    for model in GROQ_MODELS:
        for _ in range(2):
            attempt += 1
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.9,
                    response_format={"type": "json_object"},
                )
                raw = response.choices[0].message.content
                if raw is None:
                    raise ValueError("model returned empty content")
                script = json.loads(raw)
                if not all(k in script for k in ("title", "hook", "facts", "cta")):
                    raise ValueError(f"missing keys in script: {list(script)}")
                script = {k: sanitize_text(v) if isinstance(v, str) else v
                          for k, v in script.items()}
                words = len(spoken_text(script).split())
                if words > MAX_SPOKEN_WORDS:
                    raise ValueError(f"script too long ({words} words)")
                flags = content_red_flags(spoken_text(script))
                if flags:
                    raise ValueError(f"script hit content red flags: {flags}")
                script["topic"] = topic
                script["model"] = model
                return script
            except groq.AuthenticationError as e:
                # A dead key won't get better with retries — fail loud and fast.
                raise RuntimeError(
                    "Groq rejected the API key (401). Rotate GROQ_API_KEY in "
                    ".env and in the GitHub repository secret."
                ) from e
            except (groq.APIError, json.JSONDecodeError, ValueError,
                    KeyError, TypeError) as e:
                last_err = e
                log.warning("Script attempt %d failed on %s: %s",
                            attempt, model, e)
                time.sleep(min(2 * attempt, 10))

    raise RuntimeError(
        f"Could not get a valid script after {attempt} attempts: {last_err}")


# ── Background ───────────────────────────────────────────────────────────────
PALETTES = [
    ("0x1a0533", "0x000814"),   # violet nebula
    ("0x03254c", "0x000000"),   # deep blue
    ("0x2d0a31", "0x050505"),   # magenta dust
    ("0x0b3d2e", "0x000010"),   # green aurora
]
BG_FPS = 30


def generate_space_background(duration):
    """Render a drifting starfield + nebula wash — unique palette every run."""
    c0, c1 = random.choice(PALETTES)
    frames = BG_FPS * duration
    stars = "stars_bg.png"
    bg = "background_generated.mp4"

    # 1) One oversized star still (1.5x frame gives the drift headroom).
    subprocess.run([
        ffmpeg_bin(), "-y",
        "-f", "lavfi", "-i", "color=black:s=1620x2880",
        "-vf", "noise=alls=70:allf=u,format=gray,"
               "lutyuv=y='if(gt(val,232),255,0)',gblur=sigma=0.4",
        "-frames:v", "1", stars,
    ], check=True, capture_output=True)

    # 2) Slow zoom/drift over the stars + animated nebula gradient on top.
    drift = random.randint(-80, 80)
    zoom = (
        f"zoompan=z='1.05+0.10*on/{frames}':"
        f"x='iw/2-(iw/zoom/2)+{drift}*on/{frames}':"
        f"y='ih/2-(ih/zoom/2)':d={frames}:s=1080x1920:fps={BG_FPS}"
    )
    subprocess.run([
        ffmpeg_bin(), "-y",
        "-loop", "1", "-i", stars,
        "-f", "lavfi",
        "-i", f"gradients=s=1080x1920:c0={c0}:c1={c1}:speed=0.008:r={BG_FPS}",
        "-filter_complex",
        f"[0]{zoom}[st];[1][st]blend=all_mode=screen:all_opacity=0.85,"
        f"vignette=PI/4.5,eq=saturation=1.25",
        "-t", str(duration), "-r", str(BG_FPS),
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
        bg,
    ], check=True, capture_output=True)
    log.info("🎥 Generated background (palette %s/%s, drift %+d)", c0, c1, drift)
    return bg


def generate_plain_starfield(duration):
    """Minimal static noise-star fallback if the fancy generator fails."""
    bg = "background_generated.mp4"
    subprocess.run([
        ffmpeg_bin(), "-y",
        "-f", "lavfi",
        "-i", f"color=c=0x05050f:s=1080x1920:r=30:d={duration}",
        "-vf", "noise=alls=22:allf=t,vignette=PI/4,eq=saturation=1.2",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "30",
        bg,
    ], check=True)
    return bg


def pick_background():
    """Local bg clips win if present; otherwise generate a fresh space scene."""
    candidates = ["bg1.mp4", "bg2.mp4", "bg3.mp4", "bg4.mp4", "bg5.mp4",
                  "background.mp4"]
    available = [b for b in candidates if os.path.exists(b)]
    if available:
        bg = random.choice(available)
        log.info("🎥 Background: %s", bg)
        return bg

    log.info("🎥 No background clip found — generating a space scene.")
    try:
        return generate_space_background(VIDEO_SECONDS)
    except (subprocess.CalledProcessError, OSError) as e:
        log.warning("Procedural background failed (%s) — using plain starfield.", e)
        return generate_plain_starfield(VIDEO_SECONDS)


# ── Video assembly ───────────────────────────────────────────────────────────
def build_video(audio_file, ass_file, output_file, audio_seconds=None):
    log.info("🎬 Building video with synced captions...")
    background = pick_background()

    # Match the video length to the narration instead of a hard 60s: an
    # over-long script no longer gets chopped mid-CTA, a short one no longer
    # leaves dead air.
    target = float(VIDEO_SECONDS)
    if audio_seconds:
        if audio_seconds > VIDEO_SECONDS:
            log.warning("Voiceover is %.1fs (> %ds cap) — it will be trimmed.",
                        audio_seconds, VIDEO_SECONDS)
        else:
            target = min(target, audio_seconds + 0.8)

    # Ambient bed: brown-noise rumble + slow drone under the voice, then
    # normalize the mix to YouTube's -14 LUFS so loudness is consistent
    # across the randomized voices.
    drone_hz = random.choice([55, 65, 82])
    filter_complex = (
        f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
        f"crop=1080:1920,setsar=1,ass={ass_file}[v];"
        f"anoisesrc=color=brown:r=44100:d={target:.2f},"
        f"lowpass=f=200,volume=0.5[ns];"
        f"sine=f={drone_hz}:r=44100:d={target:.2f},"
        f"tremolo=f=0.12:d=0.6,volume=0.9[dr];"
        f"[ns][dr]amix=inputs=2:duration=longest,volume=0.16[bed];"
        f"[1:a][bed]amix=inputs=2:duration=first:normalize=0,"
        f"loudnorm=I=-14:TP=-1.5:LRA=11,apad=pad_dur=0.8[a]"
    )

    command = [
        ffmpeg_bin(), "-y",
        "-stream_loop", "-1",
        "-t", f"{target:.2f}",
        "-i", background,
        "-i", audio_file,
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-map", "[a]",
        "-c:v", "libx264",
        "-c:a", "aac",
        "-shortest",
        "-preset", "veryfast",
        "-crf", "26",
        "-pix_fmt", "yuv420p",
        "-threads", "0",
        output_file,
    ]
    subprocess.run(command, check=True)
    log.info("✅ Video saved: %s", output_file)


# ── Metadata ─────────────────────────────────────────────────────────────────
STOPWORDS = {"the", "and", "what", "with", "from", "into", "your", "every",
             "their", "that", "this", "for", "are", "you", "its", "a", "an",
             "of", "in", "on", "to", "is", "it", "if", "by", "at"}


def build_title(script):
    """Title = LLM title (word-safe truncation) + a single #shorts tag."""
    core = sanitize_text(script["title"])
    if len(core) > 82:
        core = core[:82].rsplit(" ", 1)[0].rstrip(".,;:!?- ")
    return f"{core} #shorts"


def build_tags(script):
    """Derive topical tags from the chosen topic + a stable space-base set."""
    base = ["space", "facts", "shorts", "science", "nasa", "universe", "astronomy"]
    words = [w.strip(".,").lower() for w in script["topic"].split()]
    extra = [w for w in words if len(w) > 3 and w not in STOPWORDS]
    seen, tags = set(), []
    for t in base + extra:
        if t not in seen:
            seen.add(t)
            tags.append(t)
    return tags[:15]


def topic_hashtags(topic):
    """Up to two topic-specific hashtags so videos stop competing on the same
    saturated generic terms."""
    words = [w.strip(".,'").lower() for w in topic.split()]
    picks = [w for w in words if len(w) > 4 and w not in STOPWORDS][:2]
    tags = []
    for w in picks:
        slug = re.sub(r"[^a-z0-9]", "", w)
        if slug:
            tags.append(f"#{slug}")
    return tags


def build_description(script):
    hashtags = " ".join(
        ["#shorts", "#space", "#science", "#astronomy"]
        + topic_hashtags(script["topic"])
    )
    return (
        f"{script['hook']}\n\n{script['facts']}\n\n{script['cta']}\n\n{hashtags}"
    )


# ── Observability ────────────────────────────────────────────────────────────
def write_step_summary(lines):
    """Append markdown to the GitHub Actions run summary; no-op locally."""
    path = os.getenv("GITHUB_STEP_SUMMARY")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


# ── Cleanup ──────────────────────────────────────────────────────────────────
def clean_old_artifacts():
    for pattern in ("voiceover_*.mp3", "captions_*.ass", "stars_bg.png"):
        for f in glob.glob(pattern):
            try:
                os.remove(f)
            except OSError:
                pass


# ── Pipeline ─────────────────────────────────────────────────────────────────
def main():
    require_config()
    clean_old_artifacts()
    history = load_history()

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    audio_file = f"voiceover_{stamp}.mp3"
    ass_file = f"captions_{stamp}.ass"
    video_file = f"output_{stamp}.mp4"

    script = generate_script(history)
    log.info("📹 Title: %s", script["title"])

    spoken = spoken_text(script)
    voice = random.choice(VOICES)
    log.info("🎙️ Voiceover (%s) + synced captions...", voice)
    boundaries = generate_voiceover_with_captions(
        spoken, audio_file, ass_file, voice=voice, fallback_voices=VOICES)
    audio_seconds = (
        (boundaries[-1]["start"] + boundaries[-1]["dur"]) / 1000
        if boundaries else None
    )

    build_video(audio_file, ass_file, video_file, audio_seconds=audio_seconds)

    title = build_title(script)
    video_id = None
    if DRY_RUN:
        log.info("🧪 DRY_RUN set — skipping YouTube upload.")
        log.info("    Would upload %s as: %s", video_file, title)
    else:
        log.info("📤 Uploading to YouTube...")
        video_id = upload_video(title, build_description(script), video_file,
                                tags=build_tags(script))

    history.append({"topic": script["topic"], "title": script["title"], "at": stamp})
    save_history(history)

    write_step_summary([
        "## 🚀 Space Short published" if video_id else "## 🧪 Dry run finished",
        "| Field | Value |", "|---|---|",
        f"| Topic | {script['topic']} |",
        f"| Title | {title} |",
        f"| Voice | {voice} |",
        f"| Model | {script.get('model', '?')} |",
        f"| Narration | {audio_seconds:.1f}s |" if audio_seconds else "| Narration | ? |",
        f"| Video | https://youtube.com/shorts/{video_id} |" if video_id
        else f"| Video | {video_file} (not uploaded) |",
    ])

    log.info("✅ Done! Saved locally as: %s", video_file)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001 — top-level guard: log and fail CI loudly
        log.error("💥 Agent failed: %s", e)
        write_step_summary(["## 💥 Daily short FAILED", f"```\n{e}\n```"])
        sys.exit(1)
