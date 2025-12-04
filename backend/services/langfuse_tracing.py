"""
Langfuse Tracing Integration

This module provides conditional Langfuse tracing for the OpenAI Agents SDK.
Tracing is controlled via the LANGFUSE_ENABLED environment variable.

Uses both:
- Native Langfuse SDK for parent spans with input/output
- OpenInference instrumentation for capturing agent tool calls
"""

import os
import base64
import logging

logger = logging.getLogger(__name__)

LANGFUSE_ENABLED = os.getenv("LANGFUSE_ENABLED", "false").lower() == "true"

_langfuse_client = None


def init_langfuse():
    """
    Initialize Langfuse tracing if enabled via environment variable.

    Required environment variables when enabled:
    - LANGFUSE_ENABLED: Set to "true" to enable tracing
    - LANGFUSE_PUBLIC_KEY: Your Langfuse public key
    - LANGFUSE_SECRET_KEY: Your Langfuse secret key
    - LANGFUSE_BASE_URL: Langfuse host URL (optional, defaults to US cloud)
    """
    global _langfuse_client

    if not LANGFUSE_ENABLED:
        return

    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    base_url = os.getenv("LANGFUSE_BASE_URL", "https://us.cloud.langfuse.com")

    # Initialize native Langfuse client
    from langfuse import Langfuse

    _langfuse_client = Langfuse(
        public_key=public_key,
        secret_key=secret_key,
        host=base_url
    )

    if not _langfuse_client.auth_check():
        logger.warning(f"Langfuse authentication failed for {base_url}. Check LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY.")
        _langfuse_client = None
        return

    # Set up OpenInference instrumentation to capture agent tool calls
    # Configure OTLP exporter to send to Langfuse
    auth = base64.b64encode(f"{public_key}:{secret_key}".encode()).decode()
    endpoint = f"{base_url}/api/public/otel/v1/traces"
    headers = {"Authorization": f"Basic {auth}"}

    from opentelemetry import trace
    from opentelemetry.sdk import trace as trace_sdk
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from openinference.instrumentation.openai_agents import OpenAIAgentsInstrumentor

    # Create and set global TracerProvider
    tracer_provider = trace_sdk.TracerProvider()
    tracer_provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, headers=headers))
    )
    trace.set_tracer_provider(tracer_provider)

    # Instrument OpenAI Agents SDK
    OpenAIAgentsInstrumentor().instrument(tracer_provider=tracer_provider)

    logger.info("Langfuse tracing enabled (native SDK + OpenInference)")


def get_langfuse_client():
    """Get the Langfuse client instance (or None if not enabled)"""
    return _langfuse_client
