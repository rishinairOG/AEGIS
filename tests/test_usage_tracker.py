"""
Tests for UsageTracker — focus on the delta/reset accounting, which is the
part most likely to silently over- or under-count tokens.
"""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from usage_tracker import UsageTracker, _price_for, _modality_name


def _modality(name):
    return SimpleNamespace(name=name)


def _usage(prompt=None, response=None, prompt_total=0, response_total=0):
    """Build a fake usage_metadata. prompt/response are [(modality, count)]."""
    return SimpleNamespace(
        prompt_tokens_details=[SimpleNamespace(modality=_modality(m), token_count=c) for m, c in (prompt or [])],
        response_tokens_details=[SimpleNamespace(modality=_modality(m), token_count=c) for m, c in (response or [])],
        prompt_token_count=prompt_total,
        response_token_count=response_total,
    )


class TestModalityName:
    def test_enum_like(self):
        assert _modality_name(_modality("AUDIO")) == "AUDIO"

    def test_none(self):
        assert _modality_name(None) == "_UNSPECIFIED"


class TestCumulativeWithinSession:
    def test_deltas_not_double_counted(self):
        t = UsageTracker()
        # Live API reports cumulative: 100, then 250, then 400 audio-in tokens.
        t.record("models/gemini-2.5-flash-native-audio-preview-12-2025", _usage(prompt=[("AUDIO", 100)]))
        t.record("models/gemini-2.5-flash-native-audio-preview-12-2025", _usage(prompt=[("AUDIO", 250)]))
        t.record("models/gemini-2.5-flash-native-audio-preview-12-2025", _usage(prompt=[("AUDIO", 400)]))
        # Should total 400 (the latest cumulative), NOT 100+250+400=750.
        assert t.summary()["total_tokens"] == 400
        assert t.summary()["by_modality"]["AUDIO"] == 400


class TestSessionResetOnReconnect:
    def test_reset_adds_fresh(self):
        t = UsageTracker()
        m = "models/gemini-2.5-flash-native-audio-preview-12-2025"
        t.record(m, _usage(prompt=[("AUDIO", 500)]))   # session 1 reaches 500
        t.record(m, _usage(prompt=[("AUDIO", 120)]))   # reconnect -> new session starts at 120
        # 500 (session 1) + 120 (session 2 so far) = 620.
        assert t.summary()["total_tokens"] == 620


class TestPerResponseCalls:
    def test_each_call_added(self):
        t = UsageTracker()
        m = "models/gemini-3-pro-preview"
        # Regular generate_content: each response carries its own counts.
        t.record(m, _usage(prompt=[("TEXT", 30)], response=[("TEXT", 70)]), cumulative=False)
        t.record(m, _usage(prompt=[("TEXT", 40)], response=[("TEXT", 60)]), cumulative=False)
        # in: 30+40=70, out: 70+60=130 => 200 total (each treated as its own).
        assert t.summary()["total_tokens"] == 200


class TestCostEstimate:
    def test_audio_costs_more_than_text(self):
        t = UsageTracker()
        m = "models/gemini-2.5-flash-native-audio-preview-12-2025"
        # 1M audio output tokens @ $12/1M = $12.00
        t.record(m, _usage(response=[("AUDIO", 1_000_000)]))
        assert t.summary()["est_cost_usd"] == 12.0

    def test_price_lookup_falls_back(self):
        # Unknown model + unknown modality -> conservative default, not zero.
        assert _price_for("nonexistent-model", "out", "WEIRD") > 0


class TestFlatFallback:
    def test_no_modality_breakdown(self):
        t = UsageTracker()
        m = "models/gemini-2.5-flash-native-audio-preview-12-2025"
        t.record(m, _usage(prompt_total=200, response_total=50))
        s = t.summary()
        assert s["total_tokens"] == 250
        assert s["by_modality"]["_UNSPECIFIED"] == 250


class TestEmptyUsage:
    def test_none_and_empty_are_noops(self):
        t = UsageTracker()
        assert t.record("m", None) is False
        assert t.record("m", _usage()) is False
        assert t.summary()["total_tokens"] == 0
