"""Small LLM wrapper with a content-addressed disk cache.

Backends
  claude_cli  the local Claude Code CLI (`claude -p`), works on a Max plan with no API key
  anthropic   Anthropic Messages API (needs ANTHROPIC_API_KEY), supports temperature
  openai      OpenAI Chat Completions (needs OPENAI_API_KEY), supports temperature

Every call is cached under cache_dir/<sha256>.json, keyed on backend, model,
system, user and a tag (sample and attempt index). Re-running the experiment
replays cached outputs exactly, so analysis is bit-for-bit reproducible even
though sampling itself is not seeded.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

API_IDS = {  # aliases used by the API backends
    "haiku": "claude-haiku-5-5", "sonnet": "claude-sonnet-5-5", "opus": "claude-opus-5-5",
}


def _claude_exe() -> str:
    for c in (os.environ.get("CLAUDE_EXE"), os.environ.get("CLAUDE_CODE_EXECPATH"),
              shutil.which("claude.exe"), shutil.which("claude")):
        if c and Path(c).exists():
            return c
    raise RuntimeError("Claude Code CLI not found; set CLAUDE_EXE")


class LLM:
    def __init__(self, backend: str, cache_dir: Path, temperature: float | None = None):
        self.backend, self.temperature = backend, temperature
        self.cache = Path(cache_dir)
        self.cache.mkdir(parents=True, exist_ok=True)
        self.exe = None  # found on the first uncached call, so replaying the cache needs no CLI
        self.cwd = self.cache.parent / "_cli_cwd"   # empty dir: no project files or CLAUDE.md

    def __call__(self, model: str, system: str, user: str, tag: str = "") -> dict:
        key = hashlib.sha256(json.dumps([self.backend, model, self.temperature, system, user, tag]).encode()).hexdigest()
        f = self.cache / f"{key}.json"
        if f.exists():
            out = json.loads(f.read_text(encoding="utf-8"))
            out["cached"] = True
            return out
        last = None
        for attempt in range(4):
            try:
                t0 = time.time()
                out = getattr(self, "_" + self.backend)(model, system, user)
                out.update(model=model, secs=round(time.time() - t0, 2), cached=False)
                tmp = f.with_suffix(".tmp")
                tmp.write_text(json.dumps(out), encoding="utf-8")
                tmp.replace(f)
                return out
            except Exception as e:  # infrastructure failure: back off and retry
                last = e
                time.sleep(5 * (attempt + 1))
        raise RuntimeError(f"LLM call failed after retries: {last}")

    def _claude_cli(self, model, system, user):
        self.exe = self.exe or _claude_exe()
        self.cwd.mkdir(exist_ok=True)
        cmd = [self.exe, "-p", "--model", model, "--output-format", "json", "--tools", "",
               "--no-session-persistence", "--strict-mcp-config", "--setting-sources", "",
               "--system-prompt", system]
        p = subprocess.run(cmd, input=user, capture_output=True, text=True, encoding="utf-8",
                           cwd=self.cwd, timeout=600)
        d = json.loads(p.stdout)
        if p.returncode != 0 or d.get("is_error"):
            raise RuntimeError(f"claude rc={p.returncode}: {str(d.get('result'))[:200]}")
        u = d.get("usage", {})
        return {"text": d["result"], "resolved_model": next(iter(d.get("modelUsage", {})), model),
                "in_tokens": u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0)
                + u.get("cache_read_input_tokens", 0),
                "out_tokens": u.get("output_tokens", 0)}

    def _anthropic(self, model, system, user):
        import anthropic
        kw = {"temperature": self.temperature} if self.temperature is not None else {}
        r = anthropic.Anthropic().messages.create(
            model=API_IDS.get(model, model), max_tokens=4000, system=system,
            messages=[{"role": "user", "content": user}], **kw)
        return {"text": "".join(b.text for b in r.content if b.type == "text"), "resolved_model": r.model,
                "in_tokens": r.usage.input_tokens, "out_tokens": r.usage.output_tokens}

    def _openai(self, model, system, user):
        from openai import OpenAI
        kw = {"temperature": self.temperature} if self.temperature is not None else {}
        r = OpenAI().chat.completions.create(
            model=model, messages=[{"role": "system", "content": system}, {"role": "user", "content": user}], **kw)
        return {"text": r.choices[0].message.content, "resolved_model": r.model,
                "in_tokens": r.usage.prompt_tokens, "out_tokens": r.usage.completion_tokens}
