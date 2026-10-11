"""Settings: .env loading, which business we talk to, where tokens and runs live."""
from __future__ import annotations

import os
import ssl
from dataclasses import dataclass
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = REPO_DIR / ".env"
SECRETS_DIR = REPO_DIR / ".secrets"
RUNS_DIR = REPO_DIR / "runs"
CATALOG_DIR = REPO_DIR / "catalog"

SEAT_APP = "storefront"


@dataclass(frozen=True)
class Business:
    key: str          # "in" | "us"
    name: str
    base_url: str


_BUSINESSES = {
    "in": ("AS_URL_IN", "https://agentswitch.theschoolofai.in", "Suryodaya Precision Works"),
    "us": ("AS_URL_US", "https://class.agentswitch.theschoolofai.in", "Keystone Precision Works LLC"),
}


def _parse_value(v: str) -> str:
    v = v.strip()
    if v[:1] in ("'", '"'):
        end = v.find(v[0], 1)
        return v[1:end] if end > 0 else v[1:]
    return v.split(" #", 1)[0].strip()


def load_env(path: Path = ENV_PATH) -> dict[str, str]:
    """The repo's .env, overridden by the real environment."""
    env: dict[str, str] = {}
    if path.exists():
        for raw in path.read_text(encoding="utf-8-sig").splitlines():
            line = raw.strip()
            if line.startswith("export "):
                line = line[len("export "):]
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = _parse_value(v)
    env.update(os.environ)
    return env


def ssl_context() -> ssl.SSLContext:
    """TLS context for every call to the platform.

    Python on Windows verifies against the system certificate store, which on
    some machines rejects AgentSwitch's Let's Encrypt chain as expired. The
    certifi bundle (pulled in by google-genai) accepts it, so prefer that.
    """
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


INSTANCE_KEYS = {"suryodaya": "in", "keystone": "us"}


def platform_instance() -> str | None:
    """'in'/'us' when running under the official harness (AGENTSWITCH_INSTANCE), else None."""
    return INSTANCE_KEYS.get((os.environ.get("AGENTSWITCH_INSTANCE") or "").lower())


def business(key: str | None = None, env: dict[str, str] | None = None) -> Business:
    """On the official harness run, AGENTSWITCH_BASE_URL is the instance for
    AGENTSWITCH_INSTANCE; locally the AS_URL_* settings (or defaults) apply."""
    env = env if env is not None else load_env()
    official = platform_instance()
    key = (key or official or env.get("AS_BIZ") or "in").lower()
    if key not in _BUSINESSES:
        raise ValueError(f"unknown business {key!r}: use 'in' (Suryodaya) or 'us' (Keystone)")
    url_var, default_url, name = _BUSINESSES[key]
    if official == key and os.environ.get("AGENTSWITCH_BASE_URL"):
        return Business(key, name, os.environ["AGENTSWITCH_BASE_URL"].rstrip("/"))
    return Business(key, name, (env.get(url_var) or default_url).rstrip("/"))
