# briefing.py
from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from typing import Dict, Any, List
from datetime import datetime
import logging
import os

logger = logging.getLogger("recoveryos")

# ----------------------
# Optional consent hook (safe if consent.py is absent)
# ----------------------
try:
    from consent import ConsentRecord, ConsentType, ConsentStatus, can_send_weekly  # type: ignore

    _HAS_CONSENT = True
except Exception:
    _HAS_CONSENT = False
    from typing import Any

if not _HAS_CONSENT:

    class ConsentRecord:  # type: ignore[no-redef]
        def __init__(self, user_id: str, consent_type: str, status: str):
            self.user_id = user_id
            self.consent_type = consent_type
            self.status = status

    class ConsentType:  # type: ignore[no-redef]
        WEEKLY_BRIEFING = "weekly_briefing"

    class ConsentStatus:  # type: ignore[no-redef]
        GIVEN = "given"

    def can_send_weekly(user_consent: Any) -> bool:  # type: ignore[misc]
        return True


# ----------------------
# Mock Data Source (Replace with DB or API)
# ----------------------
def get_patient_trends_last_7d() -> List[Dict[str, Any]]:
    """
    De-identified, minimal dataset for weekly briefing.
    Replace with a real DB query, making sure fields are PHI-safe.
    """
    return [
        {
            "user_id": "usr-101",  # de-identified ID
            "name_display": "Patient J",  # pseudonym only
            "recovery_days": 54,
            "trend": {
                "mood_change": "+0.8",
                "urge_avg": 2.7,
                "sleep_improvement": True,
                "checkin_rate": "85%",
            },
            "risk_flags": {
                "rising_urge": False,
                "isolation_risk": True,
                "engagement_drop": False,
            },
            "ai_insight": "Improved sleep correlates with lower urge scores.",
        },
        {
            "user_id": "usr-102",
            "name_display": "Patient M",
            "recovery_days": 21,
            "trend": {
                "mood_change": "-1.2",
                "urge_avg": 4.1,
                "sleep_improvement": False,
                "checkin_rate": "40%",
            },
            "risk_flags": {
                "rising_urge": True,
                "isolation_risk": False,
                "engagement_drop": True,
            },
            "ai_insight": "Urge scores rising for 4 days. Last check-in 3 days ago.",
        },
    ]


# ----------------------
# Minimal notifier (replace with SendGrid/SES, Slack, etc.)
# ----------------------
def send_email_or_notification(subject: str, body: str, recipients: List[str]) -> None:
    """
    Replace this with a real email/SMS/push integration.
    This function must NOT include PHI. Keep content de-identified.
    """
    logger.info(f"📬 Simulated send | To: {recipients} | Subject: {subject}")
    logger.debug(f"Body: {body}")


# ----------------------
# Helpers
# ----------------------
def _pct_int(s: str) -> int:
    try:
        return int(float(s.strip("%")))
    except Exception:
        return 0


def _safe_avg_checkin_rate(trends: List[Dict[str, Any]]) -> str:
    if not trends:
        return "0%"
    vals = [_pct_int(p["trend"].get("checkin_rate", "0%")) for p in trends]
    return f"{int(sum(vals) / max(1, len(vals)))}%"


def _filter_by_consent(trends: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    If consent module exists, filter out patients who haven't consented to weekly briefings.
    In production, you’d fetch actual consent records from your DB.
    """
    if not _HAS_CONSENT:
        return trends

    # Example stub: everyone has a "given" consent unless you wire real data
    filtered: List[Dict[str, Any]] = []
    for p in trends:
        # Build a fake consent record for the demo; swap with your DB record
        cr = ConsentRecord(
            user_id=p["user_id"],
            consent_type=ConsentType.WEEKLY_BRIEFING,
            status=ConsentStatus.GIVEN,
        )
        if can_send_weekly(cr):
            filtered.append(p)
        else:
            logger.info(
                "Excluded from weekly briefing (no consent) | User=%s", p["user_id"]
            )
    return filtered


# ----------------------
# Router
# ----------------------
router = APIRouter(prefix="/briefings", tags=["briefings"])


# ----------------------
# POST /briefings/weekly:run  (async send)
# ----------------------
@router.post("/weekly:run")
def run_weekly_briefing(background_tasks: BackgroundTasks):
    """
    Generate and send a weekly clinical briefing to the care team.
    Runs asynchronously via BackgroundTasks to avoid request timeout.
    All content is de-identified and PHI-free by design.
    """
    logger.info("Weekly briefing triggered")
    try:
        raw = get_patient_trends_last_7d()
        trends = _filter_by_consent(raw)

        # Prioritization
        at_risk = [
            p
            for p in trends
            if p["risk_flags"].get("rising_urge")
            or p["risk_flags"].get("engagement_drop")
        ]
        improved = [
            p
            for p in trends
            if (p["risk_flags"].get("rising_urge") is False)
            and (
                str(p["trend"].get("mood_change", "0")).replace("+", "")
                not in {"", "0"}
            )
            and (float(str(p["trend"]["mood_change"]).replace("+", "")) >= 0.5)
        ]

        briefing: Dict[str, Any] = {
            "report_date": datetime.utcnow().date().isoformat(),
            "period": "last_7_days",
            "summary": {
                "total_patients_tracked": len(trends),
                "at_risk_count": len(at_risk),
                "improved_count": len(improved),
                "avg_checkin_rate": _safe_avg_checkin_rate(trends),
            },
            "at_risk_patients": at_risk,
            "patients_showing_improvement": improved,
            "team_insights": [
                "Sleep quality strongly correlates with urge reduction.",
                "Patients with <50% check-in rate are more likely to show rising urges.",
                "Consider a short group session on sleep hygiene.",
            ],
            "recommended_actions": [
                "Follow up with at-risk patients within 24h.",
                "Acknowledge progress with improving patients.",
                "Review isolation risk protocols.",
            ],
        }

        # Build de-identified message body
        body = f"""
Weekly RecoveryOS Briefing ({briefing['period']})

📊 Summary:
- Tracked: {briefing['summary']['total_patients_tracked']} patients
- At Risk: {briefing['summary']['at_risk_count']}
- Showing Improvement: {briefing['summary']['improved_count']}
- Avg Engagement: {briefing['summary']['avg_checkin_rate']}

🚨 At-Risk Patients:
{chr(10).join([f"• {p['name_display']} (Urge: {p['trend']['urge_avg']}) – {p['ai_insight']}" for p in at_risk]) or "• None in the last 7 days"}

📈 Improvement Highlights:
{chr(10).join([f"• {p['name_display']} Mood ↑{p['trend']['mood_change']} – {p['ai_insight']}" for p in improved]) or "• No significant improvements flagged"}

💡 Team Insights:
{chr(10).join([f"• {insight}" for insight in briefing['team_insights']])}

✅ Recommended Actions:
{chr(10).join([f"• {action}" for action in briefing['recommended_actions']])}

This briefing is de-identified and for clinical use only.
        """.strip()

        recipients = os.getenv(
            "BRIEFINGS_RECIPIENTS", "clinical-team@recoveryos.app"
        ).split(",")
        subject = f"RecoveryOS Weekly Briefing – {briefing['report_date']}"

        # Queue async send
        background_tasks.add_task(
            send_email_or_notification,
            subject=subject,
            body=body,
            recipients=recipients,
        )

        logger.info("Weekly briefing generated and queued")
        return {
            "ok": True,
            "status": "briefing queued",
            "report_date": briefing["report_date"],
        }

    except Exception as e:
        logger.error(f"Weekly briefing failed | Error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Briefing generation failed",
        )


# ----------------------
# GET /briefings/weekly:preview  (no send)
# ----------------------
@router.get("/weekly:preview")
def preview_weekly_briefing():
    """
    Preview the briefing content without sending.
    Useful for testing or clinician review.
    """
    trends = _filter_by_consent(get_patient_trends_last_7d())
    at_risk = [
        p
        for p in trends
        if p["risk_flags"].get("rising_urge") or p["risk_flags"].get("engagement_drop")
    ]
    improved = [
        p
        for p in trends
        if (p["risk_flags"].get("rising_urge") is False)
        and (float(str(p["trend"].get("mood_change", "0")).replace("+", "")) >= 0.5)
    ]

    return {
        "preview": True,
        "report_date": datetime.utcnow().date().isoformat(),
        "patient_count": len(trends),
        "at_risk_count": len(at_risk),
        "improved_count": len(improved),
        "avg_checkin_rate": _safe_avg_checkin_rate(trends),
        "sample_at_risk": at_risk[:1],
        "sample_improved": improved[:1],
    }
