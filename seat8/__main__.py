"""Command line: `uv run python -m seat8 <command> [--biz in|us]`.

    login     prompt for the password, cache a bearer token
    whoami    /api/auth/me: roles and allowed apps
    probe     dump tools, schemas and agent tools to catalog/<biz>/
    call      call one MCP tool: call Order.list '{"limit": 5}'
"""
from __future__ import annotations

import argparse
import getpass
import json
import sys

from . import auth
from .config import business, load_env
from .mcp import MCPClient, MCPError


def client_for(biz_key: str | None, **kw) -> MCPClient:
    biz = business(biz_key)
    return MCPClient(biz.base_url, auth.load_token(biz), **kw)


def cmd_login(a) -> int:
    env = load_env()
    biz = business(a.biz, env)
    email = a.email or env.get("AS_EMAIL") or input("email: ")
    if a.from_env:
        password = env.get(f"AS_PASSWORD_{biz.key.upper()}")
        if not password:
            print(f"AS_PASSWORD_{biz.key.upper()} is not set", file=sys.stderr)
            return 2
    else:
        password = getpass.getpass(f"password for {email} on {biz.name}: ")
    password = password.strip()
    if not password:
        print("empty password", file=sys.stderr)
        return 2
    if any(ord(c) < 32 for c in password):
        # Ctrl+V into a hidden prompt on some Windows consoles types \x16, not the clipboard
        print("the password contains control characters: the paste did not work. "
              "Right-click to paste, type it, or use --from-env.", file=sys.stderr)
        return 2
    print(f"sending {len(password)} characters for {email}")
    token = auth.login(biz, email, password)
    auth.save_token(biz, email, token)
    print(f"logged in to {biz.name} as {email}; token cached in {auth.token_path(biz)}")
    return 0


def cmd_whoami(a) -> int:
    print(json.dumps(client_for(a.biz).rest_get("/api/auth/me"), indent=2))
    return 0


def cmd_probe(a) -> int:
    from .probe import run_probe
    biz = business(a.biz)
    report = run_probe(client_for(a.biz), biz)
    print(json.dumps(report, indent=2))
    return 0


def cmd_call(a) -> int:
    args = json.loads(a.arguments) if a.arguments else {}
    try:
        result = client_for(a.biz).call(a.tool, args)
    except MCPError as e:
        print(json.dumps({"error_code": e.code, "error": str(e), "errors": e.errors}, indent=2))
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    return 0


def cmd_ask(a) -> int:
    from datetime import date
    from .agent import run
    data = run(a.question, client_for(a.biz), biz_key=a.biz or "in", write=a.write,
               use_llm=not a.no_llm, today=date.fromisoformat(a.today) if a.today else None,
               run_id=a.run_id)
    print(data.get("answer") or "")
    print(f"\n[run {data['run_id']} · status {data['status']} · "
          f"{'WRITE' if a.write else 'dry run'} · runs/{data['run_id']}/]", file=sys.stderr)
    return 0 if data["status"] == "done" else 1


def main(argv: list[str] | None = None) -> int:
    # --biz is accepted before or after the command name
    biz_opt = argparse.ArgumentParser(add_help=False)
    biz_opt.add_argument("--biz", choices=["in", "us"], default=argparse.SUPPRESS,
                         help="in = Suryodaya (default), us = Keystone")
    p = argparse.ArgumentParser(prog="seat8", parents=[biz_opt])
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("login", parents=[biz_opt])
    s.add_argument("--email")
    s.add_argument("--from-env", action="store_true", help="read AS_PASSWORD_<BIZ> instead of prompting")
    s.set_defaults(fn=cmd_login)

    sub.add_parser("whoami", parents=[biz_opt]).set_defaults(fn=cmd_whoami)
    sub.add_parser("probe", parents=[biz_opt]).set_defaults(fn=cmd_probe)

    s = sub.add_parser("ask", parents=[biz_opt], help="ask the storefront agent")
    s.add_argument("question")
    s.add_argument("--write", action="store_true",
                   help="allow writes to this team's agent space (session, escalation, memory)")
    s.add_argument("--no-llm", action="store_true", help="keyword routing and template answer only")
    s.add_argument("--today", help="pin 'today' (YYYY-MM-DD) for age rules")
    s.add_argument("--run-id")
    s.set_defaults(fn=cmd_ask)

    s = sub.add_parser("call", parents=[biz_opt])
    s.add_argument("tool")
    s.add_argument("arguments", nargs="?")
    s.set_defaults(fn=cmd_call)

    a = p.parse_args(argv)
    a.biz = getattr(a, "biz", None)
    for stream in (sys.stdout, sys.stderr):  # Windows consoles default to cp1252 (no ₹)
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    try:
        return a.fn(a)
    except (RuntimeError, MCPError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
