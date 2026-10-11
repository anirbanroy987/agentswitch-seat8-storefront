"""Login and the cached bearer token.

The password is typed at a prompt (or read from AS_PASSWORD_<BIZ> with
--from-env) and sent once to /api/auth/login. Only the returned token is
kept, in .secrets/token_<biz>.json, which is gitignored.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

from .config import SECRETS_DIR, Business, ssl_context


def login(biz: Business, email: str, password: str, timeout: float = 30) -> str:
    req = urllib.request.Request(
        biz.base_url + "/api/auth/login", method="POST",
        data=json.dumps({"email": email, "password": password}).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        raw = urllib.request.urlopen(req, timeout=timeout, context=ssl_context()).read()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"login failed: HTTP {e.code} {e.read()[:200]!r}") from None
    except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
        raise RuntimeError(f"login failed: {biz.base_url} unreachable ({e})") from None
    token = json.loads(raw).get("token")
    if not token:
        raise RuntimeError("login response had no token")
    return token


def token_path(biz: Business):
    return SECRETS_DIR / f"token_{biz.key}.json"


def save_token(biz: Business, email: str, token: str) -> None:
    SECRETS_DIR.mkdir(exist_ok=True)
    token_path(biz).write_text(json.dumps({
        "email": email, "base_url": biz.base_url, "token": token,
        "obtained_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }, indent=2), encoding="utf-8")


def load_token(biz: Business) -> str:
    """AGENTSWITCH_TOKEN on the official harness run (for AGENTSWITCH_INSTANCE);
    otherwise the token cached by `seat8 login`."""
    import os
    from .config import platform_instance
    if os.environ.get("AGENTSWITCH_TOKEN") and platform_instance() in (None, biz.key):
        return os.environ["AGENTSWITCH_TOKEN"]
    p = token_path(biz)
    if not p.exists():
        raise RuntimeError(f"no token for {biz.name}: run `uv run python -m seat8 login --biz {biz.key}`")
    return json.loads(p.read_text(encoding="utf-8"))["token"]
