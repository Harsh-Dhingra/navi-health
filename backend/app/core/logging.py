"""Structured JSON logging with PHI redaction.

Application logs are a common, under-scrutinized PHI leak: a stray
`logger.info(f"processing {member_id}")` ends up in a log aggregator with
looser access controls than the primary database. This module forces
structured (field, not string-interpolated) logging and redacts any field
name that looks like it could hold PHI before it leaves the process.
"""

import logging
import sys

import structlog

REDACTED = "***REDACTED***"
SENSITIVE_KEYS = {
    "member_id",
    "group_number",
    "ssn",
    "dob",
    "date_of_birth",
    "password",
    "hashed_password",
    "access_token",
    "refresh_token",
    "token",
    "notes",
    "reason",
    "medication",
    "diagnosis",
    "email",
}


def _redact_sensitive(_logger, _method_name, event_dict):
    for key in list(event_dict.keys()):
        if key.lower() in SENSITIVE_KEYS:
            event_dict[key] = REDACTED
    return event_dict


def configure_logging(json_logs: bool = True) -> None:
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=logging.INFO)

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        _redact_sensitive,
    ]

    structlog.configure(
        processors=shared_processors
        + [structlog.processors.JSONRenderer() if json_logs else structlog.dev.ConsoleRenderer()],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str):
    return structlog.get_logger(name)
