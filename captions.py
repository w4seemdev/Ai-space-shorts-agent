"""
captions.py — generate a voiceover AND word-synced karaoke captions in a single
edge-tts pass.

edge-tts can stream `WordBoundary` events alongside the audio. We capture those
word timings and turn them into a styled ASS subtitle file with a TikTok-style
"pop" caption that highlights each word as it is spoken. Burning this in with
ffmpeg's `ass` filter is the single biggest retention upgrade for Shorts.
"""

import asyncio
import re

import edge_tts

# 100-nanosecond "ticks" per millisecond (edge-tts offsets are in ticks).
TICKS_PER_MS = 10_000

# How many words to show on screen at once (Shorts caption "chunk").
WORDS_PER_CHUNK = 3
# Don't let a caption linger more than this after its last word (ms).
MAX_TAIL_MS = 350


def _ass_timestamp(ms: float) -> str:
    """Format milliseconds as an ASS timestamp: H:MM:SS.cs (centiseconds)."""
    ms = max(0, int(ms))
    cs = (ms % 1000) // 10
    s = (ms // 1000) % 60
    m = (ms // 60_000) % 60
    h = ms // 3_600_000
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _clean_word(word: str) -> str:
    """Strip characters that would break ASS markup or look noisy on screen."""
    word = word.replace("{", "").replace("}", "").replace("\\", "")
    word = word.replace("\n", " ").strip()
    return word.upper()


def _build_ass(boundaries, font: str, primary: str, secondary: str,
               outline: str, fontsize: int, margin_v: int) -> str:
    """Turn a list of (start_ms, dur_ms, text) word boundaries into ASS text."""
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Pop,{font},{fontsize},{primary},{secondary},{outline},&H64000000,-1,0,0,0,100,100,1,0,1,6,3,2,80,80,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    # Group consecutive words into fixed-size chunks, breaking on sentence-ending
    # punctuation so a caption never straddles two sentences.
    chunks = []
    current = []
    for b in boundaries:
        current.append(b)
        ends_sentence = bool(re.search(r"[.!?]$", b["text"].strip()))
        if len(current) >= WORDS_PER_CHUNK or ends_sentence:
            chunks.append(current)
            current = []
    if current:
        chunks.append(current)

    lines = []
    for i, chunk in enumerate(chunks):
        start_ms = chunk[0]["start"]
        last = chunk[-1]
        chunk_end = last["start"] + last["dur"]
        # Hold the caption until the next chunk starts (smoother), capped.
        if i + 1 < len(chunks):
            next_start = chunks[i + 1][0]["start"]
            chunk_end = min(next_start, chunk_end + MAX_TAIL_MS)
        else:
            chunk_end += MAX_TAIL_MS

        parts = []
        for j, w in enumerate(chunk):
            text = _clean_word(w["text"])
            if not text:
                continue
            # Karaoke fill duration = time until the next word starts, so the
            # highlight sweep tracks the actual speech pacing (gaps included).
            if j + 1 < len(chunk):
                fill_ms = chunk[j + 1]["start"] - w["start"]
            else:
                fill_ms = w["dur"]
            fill_cs = max(1, round(fill_ms / 10))
            parts.append(f"{{\\kf{fill_cs}}}{text}")

        if not parts:
            continue
        text = " ".join(parts)
        lines.append(
            f"Dialogue: 0,{_ass_timestamp(start_ms)},{_ass_timestamp(chunk_end)},"
            f"Pop,,0,0,0,,{text}"
        )

    return header + "\n".join(lines) + "\n"


def _expand_sentence(start_ms, dur_ms, text):
    """Split a sentence's time budget across its words proportional to length.

    Used as a fallback when the TTS service only returns sentence-level timings.
    """
    words = text.split()
    if not words:
        return []
    weights = [len(w) + 1 for w in words]
    total = sum(weights)
    out, cursor = [], start_ms
    for w, weight in zip(words, weights):
        span = dur_ms * weight / total
        out.append({"start": cursor, "dur": span, "text": w})
        cursor += span
    return out


async def _synthesize(text, audio_path, voice, rate, pitch):
    """Stream TTS audio to disk and collect timing boundaries.

    Prefers true word boundaries; falls back to expanding sentence boundaries
    into per-word timings so captions are never empty across edge-tts versions.
    """
    try:
        communicate = edge_tts.Communicate(
            text, voice=voice, rate=rate, pitch=pitch, boundary="WordBoundary")
    except TypeError:
        # Older edge-tts without the `boundary` kwarg (emits WordBoundary anyway).
        communicate = edge_tts.Communicate(text, voice=voice, rate=rate, pitch=pitch)

    words, sentences = [], []
    with open(audio_path, "wb") as audio:
        async for chunk in communicate.stream():
            ctype = chunk["type"]
            if ctype == "audio":
                audio.write(chunk["data"])
            elif ctype == "WordBoundary":
                words.append({
                    "start": chunk["offset"] / TICKS_PER_MS,
                    "dur": chunk["duration"] / TICKS_PER_MS,
                    "text": chunk["text"],
                })
            elif ctype == "SentenceBoundary":
                sentences.append((
                    chunk["offset"] / TICKS_PER_MS,
                    chunk["duration"] / TICKS_PER_MS,
                    chunk["text"],
                ))

    if words:
        return words
    boundaries = []
    for start_ms, dur_ms, sent in sentences:
        boundaries.extend(_expand_sentence(start_ms, dur_ms, sent))
    return boundaries


def generate_voiceover_with_captions(
    text,
    audio_path,
    ass_path,
    voice="en-US-GuyNeural",
    rate="+8%",
    pitch="+0Hz",
    font="DejaVu Sans",
    primary="&H0000E5FF",      # highlighted fill (orange) — BBGGRR
    secondary="&H00FFFFFF",    # base white before the sweep
    outline="&H00000000",      # black outline
    fontsize=92,
    margin_v=520,
):
    """Create `audio_path` (mp3) and `ass_path` (synced captions) from `text`.

    Returns the list of word boundaries (handy for tests / debugging).
    """
    boundaries = asyncio.run(_synthesize(text, audio_path, voice, rate, pitch))
    ass = _build_ass(
        boundaries, font=font, primary=primary, secondary=secondary,
        outline=outline, fontsize=fontsize, margin_v=margin_v,
    )
    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(ass)
    return boundaries
