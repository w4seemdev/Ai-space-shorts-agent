"""Unit tests for upload.py metadata sanitization and CI guards."""

import upload
from upload import DESCRIPTION_MAX_BYTES, _clean_metadata, _headless


class TestCleanMetadata:
    def test_strips_angle_brackets(self):
        assert _clean_metadata("What <Really> Happens", 100) == "What Really Happens"

    def test_byte_limit_not_char_limit(self):
        # 4-byte emoji: 2000 chars but 8000 bytes must be cut to <= limit.
        text = "🚀" * 2000
        cleaned = _clean_metadata(text, DESCRIPTION_MAX_BYTES)
        assert len(cleaned.encode("utf-8")) <= DESCRIPTION_MAX_BYTES

    def test_truncation_never_leaves_broken_utf8(self):
        text = "a" + "🚀" * 2000
        cleaned = _clean_metadata(text, 10)
        cleaned.encode("utf-8").decode("utf-8")  # must not raise


class TestHeadlessGuard:
    def test_ci_env_forces_headless(self, monkeypatch):
        monkeypatch.setenv("CI", "true")
        assert _headless() is True

    def test_returns_bool(self, monkeypatch):
        monkeypatch.delenv("CI", raising=False)
        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
        assert isinstance(_headless(), bool)


class TestConstants:
    def test_description_budget_below_youtube_hard_limit(self):
        assert DESCRIPTION_MAX_BYTES <= 5000

    def test_retriable_status_are_server_errors(self):
        assert all(500 <= s < 600 for s in upload.RETRIABLE_STATUS)
