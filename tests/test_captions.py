"""Unit tests for caption chunking, timing, and ASS generation."""

import captions
from captions import (
    MAX_CHUNK_CHARS,
    MAX_CHUNK_WORDS,
    _ass_timestamp,
    _build_ass,
    _chunk_boundaries,
    _clean_word,
    _estimate_boundaries,
    _expand_sentence,
)


def word(start, dur, text):
    return {"start": start, "dur": dur, "text": text}


def joined_len(chunk):
    words = [b["text"].strip() for b in chunk]
    return sum(len(w) for w in words) + (len(words) - 1)


class TestAssTimestamp:
    def test_zero(self):
        assert _ass_timestamp(0) == "0:00:00.00"

    def test_minutes_seconds_centiseconds(self):
        assert _ass_timestamp(61_234) == "0:01:01.23"

    def test_negative_clamps_to_zero(self):
        assert _ass_timestamp(-500) == "0:00:00.00"


class TestCleanWord:
    def test_strips_ass_markup_and_uppercases(self):
        assert _clean_word("{hello}\\") == "HELLO"

    def test_plain_word(self):
        assert _clean_word("nebula") == "NEBULA"


class TestChunking:
    def test_never_exceeds_char_budget_for_multiword_chunks(self):
        boundaries = [
            word(i * 500, 400, w)
            for i, w in enumerate(
                ["the", "universe", "is", "expanding", "faster", "every",
                 "second", "toward", "nothing"])
        ]
        for chunk in _chunk_boundaries(boundaries):
            if len(chunk) > 1:
                assert joined_len(chunk) <= MAX_CHUNK_CHARS

    def test_single_long_word_gets_own_chunk(self):
        boundaries = [
            word(0, 400, "watch"),
            word(500, 400, "spaghettification"),
            word(1000, 400, "happen"),
        ]
        chunks = _chunk_boundaries(boundaries)
        solo = [c for c in chunks if c[0]["text"] == "spaghettification"]
        assert len(solo) == 1 and len(solo[0]) == 1

    def test_word_cap(self):
        boundaries = [word(i * 300, 200, "ab") for i in range(9)]
        for chunk in _chunk_boundaries(boundaries):
            assert len(chunk) <= MAX_CHUNK_WORDS

    def test_pause_starts_new_chunk(self):
        boundaries = [
            word(0, 200, "one"),
            word(250, 200, "two"),
            # 800ms gap after "two" ends (450 -> 1250): sentence pause.
            word(1250, 200, "three"),
        ]
        chunks = _chunk_boundaries(boundaries)
        assert chunks[0][-1]["text"] == "two"
        assert chunks[1][0]["text"] == "three"

    def test_all_words_survive_chunking(self):
        boundaries = [word(i * 300, 250, f"w{i}") for i in range(20)]
        chunks = _chunk_boundaries(boundaries)
        flat = [b["text"] for c in chunks for b in c]
        assert flat == [b["text"] for b in boundaries]


class TestBuildAss:
    def kwargs(self):
        return dict(font="DejaVu Sans", primary="&H0000E5FF",
                    secondary="&H00FFFFFF", outline="&H00000000",
                    fontsize=92, margin_v=520)

    def test_uses_smart_wrapping(self):
        ass = _build_ass([word(0, 300, "star")], **self.kwargs())
        assert "WrapStyle: 0" in ass

    def test_karaoke_tags_and_dialogue_lines(self):
        boundaries = [word(0, 300, "stars"), word(400, 300, "burn")]
        ass = _build_ass(boundaries, **self.kwargs())
        dialogue = [ln for ln in ass.splitlines() if ln.startswith("Dialogue:")]
        assert dialogue and "\\kf" in ass

    def test_empty_boundaries_yield_no_dialogue(self):
        ass = _build_ass([], **self.kwargs())
        assert "Dialogue:" not in ass


class TestExpandSentence:
    def test_spans_cover_duration_proportionally(self):
        out = _expand_sentence(1000, 3000, "tiny galaxies collide")
        assert len(out) == 3
        assert out[0]["start"] == 1000
        total = sum(b["dur"] for b in out)
        assert abs(total - 3000) < 1e-6

    def test_empty_text(self):
        assert _expand_sentence(0, 1000, "   ") == []


class TestEstimateBoundaries:
    def test_duration_from_bitrate(self, tmp_path):
        mp3 = tmp_path / "voice.mp3"
        mp3.write_bytes(b"\0" * 48_000)  # 48 kB at 48 kbps -> 8000 ms
        out = _estimate_boundaries("one two three four", str(mp3))
        assert len(out) == 4
        last_end = out[-1]["start"] + out[-1]["dur"]
        assert abs(last_end - 8000) < 1


class TestConstantsSanity:
    def test_min_audio_bytes_is_reachable(self):
        # ~3.3s of speech at edge-tts's 48 kbps floor; real scripts are longer.
        assert captions.MIN_AUDIO_BYTES < 48_000
