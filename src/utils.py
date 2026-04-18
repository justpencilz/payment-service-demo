"""
Utility Helpers

Shared helpers used across the payment service — logging setup, date
formatting, retry logic, and cursor-based pagination. Keep this module
light; heavy business logic belongs in domain-specific modules.
"""

from __future__ import annotations

import functools
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, TypeVar

from flask import jsonify, request

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def setup_logging(level: Optional[str] = None) -> None:
    """Configure root logger with structured JSON-style output.

    In production, set LOG_FORMAT=json for machine-parseable logs.
    Falls back to a human-readable format for local development.
    """
    fmt = os.environ.get("LOG_FORMAT", "text")
    log_level = getattr(logging, (level or os.environ.get("LOG_LEVEL", "INFO")).upper(), logging.INFO)

    handlers: List[logging.Handler] = []

    if fmt == "json":
        # Minimal structured handler — production should use a proper
        # library like python-json-logger for full JSON output.
        formatter = logging.Formatter('{"ts":"%(asctime)s","level":"%(levelname)s","msg":"%(message)s"}')
    else:
        formatter = logging.Formatter("[%(asctime)s] %(levelname)s %(name)s — %(message)s")

    stream = logging.StreamHandler()
    stream.setFormatter(formatter)
    handlers.append(stream)

    logging.basicConfig(level=log_level, handlers=handlers, force=True)


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

def iso_now() -> str:
    """Return current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


def format_epoch(ts: float, fmt: str = "%Y-%m-%dT%H:%M:%SZ") -> str:
    """Convert a UNIX epoch timestamp to a formatted string."""
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime(fmt)


# ---------------------------------------------------------------------------
# Retry decorator
# ---------------------------------------------------------------------------

F = TypeVar("F", bound=Callable[..., Any])


def retry(max_attempts: int = 3, backoff_base: float = 2.0, retryable: Optional[Callable[[Exception], bool]] = None) -> Callable[[F], F]:
    """Retry *fn* up to *max_attempts* with exponential back-off.

    By default retries on IOError and ConnectionError. Pass a custom
    *retryable* callable to control which exceptions trigger a retry.
    """
    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            last_exc: Optional[Exception] = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except Exception as exc:
                    last_exc = exc
                    if retryable and not retryable(exc):
                        raise
                    if attempt == max_attempts:
                        raise
                    delay = backoff_base ** (attempt - 1)
                    logging.getLogger(fn.__module__).warning(
                        "Retry %d/%d for %s after %.1fs — %s",
                        attempt, max_attempts, fn.__qualname__, delay, exc,
                    )
                    time.sleep(delay)
            raise last_exc  # type: ignore
        return wrapper  # type: ignore
    return decorator


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------

def paginate(items: List[Any], per_page: int = 50, max_per_page: int = 200) -> Dict[str, Any]:
    """Build a cursor-based pagination response from *items*.

    Reads ``after`` from query params to skip already-returned items.
    Returns a dict with ``data``, ``has_more``, and ``next_cursor`` keys.
    """
    per_page = min(max(per_page, 1), max_per_page)
    after = request.args.get("after")

    if after:
        try:
            cursor_index = next(i for i, item in enumerate(items) if getattr(item, "id", None) == after)
            items = items[cursor_index + 1:]
        except StopIteration:
            pass  # invalid cursor — return from beginning

    page = items[:per_page]
    has_more = len(items) > per_page
    next_cursor = getattr(page[-1], "id", None) if has_more and page else None

    return {
        "data": page,
        "has_more": has_more,
        "next_cursor": next_cursor,
    }
