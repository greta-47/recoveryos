import logging
import time
import json
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass
from functools import wraps
import contextvars
from prometheus_client import Counter, Histogram, Gauge, generate_latest
import re

correlation_id_var = contextvars.ContextVar("correlation_id", default=None)

logger = logging.getLogger("recoveryos")

REQUEST_COUNT = Counter(
    "recoveryos_requests_total",
    "Total requests",
    ["endpoint", "version", "env", "status"],
)
REQUEST_LATENCY = Histogram(
    "recoveryos_request_duration_seconds",
    "Request latency",
    ["endpoint", "version", "env"],
)
ERROR_RATE = Counter(
    "recoveryos_errors_total",
    "Total errors",
    ["endpoint", "version", "env", "error_type"],
)
ACTIVE_REQUESTS = Gauge(
    "recoveryos_active_requests", "Active requests", ["endpoint", "version", "env"]
)


@dataclass
class TraceSpan:
    span_id: str
    parent_id: Optional[str]
    operation_name: str
    start_time: float
    end_time: Optional[float] = None
    tags: Optional[Dict[str, Any]] = None
    logs: Optional[List[Dict[str, Any]]] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = {}
        if self.logs is None:
            self.logs = []

    def finish(self):
        self.end_time = time.time()

    def log(self, message: str, level: str = "info"):
        if self.logs is not None:
            self.logs.append(
                {"timestamp": time.time(), "level": level, "message": message}
            )

    def set_tag(self, key: str, value: Any):
        if self.tags is not None:
            self.tags[key] = value


class DistributedTracer:
    def __init__(self):
        self.spans: Dict[str, TraceSpan] = {}

    def start_span(
        self, operation_name: str, parent_id: Optional[str] = None
    ) -> TraceSpan:
        span_id = str(uuid.uuid4())
        span = TraceSpan(
            span_id=span_id,
            parent_id=parent_id,
            operation_name=operation_name,
            start_time=time.time(),
        )
        self.spans[span_id] = span
        return span

    def get_trace_context(self) -> Dict[str, str]:
        correlation_id = correlation_id_var.get()
        return {
            "correlation_id": correlation_id or str(uuid.uuid4()),
            "trace_id": str(uuid.uuid4()),
        }


@dataclass
class EnhancedMetrics:
    endpoint_name: str
    request_count: int = 0
    error_count: int = 0
    total_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    success_rate: float = 1.0
    last_request: Optional[str] = None
    latency_samples: Optional[List[float]] = None

    def __post_init__(self):
        if self.latency_samples is None:
            self.latency_samples = []


class PIIRedactor:
    """Enhanced PII redaction with more patterns"""

    PII_PATTERNS = [
        (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL_REDACTED]"),
        (r"\b\d{3}-\d{2}-\d{4}\b", "[SSN_REDACTED]"),
        (r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b", "[CARD_REDACTED]"),
        (r"\b\d{10,11}\b", "[PHONE_REDACTED]"),
        (
            r"\b\d{1,5}\s\w+\s(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd)\b",
            "[ADDRESS_REDACTED]",
        ),
        (r"\b(?:patient|client)[-_]?id[-_]?\d+\b", "[PATIENT_ID_REDACTED]"),
        (
            r"\b(?:medical|record|chart)[-_]?(?:number|num|id)[-_]?\d+\b",
            "[MEDICAL_RECORD_REDACTED]",
        ),
        (r"\b\d{3}-\d{3}-\d{4}\b", "[PHONE_REDACTED]"),
        (
            r"\b(?:dob|birth)[-_]?date[-_]?\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
            "[DOB_REDACTED]",
        ),
    ]

    @classmethod
    def redact_pii(cls, text: str) -> str:
        if not isinstance(text, str):
            return str(text)

        redacted = text
        for pattern, replacement in cls.PII_PATTERNS:
            redacted = re.sub(pattern, replacement, redacted, flags=re.IGNORECASE)
        return redacted

    @classmethod
    def redact_dict(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        redacted: Dict[str, Any] = {}
        for key, value in data.items():
            if isinstance(value, str):
                redacted[key] = cls.redact_pii(value)
            elif isinstance(value, dict):
                redacted[key] = cls.redact_dict(value)
            elif isinstance(value, list):
                redacted_list: List[Any] = []
                for item in value:
                    if isinstance(item, dict):
                        redacted_list.append(cls.redact_dict(item))
                    else:
                        redacted_list.append(cls.redact_pii(str(item)))
                redacted[key] = redacted_list
            else:
                redacted[key] = value
        return redacted


class EnhancedObservability:
    """Production-ready observability with tracing, metrics, and structured logging"""

    def __init__(self, version: str = "v1.0.0", environment: str = "staging"):
        self.metrics: Dict[str, EnhancedMetrics] = {}
        self.redactor = PIIRedactor()
        self.tracer = DistributedTracer()
        self.version = version
        self.environment = environment

    def track_request(
        self,
        endpoint_name: str,
        latency_ms: float,
        success: bool,
        request_data: Optional[Dict[str, Any]] = None,
        error_type: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ):
        """Enhanced request tracking with Prometheus metrics"""

        if endpoint_name not in self.metrics:
            self.metrics[endpoint_name] = EnhancedMetrics(endpoint_name=endpoint_name)

        metric = self.metrics[endpoint_name]
        metric.request_count += 1
        metric.total_latency_ms += latency_ms
        if metric.latency_samples is not None:
            metric.latency_samples.append(latency_ms)

            if len(metric.latency_samples) > 1000:
                metric.latency_samples = metric.latency_samples[-1000:]

            sorted_samples = sorted(metric.latency_samples)
            if sorted_samples:
                metric.p50_latency_ms = sorted_samples[int(len(sorted_samples) * 0.5)]
                metric.p95_latency_ms = sorted_samples[int(len(sorted_samples) * 0.95)]
                metric.p99_latency_ms = sorted_samples[int(len(sorted_samples) * 0.99)]

        if not success:
            metric.error_count += 1
            ERROR_RATE.labels(
                endpoint=endpoint_name,
                version=self.version,
                env=self.environment,
                error_type=error_type or "unknown",
            ).inc()

        metric.success_rate = (
            metric.request_count - metric.error_count
        ) / metric.request_count
        metric.last_request = datetime.utcnow().isoformat() + "Z"

        REQUEST_COUNT.labels(
            endpoint=endpoint_name,
            version=self.version,
            env=self.environment,
            status="success" if success else "error",
        ).inc()

        REQUEST_LATENCY.labels(
            endpoint=endpoint_name, version=self.version, env=self.environment
        ).observe(
            latency_ms / 1000.0
        )  # Convert to seconds

        safe_request_data = self.redactor.redact_dict(request_data or {})
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": "ERROR" if not success else "INFO",
            "service": "recoveryos",
            "version": self.version,
            "environment": self.environment,
            "endpoint": endpoint_name,
            "correlation_id": correlation_id or correlation_id_var.get(),
            "success": success,
            "latency_ms": round(latency_ms, 2),
            "request_data": safe_request_data,
            "error_type": error_type,
        }

        logger.info(json.dumps(log_entry))

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Enhanced metrics with percentiles and Prometheus format"""
        return {
            "endpoints": {
                name: {
                    "request_count": metric.request_count,
                    "error_count": metric.error_count,
                    "avg_latency_ms": round(
                        (
                            metric.total_latency_ms / metric.request_count
                            if metric.request_count > 0
                            else 0
                        ),
                        2,
                    ),
                    "p50_latency_ms": round(metric.p50_latency_ms, 2),
                    "p95_latency_ms": round(metric.p95_latency_ms, 2),
                    "p99_latency_ms": round(metric.p99_latency_ms, 2),
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
            "version": self.version,
            "environment": self.environment,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

    def get_prometheus_metrics(self) -> str:
        """Return Prometheus-formatted metrics"""
        return generate_latest().decode("utf-8")


enhanced_observability = EnhancedObservability()


def track_elite_endpoint_enhanced(endpoint_name: str):
    """Enhanced decorator with distributed tracing"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            correlation_id = str(uuid.uuid4())
            correlation_id_var.set(correlation_id)

            tracer = enhanced_observability.tracer
            span = tracer.start_span(f"endpoint.{endpoint_name}")
            span.set_tag("endpoint", endpoint_name)
            span.set_tag("correlation_id", correlation_id)

            start_time = time.time()
            success = True
            error_type = None
            request_data = {}

            ACTIVE_REQUESTS.labels(
                endpoint=endpoint_name,
                version=enhanced_observability.version,
                env=enhanced_observability.environment,
            ).inc()

            try:
                if args and isinstance(args[0], dict):
                    request_data = args[0]

                span.log("Processing request")
                result = func(*args, **kwargs)
                span.log("Request completed successfully")
                return result

            except Exception as e:
                success = False
                error_type = type(e).__name__
                span.log(f"Request failed: {str(e)}", "error")
                span.set_tag("error", True)
                span.set_tag("error_type", error_type)
                raise

            finally:
                latency_ms = (time.time() - start_time) * 1000
                span.set_tag("latency_ms", latency_ms)
                span.finish()

                enhanced_observability.track_request(
                    endpoint_name,
                    latency_ms,
                    success,
                    request_data,
                    error_type,
                    correlation_id,
                )

                ACTIVE_REQUESTS.labels(
                    endpoint=endpoint_name,
                    version=enhanced_observability.version,
                    env=enhanced_observability.environment,
                ).dec()

        return wrapper

    return decorator
