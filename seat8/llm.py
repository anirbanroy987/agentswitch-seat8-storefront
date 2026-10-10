"""Gemini, through the google-genai SDK. The model comes from GEMINI_MODEL.

Two uses only:
  * `generate_json`: one-shot structured output (intent parsing, narration).
  * `ToolLoop`: function calling over a curated set of MCP tools, for
    questions outside the fixed plans.
Rate limits (429) and transient 5xx are retried with backoff; the free tier
hits them often.
"""
from __future__ import annotations

import json
import time
from typing import Any, Callable

from .config import load_env

_RETRYABLE = ("429", "RESOURCE_EXHAUSTED", "500", "503", "UNAVAILABLE", "DEADLINE_EXCEEDED")


class LLMUnavailable(RuntimeError):
    pass


class Gemini:
    def __init__(self, model: str | None = None, api_key: str | None = None,
                 max_retries: int = 5, on_call: Callable[[dict], None] | None = None):
        env = load_env()
        self.model = model or env.get("GEMINI_MODEL") or "gemini-3.1-flash-lite"
        key = api_key or env.get("GEMINI_API_KEY")
        if not key:
            raise LLMUnavailable("GEMINI_API_KEY is not set")
        from google import genai
        self._genai = genai
        self.client = genai.Client(api_key=key)
        self.max_retries = max_retries
        self.on_call = on_call
        self.usage = {"calls": 0, "input_tokens": 0, "output_tokens": 0}

    def _generate(self, contents, config) -> Any:
        delay = 2.0
        for attempt in range(self.max_retries + 1):
            started = time.time()
            try:
                resp = self.client.models.generate_content(
                    model=self.model, contents=contents, config=config)
                self._account(resp, started)
                return resp
            except Exception as e:  # the SDK raises several error types
                msg = str(e)
                if attempt < self.max_retries and any(s in msg for s in _RETRYABLE):
                    time.sleep(delay)
                    delay = min(delay * 2, 40)
                    continue
                raise LLMUnavailable(f"{self.model}: {msg[:300]}") from None

    def _account(self, resp, started: float) -> None:
        u = getattr(resp, "usage_metadata", None)
        self.usage["calls"] += 1
        self.usage["input_tokens"] += getattr(u, "prompt_token_count", 0) or 0
        self.usage["output_tokens"] += getattr(u, "candidates_token_count", 0) or 0
        if self.on_call:
            self.on_call({"model": self.model, "ms": round((time.time() - started) * 1000),
                          "input_tokens": getattr(u, "prompt_token_count", None),
                          "output_tokens": getattr(u, "candidates_token_count", None)})

    def generate_json(self, system: str, prompt: str, schema: dict | None = None,
                      temperature: float = 0.0) -> Any:
        types = self._genai.types
        config = types.GenerateContentConfig(
            system_instruction=system, temperature=temperature,
            response_mime_type="application/json",
            **({"response_json_schema": schema} if schema else {}))
        resp = self._generate(prompt, config)
        text = resp.text or ""
        try:
            return json.loads(text)
        except ValueError:
            raise LLMUnavailable(f"model returned non-JSON: {text[:200]!r}") from None

    def generate_text(self, system: str, prompt: str, temperature: float = 0.2) -> str:
        types = self._genai.types
        config = types.GenerateContentConfig(system_instruction=system, temperature=temperature)
        return (self._generate(prompt, config).text or "").strip()


# ── function calling ────────────────────────────────────────────────────────

_DROP_KEYS = {"$schema", "additionalProperties", "$id", "$defs", "definitions", "examples",
              "readOnly", "writeOnly", "default", "const", "pattern", "format"}


def to_gemini_schema(schema: Any) -> Any:
    """MCP tool input schemas are full JSON Schema; Gemini's function
    declarations accept a subset. Keep what it understands."""
    if isinstance(schema, list):
        return [to_gemini_schema(s) for s in schema]
    if not isinstance(schema, dict):
        return schema
    out: dict = {}
    for k, v in schema.items():
        if k in _DROP_KEYS:
            continue
        if k == "type" and isinstance(v, list):  # ["string","null"] -> "string", nullable
            non_null = [t for t in v if t != "null"]
            out["type"] = non_null[0] if non_null else "string"
            if "null" in v:
                out["nullable"] = True
            continue
        if k in ("anyOf", "oneOf"):
            non_null = [s for s in v if not (isinstance(s, dict) and s.get("type") == "null")]
            if len(non_null) == 1:
                out.update(to_gemini_schema(non_null[0]))
                continue
            out["anyOf"] = to_gemini_schema(non_null)
            continue
        if k == "properties":
            out[k] = {pk: to_gemini_schema(pv) for pk, pv in v.items()}
            continue
        out[k] = to_gemini_schema(v)
    if out.get("type") == "object" and "properties" not in out:
        out["properties"] = {}
    return out


class ToolLoop:
    """Gemini picks tools from `tools` (name -> MCP tool dict) and `executor`
    runs them. Every step is appended to `trace`."""

    def __init__(self, llm: Gemini, tools: dict[str, dict],
                 executor: Callable[[str, dict], Any], max_steps: int = 12):
        self.llm = llm
        self.tools = tools
        self.executor = executor
        self.max_steps = max_steps
        self.trace: list[dict] = []

    def _declarations(self):
        types = self.llm._genai.types
        decls = []
        for name, t in self.tools.items():
            decls.append(types.FunctionDeclaration(
                name=name.replace(".", "__"),  # Gemini names: [a-zA-Z0-9_-]
                description=(t.get("description") or name)[:1000],
                parameters_json_schema=to_gemini_schema(t.get("inputSchema") or {"type": "object"}),
            ))
        return [types.Tool(function_declarations=decls)]

    def run(self, system: str, question: str) -> str:
        types = self.llm._genai.types
        config = types.GenerateContentConfig(
            system_instruction=system, temperature=0.0, tools=self._declarations(),
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True))
        contents = [types.Content(role="user", parts=[types.Part(text=question)])]
        for step in range(self.max_steps):
            resp = self.llm._generate(contents, config)
            cand = resp.candidates[0].content if resp.candidates else None
            calls = [p.function_call for p in (cand.parts if cand and cand.parts else [])
                     if getattr(p, "function_call", None)]
            if not calls:
                return (resp.text or "").strip()
            contents.append(cand)
            parts = []
            for fc in calls:
                tool = fc.name.replace("__", ".")
                args = dict(fc.args or {})
                try:
                    result = {"ok": True, "result": self.executor(tool, args)}
                except Exception as e:  # report the failure to the model, keep going
                    result = {"ok": False, "error_code": getattr(e, "code", "error"),
                              "error": str(e)[:500]}
                self.trace.append({"step": step, "tool": tool, "arguments": args,
                                   "ok": result["ok"],
                                   "error_code": result.get("error_code")})
                parts.append(types.Part.from_function_response(
                    name=fc.name, response=_truncate(result)))
            contents.append(types.Content(role="user", parts=parts))
        return "I stopped after the step limit without a complete answer."


def _truncate(result: dict, limit: int = 30000) -> dict:
    text = json.dumps(result, default=str)
    if len(text) <= limit:
        return json.loads(text)
    return {"ok": result.get("ok"), "truncated": True, "partial": text[:limit]}
