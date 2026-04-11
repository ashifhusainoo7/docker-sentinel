from prometheus_client import Counter, Histogram, generate_latest, start_http_server

CRASHES_TOTAL = Counter(
    "sentinel_crashes_total",
    "Total container crashes detected",
    ["tenant_id", "container", "category"],
)

AGENT_LATENCY = Histogram(
    "sentinel_agent_latency_seconds",
    "Time spent in each agent",
    ["agent_name"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

RESTART_TOTAL = Counter(
    "sentinel_restarts_total",
    "Container restart attempts",
    ["tenant_id", "result"],
)

RESOLUTION_TYPE = Counter(
    "sentinel_resolution_type",
    "How crashes were resolved",
    ["type"],  # 'cache_hit' | 'llm_analysis' | 'auto_restart'
)

LLM_TOKENS = Counter(
    "sentinel_llm_tokens_total",
    "LLM tokens consumed",
    ["provider", "agent"],
)

CACHE_HIT = Counter(
    "sentinel_cache_hits_total",
    "Qdrant cache hits",
    ["tenant_id"],
)


def get_metrics() -> bytes:
    return generate_latest()


def start_metrics_server(port: int = 9091) -> None:
    """Start a standalone Prometheus metrics server (for worker process)."""
    start_http_server(port)
