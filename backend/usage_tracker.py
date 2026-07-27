"""
Token-usage and cost tracking for ATLAS's Gemini calls.

Gemini reports usage via usage_metadata on both the Live API
(LiveServerMessage.usage_metadata) and regular generate_content
(GenerateContentResponse.usage_metadata). The Live API reports usage
*cumulatively within a session*, resets to 0 on reconnect, and regular
calls report per-response — so this tracker accumulates by DELTA with
reset detection, which is correct for all three cases:
  - cumulative-within-session: adds (new - previous)
  - session reset / reconnect (new < previous): adds new fresh
  - per-response: each call's own count is added

Prices are USD per 1M tokens, split by direction (input/output) and
modality (audio priced very differently from text). Update PRICING as
Google's rates change; unknown models/modalities fall back to a
conservative default so cost is never silently zero.
"""
import threading

# USD per 1,000,000 tokens.
_LIVE_AUDIO = {
    # gemini-2.5-flash native audio (Live API) — the current voice model.
    "in": {"TEXT": 0.50, "AUDIO": 3.00, "VIDEO": 3.00, "IMAGE": 3.00, "_default": 3.00},
    "out": {"TEXT": 2.00, "AUDIO": 12.00, "_default": 12.00},
}
_PRO = {
    # gemini-3-pro-preview (CAD agent) — approximate, refine when wired.
    "in": {"TEXT": 2.00, "IMAGE": 2.00, "_default": 2.00},
    "out": {"TEXT": 12.00, "_default": 12.00},
}
_DEFAULT_PRICING = {
    "in": {"_default": 3.00},
    "out": {"_default": 12.00},
}

PRICING = {
    "gemini-2.5-flash-native-audio-preview-12-2025": _LIVE_AUDIO,
    "gemini-3.1-flash-live-preview": _LIVE_AUDIO,
    "gemini-3-pro-preview": _PRO,
}


def _modality_name(mod):
    """Normalize a MediaModality enum / string to an uppercase name."""
    if mod is None:
        return "_UNSPECIFIED"
    for attr in ("name", "value"):
        v = getattr(mod, attr, None)
        if isinstance(v, str) and v:
            return v.upper()
    return str(mod).upper()


def _price_for(model, direction, modality):
    table = PRICING.get(model, _DEFAULT_PRICING).get(direction, _DEFAULT_PRICING[direction])
    return table.get(modality, table.get("_default", _DEFAULT_PRICING[direction]["_default"]))


class UsageTracker:
    """Thread-safe accumulator of token usage + estimated cost.

    record() is safe to call from the async audio loop on every message.
    summary() returns a plain dict suitable for a socket emit.
    """

    def __init__(self):
        self._lock = threading.Lock()
        # accumulated tokens keyed by (model, direction, modality)
        self._acc = {}
        # last cumulative value seen, for delta/reset detection, same key
        self._last = {}

    def _model_key(self, model):
        # Strip a leading "models/" so "models/gemini-..." matches PRICING keys.
        return model.split("/", 1)[1] if model and model.startswith("models/") else (model or "unknown")

    def record(self, model, usage_metadata, cumulative=True):
        """Fold one usage_metadata snapshot into the running totals.

        cumulative=True (Live API): usage_metadata reports session-cumulative
        counts, so accumulate by delta with reset detection. cumulative=False
        (regular generate_content): each response carries its own counts, so
        add them directly. The caller always knows which API it is, so this is
        unambiguous — auto-detecting the two is impossible when per-response
        counts happen to rise.

        Returns True if anything was recorded, False if usage_metadata was
        empty/None (so callers can skip emitting a no-op update).
        """
        if usage_metadata is None:
            return False
        model = self._model_key(model)

        # Prefer per-modality detail lists; fall back to the flat totals.
        prompt_details = getattr(usage_metadata, "prompt_tokens_details", None) or []
        response_details = getattr(usage_metadata, "response_tokens_details", None) or []

        buckets = []  # (direction, modality, cumulative_count)
        for d in prompt_details:
            buckets.append(("in", _modality_name(getattr(d, "modality", None)), getattr(d, "token_count", 0) or 0))
        for d in response_details:
            buckets.append(("out", _modality_name(getattr(d, "modality", None)), getattr(d, "token_count", 0) or 0))

        if not buckets:
            # No modality breakdown — use flat counts under _UNSPECIFIED.
            p = getattr(usage_metadata, "prompt_token_count", 0) or 0
            r = getattr(usage_metadata, "response_token_count", 0) or 0
            if p:
                buckets.append(("in", "_UNSPECIFIED", p))
            if r:
                buckets.append(("out", "_UNSPECIFIED", r))

        if not buckets:
            return False

        with self._lock:
            for direction, modality, cur in buckets:
                key = (model, direction, modality)
                if cumulative:
                    prev = self._last.get(key, 0)
                    delta = (cur - prev) if cur >= prev else cur  # reset-aware
                    self._last[key] = cur
                else:
                    delta = cur  # per-response: count is this call's own usage
                if delta:
                    self._acc[key] = self._acc.get(key, 0) + delta
        return True

    def summary(self):
        with self._lock:
            total_tokens = 0
            total_cost = 0.0
            by_model = {}
            by_modality = {}
            for (model, direction, modality), toks in self._acc.items():
                total_tokens += toks
                cost = toks / 1_000_000 * _price_for(model, direction, modality)
                total_cost += cost
                m = by_model.setdefault(model, {"tokens": 0, "cost": 0.0})
                m["tokens"] += toks
                m["cost"] += cost
                by_modality[modality] = by_modality.get(modality, 0) + toks
            return {
                "total_tokens": total_tokens,
                "est_cost_usd": round(total_cost, 4),
                "by_model": {k: {"tokens": v["tokens"], "cost": round(v["cost"], 4)} for k, v in by_model.items()},
                "by_modality": by_modality,
            }

    def reset(self):
        with self._lock:
            self._acc.clear()
            self._last.clear()
