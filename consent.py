# consent.py
from __future__ import annotations

from enum import Enum
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger("recoveryos")

# ----------------------
# Consent Types & Status
# ----------------------
class ConsentType(Enum):
    WEEKLY_BRIEFING = "weekly_briefing"
    DATA_ANALYTICS = "data_analytics"
    AI_RESEARCH = "ai_research"
    PEER_SUPPORT = "peer_support"
    FAMILY_UPDATES = "family_updates"


class ConsentStatus(Enum):
    GIVEN = "given"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"
    PENDING = "pending"


# ----------------------
# Utilities
# ----------------------
def _as_enum(value, enum_cls):
    """Coerce strings to Enum values (accepts value or NAME)."""
    if isinstance(value, enum_cls):
        return value
    try:
        return enum_cls(value)  # match by value
    except Exception:
        return enum_cls[str(value).upper()]  # match by NAME


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() + "Z" if isinstance(dt, datetime) else None


# ----------------------
# Consent Record Model (De-identified)
# ----------------------
class ConsentRecord:
    """
    De-identified consent record suitable for audit logs.
    Includes optional expiry (ttl_days) and renew/withdraw helpers.
    """

    def __init__(
        self,
        user_id: str,
        consent_type: ConsentType | str,
        status: ConsentStatus | str,
        *,
        given_at: Optional[datetime] = None,
        withdrawn_at: Optional[datetime] = None,
        scope: str = "recoveryos.app",
        version: str = "1.0",
        expires_at: Optional[datetime] = None,
        ttl_days: Optional[int] = 365,
    ):
        self.user_id = user_id
        self.consent_type = _as_enum(consent_type, ConsentType)
        self.status = _as_enum(status, ConsentStatus)
        self.given_at = given_at or datetime.utcnow()
        self.withdrawn_at = withdrawn_at
        self.scope = scope  # e.g., "RecoveryOS Clinical Dashboard"
        self.version = version  # For audit/versioning

        # Expiration handling
        if expires_at is not None:
            self.expires_at = expires_at
        elif ttl_days is not None:
            self.expires_at = self.given_at + timedelta(days=int(ttl_days))
        else:
            self.expires_at = None

    # ----------------------
    # State & Lifecycle
    # ----------------------
    def is_active(self, *, now: Optional[datetime] = None) -> bool:
        """True if consent is currently valid."""
        now = now or datetime.utcnow()

        if self.status in (ConsentStatus.WITHDRAWN, ConsentStatus.EXPIRED, ConsentStatus.PENDING):
            return False

        if self.expires_at and now >= self.expires_at:
            # Mark as expired (idempotent)
            self.status = ConsentStatus.EXPIRED
            logger.info(
                "Consent expired | User=%s | Type=%s | ExpiredAt=%s",
                self.user_id,
                self.consent_type.value,
                _iso(self.expires_at),
            )
            return False

        return True

    def withdraw(self, reason: Optional[str] = None) -> None:
        """Withdraw consent (immutable action)."""
        if self.status == ConsentStatus.WITHDRAWN:
            return
        self.status = ConsentStatus.WITHDRAWN
        self.withdrawn_at = datetime.utcnow()
        logger.info(
            "Consent withdrawn | User=%s | Type=%s | Reason=%s",
            self.user_id,
            self.consent_type.value,
            reason or "-",
        )

    def renew(self, *, ttl_days: int = 365, version: Optional[str] = None) -> None:
        """Renew consent from 'now' with a new expiry; sets status to GIVEN."""
        self.status = ConsentStatus.GIVEN
        self.given_at = datetime.utcnow()
        self.withdrawn_at = None
        self.expires_at = self.given_at + timedelta(days=int(ttl_days))
        if version:
            self.version = version
        logger.info(
            "Consent renewed | User=%s | Type=%s | NewExpiry=%s | Version=%s",
            self.user_id,
            self.consent_type.value,
            _iso(self.expires_at),
            self.version,
        )

    # ----------------------
    # Serialization
    # ----------------------
    def to_audit_log(self) -> Dict[str, Any]:
        """Minimal, de-identified audit payload."""
        return {
            "user_id": self.user_id,
            "consent_type": self.consent_type.value,
            "status": self.status.value,
            "given_at": _iso(self.given_at),
            "withdrawn_at": _iso(self.withdrawn_at),
            "expires_at": _iso(self.expires_at),
            "scope": self.scope,
            "version": self.version,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }


# ----------------------
# Core Consent Checks
# ----------------------
def can_use(consent: Optional[ConsentRecord], expected_type: ConsentType) -> bool:
    """
    Generic guard for any consent type.
    Returns False if no record, wrong type, withdrawn, pending, or expired.
    """
    if not consent:
        logger.warning("Consent check failed | Reason=no_record | Expected=%s", expected_type.value)
        return False

    if consent.consent_type != expected_type:
        logger.warning(
            "Consent check failed | Reason=wrong_type | Expected=%s | Got=%s",
            expected_type.value,
            consent.consent_type.value,
        )
        return False

    allowed = consent.is_active()
    logger.info(
        "Consent check | User=%s | Type=%s | Allowed=%s",
        consent.user_id,
        expected_type.value,
        allowed,
    )
    return allowed


def can_send_weekly(user_consent: Optional[ConsentRecord]) -> bool:
    """Specific helper for weekly briefings."""
    return can_use(user_consent, ConsentType.WEEKLY_BRIEFING)


def can_run_analytics(user_consent: Optional[ConsentRecord]) -> bool:
    """Specific helper for de-identified analytics."""
    return can_use(user_consent, ConsentType.DATA_ANALYTICS)


def can_use_ai_research(user_consent: Optional[ConsentRecord]) -> bool:
    """Specific helper for AI research participation."""
    return can_use(user_consent, ConsentType.AI_RESEARCH)


def can_enroll_peer_support(user_consent: Optional[ConsentRecord]) -> bool:
    """Specific helper for peer-support features."""
    return can_use(user_consent, ConsentType.PEER_SUPPORT)


def can_notify_family(user_consent: Optional[ConsentRecord]) -> bool:
    """Specific helper for family notifications/updates."""
    return can_use(user_consent, ConsentType.FAMILY_UPDATES)


# ----------------------
# Example Usage
# ----------------------
if __name__ == "__main__":
    # Simulate patient consent
    patient_consent = ConsentRecord(
        user_id="usr-abc123",
        consent_type=ConsentType.WEEKLY_BRIEFING,
        status=ConsentStatus.GIVEN,
        ttl_days=365,  # set to None for non-expiring
    )

    print("Audit log:", patient_consent.to_audit_log())

    print("Active now? ->", patient_consent.is_active())
    print("Can send weekly? ->", can_send_weekly(patient_consent))

    # Withdraw and check again
    patient_consent.withdraw(reason="User toggled off in settings")
    print("Active after withdraw? ->", patient_consent.is_active())
    print("Can send weekly after withdraw? ->", can_send_weekly(patient_consent))

