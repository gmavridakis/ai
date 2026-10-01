#!/usr/bin/env python3
"""Shared pieces of the evaluation harness: case loading, transcript parsing, deterministic checks.

Imported by run.py, grade.py and report.py. No third-party dependencies; Python 3.10+.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVALS = ROOT / "evals"
CASES = EVALS / "cases"
SKILLS = ROOT / "skills"


# ----------------------------------------------------------------------------- cases

@dataclass
class Case:
    skill: str            # folder under evals/cases (a skill name, or "routing")
    id: int
    name: str
    prompt: str
    fixture: Path | None  # directory copied into the temp workspace
    git_init: bool
    expected_output: str
    checks: list[dict]    # deterministic, graded by code
    expectations: list[str]  # rubric lines, graded by the judge
    skill_under_test: str  # which SKILL.md the judge reads and --ref swaps

    @property
    def key(self) -> str:
        return f"{self.skill}/{self.name}"


def load_cases(skill_filter: str | None = None, case_filter: str | None = None) -> list[Case]:
    out: list[Case] = []
    for evals_json in sorted(CASES.glob("*/evals.json")):
        folder = evals_json.parent.name
        if skill_filter and folder != skill_filter:
            continue
        data = json.loads(evals_json.read_text(encoding="utf-8"))
        for ev in data["evals"]:
            if case_filter and ev["name"] != case_filter:
                continue
            fixture = evals_json.parent / ev["fixture"] if ev.get("fixture") else None
            if fixture and not fixture.is_dir():
                raise SystemExit(f"{evals_json}: fixture {fixture} does not exist")
            out.append(Case(
                skill=folder, id=int(ev["id"]), name=ev["name"], prompt=ev["prompt"],
                fixture=fixture, git_init=bool(ev.get("git_init", False)),
                expected_output=ev.get("expected_output", ""),
                checks=ev.get("checks", []), expectations=ev.get("expectations", []),
                skill_under_test=ev.get("skill_under_test", data.get("skill_name", folder)),
            ))
    return out


# ----------------------------------------------------------------------------- transcript

@dataclass
class ToolCall:
    name: str
    input: dict
    result: str = ""
    index: int = 0


@dataclass
class Transcript:
    tool_calls: list[ToolCall] = field(default_factory=list)
    assistant_text: list[str] = field(default_factory=list)   # every assistant text block, in order
    final_text: str = ""
    result: dict = field(default_factory=dict)                # the final 'result' event
    raw_events: int = 0

    def skills_fired(self) -> list[str]:
        return [tc.input.get("skill", "") for tc in self.tool_calls if tc.name == "Skill"]

    def all_text(self) -> str:
        """Everything in order: assistant text and tool calls, for ordered regex checks."""
        return "\n".join(self._ordered_lines())

    def _ordered_lines(self) -> list[str]:
        return self._lines

    def to_markdown(self, max_result_chars: int = 1500) -> str:
        lines = ["# Transcript", ""]
        for item in self._ordered:
            if item[0] == "text":
                lines += ["**Assistant:**", "", item[1], ""]
            else:
                tc: ToolCall = item[1]
                arg = json.dumps(tc.input, ensure_ascii=False)
                if len(arg) > 800:
                    arg = arg[:800] + " …"
                lines += [f"**Tool {tc.name}:** `{arg}`", ""]
                res = tc.result or ""
                if len(res) > max_result_chars:
                    res = res[:max_result_chars] + f"\n… [{len(tc.result) - max_result_chars} more chars]"
                if res:
                    lines += ["```", res, "```", ""]
        if not (self._ordered and self._ordered[-1][0] == "text" and self._ordered[-1][1].strip() == self.final_text.strip()):
            lines += ["**Final reply:**", "", self.final_text, ""]
        return "\n".join(lines)

    # filled by parse_stream_json
    _ordered: list = field(default_factory=list)
    _lines: list = field(default_factory=list)


def parse_stream_json(path: Path) -> Transcript:
    """Parse `claude -p --output-format stream-json --verbose` output (one JSON event per line)."""
    t = Transcript()
    pending: dict[str, ToolCall] = {}
    idx = 0
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        t.raw_events += 1
        typ = ev.get("type")
        if typ == "assistant":
            for block in ev.get("message", {}).get("content", []):
                if block.get("type") == "text" and block.get("text", "").strip():
                    t.assistant_text.append(block["text"])
                    t._ordered.append(("text", block["text"]))
                    t._lines.append(block["text"])
                elif block.get("type") == "tool_use":
                    idx += 1
                    tc = ToolCall(name=block.get("name", ""), input=block.get("input", {}) or {}, index=idx)
                    pending[block.get("id", f"_{idx}")] = tc
                    t.tool_calls.append(tc)
                    t._ordered.append(("tool", tc))
                    t._lines.append(f"[tool {tc.name}] {json.dumps(tc.input, ensure_ascii=False)}")
        elif typ == "user":
            for block in ev.get("message", {}).get("content", []):
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    tc = pending.get(block.get("tool_use_id"))
                    content = block.get("content")
                    if isinstance(content, list):
                        content = "\n".join(c.get("text", "") for c in content if isinstance(c, dict))
                    if tc is not None:
                        tc.result = str(content or "")
                        t._lines.append(f"[result {tc.name}] {tc.result[:2000]}")
        elif typ == "result":
            t.result = ev
            t.final_text = ev.get("result", "") or ""
    if not t.final_text and t.assistant_text:
        t.final_text = t.assistant_text[-1]
    return t


# ----------------------------------------------------------------------------- checks

def _rx(pattern: str) -> re.Pattern:
    return re.compile(pattern, re.I | re.M | re.S)


def run_checks(case: Case, t: Transcript, workspace: Path, fixture_hashes: dict[str, str]) -> list[dict]:
    """Grade the deterministic checks of a case. Each returns {text, passed, evidence}."""
    results = []
    for chk in case.checks:
        kind = chk["type"]
        text = chk.get("text") or _describe(chk)
        passed, evidence = False, ""
        try:
            if kind == "skill_fired":
                fired = t.skills_fired()
                passed = chk["skill"] in fired
                evidence = f"Skill tool calls: {fired or 'none'}"
            elif kind == "skill_not_fired":
                fired = t.skills_fired()
                passed = chk["skill"] not in fired
                evidence = f"Skill tool calls: {fired or 'none'}"
            elif kind == "final_regex":
                m = _rx(chk["pattern"]).search(t.final_text)
                passed, evidence = bool(m), (f"matched: {m.group(0)[:120]!r}" if m else "no match in final reply")
            elif kind == "transcript_regex":
                m = _rx(chk["pattern"]).search(t.all_text())
                passed, evidence = bool(m), (f"matched: {m.group(0)[:120]!r}" if m else "no match in transcript")
            elif kind == "must_not_regex":
                where = t.final_text if chk.get("where") == "final" else t.all_text()
                m = _rx(chk["pattern"]).search(where)
                passed, evidence = not m, (f"found forbidden: {m.group(0)[:120]!r}" if m else "not present")
            elif kind == "tool_called":
                pat = _rx(chk.get("pattern", ".")) if chk.get("pattern") else None
                hits = [tc for tc in t.tool_calls if tc.name == chk["tool"]
                        and (pat is None or pat.search(json.dumps(tc.input, ensure_ascii=False)))]
                passed = len(hits) >= int(chk.get("min", 1))
                evidence = f"{len(hits)} matching {chk['tool']} call(s)" + (f"; first: {json.dumps(hits[0].input, ensure_ascii=False)[:160]}" if hits else "")
            elif kind == "tool_not_called":
                pat = _rx(chk.get("pattern", ".")) if chk.get("pattern") else None
                hits = [tc for tc in t.tool_calls if tc.name == chk["tool"]
                        and (pat is None or pat.search(json.dumps(tc.input, ensure_ascii=False)))]
                passed = not hits
                evidence = f"{len(hits)} matching {chk['tool']} call(s)"
            elif kind == "order":
                lines = t._lines
                first = next((i for i, l in enumerate(lines) if _rx(chk["first"]).search(l)), None)
                then = next((i for i, l in enumerate(lines) if _rx(chk["then"]).search(l)), None)
                passed = first is not None and then is not None and first < then
                evidence = f"first at {first}, then at {then}"
            elif kind == "file_exists":
                p = workspace / chk["path"]
                passed = p.exists()
                evidence = f"{p.name} {'exists' if passed else 'missing'}"
            elif kind == "file_regex":
                p = workspace / chk["path"]
                if p.exists():
                    m = _rx(chk["pattern"]).search(p.read_text(encoding="utf-8", errors="replace"))
                    passed, evidence = bool(m), (f"matched: {m.group(0)[:120]!r}" if m else f"no match in {chk['path']}")
                else:
                    evidence = f"{chk['path']} missing"
            elif kind == "file_not_regex":
                p = workspace / chk["path"]
                if p.exists():
                    m = _rx(chk["pattern"]).search(p.read_text(encoding="utf-8", errors="replace"))
                    passed, evidence = not m, (f"found forbidden: {m.group(0)[:120]!r}" if m else "not present")
                else:
                    passed, evidence = True, f"{chk['path']} missing (nothing forbidden)"
            elif kind == "files_changed_only":
                allowed = [_rx(p) for p in chk["patterns"]]
                changed = changed_files(workspace, fixture_hashes)
                bad = [f for f in changed if not any(a.search(f) for a in allowed)]
                passed = not bad
                evidence = f"changed: {changed or 'none'}; outside allowed: {bad or 'none'}"
            elif kind == "final_max_lines":
                n = len([l for l in t.final_text.splitlines() if l.strip()])
                passed = n <= int(chk["max"])
                evidence = f"final reply has {n} non-empty lines (max {chk['max']})"
            elif kind == "read_uses_ranges":
                # every Read of a file longer than `min_lines` must carry offset or limit
                bad = []
                for tc in t.tool_calls:
                    if tc.name != "Read":
                        continue
                    fp = Path(tc.input.get("file_path", ""))
                    if not fp.is_absolute():
                        fp = workspace / fp
                    try:
                        n = sum(1 for _ in open(fp, encoding="utf-8", errors="replace"))
                    except OSError:
                        continue
                    if n > int(chk.get("min_lines", 200)) and not ("offset" in tc.input or "limit" in tc.input):
                        bad.append(f"{fp.name} ({n} lines)")
                passed = not bad
                evidence = f"whole-file reads over the limit: {bad or 'none'}"
            elif kind == "max_turns":
                n = int(t.result.get("num_turns", 0))
                passed = n <= int(chk["max"])
                evidence = f"{n} turns (max {chk['max']})"
            else:
                evidence = f"unknown check type {kind}"
        except Exception as e:  # a broken check must not crash the run
            evidence = f"check error: {e}"
        results.append({"text": text, "passed": bool(passed), "evidence": evidence, "kind": "check"})
    return results


def _describe(chk: dict) -> str:
    k = chk["type"]
    if k in ("skill_fired", "skill_not_fired"):
        return f"Skill tool {'fires' if k == 'skill_fired' else 'does not fire'} {chk['skill']}"
    if k in ("final_regex", "transcript_regex", "must_not_regex", "file_regex", "file_not_regex"):
        return f"{k}: {chk['pattern']}" + (f" in {chk['path']}" if 'path' in chk else "")
    if k in ("tool_called", "tool_not_called"):
        return f"{k}: {chk['tool']} {chk.get('pattern', '')}".strip()
    if k == "order":
        return f"'{chk['first']}' happens before '{chk['then']}'"
    return f"{k}: {json.dumps({k2: v for k2, v in chk.items() if k2 != 'type'}, ensure_ascii=False)}"


# ----------------------------------------------------------------------------- workspace helpers

def hash_tree(root: Path) -> dict[str, str]:
    out = {}
    for p in root.rglob("*"):
        if p.is_file() and ".git" not in p.parts:
            out[str(p.relative_to(root)).replace(os.sep, "/")] = hashlib.sha1(p.read_bytes()).hexdigest()
    return out


def changed_files(workspace: Path, before: dict[str, str]) -> list[str]:
    after = hash_tree(workspace)
    return sorted([f for f, h in after.items() if before.get(f) != h] + [f for f in before if f not in after])


def claude_cmd() -> str:
    exe = shutil.which("claude") or shutil.which("claude.cmd")
    if not exe:
        raise SystemExit("claude CLI not found on PATH. Install Claude Code and run `claude` once to log in.")
    return exe


def git_show(ref: str, relpath: str) -> str:
    return subprocess.run(["git", "show", f"{ref}:{relpath}"], cwd=ROOT, check=True,
                          capture_output=True, text=True, encoding="utf-8").stdout
