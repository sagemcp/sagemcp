"""Prometheus metrics for SageMCP.

Cardinality rule: tenant_slug is NOT a Prometheus label (unbounded).
connector_type and tool_name are labels (bounded).
"""

import logging
import os
import time
from typing import Optional

logger = logging.getLogger(__name__)

# Lazy-load prometheus_client to allow graceful degradation
_prom = None


def _get_prom():
    """Lazily import prometheus_client."""
    global _prom
    if _prom is None:
        try:
            import prometheus_client
            _prom = prometheus_client
        except ImportError:
            logger.warning("prometheus_client not installed; metrics disabled")
            _prom = False
    return _prom if _prom else None


# --- Metric singletons (created on first access) ---

_metrics = {}


def _metric(name, metric_type, description, labelnames=()):
    """Get or create a Prometheus metric."""
    if name in _metrics:
        return _metrics[name]
    prom = _get_prom()
    if prom is None:
        _metrics[name] = None
        return None
    cls = getattr(prom, metric_type)
    m = cls(name, description, labelnames=labelnames)
    _metrics[name] = m
    return m


def http_request_duration():
    return _metric(
        "sagemcp_http_request_duration_seconds",
        "Histogram",
        "HTTP request duration in seconds",
        labelnames=["method", "path_template", "status_code"],
    )


def tool_calls_total():
    return _metric(
        "sagemcp_tool_calls_total",
        "Counter",
        "Total tool calls",
        labelnames=["connector_type", "status"],
    )


def tool_call_duration():
    return _metric(
        "sagemcp_tool_call_duration_seconds",
        "Histogram",
        "Tool call duration in seconds",
        labelnames=["connector_type", "tool_name", "status"],
    )


def active_sessions():
    return _metric(
        "sagemcp_active_sessions",
        "Gauge",
        "Number of active MCP sessions",
    )


def pool_size():
    return _metric(
        "sagemcp_pool_size",
        "Gauge",
        "Number of entries in the server pool",
    )


def pool_hits_total():
    return _metric(
        "sagemcp_pool_hits_total",
        "Counter",
        "Total server pool cache hits",
    )


def pool_misses_total():
    return _metric(
        "sagemcp_pool_misses_total",
        "Counter",
        "Total server pool cache misses",
    )


def external_processes():
    return _metric(
        "sagemcp_external_processes",
        "Gauge",
        "Number of active external MCP processes",
    )


def memory_usage_bytes():
    return _metric(
        "sagemcp_memory_usage_bytes",
        "Gauge",
        "Memory usage in bytes",
        labelnames=["component"],
    )


# --- Helper functions for recording metrics ---

def record_pool_hit():
    m = pool_hits_total()
    if m:
        m.inc()


def record_pool_miss():
    m = pool_misses_total()
    if m:
        m.inc()


def record_tool_call(connector_type: str, tool_name: str, status: str, duration: float):
    tc = tool_calls_total()
    if tc:
        tc.labels(connector_type=connector_type, status=status).inc()
    tcd = tool_call_duration()
    if tcd:
        tcd.labels(connector_type=connector_type, tool_name=tool_name, status=status).observe(duration)


def set_active_sessions(count: int):
    m = active_sessions()
    if m:
        m.set(count)


def set_pool_size(count: int):
    m = pool_size()
    if m:
        m.set(count)


def set_external_processes(count: int):
    m = external_processes()
    if m:
        m.set(count)


def generate_metrics_text() -> Optional[str]:
    """Generate Prometheus metrics text output."""
    prom = _get_prom()
    if prom is None:
        return None
    return prom.generate_latest().decode("utf-8")
