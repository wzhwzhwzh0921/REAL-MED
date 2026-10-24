#!/usr/bin/env python3
"""Aggregate eval results into a leaderboard.

Scans all run directories in an experiment, combines run.json + summary.json +
judge/score.json, and writes:
  evals/runs/<experiment_id>/aggregate/leaderboard.json
  evals/runs/<experiment_id>/aggregate/leaderboard.csv

Usage:
    python scripts/aggregate_eval.py evals/experiments/exp_baseline.yaml
    python scripts/aggregate_eval.py evals/experiments/exp_baseline.yaml --output-dir /tmp/results
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
EVALS_DIR = REPO_ROOT / "evals"
RUNS_DIR = EVALS_DIR / "runs"


def _load_json_safe(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def collect_run_data(run_dir: Path) -> dict | None:
    run_spec = _load_json_safe(run_dir / "run.json")
    summary = _load_json_safe(run_dir / "summary.json")
    score_data = _load_json_safe(run_dir / "judge" / "score.json")
    image_data = _load_json_safe(run_dir / "judge" / "score_image.json")
    rubric_tracks = [track for track in (score_data, image_data) if "max_score" in track]
    total_score = sum(track.get("total_score", 0) for track in rubric_tracks)
    max_score = sum(track.get("max_score", 0) for track in rubric_tracks)
    overall = 100 * total_score / max_score if max_score else score_data.get("overall")

    if not run_spec or not summary:
        return None

    case = run_spec.get("case") or {}
    return {
        "run_id": run_dir.name,
        "model": run_spec.get("model_name", "?"),
        "case_id": case.get("case_id", "?"),
        "task_type": case.get("task_type", "?"),
        "status": summary.get("status", "?"),
        "elapsed_s": summary.get("elapsed_s", 0),
        "event_count": summary.get("event_count", 0),
        "tool_errors": summary.get("tool_errors", 0),
        "output_files": summary.get("output_files", []),
        "overall_score": overall,
        "total_score": total_score if max_score else None,
        "max_score": max_score or None,
        "scores": score_data.get("scores"),
        "rationale": score_data.get("rationale", ""),
        "issues": score_data.get("issues", []),
        "judge_model": (score_data.get("_meta") or {}).get("judge_model"),
        "judge_elapsed_s": (score_data.get("_meta") or {}).get("elapsed_s"),
    }


def build_leaderboard(runs: list[dict]) -> list[dict]:
    """Aggregate equally weighted binary rubric items across both judge tracks."""
    buckets: dict[str, list[dict]] = defaultdict(list)
    for r in runs:
        buckets[r["model"]].append(r)

    rows = []
    for model, model_runs in sorted(buckets.items()):
        scored = [r for r in model_runs if r["overall_score"] is not None]
        total_rubrics = sum(r.get("max_score") or 0 for r in scored)
        total_points = sum(r.get("total_score") or 0 for r in scored)
        avg_score = (100 * total_points / total_rubrics) if total_rubrics else ((sum(r["overall_score"] for r in scored) / len(scored)) if scored else None)
        avg_elapsed = (sum(r["elapsed_s"] for r in model_runs) / len(model_runs)) if model_runs else 0
        total_tool_errors = sum(r["tool_errors"] for r in model_runs)

        # Per-criterion averages
        criterion_avgs: dict[str, float] = {}
        if scored:
            all_keys = set()
            for r in scored:
                if r["scores"]:
                    all_keys.update(r["scores"].keys())
            for key in all_keys:
                vals = [r["scores"][key] for r in scored if r.get("scores") and key in r["scores"]]
                if vals:
                    criterion_avgs[key] = round(sum(vals) / len(vals), 2)

        rows.append({
            "model": model,
            "run_count": len(model_runs),
            "scored_count": len(scored),
            "avg_score": round(avg_score, 2) if avg_score is not None else None,
            "avg_elapsed_s": round(avg_elapsed, 1),
            "total_tool_errors": total_tool_errors,
            "criterion_avgs": criterion_avgs,
        })

    rows.sort(key=lambda r: r["avg_score"] if r["avg_score"] is not None else -1, reverse=True)
    return rows


def write_csv(rows: list[dict], path: Path) -> None:
    if not rows:
        return
    # Flatten criterion_avgs into columns
    all_criteria = set()
    for r in rows:
        all_criteria.update(r.get("criterion_avgs", {}).keys())
    criteria_cols = sorted(all_criteria)

    fieldnames = ["model", "avg_score", "avg_elapsed_s", "run_count", "scored_count",
                  "total_tool_errors"] + [f"avg_{c}" for c in criteria_cols]

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            flat = {k: v for k, v in row.items() if k != "criterion_avgs"}
            for c in criteria_cols:
                flat[f"avg_{c}"] = row.get("criterion_avgs", {}).get(c)
            writer.writerow(flat)


def print_leaderboard(rows: list[dict]) -> None:
    print(f"\n{'Model':<25} {'Score':>7} {'Elapsed':>9} {'Runs':>5} {'ToolErr':>8}")
    print("-" * 60)
    for r in rows:
        score_str = f"{r['avg_score']:.2f}" if r["avg_score"] is not None else "  N/A"
        print(f"{r['model']:<25} {score_str:>7} {r['avg_elapsed_s']:>8.0f}s "
              f"{r['run_count']:>5} {r['total_tool_errors']:>8}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate DeerFlow eval results into leaderboard")
    parser.add_argument("experiment", help="Path to experiment YAML")
    parser.add_argument("--output-dir", default=None, help="Override output directory")
    args = parser.parse_args()

    exp_path = Path(args.experiment).resolve()
    if not exp_path.exists():
        print(f"Experiment not found: {exp_path}", file=sys.stderr)
        return 1

    with exp_path.open(encoding="utf-8") as f:
        exp = yaml.safe_load(f) or {}
    experiment_id = exp["experiment_id"]

    runs_dir = RUNS_DIR / experiment_id
    if not runs_dir.exists():
        print(f"No runs directory: {runs_dir}")
        return 0

    run_dirs = sorted(d for d in runs_dir.iterdir() if d.is_dir() and d.name != "aggregate")
    print(f"Experiment : {experiment_id}")
    print(f"Run dirs   : {len(run_dirs)}")

    all_runs = []
    for run_dir in run_dirs:
        data = collect_run_data(run_dir)
        if data:
            all_runs.append(data)

    if not all_runs:
        print("No valid run data found.")
        return 0

    leaderboard = build_leaderboard(all_runs)

    output_dir = Path(args.output_dir).resolve() if args.output_dir else (runs_dir / "aggregate")
    output_dir.mkdir(parents=True, exist_ok=True)

    lb_json_path = output_dir / "leaderboard.json"
    lb_csv_path = output_dir / "leaderboard.csv"
    runs_json_path = output_dir / "all_runs.json"

    lb_json_path.write_text(json.dumps(leaderboard, ensure_ascii=False, indent=2), encoding="utf-8")
    runs_json_path.write_text(json.dumps(all_runs, ensure_ascii=False, indent=2), encoding="utf-8")
    write_csv(leaderboard, lb_csv_path)

    print_leaderboard(leaderboard)

    print(f"\nOutput:")
    print(f"  {lb_json_path}")
    print(f"  {lb_csv_path}")
    print(f"  {runs_json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
