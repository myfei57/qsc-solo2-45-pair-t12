"""Shared helpers for the control service tests."""

import json
import os

from dredgeops.config import Config
from dredgeops.console.http import Request, Response

WEB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")


def build(config: Config):
    from dredgeops.app import build_services

    return build_services(config)


def call(console, method: str, path: str, body=None) -> Response:
    text = "" if body is None else json.dumps(body)
    return console.handle(Request.parse(method, path, text))


def call_raw(console, method: str, path: str, text: str) -> Response:
    """Send a body exactly as given, for malformed payload checks."""
    return console.handle(Request.parse(method, path, text))


def ok(console, method: str, path: str, body=None):
    response = call(console, method, path, body)
    assert response.status == 200, response.body
    return response.body


def refused(console, method: str, path: str, body=None) -> Response:
    response = call(console, method, path, body)
    assert response.status >= 400, response.body
    return response


def issue_confirmation(console, name: str, subject: str, ttl_ticks: int = 20) -> str:
    body = ok(
        console,
        "POST",
        "/api/confirmation",
        {"name": name, "subject": subject, "ttl_ticks": ttl_ticks},
    )
    return body["confirmation_id"]


def advance_clock(console, steps: int = 1) -> int:
    return ok(console, "POST", "/api/clock/advance", {"steps": steps})["tick"]
