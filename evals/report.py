#!/usr/bin/env python3
"""Aggregate graded runs into benchmark.json (skill-creator compatible) and summary.md.

  python evals/report.py evals/results/2026-10-01_1200
  python evals/report.py evals/results/2026-10-08_0900 --compare evals/results/2026-10-01_1200

summary.md shows, per skill and case: pass rate (mean ± stddev over runs) per configuration, the
cost and duration, every expectation with its pass count (so a line that always passes or always
fails is visible), and the judge's eval feedback. --compare adds the delta against an older run.
"""
from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path


def _stats(values: list[float]) -> dict:
    values = [v for v in values if v is not None]
    if not values:
        return {"mean": 0.0, "stddev": 0.0, "min": 0.0, "max": 0.0}
    return {"mean": round(statistics.mean(values), 3), "stddev": round(statistics.pstdev(values), 3) if len(values) > 1 else 0.0,
            "min": round(min(values), 3), "max": round(max(values), 3)}


def collect(results_dir: Path) -> list[dict]:
    runs = []
    for g in sorted(results_dir.rglob("grading.json")):
        run_dir = g.parent
        grading = json.loads(g.read_text(encoding="utf-8"))
        case = json.loads((run_dir / "case.json").read_text(encoding="utf-8"))
        tm = grading.get("timing", {})
        runs.append({
            "skill": case["skill"], "eval_id": case["id"], "eval_name": case["name"], "configuration": case["config"],
            "run_number": int(run_dir.name.split("-")[-1]), "ref": case.get("ref"),
            "result": {
                "pass_rate": grading["summary"]["pass_rate"], "passed": grading["summary"]["passed"],
                "failed": grading["summary"]["failed"], "total": grading["summary"]["total"],
                "checks_passed": grading["summary"].get("checks_passed", 0), "checks_total": grading["summary"].get("checks_total", 0),
                "judge_passed": grading["summary"].get("judge_passed", 0), "judge_total": grading["summary"].get("judge_total", 0),
                "time_seconds": tm.get("total_duration_seconds") or 0, "tokens": tm.get("total_tokens") or 0,
                "cost_usd": tm.get("total_cost_usd") or 0, "tool_calls": grading.get("execution_metrics", {}).get("total_tool_calls", 0),
                "errors": int(bool(grading.get("execution_metrics", {}).get("is_error"))) + int(bool(grading.get("execution_metrics", {}).get("timed_out"))),
            },
            "expectations": grading["expectations"],
            "notes": [grading.get("eval_feedback", {}).get("overall", "")],
            "skills_fired": grading.get("execution_metrics", {}).get("skills_fired", []),
        })
    return runs


def summarize(runs: list[dict]) -> dict:
    by_cfg = defaultdict(list)
    for r in runs:
        by_cfg[r["configuration"]].append(r)
    summary = {}
    for cfg, rs in by_cfg.items():
        summary[cfg] = {
            "pass_rate": _stats([r["result"]["pass_rate"] for r in rs]),
            "time_seconds": _stats([r["result"]["time_seconds"] for r in rs]),
            "tokens": _stats([r["result"]["tokens"] for r in rs]),
            "cost_usd": _stats([r["result"]["cost_usd"] for r in rs]),
            "runs": len(rs),
        }
    if "with_skill" in summary and "without_skill" in summary:
        w, wo = summary["with_skill"], summary["without_skill"]
        summary["delta"] = {
            "pass_rate": f"{w['pass_rate']['mean'] - wo['pass_rate']['mean']:+.2f}",
            "time_seconds": f"{w['time_seconds']['mean'] - wo['time_seconds']['mean']:+.1f}",
            "tokens": f"{w['tokens']['mean'] - wo['tokens']['mean']:+.0f}",
        }
    return summary


def build(results_dir: Path, compare: Path | None = None) -> None:
    results_dir = Path(results_dir)
    runs = collect(results_dir)
    meta = json.loads((results_dir / "meta.json").read_text(encoding="utf-8")) if (results_dir / "meta.json").exists() else {}
    benchmark = {
        "metadata": {"skill_name": "ai-skills", "timestamp": meta.get("started"), "head": meta.get("head"), "ref": meta.get("ref"),
                     "executor_model": meta.get("model"), "judge_model": meta.get("judge_model"),
                     "evals_run": sorted({f"{r['skill']}/{r['eval_name']}" for r in runs}), "runs_per_configuration": meta.get("runs")},
        "runs": runs, "run_summary": summarize(runs), "notes": [],
    }
    old = {}
    if compare:
        for r in collect(Path(compare)):
            old[(r["skill"], r["eval_name"], r["configuration"])] = old.get((r["skill"], r["eval_name"], r["configuration"]), []) + [r["result"]["pass_rate"]]

    # per skill / case / config
    groups = defaultdict(list)
    for r in runs:
        groups[(r["skill"], r["eval_name"], r["configuration"])].append(r)

    lines = [f"# Evaluation summary: {results_dir.name}", "",
             f"HEAD `{meta.get('head')}`, skills from `{meta.get('ref')}`, model `{meta.get('model')}`, judge `{meta.get('judge_model')}`, "
             f"{meta.get('runs')} run(s) per case. {len(runs)} graded runs.", ""]
    rs = benchmark["run_summary"]
    lines += ["| Configuration | Runs | Pass rate (mean ± sd) | Time s | Cost $ |", "| --- | --- | --- | --- | --- |"]
    for cfg in ("with_skill", "without_skill"):
        if cfg in rs:
            s = rs[cfg]
            lines.append(f"| {cfg} | {s['runs']} | {s['pass_rate']['mean']:.2f} ± {s['pass_rate']['stddev']:.2f} | {s['time_seconds']['mean']:.0f} | {s['cost_usd']['mean']:.2f} |")
    if "delta" in rs:
        lines.append(f"| delta (with − without) | | {rs['delta']['pass_rate']} | {rs['delta']['time_seconds']} | |")
    lines += ["", "## Per case", "", "| Skill | Case | Config | Pass rate | Checks | Judge | Skills fired | Cost $ | Time s |" + (" Δ vs compare |" if compare else ""),
              "| --- | --- | --- | --- | --- | --- | --- | --- | --- |" + (" --- |" if compare else "")]
    for (skill, name, cfg), grp in sorted(groups.items()):
        pr = _stats([r["result"]["pass_rate"] for r in grp])
        ck = f"{sum(r['result']['checks_passed'] for r in grp)}/{sum(r['result']['checks_total'] for r in grp)}"
        jd = f"{sum(r['result']['judge_passed'] for r in grp)}/{sum(r['result']['judge_total'] for r in grp)}"
        fired = sorted({s for r in grp for s in r["skills_fired"]})
        cost = statistics.mean([r["result"]["cost_usd"] for r in grp])
        secs = statistics.mean([r["result"]["time_seconds"] for r in grp])
        row = f"| {skill} | {name} | {cfg} | {pr['mean']:.2f} ± {pr['stddev']:.2f} | {ck} | {jd} | {', '.join(fired) or 'none'} | {cost:.2f} | {secs:.0f} |"
        if compare:
            prev = old.get((skill, name, cfg))
            row += (f" {pr['mean'] - statistics.mean(prev):+.2f} |" if prev else " n/a |")
        lines.append(row)
        if pr["stddev"] >= 0.25:
            benchmark["notes"].append(f"{skill}/{name} {cfg}: high variance ({pr['mean']:.2f} ± {pr['stddev']:.2f}); possibly flaky")

    lines += ["", "## Expectations (pass count over all runs of the case)", ""]
    for (skill, name, cfg), grp in sorted(groups.items()):
        lines.append(f"### {skill} / {name} / {cfg}")
        lines.append("")
        counts = defaultdict(lambda: [0, 0])
        order = []
        for r in grp:
            for e in r["expectations"]:
                k = (e.get("kind", "judge"), e["text"])
                if k not in counts:
                    order.append(k)
                counts[k][1] += 1
                counts[k][0] += int(e["passed"])
        for k in order:
            p, n = counts[k]
            mark = "✅" if p == n else ("❌" if p == 0 else "⚠️")
            lines.append(f"- {mark} {p}/{n} [{k[0]}] {k[1]}")
            if n >= 2 and p == n and k[0] == "check":
                pass  # always-passing checks are fine for routing; judge lines are flagged below
        fb = [n for r in grp for n in r["notes"] if n and n.lower().strip() not in ("none", "none.")]
        if fb:
            lines.append("")
            lines.append("Judge feedback: " + " / ".join(dict.fromkeys(fb)))
        lines.append("")
        for k in order:
            p, n = counts[k]
            if k[0] == "judge" and n >= 2 and p == n:
                benchmark["notes"].append(f"{skill}/{name} {cfg}: judge line always passes, check it discriminates: {k[1][:80]}")

    if benchmark["notes"]:
        lines += ["## Notes", ""] + [f"- {n}" for n in benchmark["notes"]] + [""]
    (results_dir / "benchmark.json").write_text(json.dumps(benchmark, indent=2, ensure_ascii=False), encoding="utf-8")
    (results_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("results_dir")
    ap.add_argument("--compare", help="an older results directory to diff against")
    args = ap.parse_args()
    build(Path(args.results_dir), Path(args.compare) if args.compare else None)
    print((Path(args.results_dir) / "summary.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
