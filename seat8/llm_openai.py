"""OpenAI-compatible model client: the platform's model on the official harness run.

On the AgentSwitch server the only model available is OpenAI-compatible
(OPENAI_BASE_URL, OPENAI_API_KEY, OPENAI_MODEL); the Gemini SDK does not work
there. This class has the same surface as `llm.Gemini` (generate_json,
generate_text, usage, on_call) plus `run_tools` for the function-calling
loop, so the agent does not care which one it holds. Locally it also runs
against any OpenAI-compatible endpoint (Groq, OpenRouter, ...).
"""
from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Callable

from .config import load_env


class LLMUnavailable(RuntimeError):
    pass


def _strip_fences(text: str) -> str:
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    return (m.group(1) if m else text).strip()


def _tool_schema(schema: Any) -> dict:
    if not isinstance(schema, dict):
        return {"type": "object", "properties": {}}
    s = {k: v for k, v in schema.items() if k != "$schema"}
    s.setdefault("type", "object")
    s.setdefault("properties", {})
    return s


class OpenAICompat:
    provider = "openai"

    def __init__(self, model: str | None = None, on_call: Callable[[dict], None] | None = None,
                 base_url: str | None = None, api_key: str | None = None):
        env = {**load_env(), **os.environ}
        key = api_key or env.get("OPENAI_API_KEY")
        url = base_url or env.get("OPENAI_BASE_URL")
        if not key:
            raise LLMUnavailable("OPENAI_API_KEY is not set")
        try:
            from openai import OpenAI
        except ImportError:
            raise LLMUnavailable("the openai package is not installed") from None
        self.client = OpenAI(api_key=key, base_url=url, max_retries=3, timeout=120)
        self.model = model or env.get("OPENAI_MODEL") or "agentswitch-default"
        self.on_call = on_call
        self.usage = {"calls": 0, "input_tokens": 0, "output_tokens": 0}

    def _chat(self, messages: list[dict], **kw) -> Any:
        started = time.time()
        try:
            resp = self.client.chat.completions.create(model=self.model, messages=messages, **kw)
        except Exception as e:  # the SDK raises several error types
            raise LLMUnavailable(f"{self.model}: {str(e)[:300]}") from None
        u = getattr(resp, "usage", None)
        self.usage["calls"] += 1
        self.usage["input_tokens"] += getattr(u, "prompt_tokens", 0) or 0
        self.usage["output_tokens"] += getattr(u, "completion_tokens", 0) or 0
        if self.on_call:
            msg = resp.choices[0].message if resp.choices else None
            self.on_call({"model": self.model, "provider": "openai", "ms": round((time.time() - started) * 1000),
                          "input_tokens": getattr(u, "prompt_tokens", None),
                          "output_tokens": getattr(u, "completion_tokens", None),
                          "prompt": [{"role": m.get("role"), "text": (m.get("content") or "")[:20000]}
                                     for m in messages if isinstance(m, dict)],
                          "response": getattr(msg, "content", None),
                          "function_calls": [{"name": tc.function.name, "args": tc.function.arguments}
                                             for tc in (getattr(msg, "tool_calls", None) or [])]})
        return resp

    def generate_json(self, system: str, prompt: str, schema: dict | None = None,
                      temperature: float = 0.0) -> Any:
        sys_msg = system + ("\nReturn ONLY a JSON object matching this JSON Schema:\n" + json.dumps(schema)
                            if schema else "\nReturn ONLY a JSON object.")
        messages = [{"role": "system", "content": sys_msg}, {"role": "user", "content": prompt}]
        try:
            resp = self._chat(messages, temperature=temperature, response_format={"type": "json_object"})
        except LLMUnavailable:  # some compatible servers reject response_format
            resp = self._chat(messages, temperature=temperature)
        text = resp.choices[0].message.content or ""
        try:
            return json.loads(_strip_fences(text))
        except ValueError:
            raise LLMUnavailable(f"model returned non-JSON: {text[:200]!r}") from None

    def generate_text(self, system: str, prompt: str, temperature: float = 0.2) -> str:
        resp = self._chat([{"role": "system", "content": system}, {"role": "user", "content": prompt}],
                          temperature=temperature)
        return (resp.choices[0].message.content or "").strip()

    def run_tools(self, system: str, question: str, tools: dict[str, dict],
                  executor: Callable[[str, dict], Any], max_steps: int = 10) -> tuple[str, list[dict], bool]:
        """Function calling with a repeat guard. Returns (answer, trace, stopped_at_budget)."""
        specs = [{"type": "function", "function": {
            "name": name.replace(".", "__"), "description": (t.get("description") or name)[:1000],
            "parameters": _tool_schema(t.get("inputSchema"))}} for name, t in tools.items()]
        messages: list[dict] = [{"role": "system", "content": system}, {"role": "user", "content": question}]
        trace: list[dict] = []
        seen: set[str] = set()
        for step in range(max_steps):
            resp = self._chat(messages, tools=specs, temperature=0)
            msg = resp.choices[0].message
            if not msg.tool_calls:
                return (msg.content or "").strip(), trace, False
            messages.append({"role": "assistant", "content": msg.content or "",
                             "tool_calls": [tc.model_dump() for tc in msg.tool_calls]})
            for tc in msg.tool_calls:
                tool = tc.function.name.replace("__", ".")
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except ValueError:
                    args = {}
                key = tool + json.dumps(args, sort_keys=True, default=str)
                if key in seen:
                    result = {"ok": False, "error_code": "repeated_call",
                              "error": "You already made this exact call; use its earlier result."}
                else:
                    seen.add(key)
                    try:
                        result = {"ok": True, "result": executor(tool, args)}
                    except Exception as e:  # report the failure to the model, keep going
                        result = {"ok": False, "error_code": getattr(e, "code", "error"), "error": str(e)[:500]}
                trace.append({"step": step, "tool": tool, "arguments": args, "ok": result["ok"],
                              "error_code": result.get("error_code")})
                messages.append({"role": "tool", "tool_call_id": tc.id,
                                 "content": json.dumps(result, default=str)[:30000]})
        return "I stopped after the step limit without a complete answer.", trace, True
