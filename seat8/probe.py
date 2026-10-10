"""Discovery: who this seat is, what tools it has, and the shape of its data.

Writes catalog/<biz>/:
    me.json              /api/auth/me (roles, allowed_apps)
    server.json          the MCP initialize result
    tools.json           tools/list, full schemas
    tools_summary.md     tools grouped by entity, one line each
    agent_tools.json     /api/agent/tools
    schemas_all.json     /api/schemas (gitignored: large)
    schemas_seat.json    the entities this seat has tools for
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from .config import CATALOG_DIR, Business
from .mcp import MCPClient, MCPError


def _dump(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def entity_of(tool_name: str) -> str:
    return tool_name.split(".", 1)[0]


def summarise_tools(tools: list[dict]) -> str:
    by_entity: dict[str, list[dict]] = defaultdict(list)
    for t in tools:
        by_entity[entity_of(t["name"])].append(t)
    lines = [f"# Tools visible to this seat ({len(tools)} tools, {len(by_entity)} entities)", ""]
    for entity in sorted(by_entity):
        lines.append(f"## {entity}")
        for t in sorted(by_entity[entity], key=lambda t: t["name"]):
            props = sorted((t.get("inputSchema") or {}).get("properties", {}))
            desc = (t.get("description") or "").strip().splitlines()[0:1]
            lines.append(f"- `{t['name']}`({', '.join(props)}) {desc[0] if desc else ''}")
        lines.append("")
    return "\n".join(lines)


def _schema_list(schemas) -> list[dict]:
    if isinstance(schemas, dict):
        for key in ("entities", "schemas", "items", "data"):
            if isinstance(schemas.get(key), list):
                return schemas[key]
        return [dict(v, name=v.get("name", k)) if isinstance(v, dict) else {"name": k}
                for k, v in schemas.items()]
    return schemas if isinstance(schemas, list) else []


def run_probe(client: MCPClient, biz: Business) -> dict:
    out = CATALOG_DIR / biz.key
    out.mkdir(parents=True, exist_ok=True)
    report: dict = {"business": biz.name, "base_url": biz.base_url}

    me = client.rest_get("/api/auth/me")
    _dump(out / "me.json", me)
    report["me"] = {k: me.get(k) for k in ("email", "roles", "allowed_apps") if isinstance(me, dict)}

    _dump(out / "server.json", client.initialize())
    tools = client.list_tools()
    _dump(out / "tools.json", tools)
    (out / "tools_summary.md").write_text(summarise_tools(tools), encoding="utf-8")
    entities = sorted({entity_of(t["name"]) for t in tools})
    report["tools"] = len(tools)
    report["entities"] = entities

    try:
        _dump(out / "agent_tools.json", client.rest_get("/api/agent/tools"))
    except MCPError as e:
        report["agent_tools_error"] = str(e)

    try:
        schemas = client.rest_get("/api/schemas")
        _dump(out / "schemas_all.json", schemas)
        rows = _schema_list(schemas)
        seat = [s for s in rows if isinstance(s, dict) and (s.get("name") or s.get("entity")) in set(entities)]
        _dump(out / "schemas_seat.json", seat)
        report["schemas_total"] = len(rows)
        report["schemas_seat"] = len(seat)
    except MCPError as e:
        report["schemas_error"] = str(e)

    _dump(out / "probe_report.json", report)
    return report
