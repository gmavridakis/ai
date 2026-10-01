#!/usr/bin/env python3
"""Run evaluation cases against the installed skills with `claude -p`, then grade and report.

Examples
  python evals/run.py --all                       # every case, with the skill, 3 runs each
  python evals/run.py --skill nodejs --runs 1     # one skill, quick
  python evals/run.py --skill nodejs --config both   # with_skill and without_skill (baseline)
  python evals/run.py --all --ref HEAD~5          # the skills as they were 5 commits ago
  python evals/run.py --skill error-triage --no-grade   # transcripts only, grade later with grade.py

Each run gets a directory under evals/results/<timestamp>/<skill>/<case>/<config>/run-<n>/ with
transcript.jsonl (raw), transcript.md (readable), final.md, metrics.json, timing.json, outputs/
(files the run created or changed) and, after grading, grading.json. report.py aggregates.

Requirements: Python 3.10+, the `claude` CLI logged in, the skills linked into ~/.claude/skills
(install.ps1 / install.sh). Runs are unattended (`--dangerously-skip-permissions`) inside a
temporary copy of the case fixture, never inside this repo.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import (ROOT, SKILLS, Case, claude_cmd, git_show, hash_tree, changed_files,  # noqa: E402
                     load_cases, parse_stream_json)
import grade as grader  # noqa: E402
import report as reporter  # noqa: E402


def run_one(case: Case, config: str, run_dir: Path, args) -> dict:
    run_dir.mkdir(parents=True, exist_ok=True)
    workspace = Path(tempfile.mkdtemp(prefix=f"eval-{case.name}-"))
    try:
        if case.fixture:
            shutil.copytree(case.fixture, workspace, dirs_exist_ok=True)
        if case.git_init:
            for cmd in (["git", "init", "-q"], ["git", "add", "-A"],
                        ["git", "-c", "user.name=eval", "-c", "user.email=eval@example.com", "commit", "-q", "-m", "fixture"]):
                subprocess.run(cmd, cwd=workspace, check=True, capture_output=True)
        before = hash_tree(workspace)

        cmd = [claude_cmd(), "-p", "--output-format", "stream-json", "--verbose",
               "--dangerously-skip-permissions", "--max-turns", str(args.max_turns),
               "--max-budget-usd", str(args.budget_usd)]
        if args.model:
            cmd += ["--model", args.model]
        if config == "without_skill":
            cmd += ["--disable-slash-commands"]
        env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
        env.setdefault("PYTHONIOENCODING", "utf-8")

        t0 = time.time()
        with open(run_dir / "transcript.jsonl", "w", encoding="utf-8") as out:
            try:
                proc = subprocess.run(cmd, cwd=workspace, env=env, input=case.prompt, stdout=out, stderr=subprocess.PIPE,
                                      timeout=args.timeout, text=True, encoding="utf-8", errors="replace")
                stderr, rc, timed_out = proc.stderr, proc.returncode, False
            except subprocess.TimeoutExpired as e:
                stderr, rc, timed_out = (e.stderr or "") if isinstance(e.stderr, str) else "", -1, True
        wall = time.time() - t0
        (run_dir / "stderr.txt").write_text(stderr or "", encoding="utf-8")

        t = parse_stream_json(run_dir / "transcript.jsonl")
        (run_dir / "transcript.md").write_text(t.to_markdown(), encoding="utf-8")
        (run_dir / "final.md").write_text(t.final_text, encoding="utf-8")

        changed = changed_files(workspace, before)
        outputs = run_dir / "outputs"
        outputs.mkdir(exist_ok=True)
        for rel in changed:
            src = workspace / rel
            if src.is_file() and src.stat().st_size < 2_000_000:
                dst = outputs / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)

        tool_counts: dict[str, int] = {}
        for tc in t.tool_calls:
            tool_counts[tc.name] = tool_counts.get(tc.name, 0) + 1
        metrics = {
            "tool_calls": tool_counts, "total_tool_calls": len(t.tool_calls),
            "skills_fired": t.skills_fired(), "files_changed": changed,
            "num_turns": t.result.get("num_turns"), "exit_code": rc, "timed_out": timed_out,
            "is_error": bool(t.result.get("is_error")), "stop_reason": t.result.get("stop_reason"),
            "output_chars": len(t.final_text), "transcript_events": t.raw_events,
        }
        usage = t.result.get("usage", {}) or {}
        timing = {
            "total_duration_seconds": round(wall, 1), "duration_ms": t.result.get("duration_ms"),
            "duration_api_ms": t.result.get("duration_api_ms"), "total_cost_usd": t.result.get("total_cost_usd"),
            "total_tokens": (usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
                             + usage.get("cache_creation_input_tokens", 0) + usage.get("cache_read_input_tokens", 0)),
            "model": (max((t.result.get("modelUsage") or {}).items(), key=lambda kv: kv[1].get("costUSD", 0))[0]
                      if t.result.get("modelUsage") else (args.model or "default")),
        }
        (run_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        (run_dir / "timing.json").write_text(json.dumps(timing, indent=2), encoding="utf-8")
        (run_dir / "case.json").write_text(json.dumps({
            "skill": case.skill, "id": case.id, "name": case.name, "config": config, "prompt": case.prompt,
            "skill_under_test": case.skill_under_test, "expected_output": case.expected_output,
            "fixture": str(case.fixture.relative_to(ROOT)).replace(os.sep, "/") if case.fixture else None,
            "checks": case.checks, "expectations": case.expectations, "ref": args.ref or "working-tree",
        }, indent=2, ensure_ascii=False), encoding="utf-8")
        (run_dir / "fixture_hashes.json").write_text(json.dumps(before), encoding="utf-8")
        return {"metrics": metrics, "timing": timing, "workspace": str(workspace)}
    finally:
        if args.keep_workspaces:
            print(f"    workspace kept: {workspace}")
        else:
            shutil.rmtree(workspace, ignore_errors=True)


class SkillSwap:
    """Temporarily put the SKILL.md of a git ref in place (the skills are linked, so this is live)."""

    def __init__(self, ref: str | None, skill_names: set[str]):
        self.ref, self.names, self.saved = ref, skill_names, {}

    def __enter__(self):
        if not self.ref:
            return self
        for name in self.names:
            p = SKILLS / name / "SKILL.md"
            if not p.exists():
                continue
            self.saved[p] = p.read_text(encoding="utf-8")
            try:
                p.write_text(git_show(self.ref, f"skills/{name}/SKILL.md"), encoding="utf-8")
                print(f"  swapped {name} to {self.ref}")
            except subprocess.CalledProcessError:
                print(f"  {name} does not exist at {self.ref}; keeping the working-tree version")
        return self

    def __exit__(self, *exc):
        for p, text in self.saved.items():
            p.write_text(text, encoding="utf-8")
        if self.saved:
            print("  restored working-tree skills")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--all", action="store_true", help="run every case")
    g.add_argument("--skill", help="run the cases of one skill folder under evals/cases")
    ap.add_argument("--case", help="only this case name")
    ap.add_argument("--runs", type=int, default=3, help="runs per case and configuration (default 3)")
    ap.add_argument("--config", choices=["with_skill", "without_skill", "both"], default="with_skill")
    ap.add_argument("--ref", help="git ref whose SKILL.md files to evaluate (default: working tree)")
    ap.add_argument("--model", help="model for the runs (default: your configured model)")
    ap.add_argument("--judge-model", help="model for the judge (default: the run model)")
    ap.add_argument("--max-turns", type=int, default=40)
    ap.add_argument("--budget-usd", type=float, default=3.0, help="per-run spend cap")
    ap.add_argument("--timeout", type=int, default=900, help="seconds per run")
    ap.add_argument("--out", help="results directory (default evals/results/<timestamp>)")
    ap.add_argument("--no-grade", action="store_true", help="skip grading; run grade.py later")
    ap.add_argument("--keep-workspaces", action="store_true")
    args = ap.parse_args()

    cases = load_cases(args.skill, args.case)
    if not cases:
        raise SystemExit("no cases matched")
    configs = ["with_skill", "without_skill"] if args.config == "both" else [args.config]
    out = Path(args.out) if args.out else ROOT / "evals" / "results" / dt.datetime.now().strftime("%Y-%m-%d_%H%M")
    out.mkdir(parents=True, exist_ok=True)
    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    (out / "meta.json").write_text(json.dumps({
        "started": dt.datetime.now().isoformat(timespec="seconds"), "head": head, "ref": args.ref or "working-tree",
        "model": args.model or "default", "judge_model": args.judge_model or args.model or "default",
        "runs": args.runs, "configs": configs, "cases": [c.key for c in cases],
    }, indent=2), encoding="utf-8")

    total = len(cases) * len(configs) * args.runs
    print(f"{len(cases)} case(s) × {len(configs)} config(s) × {args.runs} run(s) = {total} runs → {out}")
    done = 0
    with SkillSwap(args.ref, {c.skill_under_test for c in cases}):
        for case in cases:
            for config in configs:
                for n in range(1, args.runs + 1):
                    done += 1
                    run_dir = out / case.skill / case.name / config / f"run-{n}"
                    print(f"[{done}/{total}] {case.key} {config} run {n} …", flush=True)
                    r = run_one(case, config, run_dir, args)
                    m, tm = r["metrics"], r["timing"]
                    print(f"    turns={m['num_turns']} tools={m['total_tool_calls']} skills={m['skills_fired']} "
                          f"cost=${tm['total_cost_usd'] or 0:.2f} {tm['total_duration_seconds']}s"
                          + (" TIMEOUT" if m["timed_out"] else "") + (" ERROR" if m["is_error"] else ""), flush=True)
                    if not args.no_grade:
                        g = grader.grade_run(run_dir, judge_model=args.judge_model or args.model)
                        print(f"    graded {g['summary']['passed']}/{g['summary']['total']} "
                              f"(checks {g['summary']['checks_passed']}/{g['summary']['checks_total']}, "
                              f"judge {g['summary']['judge_passed']}/{g['summary']['judge_total']})", flush=True)
    if not args.no_grade:
        reporter.build(out)
        print(f"\nreport: {out / 'summary.md'}")


if __name__ == "__main__":
    main()
