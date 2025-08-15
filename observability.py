import logging
import time
import re
from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass
from functools import wraps

logger = logging.getLogger("recoveryos")


@dataclass
class EliteMetrics:
    endpoint_name: str
    request_count: int = 0
    error_count: int = 0
    total_latency_ms: float = 0.0
    avg_latency_ms: float = 0.0
    success_rate: float = 1.0
    last_request: Optional[str] = None


class PIIRedactor:
    """Redact PII from logs and responses"""

    PII_PATTERNS = [
        (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL_REDACTED]"),
        (r"\b\d{3}-\d{2}-\d{4}\b", "[SSN_REDACTED]"),
        (r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b", "[CARD_REDACTED]"),
        (r"\b\d{10,11}\b", "[PHONE_REDACTED]"),
        (
            r"\b\d{1,5}\s\w+\s(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd)\b",
            "[ADDRESS_REDACTED]",
        ),
    ]

    @classmethod
    def redact_pii(cls, text: str) -> str:
        """Redact PII from text"""
        if not isinstance(text, str):
            return str(text)

        redacted = text
        for pattern, replacement in cls.PII_PATTERNS:
            redacted = re.sub(pattern, replacement, redacted, flags=re.IGNORECASE)
        return redacted

    @classmethod
    def redact_dict(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively redact PII from dictionary"""
        if not isinstance(data, dict):
            return data

        redacted = {}
        for key, value in data.items():
            if isinstance(value, str):
                redacted[key] = cls.redact_pii(value)
            elif isinstance(value, dict):
                redacted[key] = cls.redact_dict(value)
            elif isinstance(value, list):
                redacted[key] = [
                    (
                        cls.redact_dict(item)
                        if isinstance(item, dict)
                        else cls.redact_pii(str(item))
                    )
                    for item in value
                ]
            else:
                redacted[key] = value
        return redacted


class EliteObservability:
    """Centralized observability for elite AI endpoints"""

    def __init__(self):
        self.metrics: Dict[str, EliteMetrics] = {}
        self.redactor = PIIRedactor()

    def track_request(
        self,
        endpoint_name: str,
        latency_ms: float,
        success: bool,
        request_data: Dict[str, Any] = None,
    ):
        """Track request metrics"""
        if endpoint_name not in self.metrics:
            self.metrics[endpoint_name] = EliteMetrics(endpoint_name=endpoint_name)

        metric = self.metrics[endpoint_name]
        metric.request_count += 1
        metric.total_latency_ms += latency_ms
        metric.avg_latency_ms = metric.total_latency_ms / metric.request_count

        if not success:
            metric.error_count += 1

        metric.success_rate = (
            metric.request_count - metric.error_count
        ) / metric.request_count
        metric.last_request = datetime.utcnow().isoformat() + "Z"

        safe_request_data = self.redactor.redact_dict(request_data or {})
        logger.info(
            f"Elite endpoint request | Endpoint={endpoint_name} | Success={success} | Latency={latency_ms:.2f}ms | Data={safe_request_data}"
        )

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary"""
        return {
            "endpoints": {
                name: {
                    "request_count": metric.request_count,
                    "error_count": metric.error_count,
                    "avg_latency_ms": round(metric.avg_latency_ms, 2),
                    "success_rate": round(metric.success_rate, 4),
                    "last_request": metric.last_request,
                }
                for name, metric in self.metrics.items()
            },
            "total_requests": sum(m.request_count for m in self.metrics.values()),
            "total_errors": sum(m.error_count for m in self.metrics.values()),
            "avg_success_rate": (
                sum(m.success_rate for m in self.metrics.values()) / len(self.metrics)
                if self.metrics
                else 1.0
            ),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }


elite_observability = EliteObservability()


def track_elite_endpoint(endpoint_name: str):
    """Decorator to track elite endpoint performance"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            request_data = {}

            try:
                if args and isinstance(args[0], dict):
                    request_data = args[0]

                result = func(*args, **kwargs)
                return result
            except Exception:
                success = False
                raise
            finally:
                latency_ms = (time.time() - start_time) * 1000
                elite_observability.track_request(
                    endpoint_name, latency_ms, success, request_data
                )

        return wrapper

    return decorator
