#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HISSession — a recorder for a single diagnosis/treatment session.
Tracks session state (loaded case, recorded diagnoses/prescriptions/orders, ...)
and flushes the full record to JSONL when the session ends.

Because the MCP stdio server may start a fresh process for every tool call
(especially in subagent scenarios), session state is persisted via
$OUTPUTS_DIR/his_session_state.json.

Concurrency safety: `atomic_call()` holds a file lock across the entire
read-modify-write transaction so parallel subagent processes don't lose
each other's updates.
"""

import contextlib
import fcntl
import json
import os
import time
from typing import Any, Dict


_EMPTY_RECORDS = lambda: {
    "diagnoses": [], "prescriptions": [], "lab_orders": [],
    "imaging_orders": [], "follow_up_plan": {}, "referrals": [],
    "analysis_conclusion": "",
}


class HISSession:
    """Recorder for a single session (file-backed, cross-process)."""

    def __init__(self, output_path: str):
        self.output_path = output_path
        self._state_path = os.path.join(os.path.dirname(output_path), "his_session_state.json")
        self._lock_path = self._state_path + ".lock"
        self._lockfile = None
        self._load_state()

    # ── File lock (prevents concurrent subagent MCP processes from racing on the state file) ──

    def _acquire_lock(self):
        os.makedirs(os.path.dirname(self._lock_path), exist_ok=True)
        self._lockfile = open(self._lock_path, 'w')
        fcntl.flock(self._lockfile, fcntl.LOCK_EX)

    def _release_lock(self):
        if self._lockfile is not None:
            fcntl.flock(self._lockfile, fcntl.LOCK_UN)
            self._lockfile.close()
            self._lockfile = None

    @contextlib.contextmanager
    def atomic_call(self):
        """Run read-modify-write under the file lock:
        enter -> reload latest state, handler mutates in-memory, exit -> save + release lock.
        If the handler called flush_to_jsonl (e.g. submit_orders) the state file has been
        cleared; in that case skip the final save to avoid leaving stale data behind.
        """
        self._acquire_lock()
        try:
            self._load_state_unlocked()
            yield self
            # handler already flushed (real submit) -> don't write the state file back
            if not self.submitted:
                self._save_state_unlocked()
        finally:
            self._release_lock()

    # ── State loading ───────────────────────────────────────────────────────

    def _load_state(self):
        """Public load entry point (used at construction): acquire the lock and reload."""
        self._acquire_lock()
        try:
            self._load_state_unlocked()
        finally:
            self._release_lock()

    def _load_state_unlocked(self):
        """Load session state from disk; caller must already hold the lock."""
        if os.path.exists(self._state_path):
            try:
                with open(self._state_path, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                # Validate ownership: the state file must carry a matching _session_output_path,
                # otherwise it's stale data left over from a previous case — discard it.
                if state.get("_session_output_path") != self.output_path:
                    print(
                        f"Warning: detected stale state file from a different case "
                        f"(from {state.get('_session_output_path')}); discarded.",
                        flush=True,
                    )
                    self._init_empty()
                    return
                self.case_id = state.get("case_id", "")
                self.patient_loaded = state.get("patient_loaded", True)
                self.records = state.get("records", _EMPTY_RECORDS())
                self.records.setdefault("analysis_conclusion", "")
                self.tool_call_log = state.get("tool_call_log", [])
                self.submitted = state.get("submitted", False)
                return
            except Exception:
                pass
        self._init_empty()

    def _init_empty(self):
        self.case_id = ""
        self.patient_loaded = True
        self.records = _EMPTY_RECORDS()
        self.tool_call_log = []
        self.submitted = False

    # ── State persistence ──────────────────────────────────────────────────

    def _save_state_unlocked(self):
        """Caller must hold the lock; performs an atomic write to disk."""
        os.makedirs(os.path.dirname(self._state_path), exist_ok=True)
        state = {
            "_session_output_path": self.output_path,  # used to validate ownership across processes
            "case_id": self.case_id,
            "patient_loaded": self.patient_loaded,
            "records": self.records,
            "tool_call_log": self.tool_call_log,
            "submitted": self.submitted,
        }
        tmp = self._state_path + ".tmp"
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False)
        os.replace(tmp, self._state_path)

    def _save_state(self):
        """Legacy entry point: acquire the lock and save."""
        self._acquire_lock()
        try:
            self._save_state_unlocked()
        finally:
            self._release_lock()

    # ── Public API ──────────────────────────────────────────────────────────

    def log_call(self, tool_name: str, arguments: Dict[str, Any],
                 result: Dict[str, Any]) -> None:
        """Record each tool call into the in-memory log; persistence handled by atomic_call()."""
        entry = {
            "seq": len(self.tool_call_log) + 1,
            "timestamp": time.time(),
            "tool": tool_name,
            "arguments": arguments,
            "result": result,
        }
        self.tool_call_log.append(entry)

    def flush_to_jsonl(self) -> None:
        """At session end (submit), append the full record to the JSONL and clear the state file."""
        record = {
            "case_id": self.case_id,
            "submitted": self.submitted,
            "records": self.records,
            "analysis_conclusion": self.records.get("analysis_conclusion", ""),
            "tool_call_log": self.tool_call_log,
            "total_calls": len(self.tool_call_log),
        }
        with open(self.output_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
        for path in (self._state_path, self._lock_path):
            try:
                os.remove(path)
            except FileNotFoundError:
                pass

    def reset(self) -> None:
        """Reset session state."""
        self._init_empty()
        self._save_state()
