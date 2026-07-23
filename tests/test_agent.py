"""Unit tests for agent.py's pure helpers (no network, no ffmpeg)."""

import json

import agent
from agent import (
    GROQ_MODELS,
    HISTORY_KEEP,
    build_description,
    build_tags,
    build_title,
    content_red_flags,
    load_history,
    pick_topic,
    sanitize_text,
    save_history,
    spoken_text,
    topic_hashtags,
)
from topics import TOPICS


def script(**overrides):
    base = {
        "title": "Neutron Stars Are Heavier Than You Think",
        "hook": "A teaspoon of this star outweighs a mountain.",
        "facts": "It spins 700 times a second. Its core is a mystery.",
        "cta": "So what happens when two of them collide?",
        "topic": "Neutron stars spinning 700 times per second",
    }
    base.update(overrides)
    return base


class TestSanitizeText:
    def test_strips_angle_brackets_and_collapses_whitespace(self):
        assert sanitize_text("a <b>  c\n d") == "a b c d"


class TestContentRedFlags:
    def test_flags_red_flag_terms(self):
        assert content_red_flags("The election on Mars") == ["election"]

    def test_word_boundary_prevents_false_positives(self):
        # "sextillion" must not trip anything; neither should clean text.
        assert content_red_flags("A sextillion stars shine brightly") == []


class TestBuildTitle:
    def test_appends_single_shorts_tag(self):
        title = build_title(script())
        assert title.endswith(" #shorts")
        assert title.count("#") == 1

    def test_long_title_truncates_on_word_boundary_under_100(self):
        long_title = "Black Holes " + "Absolutely Enormous Gravitational " * 4
        title = build_title(script(title=long_title))
        assert len(title) <= 100
        core = title[: -len(" #shorts")]
        for w in core.split():
            assert w in long_title  # no mid-word cut

    def test_angle_brackets_removed(self):
        assert "<" not in build_title(script(title="What <Really> Happens"))


class TestTags:
    def test_unique_capped_and_seeded(self):
        tags = build_tags(script())
        assert len(tags) <= 15
        assert len(tags) == len(set(tags))
        assert "space" in tags


class TestTopicHashtags:
    def test_topic_specific_hashtags(self):
        tags = topic_hashtags("Black holes and what happens if you fall in")
        assert 0 < len(tags) <= 2
        for t in tags:
            assert t.startswith("#") and t[1:].isalnum()


class TestDescription:
    def test_contains_script_and_hashtags(self):
        desc = build_description(script())
        assert script()["hook"] in desc
        assert "#shorts" in desc and "#space" in desc


class TestSpokenText:
    def test_concatenates_hook_facts_cta(self):
        s = script()
        spoken = spoken_text(s)
        assert s["hook"] in spoken and s["cta"] in spoken


class TestPickTopic:
    def test_avoids_recently_used_topics(self):
        used = TOPICS[:5]
        history = [{"topic": t, "title": t, "at": "x"} for t in used]
        for _ in range(20):
            assert pick_topic(history) not in used

    def test_still_returns_topic_when_pool_exhausted(self):
        history = [{"topic": t, "title": t, "at": "x"} for t in TOPICS]
        assert pick_topic(history) in TOPICS


class TestHistory:
    def test_roundtrip_and_trim(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        entries = [{"topic": f"t{i}", "title": f"T{i}", "at": "20260101_000000"}
                   for i in range(HISTORY_KEEP + 10)]
        save_history(entries)
        loaded = load_history()
        assert len(loaded) == HISTORY_KEEP
        assert loaded[-1]["topic"] == f"t{HISTORY_KEEP + 9}"

    def test_corrupt_history_returns_empty(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "history.json").write_text("{not json", encoding="utf-8")
        assert load_history() == []


class TestModelFallbacks:
    def test_primary_first_no_duplicates(self):
        assert GROQ_MODELS[0]  # primary exists
        assert len(GROQ_MODELS) == len(set(GROQ_MODELS))
        assert len(GROQ_MODELS) >= 3  # real fallback depth


class TestStepSummary:
    def test_noop_without_env(self, monkeypatch):
        monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
        agent.write_step_summary(["## test"])  # must not raise

    def test_appends_when_env_set(self, tmp_path, monkeypatch):
        summary = tmp_path / "summary.md"
        monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
        agent.write_step_summary(["## run", "| a | b |"])
        assert "## run" in summary.read_text(encoding="utf-8")
