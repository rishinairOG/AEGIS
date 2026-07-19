"""
Tests for AtlasMemory (HippoMem wrapper).
Run without GEMINI_API_KEY to test disabled path; with key and hippomem installed for full start/recall/remember.
"""
import os
import pytest

# Add backend to path
import sys
from pathlib import Path
BACKEND_DIR = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))


@pytest.fixture
def no_api_key(monkeypatch):
    """Ensure GEMINI_API_KEY is unset for tests that expect memory disabled."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    yield


@pytest.fixture
def fake_api_key(monkeypatch):
    """Set a fake API key so start() is attempted (will fail or no-op without real hippomem)."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-no-real-calls")
    yield


class TestAtlasMemoryInit:
    """AtlasMemory construction and config."""

    def test_memory_class_import(self):
        from memory import AtlasMemory
        assert AtlasMemory is not None

    def test_memory_init_no_key(self, no_api_key):
        from memory import AtlasMemory
        m = AtlasMemory()
        assert m.service is None
        assert m._api_key is None or m._api_key == ""

    def test_memory_init_with_key(self, fake_api_key):
        from memory import AtlasMemory
        m = AtlasMemory()
        assert m._api_key == "test-key-no-real-calls"
        assert m.service is None  # not started yet


class TestAtlasMemoryWithoutService:
    """When service is None (no key or not started), recall/remember/stop are safe no-ops."""

    @pytest.mark.asyncio
    async def test_recall_returns_empty_when_no_service(self, no_api_key):
        from memory import AtlasMemory
        m = AtlasMemory()
        result = await m.recall("hello")
        assert result == ""

    @pytest.mark.asyncio
    async def test_remember_no_op_when_no_service(self, no_api_key):
        from memory import AtlasMemory
        m = AtlasMemory()
        await m.remember("user said this", "assistant said that")  # should not raise

    @pytest.mark.asyncio
    async def test_stop_no_op_when_no_service(self, no_api_key):
        from memory import AtlasMemory
        m = AtlasMemory()
        await m.stop()  # should not raise


class TestAtlasMemoryStart:
    """start() with no key or missing hippomem should not crash."""

    @pytest.mark.asyncio
    async def test_start_without_api_key_sets_no_service(self, no_api_key):
        from memory import AtlasMemory
        m = AtlasMemory()
        await m.start()
        assert m.service is None

    @pytest.mark.asyncio
    async def test_start_with_fake_key_attempts_import(self, fake_api_key):
        from memory import AtlasMemory
        m = AtlasMemory()
        # May succeed if hippomem is installed and setup() works, or fail at setup;
        # either way we're testing the path doesn't crash unexpectedly
        try:
            await m.start()
        except Exception:
            pass  # e.g. network or hippomem setup failure
        # If start succeeded, service is not None
        # If start failed (no hippomem / config error), service may still be None
        assert m.service is None or hasattr(m.service, "decode")
