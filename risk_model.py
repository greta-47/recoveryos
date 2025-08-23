# services/risk_model.py (or risk_model.py if this lives at top level)
import json
import os
from typing import Dict

DEFAULT_WEIGHTS: Dict[str, float] = {
    "urge": 0.35,
    "mood": 0.20,
    "sleep": 0.15,
    "isolation": 0.15,
    "lang": 0.15,
}


def get_weights() -> Dict[str, float]:
    """
    Load weights from env var RISK_MODEL_WEIGHTS (JSON), falling back to defaults.
    Any missing keys are filled from DEFAULT_WEIGHTS; extra keys are ignored.
    """
    raw = os.getenv("RISK_MODEL_WEIGHTS")
    if not raw:
        return DEFAULT_WEIGHTS
    try:
        loaded = json.loads(raw)
        return {k: float(loaded.get(k, DEFAULT_WEIGHTS[k])) for k in DEFAULT_WEIGHTS}
    except Exception:
        return DEFAULT_WEIGHTS


def score(urge: int, mood: int, sleep_hours: float, isolation: int, lang_signal: float = 0.0) -> float:
    """
    Composite risk score in 0..1 using weighted normalized features.

    - urge: 1..5 (higher = higher risk)
    - mood: 1..5 (lower = higher risk; inverted)
    - sleep_hours: 0..24 (deficit vs 8h adds risk)
    - isolation: 0..5 (higher isolation = higher risk)
    - lang_signal: 0..1 (optional language-derived risk)
    """
    w = get_weights()
    mood_inv = (6 - mood) / 5.0
    sleep_deficit = max(0.0, (8 - float(sleep_hours)) / 8.0)
    iso_norm = min(max(float(isolation) / 5.0, 0.0), 1.0)

    composite = (
        (float(urge) / 5.0) * w["urge"]
        + mood_inv * w["mood"]
        + sleep_deficit * w["sleep"]
        + iso_norm * w["isolation"]
        + float(lang_signal) * w["lang"]
    )
    return round(composite, 3)


def explain(urge: int, mood: int, sleep_hours: float, isolation: int, lang_signal: float = 0.0) -> Dict[str, float]:
    """
    Return the normalized components that make up the score, plus weights.
    """
    return {
        "urge": float(urge),
        "mood_inverse": (6 - mood) / 5.0,
        "sleep_deficit": max(0.0, (8 - float(sleep_hours)) / 8.0),
        "isolation_norm": min(max(float(isolation) / 5.0, 0.0), 1.0),
        "language_signal": float(lang_signal),
        **{f"w_{k}": v for k, v in get_weights().items()},
    }

