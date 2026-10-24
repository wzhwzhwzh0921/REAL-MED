#!/usr/bin/env python3
"""LLM-as-judge scoring for completed DeerFlow eval runs.

For each run directory under evals/runs/<experiment_id>/ that:
  - has a summary.json with status == "ok"
  - has at least one output file
  - does NOT yet have judge/score.json

...this script calls the judge model and writes judge/score.json.

Usage:
    python scripts/run_judge_eval.py evals/experiments/exp_baseline.yaml
    python scripts/run_judge_eval.py evals/experiments/exp_baseline.yaml --run-id <run_id>
    python scripts/run_judge_eval.py evals/experiments/exp_baseline.yaml --force
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import sys
import time
from pathlib import Path


# httpx 不接受 NO_PROXY 里的 IPv6 CIDR（fd00::/8、fe80::/10、2605:340::/32 等），
# 解析 netloc 时把第一个 ":" 之后当成 port，触发 ValueError("Invalid port: ':'")。
# 必须在导入 yaml/httpx/openai 之前清理。
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
RUBRICS_DIR = REPO_ROOT / "rubrics"
IMAGE_RUBRICS_DIR = REPO_ROOT / "rubrics_image"


def _load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_judge_profile(profile_name: str) -> dict:
    path = REGISTRY_DIR / "judges" / f"{profile_name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Judge profile not found: {path}")
    return _load_yaml(path)


def load_task_type(task_type: str) -> dict:
    path = REGISTRY_DIR / "task_types" / f"{task_type}.yaml"
    if not path.exists():
        return {}
    return _load_yaml(path)


def lookup_rubric(case_id: str) -> dict | None:
    """在 rubrics/*.jsonl 里按 case 名查询 rubric。

    case_id 形如 "chronic_disease_management/chronic_disease_management_011"，取最后一段与 jsonl
    每行的 `question` 字段匹配。返回 {"category": "chronic", "rubrics": [...]} 或 None。
    """
    if not RUBRICS_DIR.exists():
        return None
    key = case_id.rstrip("/").split("/")[-1]
    for jsonl_path in sorted(RUBRICS_DIR.glob("*.jsonl")):
        category = jsonl_path.stem
        for line in jsonl_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if obj.get("question") == key:
                return {"category": category, "rubrics": obj.get("rubrics", [])}
    return None


def lookup_image_rubric(case_id: str) -> dict | None:
    """与 lookup_rubric 对称, 但查 rubrics_image/<category>.jsonl.

    每条 rubric 是 dict: {"text": ..., "image_targets": [...],
    "expected_visual_elements": [...]}.
    返回 {"category": str, "rubrics": list[dict]} 或 None.
    """
    if not IMAGE_RUBRICS_DIR.exists():
        return None
    key = case_id.rstrip("/").split("/")[-1]
    for jsonl_path in sorted(IMAGE_RUBRICS_DIR.glob("*.jsonl")):
        category = jsonl_path.stem
        for line in jsonl_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if obj.get("question") == key:
                return {"category": category, "rubrics": obj.get("rubrics", [])}
    return None


def _missing_deliverables(run_spec: dict, summary: dict, outputs_dir: Path) -> list[str]:
    """Check the per-case file and submission contract before rubric judging."""
    required = summary.get("expected_output_patterns") or [
        item["pattern"] for item in run_spec.get("expected_outputs", [])
        if item.get("required", True)
    ]
    presented = summary.get("presented_output_files")
    existing = [name for name in summary.get("output_files", []) if (outputs_dir / name).is_file()]
    missing = []
    for pattern in required:
        eligible = existing if pattern == "his_result.jsonl" or presented is None else [name for name in existing if name in presented]
        if not any(fnmatch.fnmatch(name, pattern) for name in eligible):
            missing.append(pattern)
    return missing


def build_judge_prompt(run_spec: dict, run_summary: dict, judge_profile: dict, outputs_dir: Path) -> str:
    """默认（非 rubric）judge prompt builder。
    rubric 路径的两阶段 prompt 由 judge_run_rubric 内部直接构造，不走这里。
    """
    case = run_spec.get("case", {})
    prompt_text = case.get("prompt", "")
    golden_notes = case.get("golden_notes", "")
    criteria = judge_profile.get("criteria", {})
    output_schema = judge_profile.get("output_schema", {})

    output_list = run_summary.get("output_files", [])
    elapsed = run_summary.get("elapsed_s", 0)
    tool_errors = run_summary.get("tool_errors", 0)

    output_schema_text = json.dumps(output_schema, ensure_ascii=False, indent=2)

    # Fallback mode: equally weighted binary criteria
    criteria_text = ""
    for key, cfg in criteria.items():
        desc = cfg.get("description", "").strip()
        criteria_text += f"\n### {key}\n{desc}\n"

    prompt = f"""You are an expert evaluator for AI-generated content. Score the following DeerFlow task run.

## Task prompt
{prompt_text}

## Evaluation notes
{golden_notes}

## Run metadata
- model: {run_spec.get('model_name', '?')}
- elapsed_s: {elapsed}
- tool_errors: {tool_errors}
- output_files: {output_list}

## Scoring criteria
{criteria_text}

## Instructions
1. Review the attached output artifact(s).
2. Score each criterion as 0 or 1 based on explicit evidence in the artifact.
3. Compute the fraction of satisfied criteria; all criteria have equal weight.
4. Provide a brief rationale and list any concrete issues found.
5. Return ONLY a JSON object matching this schema:
{output_schema_text}
"""
    return prompt


def _make_openai_client(judge_model: str) -> tuple:
    """Build a langchain BaseChatModel via the deerflow model factory.

    Using the factory rather than a raw OpenAI client lets the judge also call
    the configured OpenRouter adapters
    in addition to OpenAI-compatible chat models. Returns (BaseChatModel, model_name).
    """
    backend_dir = REPO_ROOT / "backend"
    if str(backend_dir / "packages" / "harness") not in sys.path:
        sys.path.insert(0, str(backend_dir / "packages" / "harness"))
    _cwd = os.getcwd()
    os.chdir(str(backend_dir))
    try:
        from deerflow.config import get_app_config  # type: ignore
        from deerflow.models import create_chat_model  # type: ignore
        cfg = get_app_config()
        m = cfg.get_model_config(judge_model)
        if m is None:
            raise ValueError(f"Judge model '{judge_model}' not found in backend config")
        client = create_chat_model(judge_model, thinking_enabled=False)
    finally:
        os.chdir(_cwd)
    model_name = str(getattr(m, "model", None) or getattr(m, "model_name", judge_model))
    return client, model_name


def _call_judge(client, prompt: str, judge_model_name: str, _max_retries: int = 5, **api_kwargs) -> str:
    """Invoke a langchain BaseChatModel; auto-retries with exponential backoff on 429 QPM.

    We use the langchain interface (rather than a stock openai client) so that
    the configured OpenRouter adapters
    work transparently alongside plain OpenAI-compatible models.
    """
    from langchain_core.messages import HumanMessage
    for attempt in range(_max_retries + 1):
        try:
            resp = client.invoke([HumanMessage(content=prompt)], **api_kwargs)
            return resp.content if hasattr(resp, "content") else str(resp)
        except Exception as exc:
            msg = str(exc)
            if attempt < _max_retries and ("429" in msg or "rate" in msg.lower() or "qpm" in msg.lower()):
                wait = 10 * (2 ** attempt)
                print(f"  [retry {attempt+1}/{_max_retries}] sleeping {wait}s ...")
                time.sleep(wait)
            else:
                raise


def _extract_json(text: str) -> dict | None:
    """从文本里提取首个合法 JSON 对象。"""
    import re as _re
    text = text.strip()
    m = _re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=_re.DOTALL)
    json_text = m.group(1) if m else None
    if json_text is None:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            json_text = text[start:end]
    if not json_text:
        return None
    try:
        return json.loads(json_text)
    except json.JSONDecodeError:
        return None


def _classify_rubric_visual(rubric_text: str, client, model_name: str) -> bool:
    """One LLM call: classify a single rubric as VISUAL (needs rendered image)
    or TEXT (judgeable from textual output only). Returns True iff VISUAL.
    Fail-safe: any error or unparseable response defaults to TEXT (False).
    """
    prompt = (
        "Classify a medical-evaluation rubric as VISUAL or TEXT.\n\n"
        "A rubric is VISUAL only when judging it requires actually viewing the rendered "
        "document / slide / page — e.g. layout quality, font/size, presence of an image / "
        "chart / diagram / forest plot, slide count, page-overflow, image-text overlap, "
        "whether a figure was actually drawn vs. only described.\n"
        "All other rubrics (facts, drug names, dosing, diagnoses, reasoning, structure "
        "described in text, table cell values, recommended steps, citation correctness) "
        "are TEXT.\n\n"
        f"Rubric:\n{rubric_text}\n\n"
        "Output ONLY one word: VISUAL or TEXT."
    )
    try:
        raw = _call_judge(client, prompt, model_name)
    except Exception:
        return False
    return "VISUAL" in (raw or "").strip().upper().split()[:3]


def _split_rubrics_by_visual(rubrics: list, client, model_name: str,
                              workers: int = 8) -> tuple[list, list]:
    """Parallel classify rubrics. Returns (text_rubrics, visual_rubrics).
    Order within each list preserves the original index."""
    import concurrent.futures as _cf
    n = len(rubrics)
    flags = [False] * n

    def _one(i: int):
        return i, _classify_rubric_visual(rubrics[i], client, model_name)

    with _cf.ThreadPoolExecutor(max_workers=min(workers, max(1, n))) as pool:
        for i, is_vis in pool.map(_one, range(n)):
            flags[i] = is_vis

    text_list = [r for r, v in zip(rubrics, flags) if not v]
    visual_list = [r for r, v in zip(rubrics, flags) if v]
    return text_list, visual_list


def _coerce_numeric_score(value) -> float | None:
    """Parse numeric score fields emitted by the judge."""
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def _inline_his_submission(outputs_dir: Path) -> str:
    """读 his_result.jsonl 最后一行（最终 submit 快照）转为 indented JSON 文本。"""
    his_result_path = outputs_dir / "his_result.jsonl"
    if not his_result_path.exists():
        return ""
    lines = his_result_path.read_text(encoding="utf-8").strip().splitlines()
    if not lines:
        return ""
    try:
        last = json.loads(lines[-1])
        return json.dumps(last, ensure_ascii=False, indent=2)
    except Exception:
        return lines[-1]


def _read_docx_text(path: Path) -> str:
    """Extract plain text from a .docx file (paragraphs + tables)."""
    try:
        from docx import Document  # type: ignore
        doc = Document(str(path))
        lines = []
        for para in doc.paragraphs:
            if para.text.strip():
                lines.append(para.text)
        for table in doc.tables:
            for row in table.rows:
                lines.append(" | ".join(cell.text.strip() for cell in row.cells))
        return "\n".join(lines)
    except Exception as exc:
        return f"[docx read error: {exc}]"


def _read_pdf_text(path: Path, max_pages: int = 30) -> str:
    """Extract text from a .pdf file (first max_pages pages)."""
    try:
        import pdfplumber  # type: ignore
        parts = []
        with pdfplumber.open(str(path)) as pdf:
            for i, page in enumerate(pdf.pages[:max_pages]):
                txt = (page.extract_text() or "").strip()
                if txt:
                    parts.append(f"--- page {i+1} ---\n{txt}")
            if len(pdf.pages) > max_pages:
                parts.append(f"... [truncated: total {len(pdf.pages)} pages, only first {max_pages} extracted]")
        return "\n\n".join(parts)
    except Exception as exc:
        return f"[pdf read error: {exc}]"


def _read_pptx_text(path: Path) -> str:
    """Extract slide text + speaker notes from a .pptx file."""
    try:
        from pptx import Presentation  # type: ignore
        prs = Presentation(str(path))
        parts = []
        for i, slide in enumerate(prs.slides, 1):
            slide_lines = [f"--- slide {i} ---"]
            for shape in slide.shapes:
                if shape.has_text_frame:
                    for para in shape.text_frame.paragraphs:
                        t = para.text.strip()
                        if t:
                            slide_lines.append(t)
            if slide.has_notes_slide:
                notes = slide.notes_slide.notes_text_frame.text.strip()
                if notes:
                    slide_lines.append(f"[notes] {notes}")
            parts.append("\n".join(slide_lines))
        return "\n\n".join(parts)
    except Exception as exc:
        return f"[pptx read error: {exc}]"


def _collect_output_text(outputs_dir: Path, summary: dict) -> str:
    """For non-HIS cases: extract text from accepted deliverable formats only.

    Accepted: .docx, .xlsx, .pdf, .pptx — i.e. structured documents the task
    types actually request. Markdown / plain-text files (.md / .txt / .csv)
    are deliberately NOT read: if a task asked for .docx and the model only
    submitted .md, judge should see no usable deliverable and score the run
    as a non-delivery (model_output = None → 0 across all rubric points).
    """
    output_files, _, _ = _select_deliverable_files(outputs_dir, summary)
    parts = []
    for fname in output_files:
        fpath = outputs_dir / fname
        if not fpath.exists():
            continue
        suffix = fpath.suffix.lower()
        if suffix == ".docx":
            text = _read_docx_text(fpath)
            parts.append(f"=== {fname} ===\n{text}")
        elif suffix == ".xlsx":
            try:
                import openpyxl  # type: ignore
                wb = openpyxl.load_workbook(str(fpath), read_only=True, data_only=True)
                for sheet_name in wb.sheetnames:
                    ws = wb[sheet_name]
                    rows_text = []
                    for row in ws.iter_rows(values_only=True):
                        row_vals = [str(c) if c is not None else "" for c in row]
                        if any(v.strip() for v in row_vals):
                            rows_text.append(" | ".join(row_vals))
                    if rows_text:
                        parts.append(f"=== {fname} (sheet: {sheet_name}) ===\n" + "\n".join(rows_text[:200]))
            except Exception as exc:
                parts.append(f"[xlsx read error for {fname}: {exc}]")
        elif suffix == ".pdf":
            text = _read_pdf_text(fpath)
            parts.append(f"=== {fname} ===\n{text}")
        elif suffix == ".pptx":
            text = _read_pptx_text(fpath)
            parts.append(f"=== {fname} ===\n{text}")
        # Intentionally skip .md / .txt / .csv: only structured deliverables
        # count as "submitted". This enforces the per-task prompt_suffix's
        # hard requirement on output format.
    return "\n\n".join(parts) if parts else ""


def _select_deliverable_files(outputs_dir: Path, summary: dict) -> tuple[list[str], int, dict[str, list[str]]]:
    """Pick one latest deliverable per required format and detect duplicates.

    Returns:
    - selected output file names to read
    - duplicate-format diagnostic flag (0 or 1)
    - duplicate candidates keyed by format suffix
    """
    output_files = [str(f) for f in summary.get("output_files", [])]
    expected_patterns = [str(p) for p in summary.get("expected_output_patterns", []) if str(p).strip()]

    if not output_files:
        return [], 0, {}

    deliverable_suffixes: list[str] = []
    for pattern in expected_patterns:
        suffix = Path(pattern).suffix.lower().strip()
        if suffix and suffix not in deliverable_suffixes:
            deliverable_suffixes.append(suffix)

    if not deliverable_suffixes:
        deliverable_suffixes = [".docx", ".xlsx", ".pdf", ".pptx"]

    selected: list[str] = []
    duplicate_candidates: dict[str, list[str]] = {}

    for suffix in deliverable_suffixes:
        candidates = []
        for fname in output_files:
            fpath = outputs_dir / fname
            if not fpath.exists() or fpath.suffix.lower() != suffix:
                continue
            if expected_patterns:
                if not any(fnmatch.fnmatch(fname, pattern) for pattern in expected_patterns if Path(pattern).suffix.lower() == suffix):
                    continue
            candidates.append(fpath)
        if not candidates:
            continue
        candidates.sort(key=lambda p: (p.stat().st_mtime, p.name))
        selected.append(candidates[-1].name)
        if len(candidates) > 1:
            duplicate_candidates[suffix] = [p.name for p in candidates]

    duplicate_penalty = 1 if duplicate_candidates else 0
    return selected, duplicate_penalty, duplicate_candidates


def judge_run_rubric(run_dir: Path, rubric_entry: dict, judge_profile: dict,
                     run_spec: dict, summary: dict, force: bool = False) -> dict | None:
    """两阶段 rubric judge：Phase 1 一次性打分，Phase 2 逐条跟进说理由。

    输出结构：
    {
      "question": "HIS_高血压_011",
      "model": "kimi-k2.6",
      "rubric": {
        "rubric1": {"text": "...", "score": 0, "reason": "..."},
        ...
      },
      "total_score": X, "max_score": Y,
      "_meta": {"judge_model": ..., "elapsed_s": ...}
    }
    """
    judge_dir = run_dir / "judge"
    score_path = judge_dir / "score.json"
    if score_path.exists() and not force:
        print(f"  [skip] already judged: {run_dir.name}")
        return None

    judge_dir.mkdir(exist_ok=True)

    case = run_spec.get("case", {}) or {}
    prompt_text = case.get("prompt", "")
    case_id = case.get("case_id", "")
    question = case_id.rstrip("/").split("/")[-1]
    model_name = run_spec.get("model_name", "")
    rubrics: list[str] = rubric_entry["rubrics"]
    n = len(rubrics)
    outputs_dir = run_dir / "outputs"
    his_content = _inline_his_submission(outputs_dir)

    judge_model = judge_profile.get("judge_model", "gpt-5.4-mini")
    openai_client, judge_model_name = _make_openai_client(judge_model)

    # Build extra API kwargs from judge profile (reasoning_effort for reasoning models)
    judge_api_kwargs: dict = {}
    reasoning_effort = judge_profile.get("reasoning_effort")
    if reasoning_effort:
        judge_api_kwargs["reasoning_effort"] = reasoning_effort

    t0 = time.time()
    rubric_listing = "\n".join(f"{i+1}. {r}" for i, r in enumerate(rubrics))

    # Determine output mode: HIS JSON vs. document files (docx/xlsx)
    if his_content:
        output_section = f"## Model's HIS operational record (final submitted state)\n```json\n{his_content}\n```"
        scoring_rule = (
            "- Judge strictly based on what is present in the `records` field of the HIS submission. "
            "Do NOT infer what the model \"might know\".\n"
            "- Do NOT read model reasoning, chain-of-thought, or any text outside `records`."
        )
        reason_instruction = "quoting the specific diagnoses / prescriptions / lab orders / referrals in `records`"
    else:
        selected_output_files, duplicate_penalty, duplicate_candidates = _select_deliverable_files(outputs_dir, summary)
        doc_text = _collect_output_text(outputs_dir, summary)
        output_section = f"## Model's submitted document(s) content\n{doc_text}" if doc_text else "## Model's submitted document(s) content\n[No output files found]"
        scoring_rule = (
            "- Judge strictly based on what is explicitly stated in the submitted document(s) above. "
            "Do NOT infer or assume content not written in the document.\n"
            "- Award 1 only if the specific fact, value, or recommendation is clearly present."
        )
        reason_instruction = "quoting the specific content in the submitted document"

    # ===================== 每条 rubric 独立打分+说理由（默认 8 路并发, 可 JUDGE_ITEM_WORKERS 覆写）=====================
    import concurrent.futures as _cf

    JUDGE_WORKERS = int(os.environ.get("JUDGE_ITEM_WORKERS", "8"))

    def _judge_one_rubric(args: tuple):
        i, rubric_text = args
        prompt = f"""You are a strict medical reviewer. Score the single rubric point below against the model's output, then give a concise justification.

## Case
{prompt_text}

## Rubric point (item {i} of {n})
{rubric_text}

{output_section}

## Scoring rules
{scoring_rule}
- Award score=1 ONLY if the specific fact, value, or action is clearly and explicitly present in the output.
- Award score=0 if it is absent, vague, or incorrect.

## Output rules
- Output ONLY the following JSON (no code block, no prefix/suffix):
{{"score": <0 or 1>, "reason": "<1-3 sentences in Chinese, {reason_instruction}>"}}
- If score=0: state exactly which required element is missing.
- If score=1: quote the specific content that satisfies this point.
"""
        print(f"  [judge-rubric {i}/{n}] {run_dir.name}")
        raw = _call_judge(openai_client, prompt, judge_model_name, **judge_api_kwargs)
        obj = _extract_json(raw) or {}
        score = int(obj.get("score", 0))
        score = 1 if score else 0
        reason = obj.get("reason", raw.strip())
        # Unwrap double-encoded JSON: model sometimes returns {"score":X,"reason":"{\"score\":Y,...}"}
        # _extract_json may fail on inner JSON due to unescaped quotes in Chinese text,
        # so fall back to regex to extract the inner score value reliably.
        if isinstance(reason, str) and '"score"' in reason:
            import re as _re2
            m_inner = _re2.search(r'"score"\s*:\s*([01])', reason)
            if m_inner:
                score = int(m_inner.group(1))
                # Also extract inner reason text if possible
                inner = _extract_json(reason)
                if inner and "reason" in inner:
                    reason = inner.get("reason", reason)
        return i, f"rubric{i}", rubric_text, score, reason

    rubric_out: dict[str, dict] = {}
    scores: list[int] = []
    tasks = list(enumerate(rubrics, 1))
    with _cf.ThreadPoolExecutor(max_workers=JUDGE_WORKERS) as pool:
        results = sorted(pool.map(_judge_one_rubric, tasks), key=lambda x: x[0])
    for i, key, rubric_text, score, reason in results:
        rubric_out[key] = {"text": rubric_text, "score": score, "reason": reason}
        scores.append(score)

    elapsed = time.time() - t0
    # 保存模型输出快照：HIS 模式存 JSON 对象，文档模式存提取的文本。
    if his_content:
        try:
            model_output = json.loads(his_content)
        except Exception:
            model_output = his_content
    else:
        model_output = doc_text if doc_text else None
    artifact_penalty = 0  # Reminders are reported separately, not deducted from rubric scores.
    deliverable_penalty = 0
    selected_output_files = []
    duplicate_candidates = {}
    if not his_content:
        selected_output_files, deliverable_penalty, duplicate_candidates = _select_deliverable_files(outputs_dir, summary)
    raw_total_score = sum(scores)
    adjusted_total_score = raw_total_score
    result = {
        "question": question,
        "model": model_name,
        "rubric": rubric_out,
        "raw_total_score": raw_total_score,
        "artifact_reminder_penalty": 0,
        "duplicate_deliverable_penalty": 0,
        "total_score": adjusted_total_score,
        "max_score": n,
        "model_output": model_output,
        "_meta": {
            "judge_model": judge_model,
            "elapsed_s": round(elapsed, 1),
            "run_id": run_dir.name,
            "category": rubric_entry.get("category", ""),
            "artifact_reminder_count": int(summary.get("artifact_reminder_count", 0) or 0),
            "artifact_delivered_after_reminder": bool(summary.get("artifact_delivered_after_reminder", False)),
            "selected_output_files": selected_output_files,
            "duplicate_deliverable_candidates": duplicate_candidates,
        },
    }
    score_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"  [done]  {result['total_score']}/{n}"
        f" (raw={raw_total_score})"
        f"  elapsed={elapsed:.0f}s  -> {score_path}"
    )
    return result


def _encode_image_b64(path: Path) -> str:
    """Read PNG/JPG and return data URL string for multimodal LLM input."""
    import base64
    suffix = path.suffix.lower().lstrip(".")
    mime = "image/jpeg" if suffix in ("jpg", "jpeg") else f"image/{suffix or 'png'}"
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{data}"


def _call_vision_judge(client, prompt_text: str, image_paths: list[Path],
                       judge_model_name: str, _max_retries: int = 5,
                       **api_kwargs) -> str:
    """Multimodal invoke: text + image_url blocks via langchain HumanMessage."""
    from langchain_core.messages import HumanMessage
    content: list[dict] = [{"type": "text", "text": prompt_text}]
    for p in image_paths:
        content.append({
            "type": "image_url",
            "image_url": {"url": _encode_image_b64(p)},
        })
    for attempt in range(_max_retries + 1):
        try:
            resp = client.invoke([HumanMessage(content=content)], **api_kwargs)
            return resp.content if hasattr(resp, "content") else str(resp)
        except Exception as exc:
            msg = str(exc)
            if attempt < _max_retries and ("429" in msg or "rate" in msg.lower()
                                           or "qpm" in msg.lower()):
                wait = 10 * (2 ** attempt)
                print(f"  [vision-retry {attempt+1}/{_max_retries}] sleeping {wait}s ...")
                time.sleep(wait)
            else:
                raise


def judge_run_rubric_image(run_dir: Path, image_entry: dict, judge_profile: dict,
                           run_spec: dict, summary: dict,
                           force: bool = False) -> dict | None:
    """Per-image-rubric vision judge. Mirrors judge_run_rubric but multimodal.

    Output: judge/score_image.json
    """
    judge_dir = run_dir / "judge"
    score_path = judge_dir / "score_image.json"
    if score_path.exists() and not force:
        print(f"  [skip-image] already judged: {run_dir.name}")
        return None

    case = run_spec.get("case", {}) or {}
    prompt_text = case.get("prompt", "")
    case_id = case.get("case_id", "")
    question = case_id.rstrip("/").split("/")[-1]
    model_name = run_spec.get("model_name", "")
    rubrics: list[dict] = image_entry["rubrics"]
    n = len(rubrics)
    if n == 0:
        return None

    # Render artifacts (idempotent). Import here so the module loads even if
    # render dependencies are missing in non-vision setups.
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    try:
        from render_artifacts import render_run, collect_images_for_targets  # type: ignore
    except Exception as exc:
        print(f"  [error] render_artifacts import failed: {exc}")
        return None

    render_dpi = int(judge_profile.get("render_dpi", 144))
    try:
        render_run(run_dir, force=False, dpi=render_dpi)
    except Exception as exc:
        print(f"  [error] render failed for {run_dir.name}: {exc}")
        # Persist a 0-score result so aggregation still sees it.
        judge_dir.mkdir(exist_ok=True)
        result = {
            "question": question, "model": model_name,
            "rubric": {f"rubric{i+1}": {
                "text": (r.get("text") if isinstance(r, dict) else str(r)),
                "score": 0, "image_index": -1,
                "reason": f"渲染失败: {exc}",
            } for i, r in enumerate(rubrics)},
            "raw_total_score": 0, "total_score": 0, "max_score": n,
            "_meta": {"error": "render_failed", "category": image_entry.get("category", "")},
        }
        score_path.write_text(json.dumps(result, ensure_ascii=False, indent=2),
                              encoding="utf-8")
        return result

    judge_dir.mkdir(exist_ok=True)

    judge_model = judge_profile.get("judge_model", "gpt-5.4-mini")
    image_max = int(judge_profile.get("image_max", 20))
    openai_client, judge_model_name = _make_openai_client(judge_model)

    judge_api_kwargs: dict = {}
    reasoning_effort = judge_profile.get("reasoning_effort")
    if reasoning_effort:
        judge_api_kwargs["reasoning_effort"] = reasoning_effort

    t0 = time.time()

    import concurrent.futures as _cf
    JUDGE_WORKERS = int(os.environ.get("JUDGE_ITEM_WORKERS", "8"))

    def _judge_one_image_rubric(args: tuple):
        i, rubric_obj = args
        if isinstance(rubric_obj, str):
            rubric_obj = {"text": rubric_obj, "image_targets": ["any_rendered"]}
        rubric_text = rubric_obj.get("text", "")
        image_targets = rubric_obj.get("image_targets") or ["any_rendered"]

        image_paths = collect_images_for_targets(run_dir, image_targets,
                                                 max_images=image_max)
        if not image_paths:
            return i, f"rubric{i}", rubric_obj, 0, -1, \
                "未提交可渲染的视觉交付（rendered/ 中没有匹配 image_targets 的图片）。"

        prompt = f"""You are a strict medical reviewer. Score the single VISUAL rubric point below against the image(s) of the model's submitted artifact, then give a concise justification.

## Case
{prompt_text}

## Visual rubric point (item {i} of {n})
{rubric_text}

## Submitted artifact image(s)
The next {len(image_paths)} blocks are the rendered images (0-indexed). The total slide/page count of this artifact is {len(image_paths)}.

## Scoring rules
- Score=1 ONLY if the listed visual elements are clearly and explicitly visible in at least one of the provided images.
- Score=0 if the elements are missing, illegible, or only described in surrounding text without an actual visual rendering (e.g. a slide that just says "插入森林图" but contains no plot → 0).
- Do NOT infer presence from filenames, slide titles, or speaker-notes text — judge ONLY what is rendered in the pixels.
- For layout/page-count rubrics (e.g. "PPT 总页数 14-16 张"): use the total number of provided image blocks as the slide count.

## Output rules
- Output ONLY the following JSON (no code block, no prefix/suffix):
{{"score": <0 or 1>, "image_index": <0-based index of the image you used as evidence, or -1 if none>, "reason": "<1-3 sentences in Chinese, naming the specific visual element observed (or missing) and which slide/page it was on>"}}
- If score=0: state exactly which required visual element is missing.
- If score=1: name the specific visual element seen and the image_index where it appears.
"""
        print(f"  [judge-image-rubric {i}/{n}] {run_dir.name}  imgs={len(image_paths)}")
        try:
            raw = _call_vision_judge(openai_client, prompt, image_paths,
                                     judge_model_name, **judge_api_kwargs)
        except Exception as exc:
            return i, f"rubric{i}", rubric_obj, 0, -1, f"vision call failed: {exc}"

        obj = _extract_json(raw) or {}
        score = int(obj.get("score", 0))
        score = 1 if score else 0
        img_idx = int(obj.get("image_index", -1)) if str(obj.get("image_index", -1)).lstrip("-").isdigit() else -1
        reason = obj.get("reason", raw.strip())
        return i, f"rubric{i}", rubric_obj, score, img_idx, reason

    rubric_out: dict[str, dict] = {}
    scores: list[int] = []
    tasks = list(enumerate(rubrics, 1))
    with _cf.ThreadPoolExecutor(max_workers=JUDGE_WORKERS) as pool:
        results = sorted(pool.map(_judge_one_image_rubric, tasks),
                         key=lambda x: x[0])

    # Snapshot the image set used (per rubric — same for all if image_targets identical).
    used_image_summary: dict[str, list[str]] = {}
    for i, key, rubric_obj, score, img_idx, reason in results:
        rubric_text = rubric_obj.get("text", "") if isinstance(rubric_obj, dict) else str(rubric_obj)
        rubric_out[key] = {
            "text": rubric_text,
            "image_targets": (rubric_obj.get("image_targets")
                              if isinstance(rubric_obj, dict) else None),
            "score": score,
            "image_index": img_idx,
            "reason": reason,
        }
        scores.append(score)

    elapsed = time.time() - t0
    raw_total_score = sum(scores)
    # Both tracks count each satisfied criterion once.
    result = {
        "question": question,
        "model": model_name,
        "rubric": rubric_out,
        "raw_total_score": raw_total_score,
        "total_score": raw_total_score,
        "max_score": n,
        "_meta": {
            "judge_model": judge_model,
            "elapsed_s": round(elapsed, 1),
            "run_id": run_dir.name,
            "category": image_entry.get("category", ""),
            "image_max": image_max,
            "render_dpi": render_dpi,
        },
    }
    score_path.write_text(json.dumps(result, ensure_ascii=False, indent=2),
                          encoding="utf-8")
    print(
        f"  [done-image]  {raw_total_score}/{n}  elapsed={elapsed:.0f}s  -> {score_path}"
    )
    return result


def judge_run(run_dir: Path, judge_profile: dict, force: bool = False) -> dict | None:
    judge_dir = run_dir / "judge"
    score_path = judge_dir / "score.json"
    if score_path.exists() and not force:
        print(f"  [skip] already judged: {run_dir.name}")
        return None

    summary_path = run_dir / "summary.json"
    run_spec_path = run_dir / "run.json"
    if not summary_path.exists() or not run_spec_path.exists():
        print(f"  [skip] missing summary or run spec: {run_dir.name}")
        return None

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    run_spec = json.loads(run_spec_path.read_text(encoding="utf-8"))

    if summary.get("status") != "ok":
        print(f"  [skip] run status={summary.get('status')}: {run_dir.name}")
        return None

    # rubric 路径：先按文本/视觉分流，再分别打分
    case_id = (run_spec.get("case") or {}).get("case_id", "")
    rubric_entry = lookup_rubric(case_id)
    image_entry = lookup_image_rubric(case_id)  # legacy explicit image rubrics (may be None)

    missing = _missing_deliverables(run_spec, summary, run_dir / "outputs")
    if missing and (rubric_entry or image_entry):
        # The paper's task examples require zero credit when a required final
        # format is absent. No model calls or router calls are needed here.
        judge_dir.mkdir(exist_ok=True)
        reason = "Missing required submitted deliverable: " + ", ".join(missing)
        result = None
        for entry, filename in [(rubric_entry, "score.json"), (image_entry, "score_image.json")]:
            criteria = (entry or {}).get("rubrics", [])
            scored = {
                "question": case_id.split("/")[-1], "model": run_spec.get("model_name", ""),
                "rubric": {f"rubric{i+1}": {"text": criterion.get("text", "") if isinstance(criterion, dict) else criterion, "score": 0, "reason": reason} for i, criterion in enumerate(criteria)},
                "total_score": 0, "max_score": len(criteria),
                "_meta": {"reason": "missing_required_delivery", "missing_required_outputs": missing},
            }
            (judge_dir / filename).write_text(json.dumps(scored, ensure_ascii=False, indent=2), encoding="utf-8")
            if filename == "score.json":
                result = scored
        return result

    # 用 router 把 rubric_entry.rubrics 拆成 text vs visual 两组
    if rubric_entry and rubric_entry.get("rubrics"):
        router_model = judge_profile.get(
            "router_model", judge_profile.get("judge_model", "gpt-5.4-mini"))
        router_client, router_model_name = _make_openai_client(router_model)
        text_rubs, visual_rubs = _split_rubrics_by_visual(
            rubric_entry["rubrics"], router_client, router_model_name,
            workers=int(os.environ.get("JUDGE_ROUTER_WORKERS", "8")),
        )
        print(f"  [router] {run_dir.name}  text={len(text_rubs)} visual={len(visual_rubs)}")

        # 把分流出来的 visual rubric 合并到 image_entry
        if visual_rubs:
            wrapped = [{"text": r, "image_targets": ["any_rendered"]}
                       for r in visual_rubs]
            if image_entry:
                image_entry = {
                    "category": image_entry.get("category", rubric_entry.get("category", "")),
                    "rubrics": list(image_entry.get("rubrics", [])) + wrapped,
                }
            else:
                image_entry = {
                    "category": rubric_entry.get("category", ""),
                    "rubrics": wrapped,
                }

        # text rubric_entry 只保留非视觉那部分
        rubric_entry = {
            "category": rubric_entry.get("category", ""),
            "rubrics": text_rubs,
        } if text_rubs else None

    # 图像通道（独立, 失败不影响 text 通道）
    if image_entry and image_entry.get("rubrics"):
        try:
            vision_profile_name = judge_profile.get(
                "vision_profile", "rubric_judge_vision")
            try:
                vision_profile = load_judge_profile(vision_profile_name)
            except FileNotFoundError:
                vision_profile = judge_profile  # 复用 text profile 作为兜底
            judge_run_rubric_image(run_dir, image_entry, vision_profile,
                                   run_spec, summary, force=force)
        except Exception as exc:
            print(f"  [error] image judge failed for {run_dir.name}: {exc}")

    if rubric_entry and rubric_entry.get("rubrics"):
        return judge_run_rubric(run_dir, rubric_entry, judge_profile,
                                run_spec, summary, force=force)
    if image_entry and image_entry.get("rubrics"):
        # 全部 rubric 都被分流到视觉通道：text 路径无事可做, 直接结束
        return None

    # 非 rubric 路径：默认一次性 judge（含文件上传）
    outputs_dir = run_dir / "outputs"
    selected_output_files, deliverable_penalty, duplicate_candidates = _select_deliverable_files(outputs_dir, summary)
    output_files = [outputs_dir / f for f in selected_output_files if (outputs_dir / f).exists()]
    if not output_files:
        print(f"  [skip] no output files: {run_dir.name}")
        return None

    judge_dir.mkdir(exist_ok=True)

    # Build judge prompt
    judge_prompt = build_judge_prompt(run_spec, summary, judge_profile, outputs_dir)

    judge_model = judge_profile.get("judge_model", "glm-5")
    openai_client, judge_model_name = _make_openai_client(judge_model)

    judge_api_kwargs: dict = {}
    reasoning_effort = judge_profile.get("reasoning_effort")
    if reasoning_effort:
        judge_api_kwargs["reasoning_effort"] = reasoning_effort

    full_prompt = judge_prompt

    print(f"  [judge] {run_dir.name}  model={judge_model}")
    t0 = time.time()

    try:
        response_text = _call_judge(openai_client, full_prompt, judge_model_name, **judge_api_kwargs)
    except Exception as exc:
        print(f"  [error] judge call failed: {exc}")
        score_path.write_text(json.dumps({"error": str(exc)}, indent=2), encoding="utf-8")
        return None

    elapsed = time.time() - t0
    score_data = _extract_json(response_text) or {"raw_response": response_text, "parse_error": True}

    artifact_penalty = 0  # Reminders are reported separately, not deducted from rubric scores.
    overall_raw = _coerce_numeric_score(score_data.get("overall"))
    if overall_raw is not None:
        adjusted = overall_raw
        if adjusted.is_integer():
            adjusted = int(adjusted)
        score_data["overall_raw"] = overall_raw if not float(overall_raw).is_integer() else int(overall_raw)
        score_data["artifact_reminder_penalty"] = artifact_penalty
        score_data["duplicate_deliverable_penalty"] = 0
        score_data["overall_adjusted"] = adjusted

    score_data["_meta"] = {
        "judge_model": judge_model,
        "elapsed_s": round(elapsed, 1),
        "run_id": run_dir.name,
        "artifact_reminder_count": int(summary.get("artifact_reminder_count", 0) or 0),
        "artifact_delivered_after_reminder": bool(summary.get("artifact_delivered_after_reminder", False)),
        "selected_output_files": selected_output_files,
        "duplicate_deliverable_candidates": duplicate_candidates,
    }

    score_path.write_text(json.dumps(score_data, ensure_ascii=False, indent=2), encoding="utf-8")
    overall = score_data.get("overall", "?")
    print(
        f"  [done]  overall={overall}"
        f"  reminder_penalty={artifact_penalty}"
        f"  duplicate_penalty={deliverable_penalty}"
        f"  elapsed={elapsed:.0f}s  -> {score_path}"
    )
    return score_data


def main() -> int:
    parser = argparse.ArgumentParser(description="LLM-as-judge scoring for eval runs")
    parser.add_argument("experiment", help="Path to experiment YAML")
    parser.add_argument("--run-id", default=None, help="Score only this run")
    parser.add_argument("--force", action="store_true", help="Re-score even if judge/score.json exists")
    parser.add_argument("--judge-model", default=None, help="Override judge model from profile")
    args = parser.parse_args()

    exp_path = Path(args.experiment).resolve()
    if not exp_path.exists():
        print(f"Experiment not found: {exp_path}", file=sys.stderr)
        return 1

    exp = {}
    with exp_path.open(encoding="utf-8") as f:
        exp = yaml.safe_load(f) or {}
    experiment_id = exp["experiment_id"]

    runs_dir = RUNS_DIR / experiment_id
    if not runs_dir.exists():
        print(f"No runs directory: {runs_dir}")
        return 0

    run_dirs = sorted(d for d in runs_dir.iterdir() if d.is_dir())
    if args.run_id:
        run_dirs = [d for d in run_dirs if d.name == args.run_id]

    if not run_dirs:
        print("No run directories found.")
        return 0

    print(f"Experiment : {experiment_id}")
    print(f"Run dirs   : {len(run_dirs)}")

    errors = 0
    rubric_results: list[dict] = []  # for aggregate jsonl

    # run 级并发（可通过环境变量 JUDGE_RUN_WORKERS 覆写，默认 10）
    import concurrent.futures as _cf
    import threading
    RUN_WORKERS = int(os.environ.get("JUDGE_RUN_WORKERS", "10"))
    _lock = threading.Lock()

    def _judge_one_run(run_dir: Path) -> tuple[int, dict | None]:
        """Returns (error_count_delta, rubric_score_dict_or_None)."""
        run_spec_path = run_dir / "run.json"
        if not run_spec_path.exists():
            return (0, None)
        run_spec = json.loads(run_spec_path.read_text(encoding="utf-8"))
        case = run_spec.get("case") or {}
        task_type = case.get("task_type", "pptx")
        task_cfg = load_task_type(task_type)
        case_id = case.get("case_id", "")
        is_rubric = bool(lookup_rubric(case_id))
        is_image_rubric = bool(lookup_image_rubric(case_id))
        # 同时只有 image rubric 也走 rubric profile (judge_run 内部会路由)
        judge_profile_name = ("rubric_judge"
                              if (is_rubric or is_image_rubric)
                              else task_cfg.get("judge_profile", f"{task_type}_judge"))

        try:
            judge_profile = load_judge_profile(judge_profile_name)
        except FileNotFoundError as e:
            print(f"  [error] {e}")
            return (1, None)

        if args.judge_model:
            judge_profile = {**judge_profile, "judge_model": args.judge_model}

        result = judge_run(run_dir, judge_profile, force=args.force)
        # 文本通道有交付即视为 ok; 仅图像 rubric 时改看 score_image.json
        if is_rubric:
            err = 0 if (run_dir / "judge" / "score.json").exists() else 1
        elif is_image_rubric:
            err = 0 if (run_dir / "judge" / "score_image.json").exists() else 1
        else:
            err = 1 if (result is None and not (run_dir / "judge" / "score.json").exists()) else 0

        rub = None
        if is_rubric:
            score_file = run_dir / "judge" / "score.json"
            if score_file.exists():
                try:
                    rub = json.loads(score_file.read_text(encoding="utf-8"))
                except Exception:
                    pass
        return (err, rub)

    print(f"  [judge] run-level workers = {RUN_WORKERS}")
    with _cf.ThreadPoolExecutor(max_workers=RUN_WORKERS) as pool:
        for err_delta, rub in pool.map(_judge_one_run, run_dirs):
            with _lock:
                errors += err_delta
                if rub is not None:
                    rubric_results.append(rub)

    # 聚合 jsonl：扫描整个实验下所有 score.json / score_image.json 重建,
    # 避免并行 --run-id 调用之间相互覆盖. 按 (question, model) 去重后排序.
    experiment_runs_dir = RUNS_DIR / experiment_id
    report_dir = REPO_ROOT / "evals" / "reports" / experiment_id

    # ---- text rubric ----
    all_rubric: dict[tuple, dict] = {}
    for sf in experiment_runs_dir.glob("*/judge/score.json"):
        try:
            d = json.loads(sf.read_text(encoding="utf-8"))
        except Exception:
            continue
        if "rubric" not in d:
            continue
        key = (d.get("question", ""), d.get("model", ""))
        all_rubric[key] = d

    # ---- image rubric ----
    all_image: dict[tuple, dict] = {}
    for sf in experiment_runs_dir.glob("*/judge/score_image.json"):
        try:
            d = json.loads(sf.read_text(encoding="utf-8"))
        except Exception:
            continue
        if "rubric" not in d:
            continue
        key = (d.get("question", ""), d.get("model", ""))
        all_image[key] = d

    if all_rubric or all_image:
        report_dir.mkdir(parents=True, exist_ok=True)

        if all_rubric:
            agg_path = report_dir / "rubric_all.jsonl"
            # 在 text rubric 行上挂载 image 分数, 形成 combined 视图
            with agg_path.open("w", encoding="utf-8") as f:
                for key in sorted(all_rubric):
                    row = dict(all_rubric[key])
                    img = all_image.get(key)
                    if img:
                        row["image_total_score"] = img.get("total_score", 0)
                        row["image_max_score"] = img.get("max_score", 0)
                        row["image_rubric"] = img.get("rubric", {})
                        row["combined_total_score"] = (
                            row.get("total_score", 0) + img.get("total_score", 0)
                        )
                        row["combined_max_score"] = (
                            row.get("max_score", 0) + img.get("max_score", 0)
                        )
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
            print(f"\nRubric 聚合已写入: {agg_path} ({len(all_rubric)} 条)")

        if all_image:
            agg_image_path = report_dir / "rubric_image_all.jsonl"
            with agg_image_path.open("w", encoding="utf-8") as f:
                for key in sorted(all_image):
                    f.write(json.dumps(all_image[key], ensure_ascii=False) + "\n")
            print(f"Image rubric 聚合已写入: {agg_image_path} ({len(all_image)} 条)")

    print(f"\nDone. {len(run_dirs)} runs processed, {errors} errors.")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
