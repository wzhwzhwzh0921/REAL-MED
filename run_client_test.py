#!/usr/bin/env python3
"""CLI runner for a single DeerFlow eval case.

Called by scripts/run_batch_eval.py as a subprocess for each (model, case) pair.

Usage:
    python run_client_test.py \
        --thread-id <id> \
        --model <name> \
        --thinking on|off \
        --recursion-limit 4000 \
        --prompt "<text>" \
        --log-dir <path> \
        [--reasoning-effort high|medium|low] \
        [--plan-mode] \
        [--subagent]

Environment variables (set by run_batch_eval.py):
    DEER_FLOW_HOME                  - Per-run isolated home directory
    OUTPUTS_DIR                     - Thread outputs directory
    DEER_FLOW_EXTENSIONS_CONFIG_PATH - Resolved extensions config path
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import sys
import time
from pathlib import Path


# httpx rejects IPv6 CIDRs in NO_PROXY (fd00::/8, fe80::/10, 2605:340::/32 etc.):
# its netloc parser treats text after the first ":" as a port, raising
# ValueError("Invalid port: ':'"). Strip those before importing deerflow/httpx/openai.
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


# Must run from backend/ directory (set by run_batch_eval.py via cwd=)
# so that deerflow package is importable via uv workspace.

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--thread-id", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--thinking", default="on", choices=["on", "off"])
    parser.add_argument("--recursion-limit", type=int, default=100)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--log-dir", required=True)
    parser.add_argument("--reasoning-effort", default=None)
    parser.add_argument("--plan-mode", action="store_true")
    parser.add_argument("--subagent", action="store_true")
    parser.add_argument("--expected-output-pattern", action="append", default=[])
    args = parser.parse_args()

    log_dir = Path(args.log_dir)
    run_id = log_dir.name
    conv_path = log_dir / f"conversation_{run_id}.jsonl"

    from deerflow.client import DeerFlowClient

    client = DeerFlowClient(
        model_name=args.model,
        thinking_enabled=(args.thinking == "on"),
        reasoning_effort=args.reasoning_effort,
        plan_mode=args.plan_mode,
        subagent_enabled=args.subagent,
    )

    events = []
    reminder_count = 0
    expected_patterns = [str(p).strip() for p in args.expected_output_pattern if str(p).strip()]
    outputs_dir_env = os.environ.get("OUTPUTS_DIR")
    outputs_dir = Path(outputs_dir_env).resolve() if outputs_dir_env else None
    max_artifact_reminders = 10

    def _list_output_files() -> list[str]:
        if outputs_dir is None or not outputs_dir.exists():
            return []
        return sorted(p.name for p in outputs_dir.iterdir() if p.is_file())

    def _missing_patterns() -> list[str]:
        if not expected_patterns:
            return []
        output_files = _list_output_files()
        missing = []
        for pattern in expected_patterns:
            if not any(fnmatch.fnmatch(name, pattern) for name in output_files):
                missing.append(pattern)
        return missing

    def _summarize_missing_formats(missing_patterns: list[str]) -> str:
        formats: list[str] = []
        for pattern in missing_patterns:
            suffix = Path(pattern).suffix.strip()
            if suffix and suffix not in formats:
                formats.append(suffix)
        if not formats:
            return ""
        if len(formats) == 1:
            return f"You have not yet delivered the final file in `{formats[0]}` format."
        formatted = ", ".join(f"`{fmt}`" for fmt in formats)
        return f"You have not yet delivered final files in these formats: {formatted}."

    def _build_artifact_reminder(missing_patterns: list[str]) -> str:
        quoted = ", ".join(f"`{pattern}`" for pattern in missing_patterns)
        if missing_patterns == ["his_result.jsonl"]:
            return (
                "You have not yet completed the final deliverable required by this task."
                " `/mnt/user-data/outputs` currently does not contain `his_result.jsonl`, which means the case has not been finally submitted."
                " Please continue calling the HIS tools to record the necessary entries and perform the final submission; do not stop before the deliverable is actually produced."
            )
        format_hint = _summarize_missing_formats(missing_patterns)
        return (
            "You have not yet completed the final deliverable required by this task."
            f" {format_hint}"
            f" `/mnt/user-data/outputs` is currently missing the following required artifacts: {quoted}."
            " Please continue using the appropriate tools to generate files in the required format(s) and formally deliver them into `/mnt/user-data/outputs`."
            " Do not stop at explanations, summaries, or `.md` drafts; this task is only complete once the target-format file is actually produced."
        )

    def _write_delivery_status(reminder_count: int) -> None:
        missing_patterns = _missing_patterns()
        status = {
            "expected_output_patterns": expected_patterns,
            "artifact_reminder_count": reminder_count,
            "artifact_delivered_after_reminder": reminder_count > 0 and not missing_patterns,
            "missing_required_outputs": missing_patterns,
            "output_files": _list_output_files(),
        }
        (log_dir / "delivery_status.json").write_text(
            json.dumps(status, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _run_turn(prompt: str, turn_index: int) -> None:
        for event in client.stream(
            prompt,
            thread_id=args.thread_id,
            recursion_limit=args.recursion_limit,
        ):
            events.append(
                {
                    "event_index": len(events),
                    "ts": time.time(),
                    "turn_index": turn_index,
                    "type": event.type,
                    "data": event.data,
                }
            )

    try:
        _run_turn(args.prompt, turn_index=0)

        while expected_patterns:
            missing_patterns = _missing_patterns()
            if not missing_patterns:
                break
            if reminder_count >= max_artifact_reminders:
                break

            reminder_count += 1
            reminder = _build_artifact_reminder(missing_patterns)
            events.append(
                {
                    "event_index": len(events),
                    "ts": time.time(),
                    "turn_index": reminder_count,
                    "type": "artifact_reminder",
                    "data": {
                        "attempt": reminder_count,
                        "missing_patterns": missing_patterns,
                        "content": reminder,
                    },
                }
            )
            _run_turn(reminder, turn_index=reminder_count)

        _write_delivery_status(reminder_count)

        # Write conversation log
        with conv_path.open("w", encoding="utf-8") as f:
            for entry in events:
                f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")

        return 0

    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        try:
            _write_delivery_status(reminder_count=reminder_count)
        except Exception:
            pass
        # Still write whatever events we captured
        if events:
            with conv_path.open("w", encoding="utf-8") as f:
                for entry in events:
                    f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
