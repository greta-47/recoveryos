# alerts.py
import os
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

logger = logging.getLogger("recoveryos")

# --- Config ---
SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK", "").strip()  # Incoming Webhook URL
RISK_HIGH_THRESHOLD = float(os.getenv("RISK_HIGH_THRESHOLD", "7.0"))
ALERT_THROTTLE_MINUTES = int(os.getenv("ALERT_THROTTLE_MINUTES", "30"))  # per user_id

# In-memory throttle map (simple, process-local)
_last_sent_at: dict[str, datetime] = {}


def _risk_level(score: float) -> str:
    if score >= 9:
        return "Severe"
    if score >= 7:
        return "High"
    if score >= 4:
        return "Moderate"
    return "Low"


def _sanitize_user(user_id: str) -> str:
    # Enforce de-identification in Slack: no emails/phones/real names
    uid = (user_id or "anon").strip()
    return uid if uid.startswith("anon-") else f"anon-{uid[-6:]}"


def _build_blocks(
    user_id: str,
    risk_score: float,
    factors: List[Dict],
    suggested_action: str,
) -> List[Dict]:
    top = None
    try:
        top = max(factors or [], key=lambda x: float(x.get("impact", 0)))
    except Exception:
        top = None

    key_factors_lines = []
    for f in (factors or [])[:3]:
        name = str(f.get("name", "Factor")).strip()
        explanation = str(f.get("explanation", "")).strip()
        key_factors_lines.append(f"• *{name}*: {explanation}")

    key_factors_text = "\n".join(key_factors_lines) or "No key factors available."

    level = _risk_level(risk_score)
    uid = _sanitize_user(user_id)

    return [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "High Risk Alert", "emoji": True},
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"🚨 *{level}* — Patient `{uid}`",
            },
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"*Score:* {risk_score:.1f}/10"
                    + (
                        f" | *Top factor:* {top.get('name')}"
                        if top and top.get("name")
                        else ""
                    ),
                }
            ],
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Suggested action:* {suggested_action}",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Key factors (top 3):*\n{key_factors_text}",
            },
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "⚠️ This is a *support signal*, not a diagnosis. Use clinical judgment. No PHI included.",
                }
            ],
        },
    ]


@retry(
    retry=retry_if_exception_type(httpx.RequestError),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
    stop=stop_after_attempt(3),
    reraise=True,
)
def _post_to_slack(webhook: str, payload: Dict) -> None:
    with httpx.Client(timeout=5.0) as client:
        r = client.post(webhook, json=payload)
        r.raise_for_status()


def send_clinician_alert(
    user_id: str,
    risk_score: float,
    factors: List[Dict],
    suggested_action: str,
    *,
    webhook: Optional[str] = None,
    throttle_minutes: Optional[int] = None,
) -> None:
    """
    Synchronous helper suitable for FastAPI BackgroundTasks.
    De-identified by design. Retries transient network errors.
    """
    webhook = (webhook or SLACK_WEBHOOK or "").strip()
    if not webhook:
        logger.warning("SLACK_WEBHOOK not set — skipping alert")
        return

    # Only send when risk high (configurable)
    if risk_score < RISK_HIGH_THRESHOLD:
        logger.info(
            "Risk below threshold — not alerting (score=%.2f < %.2f)",
            risk_score,
            RISK_HIGH_THRESHOLD,
        )
        return

    # Simple per-user throttle to avoid spam
    cooldown = timedelta(
        minutes=(
            throttle_minutes if throttle_minutes is not None else ALERT_THROTTLE_MINUTES
        )
    )
    now = datetime.utcnow()
    last = _last_sent_at.get(user_id)
    if last and (now - last) < cooldown:
        logger.info(
            "Throttled alert for user=%s (last sent %s)",
            user_id,
            last.isoformat() + "Z",
        )
        return

    blocks = _build_blocks(user_id, risk_score, factors, suggested_action)
    payload = {"blocks": blocks}

    try:
        _post_to_slack(webhook, payload)
        _last_sent_at[user_id] = now
        logger.info("High-risk alert sent | user=%s | score=%.2f", user_id, risk_score)
    except httpx.HTTPStatusError as e:
        logger.error(
            "Slack webhook HTTP error %s: %s",
            e.response.status_code,
            e.response.text[:300],
        )
    except httpx.RequestError as e:
        logger.error("Slack webhook network error: %s", str(e))
    except Exception as e:
        logger.error("Slack webhook unexpected error: %s", str(e))


# Convenience: use inside a FastAPI route
def queue_clinician_alert(
    background_tasks,
    *,
    user_id: str,
    risk_score: float,
    factors: List[Dict],
    suggested_action: str,
) -> None:
    background_tasks.add_task(
        send_clinician_alert,
        user_id=user_id,
        risk_score=risk_score,
        factors=factors,
        suggested_action=suggested_action,
    )


__all__ = ["send_clinician_alert", "queue_clinician_alert"]
