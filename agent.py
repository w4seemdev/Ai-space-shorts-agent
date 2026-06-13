"""
Space Shorts Agent — generates a unique space/science YouTube Short end to end:
script (Groq LLM) -> voiceover + word-synced captions (edge-tts) -> vertical
video (ffmpeg) -> upload (YouTube Data API).

Run locally:        python agent.py
Build but skip upload:  DRY_RUN=1 python agent.py     (PowerShell: $env:DRY_RUN=1)
"""

import glob
import json
import logging
import os
import random
import shutil
import subprocess
import sys
import time
from datetime import datetime

from dotenv import load_dotenv
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
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
DRY_RUN = os.getenv("DRY_RUN", "").lower() in ("1", "true", "yes")
VIDEO_SECONDS = int(os.getenv("VIDEO_SECONDS", "60"))
HISTORY_FILE = "history.json"
HISTORY_KEEP = 20

# A handful of energetic English voices; one is picked per run for variety.
VOICES = [
    "en-US-GuyNeural",
    "en-US-AndrewNeural",
    "en-US-BrianNeural",
    "en-US-ChristopherNeural",
    "en-GB-RyanNeural",
]

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))


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


# ── History (local de-duplication; gitignored, ephemeral in CI) ──────────────
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
        {
            "role": "system",
            "content": (
                "You are a YouTube Shorts script writer specializing in space and "
                "science facts. Respond ONLY with JSON in this exact shape:\n"
                '{"title": "punchy <=70 char title", '
                '"hook": "first 1-2 sentences that grab attention", '
                '"facts": "3-4 short punchy facts, conversational", '
                '"cta": "short call to action"}'
            ),
        },
        {
            "role": "user",
            "content": (
                f"Write a YouTube Shorts script specifically about: {topic}. "
                f"Make it exciting and mind-blowing.{avoid}"
            ),
        },
    ]

    last_err = None
    for attempt in range(1, 4):
        try:
            response = groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=messages,
                temperature=0.9,
                response_format={"type": "json_object"},
            )
            script = json.loads(response.choices[0].message.content)
            if not all(k in script for k in ("title", "hook", "facts", "cta")):
                raise ValueError(f"missing keys in script: {list(script)}")
            script["topic"] = topic
            return script
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            last_err = e
            log.warning("Script parse failed (attempt %d/3): %s", attempt, e)
            time.sleep(1.5 * attempt)

    raise RuntimeError(f"Could not get valid script after 3 attempts: {last_err}")


# ── Background ───────────────────────────────────────────────────────────────
def pick_background():
    """Return an existing background clip, or generate a starfield fallback."""
    candidates = ["bg1.mp4", "bg2.mp4", "bg3.mp4", "bg4.mp4", "bg5.mp4", "background.mp4"]
    available = [b for b in candidates if os.path.exists(b)]
    if available:
        bg = random.choice(available)
        log.info("🎥 Background: %s", bg)
        return bg

    log.info("🎥 No background clip found — generating a starfield fallback.")
    bg = "background_generated.mp4"
    subprocess.run([
        ffmpeg_bin(), "-y",
        "-f", "lavfi",
        "-i", f"color=c=0x05050f:s=1080x1920:r=30:d={VIDEO_SECONDS}",
        "-vf", "noise=alls=22:allf=t,vignette=PI/4,eq=saturation=1.2",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "30",
        bg,
    ], check=True)
    return bg


# ── Video assembly ───────────────────────────────────────────────────────────
def build_video(audio_file, ass_file, output_file):
    log.info("🎬 Building video with synced captions...")
    background = pick_background()

    command = [
        ffmpeg_bin(), "-y",
        "-stream_loop", "-1",
        "-t", str(VIDEO_SECONDS),
        "-i", background,
        "-i", audio_file,
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-vf", (
            "scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,setsar=1,"
            f"ass={ass_file}"
        ),
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


def build_description(script):
    hashtags = "#shorts #space #science #astronomy #universe #nasa"
    return (
        f"{script['hook']}\n\n{script['facts']}\n\n{script['cta']}\n\n{hashtags}"
    )


# ── Cleanup ──────────────────────────────────────────────────────────────────
def clean_old_artifacts():
    for pattern in ("voiceover_*.mp3", "captions_*.ass"):
        for f in glob.glob(pattern):
            try:
                os.remove(f)
            except OSError:
                pass


# ── Pipeline ─────────────────────────────────────────────────────────────────
def main():
    clean_old_artifacts()
    history = load_history()

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    audio_file = f"voiceover_{stamp}.mp3"
    ass_file = f"captions_{stamp}.ass"
    video_file = f"output_{stamp}.mp4"

    script = generate_script(history)
    log.info("📹 Title: %s", script["title"])

    spoken = f"{script['hook']} {script['facts']} {script['cta']}"
    voice = random.choice(VOICES)
    log.info("🎙️ Voiceover (%s) + synced captions...", voice)
    generate_voiceover_with_captions(spoken, audio_file, ass_file, voice=voice)

    build_video(audio_file, ass_file, video_file)

    title = f"{script['title']} #shorts #space #science"[:100]
    if DRY_RUN:
        log.info("🧪 DRY_RUN set — skipping YouTube upload.")
        log.info("    Would upload %s as: %s", video_file, title)
    else:
        log.info("📤 Uploading to YouTube...")
        upload_video(title, build_description(script), video_file,
                     tags=build_tags(script))

    history.append({"topic": script["topic"], "title": script["title"], "at": stamp})
    save_history(history)

    log.info("✅ Done! Saved locally as: %s", video_file)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001 — top-level guard: log and fail CI loudly
        log.error("💥 Agent failed: %s", e)
        sys.exit(1)
