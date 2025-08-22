import json
import os

DEFAULT_WEIGHTS = {"urge":0.35,"mood":0.20,"sleep":0.15,"isolation":0.15,"lang":0.15}

def get_weights():
    raw = os.getenv("RISK_MODEL_WEIGHTS")
    if not raw:
        return DEFAULT_WEIGHTS
    try:
        return json.loads(raw)
    except Exception:
        return DEFAULT_WEIGHTS

def score(urge:int, mood:int, sleep_hours:float, isolation:int, lang_signal:float=0.0):
    w = get_weights()
    mood_inv = (6 - mood) / 5.0
    sleep_deficit = max(0.0, (8 - sleep_hours) / 8.0)
    iso = min(max(isolation/5.0, 0.0), 1.0)
    composite = (
        (urge/5.0)*w["urge"] + 
        mood_inv*w["mood"] + 
        sleep_deficit*w["sleep"] + 
        iso*w["isolation"] + 
        lang_signal*w["lang"]
    )
    return round(composite, 3)

def explain(urge, mood, sleep_hours, isolation, lang_signal):
    return {
        "urge": urge,
        "mood_inverse": (6-mood)/5.0,
        "sleep_deficit": max(0.0, (8-sleep_hours)/8.0),
        "isolation_norm": min(max(isolation/5.0, 0.0), 1.0),
        "language_signal": lang_signal,
        "weights": get_weights()
    }
