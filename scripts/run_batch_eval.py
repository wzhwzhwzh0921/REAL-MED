#!/usr/bin/env python3
"""Batch eval runner for DeerFlow.

Reads an experiment YAML, expands it into a list of (model, case) runs,
and executes them using run_client_test.py as a subprocess.

Usage:
    python scripts/run_batch_eval.py evals/experiments/exp_realmed_405case_11model.yaml
    python scripts/run_batch_eval.py evals/experiments/exp_realmed_405case_11model.yaml --dry-run
    python scripts/run_batch_eval.py evals/experiments/exp_realmed_405case_11model.yaml --model glm-5
    python scripts/run_batch_eval.py evals/experiments/exp_realmed_405case_11model.yaml --case medical_ppt_presentation/medical_ppt_presentation_001
"""

from __future__ import annotations

import argparse
import asyncio
import datetime
import fnmatch
import json
import re
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


# httpx 不接受 NO_PROXY 里的 IPv6 CIDR（fd00::/8、fe80::/10、2605:340::/32 等），
# 解析 netloc 时把第一个 ":" 之后当成 port，触发 ValueError("Invalid port: ':'")。
# 必须在导入 yaml/httpx/openai 之前清理（仅过滤 IPv6 CIDR，保留 IPv4 CIDR 与域名）。
def _strip_ipv6_cidr_from_no_proxy() -> None:
    for var in ("NO_PROXY", "no_proxy"):
        val = os.environ.get(var)
        if not val:
            continue
        kept = [
            tok.strip() for tok in val.split(",")
            if tok.strip() and not (":" in tok and "/" in tok)  # ":" + "/" → IPv6 CIDR
        ]
        os.environ[var] = ",".join(kept)


_strip_ipv6_cidr_from_no_proxy()


import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
EVALS_DIR = REPO_ROOT / "evals"
REGISTRY_DIR = EVALS_DIR / "registry"
RUNS_DIR = EVALS_DIR / "runs"
RUNNER = REPO_ROOT / "run_client_test.py"
PYTHON = REPO_ROOT / "backend" / ".venv" / "bin" / "python"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class CaseSpec:
    case_id: str          # e.g. "medical_ppt_presentation/medical_ppt_presentation_001"
    task_type: str
    prompt: str
    attachments: list = field(default_factory=list)   # paths relative to evals/registry/attachments/
    overrides: dict = field(default_factory=dict)
    golden_notes: str = ""
    rubric_items: dict = field(default_factory=dict)  # optional item-by-item scoring rubric


@dataclass
class RunSpec:
    run_id: str
    experiment_id: str
    model_name: str
    case: CaseSpec
    thinking: str = "on"
    reasoning_effort: str = "high"
    plan_mode: bool = True
    subagent: bool = True
    recursion_limit: int = 200
    extensions_config_path: str | None = None  # absolute path; sets DEER_FLOW_EXTENSIONS_CONFIG_PATH
    expected_outputs: list[dict] = field(default_factory=list)


@dataclass
class RunResult:
    run_id: str
    status: str           # "ok" | "error" | "timeout"
    elapsed_s: float = 0.0
    event_count: int = 0
    tool_errors: int = 0
    output_files: list = field(default_factory=list)
    error_message: str = ""
    artifact_reminder_count: int = 0
    artifact_delivered_after_reminder: bool = False


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def _load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_case(case_id: str) -> CaseSpec:
    parts = case_id.split("/")
    case_path = REGISTRY_DIR / "cases" / Path(*parts) / "case.yaml"
    if not case_path.exists():
        raise FileNotFoundError(f"Case not found: {case_path}")
    data = _load_yaml(case_path)
    return CaseSpec(
        case_id=case_id,
        task_type=data["task_type"],
        prompt=data["prompt"].strip(),
        attachments=data.get("attachments") or [],
        overrides=data.get("overrides") or {},
        golden_notes=data.get("golden_notes", ""),
        rubric_items=data.get("rubric_items") or {},
    )


def load_task_type_defaults(task_type: str) -> dict:
    path = REGISTRY_DIR / "task_types" / f"{task_type}.yaml"
    if not path.exists():
        return {}
    data = _load_yaml(path)
    return data.get("defaults") or {}


def load_task_type_prompt_suffix(task_type: str) -> str:
    """Return the prompt_suffix from task_type yaml, or empty string."""
    path = REGISTRY_DIR / "task_types" / f"{task_type}.yaml"
    if not path.exists():
        return ""
    data = _load_yaml(path)
    return (data.get("prompt_suffix") or "").strip()


def load_task_type_extensions_config_path(task_type: str) -> str | None:
    """Return the absolute path to the task-type-specific extensions_config.json, or None."""
    path = REGISTRY_DIR / "task_types" / f"{task_type}.yaml"
    if not path.exists():
        return None
    data = _load_yaml(path)
    rel = data.get("extensions_config")
    if not rel:
        return None
    abs_path = REGISTRY_DIR / rel
    if not abs_path.exists():
        print(f"  [WARN] extensions_config not found for task_type '{task_type}': {abs_path}")
        return None
    return str(abs_path)


def load_task_type_expected_outputs(task_type: str) -> list[dict]:
    """Return the expected_outputs declared in the task-type config."""
    path = REGISTRY_DIR / "task_types" / f"{task_type}.yaml"
    if not path.exists():
        return []
    data = _load_yaml(path)
    outputs = data.get("expected_outputs") or []
    return outputs if isinstance(outputs, list) else []


def resolve_cases(selectors: list[str]) -> list[str]:
    """Expand glob selectors against the cases/ directory."""
    cases_root = REGISTRY_DIR / "cases"
    all_cases = []
    for root, dirs, files in os.walk(cases_root):
        if "case.yaml" in files:
            rel = Path(root).relative_to(cases_root)
            all_cases.append(str(rel))
    matched = set()
    for sel in selectors:
        for c in all_cases:
            if fnmatch.fnmatch(c, sel) or c == sel:
                matched.add(c)
    return sorted(matched)


# ---------------------------------------------------------------------------
# Planner
# ---------------------------------------------------------------------------

class BatchPlanner:
    def __init__(self, exp_path: Path):
        self.exp = _load_yaml(exp_path)
        self.experiment_id = self.exp["experiment_id"]

    def build_runs(
        self,
        model_filter: Optional[str] = None,
        case_filter: Optional[str] = None,
    ) -> list[RunSpec]:
        exp_runtime = self.exp.get("runtime") or {}
        case_ids = resolve_cases(self.exp.get("case_selectors") or [])

        runs = []
        for model_cfg in self.exp.get("models") or []:
            model_name = model_cfg["name"]
            if model_filter and model_name != model_filter:
                continue

            for case_id in case_ids:
                if case_filter and not fnmatch.fnmatch(case_id, case_filter):
                    continue

                case = load_case(case_id)
                task_defaults = load_task_type_defaults(case.task_type)
                ext_cfg_path = load_task_type_extensions_config_path(case.task_type)
                expected_outputs = load_task_type_expected_outputs(case.task_type)
                # Concatenate task_type.prompt_suffix + experiment.runtime.prompt_suffix
                # 实验级 suffix 追加在最后，便于覆盖题目默认约束（如"中国指南优先"）。
                task_suffix = load_task_type_prompt_suffix(case.task_type)
                exp_suffix = (exp_runtime.get("prompt_suffix") or "").strip()
                combined_suffix = "\n\n".join(s for s in (task_suffix, exp_suffix) if s)
                if combined_suffix:
                    case = CaseSpec(
                        case_id=case.case_id,
                        task_type=case.task_type,
                        prompt=case.prompt + "\n\n" + combined_suffix,
                        attachments=case.attachments,
                        overrides=case.overrides,
                        golden_notes=case.golden_notes,
                        rubric_items=case.rubric_items,
                    )

                # Priority: model_cfg > exp_runtime > case.overrides > task_defaults
                merged = {**task_defaults, **case.overrides, **exp_runtime}
                merged_model = {**merged, **{k: v for k, v in model_cfg.items() if k != "name"}}

                ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
                # Strip non-ASCII characters so thread_id stays alphanumeric/hyphen/underscore.
                # Append a short hash of the original case_id to avoid collisions when two
                # cases differ only in their non-ASCII parts (e.g. HIS_高血压_011 vs HIS_乳腺恶性肿瘤_011).
                import hashlib as _hashlib
                _case_hash = _hashlib.md5(case_id.encode()).hexdigest()[:6]
                safe_case = re.sub(r"[^a-zA-Z0-9_\-]", "", case_id.replace("/", "_"))
                safe_model = model_name.replace(".", "_").replace("-", "_")
                run_id = f"{safe_model}__{safe_case}_{_case_hash}__{ts}"

                runs.append(RunSpec(
                    run_id=run_id,
                    experiment_id=self.experiment_id,
                    model_name=model_name,
                    case=case,
                    thinking=str(merged_model.get("thinking", "on")),
                    reasoning_effort=str(merged_model.get("reasoning_effort", "high")),
                    plan_mode=bool(merged_model.get("plan_mode", True)),
                    subagent=bool(merged_model.get("subagent", True)),
                    recursion_limit=int(merged_model.get("recursion_limit", 200)),
                    extensions_config_path=ext_cfg_path,
                    expected_outputs=expected_outputs,
                ))
        return runs


# ---------------------------------------------------------------------------
# Executor
# ---------------------------------------------------------------------------

def run_one(spec: RunSpec, runs_dir: Path) -> RunResult:
    run_dir = runs_dir / spec.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    outputs_dir = run_dir / "outputs"
    outputs_dir.mkdir(exist_ok=True)

    # Save spec
    (run_dir / "run.json").write_text(
        json.dumps(asdict(spec), ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    deer_flow_home = Path(os.environ.get("DEER_FLOW_HOME", str(REPO_ROOT / ".deer-flow"))).resolve()
    thread_id = spec.run_id

    # Copy attachments to thread's uploads directory BEFORE running.
    # UploadsMiddleware scans this directory and automatically injects an
    # <uploaded_files> block into the human message — no manual prompt editing needed.
    if spec.case.attachments:
        uploads_dir = deer_flow_home / "threads" / thread_id / "user-data" / "uploads"
        uploads_dir.mkdir(parents=True, exist_ok=True)
        for rel_path in spec.case.attachments:
            src = REGISTRY_DIR / "attachments" / rel_path
            if src.exists():
                shutil.copy2(src, uploads_dir / src.name)
            else:
                print(f"  [WARN] attachment not found: {src}")

    cmd = [
        str(PYTHON), str(RUNNER),
        "--thread-id", thread_id,
        "--model", spec.model_name,
        "--thinking", spec.thinking,
        "--recursion-limit", str(spec.recursion_limit),
        "--prompt", spec.case.prompt,
        "--log-dir", str(run_dir),
    ]
    if spec.reasoning_effort:
        cmd += ["--reasoning-effort", spec.reasoning_effort]
    if spec.plan_mode:
        cmd += ["--plan-mode"]
    if spec.subagent:
        cmd += ["--subagent"]
    for output_spec in spec.expected_outputs:
        pattern = str(output_spec.get("pattern", "")).strip()
        if pattern and bool(output_spec.get("required", True)):
            cmd += ["--expected-output-pattern", pattern]

    thread_outputs_dir = deer_flow_home / "threads" / thread_id / "user-data" / "outputs"
    env = {**os.environ, "DEER_FLOW_HOME": str(deer_flow_home), "OUTPUTS_DIR": str(thread_outputs_dir)}
    if spec.extensions_config_path:
        # Resolve ${REPO_ROOT} placeholders at runtime so the JSON files stay
        # portable (no hardcoded absolute paths).
        raw = Path(spec.extensions_config_path).read_text(encoding="utf-8")
        resolved = raw.replace("${REPO_ROOT}", str(REPO_ROOT))
        resolved_path = run_dir / "extensions_config_resolved.json"
        resolved_path.write_text(resolved, encoding="utf-8")
        env["DEER_FLOW_EXTENSIONS_CONFIG_PATH"] = str(resolved_path)

    print(f"\n[RUN] {spec.run_id}")
    print(f"  model={spec.model_name}  case={spec.case.case_id}  recursion_limit={spec.recursion_limit}")

    t0 = time.time()
    result = RunResult(run_id=spec.run_id, status="ok")
    stderr_path = run_dir / "runner_stderr.txt"
    try:
        with stderr_path.open("w", encoding="utf-8") as stderr_file:
            proc = subprocess.run(
                cmd,
                env=env,
                cwd=str(REPO_ROOT / "backend"),
                stdout=None,       # inherit — goes to terminal
                stderr=stderr_file,  # capture to file for post-mortem
                check=False,
            )
        result.elapsed_s = time.time() - t0
        result.status = "ok" if proc.returncode == 0 else "error"
        if proc.returncode != 0:
            # Include last 300 chars of stderr in error_message for quick diagnosis
            try:
                tail = stderr_path.read_text(encoding="utf-8").strip()[-300:]
            except Exception:
                tail = ""
            result.error_message = f"exit code {proc.returncode}" + (f"\n{tail}" if tail else "")
    except Exception as exc:
        result.elapsed_s = time.time() - t0
        result.status = "error"
        result.error_message = str(exc)

    # Copy outputs from DEER_FLOW_HOME thread
    thread_outputs = deer_flow_home / "threads" / thread_id / "user-data" / "outputs"
    if thread_outputs.exists():
        for p in sorted(thread_outputs.iterdir()):
            if p.is_file():
                dest = outputs_dir / p.name
                shutil.copy2(p, dest)
                result.output_files.append(p.name)

    summary = {
        "run_id": spec.run_id,
        "status": result.status,
        "elapsed_s": round(result.elapsed_s, 1),
        "event_count": result.event_count,
        "tool_errors": result.tool_errors,
        "output_files": result.output_files,
        "error_message": result.error_message,
        "artifact_reminder_count": result.artifact_reminder_count,
        "artifact_delivered_after_reminder": result.artifact_delivered_after_reminder,
    }

    delivery_status_path = run_dir / "delivery_status.json"
    if delivery_status_path.exists():
        try:
            delivery_status = json.loads(delivery_status_path.read_text(encoding="utf-8"))
            result.artifact_reminder_count = int(delivery_status.get("artifact_reminder_count", 0) or 0)
            result.artifact_delivered_after_reminder = bool(delivery_status.get("artifact_delivered_after_reminder", False))
            summary["artifact_reminder_count"] = result.artifact_reminder_count
            summary["artifact_delivered_after_reminder"] = result.artifact_delivered_after_reminder
            summary["expected_output_patterns"] = delivery_status.get("expected_output_patterns", [])
            summary["missing_required_outputs"] = delivery_status.get("missing_required_outputs", [])
            summary["presented_output_files"] = delivery_status.get("presented_output_files", [])
        except Exception as exc:
            print(f"  [WARN] failed to parse delivery_status.json: {exc}")

    (run_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    status_icon = "✓" if result.status == "ok" else "✗"
    print(f"  {status_icon} elapsed={result.elapsed_s:.0f}s  outputs={result.output_files}")
    return result


# ---------------------------------------------------------------------------
# Async scheduler: model buckets, serial per model, parallel across models
# ---------------------------------------------------------------------------

def _new_run_id(spec: RunSpec) -> str:
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_case = re.sub(r"[^a-zA-Z0-9_\-]", "", spec.case.case_id.replace("/", "_"))
    safe_model = spec.model_name.replace(".", "_").replace("-", "_")
    return f"{safe_model}__{safe_case}__{ts}"


def run_with_retry(spec: RunSpec, runs_dir: Path, max_retries: int, retry_delay: float) -> RunResult:
    result = run_one(spec, runs_dir)
    for attempt in range(1, max_retries + 1):
        if result.status == "ok":
            break
        print(f"  [retry {attempt}/{max_retries}] waiting {retry_delay:.0f}s then retrying {spec.case.case_id}")
        time.sleep(retry_delay)
        retry_spec = RunSpec(
            run_id=_new_run_id(spec),
            experiment_id=spec.experiment_id,
            model_name=spec.model_name,
            case=spec.case,
            thinking=spec.thinking,
            reasoning_effort=spec.reasoning_effort,
            plan_mode=spec.plan_mode,
            subagent=spec.subagent,
            recursion_limit=spec.recursion_limit,
            extensions_config_path=spec.extensions_config_path,
            expected_outputs=spec.expected_outputs,
        )
        result = run_one(retry_spec, runs_dir)
    return result


async def _run_model_bucket(
    model_name: str,
    specs: list[RunSpec],
    runs_dir: Path,
    semaphore: asyncio.Semaphore,
    results: list[RunResult],
    max_parallel_cases: int = 1,
    max_retries: int = 0,
    retry_delay: float = 30.0,
):
    async with semaphore:
        loop = asyncio.get_running_loop()
        if max_parallel_cases <= 1:
            for spec in specs:
                result = await loop.run_in_executor(None, run_with_retry, spec, runs_dir, max_retries, retry_delay)
                results.append(result)
        else:
            case_sem = asyncio.Semaphore(max_parallel_cases)

            async def _run_case(spec: RunSpec) -> None:
                async with case_sem:
                    result = await loop.run_in_executor(None, run_with_retry, spec, runs_dir, max_retries, retry_delay)
                    results.append(result)

            await asyncio.gather(*[_run_case(spec) for spec in specs])


async def run_all_async(
    specs: list[RunSpec],
    runs_dir: Path,
    max_parallel_models: int = 2,
    max_parallel_cases: int = 1,
    max_retries: int = 0,
    retry_delay: float = 30.0,
) -> list[RunResult]:
    # Group by model
    buckets: dict[str, list[RunSpec]] = {}
    for s in specs:
        buckets.setdefault(s.model_name, []).append(s)

    semaphore = asyncio.Semaphore(max_parallel_models)
    results: list[RunResult] = []
    tasks = [
        _run_model_bucket(model, bucket_specs, runs_dir, semaphore, results,
                          max_parallel_cases=max_parallel_cases,
                          max_retries=max_retries, retry_delay=retry_delay)
        for model, bucket_specs in buckets.items()
    ]
    await asyncio.gather(*tasks)
    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def find_done_cases(runs_dir: Path, experiment_id: str) -> set[tuple[str, str]]:
    """Return set of (model_name, case_id) pairs that already have a successful run."""
    exp_dir = runs_dir / experiment_id
    if not exp_dir.exists():
        return set()
    done: set[tuple[str, str]] = set()
    for run_dir in exp_dir.iterdir():
        if not run_dir.is_dir():
            continue
        summary_path = run_dir / "summary.json"
        run_spec_path = run_dir / "run.json"
        if not summary_path.exists() or not run_spec_path.exists():
            continue
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            run_spec = json.loads(run_spec_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if summary.get("status") == "ok":
            model_name = run_spec.get("model_name", "")
            case_id = (run_spec.get("case") or {}).get("case_id", "")
            if model_name and case_id:
                done.add((model_name, case_id))
    return done


def main() -> int:
    parser = argparse.ArgumentParser(description="DeerFlow batch eval runner")
    parser.add_argument("experiment", help="Path to experiment YAML")
    parser.add_argument("--dry-run", action="store_true", help="Print runs without executing")
    parser.add_argument("--model", default=None, help="Filter to a single model")
    parser.add_argument("--case", default=None, help="Filter to a single case (supports glob)")
    parser.add_argument("--max-parallel", type=int, default=None, help="Override max_parallel_models")
    parser.add_argument("--max-parallel-cases", type=int, default=None, help="Override max_parallel_cases (concurrent cases per model)")
    parser.add_argument("--skip-done", action="store_true", help="Skip cases that already have a successful run")
    parser.add_argument("--max-retries", type=int, default=0, help="Max retries on failure (default: 0)")
    parser.add_argument("--retry-delay", type=float, default=30.0, help="Seconds to wait between retries (default: 30)")
    parser.add_argument("--no-judge", action="store_true", help="Skip auto-judge even if experiment.judge.enabled is true")
    args = parser.parse_args()

    exp_path = Path(args.experiment).resolve()
    if not exp_path.exists():
        print(f"Experiment file not found: {exp_path}", file=sys.stderr)
        return 1

    planner = BatchPlanner(exp_path)
    specs = planner.build_runs(model_filter=args.model, case_filter=args.case)

    if args.skip_done:
        done_cases = find_done_cases(RUNS_DIR, planner.experiment_id)
        before = len(specs)
        specs = [s for s in specs if (s.model_name, s.case.case_id) not in done_cases]
        print(f"[skip-done] {before - len(specs)} already done, {len(specs)} remaining")

    if not specs:
        print("No runs matched — check selectors and filters.")
        return 0

    print(f"Experiment : {planner.experiment_id}")
    print(f"Runs       : {len(specs)}")
    for s in specs:
        print(f"  {s.run_id}")

    if args.dry_run:
        print("\n[dry-run] Exiting without executing.")
        return 0

    runs_dir = RUNS_DIR / planner.experiment_id
    runs_dir.mkdir(parents=True, exist_ok=True)

    exp_cfg = planner.exp
    scheduler_cfg = exp_cfg.get("scheduler") or {}
    max_parallel = args.max_parallel or scheduler_cfg.get("max_parallel_models", 2)
    max_parallel_cases = args.max_parallel_cases or scheduler_cfg.get("max_parallel_cases", 1)

    t0 = time.time()
    results = asyncio.run(run_all_async(specs, runs_dir, max_parallel_models=max_parallel,
                                        max_parallel_cases=max_parallel_cases,
                                        max_retries=args.max_retries, retry_delay=args.retry_delay))
    elapsed = time.time() - t0

    ok = sum(1 for r in results if r.status == "ok")
    err = sum(1 for r in results if r.status != "ok")
    print(f"\n{'='*60}")
    print(f"Completed: {ok} ok, {err} errors, {elapsed:.0f}s total")
    print(f"Runs dir : {runs_dir}")
    print(f"{'='*60}")

    # ---- 自动 judge + 汇总（由 experiment.judge.enabled 控制）----
    judge_cfg = exp_cfg.get("judge") or {}
    if judge_cfg.get("enabled") and not args.no_judge:
        _autorun_judge_and_report(planner.experiment_id, judge_cfg, ok_results=[r for r in results if r.status == "ok"])

    return 0 if err == 0 else 1


def _autorun_judge_and_report(experiment_id: str, judge_cfg: dict, ok_results: list) -> None:
    """批跑完自动调 run_judge_eval + 生成聚合 jsonl + Excel。
    - experiment.judge.enabled = true 时触发
    - experiment.judge.parallel = N 控制并发 judge 数（默认 4）
    - experiment.judge.build_excel = false 可关闭 Excel 生成（默认 true）
    失败不抛异常，只打印警告——batch 本身的 exit code 不受影响。
    """
    if not ok_results:
        print("[auto-judge] 无成功 run，跳过")
        return

    parallel = int(judge_cfg.get("parallel", 4))
    build_excel = judge_cfg.get("build_excel", True)
    exp_yaml = EVALS_DIR / "experiments" / f"{experiment_id}.yaml"

    print(f"\n[auto-judge] 触发 judge（并发 {parallel}）...")
    import concurrent.futures

    def _judge_one(run_id: str) -> tuple[str, int, str]:
        log_path = Path("/tmp") / f"autojudge_{run_id}.log"
        try:
            with log_path.open("w", encoding="utf-8") as logf:
                proc = subprocess.run(
                    [str(PYTHON), "scripts/run_judge_eval.py", str(exp_yaml),
                     "--run-id", run_id, "--force"],
                    cwd=str(REPO_ROOT),
                    stdout=logf, stderr=subprocess.STDOUT,
                    check=False,
                )
            return run_id, proc.returncode, str(log_path)
        except Exception as exc:
            return run_id, -1, f"exception: {exc}"

    with concurrent.futures.ThreadPoolExecutor(max_workers=parallel) as pool:
        futures = [pool.submit(_judge_one, r.run_id) for r in ok_results]
        for fut in concurrent.futures.as_completed(futures):
            rid, code, log = fut.result()
            mark = "✓" if code == 0 else "✗"
            print(f"  {mark} {rid} (exit={code}, log={log})")

    # 重建聚合（防止并行 --run-id 互相覆盖）
    runs_dir = RUNS_DIR / experiment_id
    rubric_rows: list[dict] = []
    for sf in runs_dir.glob("*/judge/score.json"):
        try:
            d = json.loads(sf.read_text(encoding="utf-8"))
        except Exception:
            continue
        if "rubric" not in d:
            continue
        # 旧 score.json 没有 model_output，回填一下（读 run 目录的 his_result.jsonl 最后一行）
        if "model_output" not in d:
            run_dir = sf.parent.parent
            hr_path = run_dir / "outputs" / "his_result.jsonl"
            if hr_path.exists():
                lines = hr_path.read_text(encoding="utf-8").strip().splitlines()
                if lines:
                    try:
                        d["model_output"] = json.loads(lines[-1])
                    except Exception:
                        d["model_output"] = lines[-1]
        rubric_rows.append(d)
    rubric_rows.sort(key=lambda x: (x.get("question", ""), x.get("model", "")))

    if rubric_rows:
        report_dir = REPO_ROOT / "evals" / "reports" / experiment_id
        report_dir.mkdir(parents=True, exist_ok=True)
        agg_path = report_dir / "rubric_all.jsonl"
        with agg_path.open("w", encoding="utf-8") as f:
            for r in rubric_rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"[auto-judge] 聚合 jsonl：{agg_path} ({len(rubric_rows)} 条)")

        if build_excel:
            excel_script = REPO_ROOT / "scripts" / "build_rubric_excel.py"
            try:
                subprocess.run(
                    [str(PYTHON), str(excel_script), str(agg_path)],
                    cwd=str(REPO_ROOT), check=True,
                )
                print(f"[auto-judge] Excel：{agg_path.with_suffix('.xlsx')}")
            except subprocess.CalledProcessError as exc:
                print(f"[auto-judge] Excel 生成失败：{exc}")
    else:
        print("[auto-judge] 没有 rubric 评分结果，跳过聚合与 Excel")

    # ---- token 用量 & 费用汇总（独立于 judge 是否有结果，总是跑） ----
    usage_script = REPO_ROOT / "scripts" / "compute_usage_cost.py"
    try:
        subprocess.run(
            [str(PYTHON), str(usage_script), experiment_id],
            cwd=str(REPO_ROOT), check=True,
        )
    except subprocess.CalledProcessError as exc:
        print(f"[auto-judge] usage/cost 汇总失败：{exc}")
    except FileNotFoundError:
        print(f"[auto-judge] {usage_script} 不存在，跳过 usage/cost 汇总")


if __name__ == "__main__":
    raise SystemExit(main())
