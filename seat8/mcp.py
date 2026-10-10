"""JSON-RPC client for AgentSwitch's MCP endpoint, plus the few REST reads we need.

Transport only: no business logic. Every failure is an MCPError with a `code`
to branch on, because the platform answers tool failures with HTTP 200 and an
error envelope, so the HTTP status alone says nothing about success.

Platform codes (error.data.code):
    not_found, invalid_arguments, invalid_transition, tool_not_available
Codes assigned here, for failures that never reach an envelope:
    transient   network error, timeout, 429, 5xx, non-JSON body
    auth        401: token missing or expired (run `seat8 login` again)
    forbidden   403: outside this seat's apps
    unknown     an error with no data.code, or a result flagged isError
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any, Callable

from .config import ssl_context

PROTOCOL_VERSION = "2025-11-25"

NOT_FOUND = "not_found"
INVALID_ARGUMENTS = "invalid_arguments"
INVALID_TRANSITION = "invalid_transition"
TOOL_NOT_AVAILABLE = "tool_not_available"
TRANSIENT = "transient"
AUTH = "auth"
FORBIDDEN = "forbidden"
UNKNOWN = "unknown"


class MCPError(Exception):
    def __init__(self, message: str, code: str = UNKNOWN, errors: list | None = None,
                 raw: Any = None):
        super().__init__(message)
        self.code = code
        self.errors = errors or []
        self.raw = raw


CallHook = Callable[[dict], None]


class MCPClient:
    """One seat, one business. `on_call` receives a record of every request
    (name, arguments, outcome, timing) so a run can log all of them."""

    def __init__(self, base_url: str, token: str, timeout: float = 45,
                 on_call: CallHook | None = None, client_name: str = "team-08-storefront"):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self.on_call = on_call
        self.client_name = client_name
        self._next_id = 0
        self.server_info: dict | None = None
        self._ssl = ssl_context()

    # ── REST ────────────────────────────────────────────────────────────────
    def rest_get(self, path: str) -> Any:
        req = urllib.request.Request(self.base_url + path, headers=self._headers())
        try:
            raw = urllib.request.urlopen(req, timeout=self.timeout, context=self._ssl).read()
        except urllib.error.HTTPError as e:
            raise self._http_error(path, e) from None
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            raise MCPError(f"GET {path}: {e}", TRANSIENT) from None
        try:
            return json.loads(raw)
        except ValueError:
            raise MCPError(f"GET {path}: non-JSON body {raw[:200]!r}", TRANSIENT) from None

    # ── MCP ─────────────────────────────────────────────────────────────────
    def initialize(self) -> dict:
        result = self._rpc("initialize", {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": self.client_name, "version": "0.1"},
        })
        self.server_info = result
        self._notify("notifications/initialized")
        return result

    def list_tools(self) -> list[dict]:
        tools: list[dict] = []
        cursor = None
        for _ in range(50):
            result = self._rpc("tools/list", {"cursor": cursor} if cursor else {})
            tools += result.get("tools") or []
            cursor = result.get("nextCursor")
            if not cursor:
                break
        return tools

    def call(self, name: str, arguments: dict | None = None) -> Any:
        """Call one tool; return its structured result. Raises MCPError."""
        args = arguments or {}
        started = time.time()
        record = {"tool": name, "arguments": args, "started": started}
        try:
            result = self._rpc("tools/call", {"name": name, "arguments": args}, label=name)
            if result.get("isError"):
                raise MCPError(f"{name}: {_content_text(result)[:400]}", UNKNOWN, raw=result)
            value = result.get("structuredContent")
            if value is None:
                value = _parse_content(result)
            record.update(ok=True, result=value)
            return value
        except MCPError as e:
            record.update(ok=False, error_code=e.code, error=str(e), errors=e.errors)
            raise
        finally:
            record["ms"] = round((time.time() - started) * 1000)
            if self.on_call:
                self.on_call(record)

    # ── plumbing ────────────────────────────────────────────────────────────
    def _headers(self) -> dict:
        return {"Authorization": "Bearer " + self.token, "Content-Type": "application/json",
                "Accept": "application/json"}

    def _post(self, payload: dict, label: str) -> bytes:
        req = urllib.request.Request(self.base_url + "/api/mcp", method="POST",
                                     data=json.dumps(payload).encode(), headers=self._headers())
        try:
            return urllib.request.urlopen(req, timeout=self.timeout, context=self._ssl).read()
        except urllib.error.HTTPError as e:
            if e.code in (401, 403, 429) or e.code >= 500:
                raise self._http_error(label, e) from None
            return e.read()  # another 4xx may still carry a JSON-RPC envelope
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            raise MCPError(f"{label}: {e}", TRANSIENT) from None

    def _rpc(self, method: str, params: dict, label: str | None = None) -> dict:
        self._next_id += 1
        label = label or method
        raw = self._post({"jsonrpc": "2.0", "id": self._next_id, "method": method,
                          "params": params}, label)
        try:
            envelope = json.loads(raw)
        except ValueError:
            raise MCPError(f"{label}: non-JSON body {raw[:200]!r}", TRANSIENT) from None
        if envelope.get("error"):
            err = envelope["error"]
            data = err.get("data") or {}
            raise MCPError(f"{label}: {err.get('message', '')}"[:600],
                           data.get("code", UNKNOWN), data.get("errors"), raw=envelope)
        return envelope.get("result") or {}

    def _notify(self, method: str) -> None:
        try:
            self._post({"jsonrpc": "2.0", "method": method}, method)
        except MCPError:
            pass  # a notification has no reply to fail on

    @staticmethod
    def _http_error(label: str, e: urllib.error.HTTPError) -> MCPError:
        body = e.read()[:300]
        if e.code == 401:
            return MCPError(f"{label}: HTTP 401 (token expired? run `seat8 login`)", AUTH)
        if e.code == 403:
            return MCPError(f"{label}: HTTP 403 {body!r}", FORBIDDEN)
        if e.code == 404:
            return MCPError(f"{label}: HTTP 404 {body!r}", NOT_FOUND)
        if e.code == 429 or e.code >= 500:
            return MCPError(f"{label}: HTTP {e.code}", TRANSIENT)
        return MCPError(f"{label}: HTTP {e.code} {body!r}", UNKNOWN)


def _content_text(result: dict) -> str:
    return " ".join(c.get("text", "") for c in result.get("content") or [] if isinstance(c, dict))


def _parse_content(result: dict) -> Any:
    text = _content_text(result)
    try:
        return json.loads(text)
    except ValueError:
        return text
