"""
Structured logging configuration for the Agentic Workflow Framework.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog


def configure_logging(
    level: str = "INFO",
    format: str = "json",
    output: str = "stdout",
) -> None:
    """
    Configure structured logging for the framework.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        format: Output format ('json' or 'console').
        output: Output destination ('stdout' or file path).
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if format == "json":
        renderer: Any = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler: logging.Handler
    if output == "stdout":
        handler = logging.StreamHandler(sys.stdout)
    else:
        handler = logging.FileHandler(output)

    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(log_level)

    logging.getLogger("uvicorn").setLevel(log_level)
    logging.getLogger("fastapi").setLevel(log_level)


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger for the given module name."""
    return structlog.get_logger(name)
