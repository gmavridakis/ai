#!/usr/bin/env python3
"""Grade one run directory (or every run under a results directory).

  python evals/grade.py evals/results/2026-10-01_1200            # grade everything not yet graded
  python evals/grade.py evals/results/.../run-1 --force          # regrade one run
  python evals/grade.py <dir> --judge-model claude-sonnet-4-5

Two layers, both written to grading.json in the run directory (skill-creator compatible shape:
expectations[] with text / passed / evidence):
  1. checks: the case's deterministic checks, graded by code (harness.run_checks).
  2. judge: the case's expectations (one per **Done when**), graded by a `claude -p` call that
     reads the skill, the transcript and the outputs. Burden of proof is on the expectation.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import ROOT, SKILLS, Case, claude_cmd, parse_stream_json, run_checks  # noqa: E402

JUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "expectations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"text": {"type": "string"}, "passed": {"type": "boolean"}, "evidence": {"type": "string"}},
                "required": ["text", "passed", "evidence"],
            },
        },
        "eval_feedback": {"type": "string"},
    },
    "required": ["expectations"],
}


def judge_prompt(case: dict, skill_md: str, transcript_md: str, outputs_md: str) -> str:
    exp = "\n".join(f"{i + 1}. {e}" for i, e in enumerate(case["expectations"]))
    return f"""You are grading one run of a Claude Code session against a skill's completion criteria.

<skill name="{case['skill_under_test']}">
{skill_md}
</skill>

<task_prompt>
{case['prompt']}
</task_prompt>

<expected_output>
{case.get('expected_output') or '(none given)'}
</expected_output>

<transcript>
{transcript_md}
</transcript>

<outputs>
{outputs_md or '(no files were created or changed)'}
</outputs>

<expectations>
{exp}
</expectations>

Grade every expectation as passed or failed, with evidence quoted from the transcript or the outputs.
Rules: the burden of proof is on the expectation; no evidence means failed. Surface compliance is not
enough: a phase is done only when the observable state the expectation names exists in the transcript
(the command was run and its output shown, the file exists with the right content, the reply contains
the named lines). A claim in the final reply without a matching tool call or output is not evidence.
No partial credit. Keep each evidence string under 300 characters and quote exact text where you can.
In eval_feedback, in one or two sentences, name any expectation that a clearly wrong run would also
pass, or an important outcome you saw that no expectation covers; write "none" otherwise.
Return only the JSON object."""


def outputs_markdown(outputs_dir: Path, max_chars: int = 4000) -> str:
    parts = []
    for p in sorted(outputs_dir.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(outputs_dir)
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            parts.append(f"### {rel}\n(binary, {p.stat().st_size} bytes)")
            continue
        if len(text) > max_chars:
            text = text[:max_chars] + f"\n… [{len(text) - max_chars} more chars]"
        parts.append(f"### {rel}\n```\n{text}\n```")
    return "\n\n".join(parts)


def call_judge(prompt: str, model: str | None) -> tuple[dict, dict]:
    # the prompt goes through stdin: it can exceed the Windows command-line limit (32 KB)
    cmd = [claude_cmd(), "-p", "--output-format", "json", "--disable-slash-commands",
           "--max-turns", "1", "--json-schema", json.dumps(JUDGE_SCHEMA)]
    if model:
        cmd += ["--model", model]
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    t0 = time.time()
    proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, timeout=600)
    meta = {"grader_duration_seconds": round(time.time() - t0, 1), "exit_code": proc.returncode}
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"expectations": [], "error": f"judge returned no JSON (exit {proc.returncode}): {proc.stderr[-500:]}"}, meta
    meta["grader_cost_usd"] = data.get("total_cost_usd")
    out = data.get("structured_output")
    if not out:
        try:
            out = json.loads(data.get("result", "") or "{}")
        except json.JSONDecodeError:
            out = {"expectations": [], "error": "judge result was not JSON"}
    return out, meta


def rebuild_workspace(case: dict, run_dir: Path) -> Path:
    ws = Path(tempfile.mkdtemp(prefix="grade-"))
    if case.get("fixture"):
        shutil.copytree(ROOT / case["fixture"], ws, dirs_exist_ok=True)
    outputs = run_dir / "outputs"
    if outputs.is_dir():
        shutil.copytree(outputs, ws, dirs_exist_ok=True)
    return ws


def grade_run(run_dir: Path, judge_model: str | None = None, force: bool = False) -> dict:
    run_dir = Path(run_dir)
    if (run_dir / "grading.json").exists() and not force:
        return json.loads((run_dir / "grading.json").read_text(encoding="utf-8"))
    case = json.loads((run_dir / "case.json").read_text(encoding="utf-8"))
    t = parse_stream_json(run_dir / "transcript.jsonl")
    fixture_hashes = json.loads((run_dir / "fixture_hashes.json").read_text(encoding="utf-8")) if (run_dir / "fixture_hashes.json").exists() else {}

    ws = rebuild_workspace(case, run_dir)
    try:
        # Read tool inputs carry the original temp path; map them onto the rebuilt workspace by relative name
        for tc in t.tool_calls:
            fp = tc.input.get("file_path") if isinstance(tc.input, dict) else None
            if tc.name == "Read" and fp and not Path(fp).exists():
                cands = list(ws.rglob(Path(fp).name))
                if cands:
                    tc.input["file_path"] = str(cands[0])
        c = Case(skill=case["skill"], id=case["id"], name=case["name"], prompt=case["prompt"], fixture=None,
                 git_init=False, expected_output=case.get("expected_output", ""), checks=case.get("checks", []),
                 expectations=case.get("expectations", []), skill_under_test=case["skill_under_test"])
        check_results = run_checks(c, t, ws, fixture_hashes)
    finally:
        shutil.rmtree(ws, ignore_errors=True)

    judge_results, judge_meta, feedback = [], {}, ""
    if case.get("expectations"):
        skill_md_path = SKILLS / case["skill_under_test"] / "SKILL.md"
        skill_md = skill_md_path.read_text(encoding="utf-8") if skill_md_path.exists() else "(skill file not found)"
        prompt = judge_prompt(case, skill_md, t.to_markdown(max_result_chars=1200), outputs_markdown(run_dir / "outputs"))
        out, judge_meta = call_judge(prompt, judge_model)
        feedback = out.get("eval_feedback", "") or out.get("error", "")
        wanted = list(case["expectations"])
        got = {re.sub(r"\s+", " ", e.get("text", "")).strip().lower(): e for e in out.get("expectations", [])}
        for i, text in enumerate(wanted):
            key = re.sub(r"\s+", " ", text).strip().lower()
            e = got.get(key)
            if e is None:  # the judge may renumber or paraphrase; fall back to position
                lst = out.get("expectations", [])
                e = lst[i] if i < len(lst) else {"passed": False, "evidence": "judge returned no verdict for this expectation"}
            judge_results.append({"text": text, "passed": bool(e.get("passed")), "evidence": str(e.get("evidence", ""))[:600], "kind": "judge"})

    all_results = check_results + judge_results
    passed = sum(1 for r in all_results if r["passed"])
    metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8")) if (run_dir / "metrics.json").exists() else {}
    timing = json.loads((run_dir / "timing.json").read_text(encoding="utf-8")) if (run_dir / "timing.json").exists() else {}
    timing.update(judge_meta)
    grading = {
        "expectations": all_results,
        "summary": {
            "passed": passed, "failed": len(all_results) - passed, "total": len(all_results),
            "pass_rate": round(passed / len(all_results), 3) if all_results else 0.0,
            "checks_passed": sum(1 for r in check_results if r["passed"]), "checks_total": len(check_results),
            "judge_passed": sum(1 for r in judge_results if r["passed"]), "judge_total": len(judge_results),
        },
        "execution_metrics": metrics, "timing": timing,
        "eval_feedback": {"overall": feedback},
    }
    (run_dir / "grading.json").write_text(json.dumps(grading, indent=2, ensure_ascii=False), encoding="utf-8")
    return grading


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", help="a run directory or a results directory")
    ap.add_argument("--judge-model")
    ap.add_argument("--force", action="store_true", help="regrade runs that already have grading.json")
    args = ap.parse_args()
    root = Path(args.path)
    runs = [root] if (root / "case.json").exists() else sorted(p.parent for p in root.rglob("case.json"))
    for r in runs:
        g = grade_run(r, args.judge_model, args.force)
        print(f"{r.relative_to(root) if r != root else r.name}: {g['summary']['passed']}/{g['summary']['total']}")
    if root != runs[0]:
        import report
        report.build(root)
        print(f"report: {root / 'summary.md'}")


if __name__ == "__main__":
    main()
