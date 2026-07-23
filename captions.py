"""
captions.py — generate a voiceover AND word-synced karaoke captions in a single
edge-tts pass.

edge-tts can stream `WordBoundary` events alongside the audio. We capture those
word timings and turn them into a styled ASS subtitle file with a TikTok-style
"pop" caption that highlights each word as it is spoken. Burning this in with
ffmpeg's `ass` filter is the single biggest retention upgrade for Shorts.
"""

import asyncio
import logging
import os
import time

import edge_tts

log = logging.getLogger("captions")

# 100-nanosecond "ticks" per millisecond (edge-tts offsets are in ticks).
TICKS_PER_MS = 10_000

# Caption chunking: budget by CHARACTERS, not words — at fontsize 92 the usable
# width (1080 minus margins) fits ~15 uppercase chars, so longer chunks clip.
MAX_CHUNK_CHARS = 14
MAX_CHUNK_WORDS = 3
# A speech gap longer than this starts a new caption (recovers sentence breaks —
# edge-tts WordBoundary text arrives punctuation-stripped).
PAUSE_BREAK_MS = 300
# Don't let a caption linger more than this after its last word (ms).
MAX_TAIL_MS = 350

# TTS reliability: Microsoft's endpoint intermittently rejects datacenter IPs
# (GitHub runners especially), so synthesis retries with backoff + voice rotation.
TTS_ATTEMPTS = 3
# A voiceover for even a very short script exceeds this; smaller output = failure.
MIN_AUDIO_BYTES = 20_000
# edge-tts emits 24 kHz mono mp3 at 48 kbps; used to estimate duration when the
# service returns audio but no timing events (48 kbps == 48 bits per ms).
EDGE_TTS_KBPS = 48


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


def _chunk_boundaries(boundaries):
    """Group word boundaries into caption chunks that never overflow the frame.

    A chunk closes when adding the next word would exceed MAX_CHUNK_CHARS, when
    it already holds MAX_CHUNK_WORDS, or after a speech pause > PAUSE_BREAK_MS.
    """
    chunks, current, cur_len = [], [], 0
    for i, b in enumerate(boundaries):
        wlen = len(b["text"].strip())
        if current and (cur_len + 1 + wlen > MAX_CHUNK_CHARS
                        or len(current) >= MAX_CHUNK_WORDS):
            chunks.append(current)
            current, cur_len = [], 0
        current.append(b)
        cur_len += (1 if cur_len else 0) + wlen

        nxt = boundaries[i + 1] if i + 1 < len(boundaries) else None
        if nxt and nxt["start"] - (b["start"] + b["dur"]) > PAUSE_BREAK_MS:
            chunks.append(current)
            current, cur_len = [], 0
    if current:
        chunks.append(current)
    return chunks


def _build_ass(boundaries, font: str, primary: str, secondary: str,
               outline: str, fontsize: int, margin_v: int) -> str:
    """Turn a list of (start_ms, dur_ms, text) word boundaries into ASS text."""
    # WrapStyle 0 = smart wrapping: a rare oversized chunk wraps to a second
    # line instead of clipping off both screen edges.
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Pop,{font},{fontsize},{primary},{secondary},{outline},&H64000000,-1,0,0,0,100,100,1,0,1,6,3,2,80,80,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    chunks = _chunk_boundaries(boundaries)

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


def _estimate_boundaries(text, audio_path):
    """No timing events at all — spread words over the estimated mp3 duration.

    Captions lose word-perfect sync but the video still ships with readable,
    roughly-synced captions instead of none.
    """
    dur_ms = os.path.getsize(audio_path) * 8 / EDGE_TTS_KBPS
    return _expand_sentence(0, dur_ms, text)


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
    fallback_voices=None,
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

    Retries synthesis with backoff, rotating through `fallback_voices` (blocks
    can be endpoint/voice-specific). Returns the list of word boundaries.
    """
    voices = [voice] + [v for v in (fallback_voices or []) if v != voice]
    last_err = None
    boundaries = None
    for attempt in range(TTS_ATTEMPTS):
        v = voices[min(attempt, len(voices) - 1)]
        try:
            boundaries = asyncio.run(_synthesize(text, audio_path, v, rate, pitch))
            size = os.path.getsize(audio_path) if os.path.exists(audio_path) else 0
            if size < MIN_AUDIO_BYTES:
                raise RuntimeError(f"TTS produced undersized audio ({size} bytes)")
            break
        except Exception as e:  # noqa: BLE001 — any TTS/network failure: retry is always right unattended
            last_err = e
            log.warning("TTS attempt %d/%d (%s) failed: %s",
                        attempt + 1, TTS_ATTEMPTS, v, e)
            time.sleep(2 * (attempt + 1))
    else:
        raise RuntimeError(f"TTS failed after {TTS_ATTEMPTS} attempts: {last_err}")

    if not boundaries:
        log.warning("TTS returned no timing events — estimating caption timings.")
        boundaries = _estimate_boundaries(text, audio_path)

    ass = _build_ass(
        boundaries, font=font, primary=primary, secondary=secondary,
        outline=outline, fontsize=fontsize, margin_v=margin_v,
    )
    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(ass)
    return boundaries
