#!/usr/bin/env python3
"""
汇总 experiment 下每个 run 的 token 用量与 OpenRouter 费用。

扫描 evals/runs/{experiment_id}/*/conversation_*.jsonl，对每条 AI 消息的
usage_metadata 累加 input_tokens / output_tokens；
读 OpenRouter /api/v1/models 实时定价（模型名取自 run.json 的 model_name），
对非 OpenRouter 模型（azure / 内网）按 cost=0 处理。

输出:
  evals/reports/{experiment_id}/usage_cost.jsonl   每 run 一条
  evals/reports/{experiment_id}/usage_cost.xlsx    表格 + 汇总

用法:
  python scripts/compute_usage_cost.py exp_junxiu_0424_glm5_or_smoke
  python scripts/compute_usage_cost.py exp_junxiu_0424_glm5_or_smoke --with-judge-scores
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from typing import Dict, Any, Optional

import urllib.request

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNS_ROOT = REPO_ROOT / "evals" / "runs"
REPORTS_ROOT = REPO_ROOT / "evals" / "reports"
CONFIG_YAML = REPO_ROOT / "config.yaml"

HEADER_FILL = PatternFill(start_color="305496", end_color="305496", fill_type="solid")
HEADER_FONT = Font(bold=True, color="FFFFFF")
TOTAL_FILL  = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")

# Fallback pricing ($/token) if OpenRouter /models 不可达
FALLBACK_PRICING = {
    "z-ai/glm-5":   {"prompt": 0.60e-6, "completion": 2.08e-6},
    "z-ai/glm-4.7": {"prompt": 0.38e-6, "completion": 1.74e-6},
    "z-ai/glm-4.6": {"prompt": 0.39e-6, "completion": 1.90e-6},
}


# ── model_name → openrouter model id 映射（从 config.yaml 的 models.[].model 字段取）──
def build_name_to_openrouter_id() -> Dict[str, str]:
    if not CONFIG_YAML.exists():
        return {}
    cfg = yaml.safe_load(CONFIG_YAML.read_text(encoding="utf-8")) or {}
    mapping: Dict[str, str] = {}
    for m in cfg.get("models") or []:
        name = m.get("name")
        model_id = m.get("model")
        base = (m.get("base_url") or "").lower()
        use = (m.get("use") or "").lower()
        # OpenRouter 模型识别：要么 base_url 里有 "openrouter"（chat/completions 路径），
        # 要么 use 指向 openrouter_responses（Responses API 路径，URL 硬编码在 adapter 里）
        is_openrouter = "openrouter" in base or "openrouter_responses" in use
        if name and model_id and is_openrouter:
            mapping[name] = model_id
    return mapping


def fetch_openrouter_pricing() -> Dict[str, Dict[str, float]]:
    """Return {"z-ai/glm-5": {"prompt": 6e-7, "completion": 2.08e-6}, ...}"""
    try:
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/models",
            headers={"User-Agent": "deerflow-cost/1.0"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.load(resp)
    except Exception as e:
        print(f"[warn] 拉 OpenRouter /models 失败，使用 fallback 定价: {e}", file=sys.stderr)
        return FALLBACK_PRICING
    out: Dict[str, Dict[str, float]] = {}
    for m in data.get("data", []):
        mid = m.get("id")
        p = m.get("pricing") or {}
        try:
            out[mid] = {
                "prompt": float(p.get("prompt", 0) or 0),
                "completion": float(p.get("completion", 0) or 0),
                # OpenRouter 暴露的 cache 价。部分模型缺失（如 OpenAI 仅有 cache_read），
                # 缺失时下游 fallback 到 prompt 价。
                "cache_read":  float(p.get("input_cache_read", 0) or 0),
                "cache_write": float(p.get("input_cache_write", 0) or 0),
            }
        except (TypeError, ValueError):
            continue
    # 合并 fallback，避免某些 id 在 API 返回里缺失
    for k, v in FALLBACK_PRICING.items():
        out.setdefault(k, v)
    return out


# ── per-run usage accumulator ───────────────────────────────────────────────
def accumulate_run_usage(run_dir: Path) -> Dict[str, int]:
    """累加一次 run 中所有 LLM call 的 token usage。

    取最后一个 ``type=values`` 事件（langgraph 的最终状态快照）的 messages 数组，
    对每条 ai message 的 ``usage_metadata`` 累加。这同时兼容：
      - chat/completions 路径（每次 LLM call 一条 ai msg，每个都有 usage_metadata）
      - Responses API 路径（gpt-5.x：每次 call 也是一条 ai msg，但顶层 ``data.usage_metadata`` 不会按调用累加）

    对比验证：与 ``end`` 事件的 ``data.usage`` 完全一致。
    """
    total = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0,
             "reasoning_tokens": 0, "cache_read_tokens": 0, "ai_messages": 0}
    for conv in run_dir.glob("conversation_*.jsonl"):
        # 找最后一个含 messages 的 values 事件
        final_messages: list = []
        for line in conv.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("type") != "values":
                continue
            data = rec.get("data")
            if not isinstance(data, dict):
                continue
            msgs = data.get("messages") or []
            if msgs:
                final_messages = msgs
        # 对 final state 中每条 ai message 的 usage_metadata 累加
        for m in final_messages:
            if not isinstance(m, dict) or m.get("type") != "ai":
                continue
            um = m.get("usage_metadata") or {}
            it = int(um.get("input_tokens") or 0)
            ot = int(um.get("output_tokens") or 0)
            if it == 0 and ot == 0:
                continue
            rsn = int((um.get("output_token_details") or {}).get("reasoning") or 0)
            cache_read = int((um.get("input_token_details") or {}).get("cache_read") or 0)
            total["input_tokens"]   += it
            total["output_tokens"]  += ot
            total["total_tokens"]   += int(um.get("total_tokens") or (it + ot))
            total["reasoning_tokens"] += rsn
            total["cache_read_tokens"] += cache_read
            total["ai_messages"]    += 1
    return total


def load_run_meta(run_dir: Path) -> Dict[str, Any]:
    meta = {"run_id": run_dir.name, "model_name": "", "case_id": "", "status": "", "elapsed_s": 0}
    r_json = run_dir / "run.json"
    s_json = run_dir / "summary.json"
    if r_json.exists():
        try:
            d = json.loads(r_json.read_text(encoding="utf-8"))
            meta["model_name"] = d.get("model_name", "")
            meta["case_id"] = (d.get("case") or {}).get("case_id", "")
        except Exception:
            pass
    if s_json.exists():
        try:
            d = json.loads(s_json.read_text(encoding="utf-8"))
            meta["status"] = d.get("status", "")
            meta["elapsed_s"] = d.get("elapsed_s", 0)
        except Exception:
            pass
    return meta


def load_judge_scores(experiment_id: str) -> Dict[tuple, Dict[str, int]]:
    """读 evals/reports/{exp}/rubric_all.jsonl, 返回 {(question, model): {total,max}}"""
    agg = REPORTS_ROOT / experiment_id / "rubric_all.jsonl"
    out: Dict[tuple, Dict[str, int]] = {}
    if not agg.exists():
        return out
    for line in agg.read_text(encoding="utf-8").splitlines():
        if not line.strip(): continue
        try:
            d = json.loads(line)
        except json.JSONDecodeError: continue
        q = d.get("question") or d.get("case_id", "").split("/")[-1]
        m = d.get("model", "")
        out[(q, m)] = {
            "total_score": d.get("total_score"),
            "max_score": d.get("max_score"),
        }
    return out


# ── main compute ────────────────────────────────────────────────────────────
def compute(experiment_id: str, with_judge: bool = True) -> list[dict]:
    exp_runs_dir = RUNS_ROOT / experiment_id
    if not exp_runs_dir.exists():
        print(f"[error] 未找到实验 runs 目录: {exp_runs_dir}", file=sys.stderr)
        sys.exit(1)

    name_to_or = build_name_to_openrouter_id()
    pricing = fetch_openrouter_pricing()
    judge_scores = load_judge_scores(experiment_id) if with_judge else {}

    rows = []
    for run_dir in sorted(exp_runs_dir.iterdir()):
        if not run_dir.is_dir(): continue
        meta = load_run_meta(run_dir)
        usage = accumulate_run_usage(run_dir)

        or_model_id = name_to_or.get(meta["model_name"], "")  # may be empty for azure
        p = pricing.get(or_model_id, {"prompt": 0.0, "completion": 0.0, "cache_read": 0.0, "cache_write": 0.0})
        # 拆分价格: cache_read 走 cache_read 价, 其余 input 走 prompt 价 (cache_write 在 langchain 不可见, 暂按 prompt 价吸收)
        cache_read_tok = usage.get("cache_read_tokens", 0) or 0
        non_cache_input = max(0, usage["input_tokens"] - cache_read_tok)
        cache_read_price = p.get("cache_read") or p["prompt"]   # 缺失时回退到 prompt 价
        cost_usd = (
            non_cache_input          * p["prompt"]
          + cache_read_tok           * cache_read_price
          + usage["output_tokens"]   * p["completion"]
        )

        q_key = (meta["case_id"] or "").split("/")[-1]
        score = judge_scores.get((q_key, meta["model_name"])) or {}

        rows.append({
            "run_id": meta["run_id"],
            "case_id": meta["case_id"],
            "question": q_key,
            "model_name": meta["model_name"],
            "openrouter_model_id": or_model_id or "—",
            "status": meta["status"],
            "elapsed_s": meta["elapsed_s"],
            "input_tokens": usage["input_tokens"],
            "cache_read_tokens": cache_read_tok,
            "output_tokens": usage["output_tokens"],
            "reasoning_tokens": usage.get("reasoning_tokens", 0),
            "total_tokens": usage["total_tokens"],
            "ai_messages": usage["ai_messages"],
            "prompt_price_per_tok":     p["prompt"],
            "completion_price_per_tok": p["completion"],
            "cache_read_price_per_tok": cache_read_price,
            "cost_usd": round(cost_usd, 6),
            "total_score": score.get("total_score"),
            "max_score":   score.get("max_score"),
        })
    return rows


def write_jsonl(rows: list[dict], path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def write_xlsx(rows: list[dict], path: Path, experiment_id: str):
    wb = Workbook()
    ws = wb.active
    ws.title = "Usage & Cost"
    headers = [
        "question", "model_name", "status", "elapsed_s",
        "input_tokens", "cache_read_tokens", "output_tokens", "total_tokens",
        "ai_messages", "cost_usd",
        "total_score", "max_score",
        "openrouter_model_id", "run_id",
    ]
    for c, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=c, value=h)
        cell.fill = HEADER_FILL; cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for ri, r in enumerate(rows, 2):
        for ci, h in enumerate(headers, 1):
            v = r.get(h, "")
            cell = ws.cell(row=ri, column=ci, value=v)
            cell.alignment = Alignment(vertical="center", wrap_text=True)
            if h == "cost_usd":
                cell.number_format = "$#,##0.000000"
            if h in ("input_tokens", "output_tokens", "total_tokens"):
                cell.number_format = "#,##0"

    # totals row
    last_row = len(rows) + 2
    ws.cell(row=last_row, column=1, value="TOTAL").font = Font(bold=True)
    for idx, h in enumerate(headers, 1):
        if h in ("input_tokens", "output_tokens", "total_tokens", "ai_messages", "cost_usd", "elapsed_s"):
            col = get_column_letter(idx)
            cell = ws.cell(row=last_row, column=idx,
                          value=f"=SUM({col}2:{col}{last_row-1})")
            cell.fill = TOTAL_FILL; cell.font = Font(bold=True)
            if h == "cost_usd":
                cell.number_format = "$#,##0.000000"
            elif h == "elapsed_s":
                cell.number_format = "0.0"
            else:
                cell.number_format = "#,##0"
    # average cost row
    avg_row = last_row + 1
    ws.cell(row=avg_row, column=1, value="AVG / 题").font = Font(bold=True, italic=True)
    n = len(rows) or 1
    for idx, h in enumerate(headers, 1):
        if h in ("input_tokens", "output_tokens", "total_tokens", "cost_usd", "elapsed_s"):
            col = get_column_letter(idx)
            cell = ws.cell(row=avg_row, column=idx, value=f"={col}{last_row}/{n}")
            cell.fill = TOTAL_FILL; cell.font = Font(italic=True)
            cell.number_format = "$#,##0.000000" if h == "cost_usd" else "0.0" if h == "elapsed_s" else "#,##0"

    widths = {"question": 40, "model_name": 16, "status": 10, "elapsed_s": 10,
              "input_tokens": 14, "output_tokens": 14, "total_tokens": 14,
              "ai_messages": 12, "cost_usd": 14, "total_score": 12, "max_score": 10,
              "openrouter_model_id": 18, "run_id": 50}
    for idx, h in enumerate(headers, 1):
        ws.column_dimensions[get_column_letter(idx)].width = widths.get(h, 14)
    ws.freeze_panes = "A2"

    # 备注 sheet
    ws2 = wb.create_sheet("Meta")
    ws2["A1"] = "experiment_id"; ws2["B1"] = experiment_id
    ws2["A2"] = "pricing_source"; ws2["B2"] = "https://openrouter.ai/api/v1/models (fallback: hardcoded)"
    ws2["A3"] = "tokens_source"; ws2["B3"] = "evals/runs/{exp}/{run}/conversation_*.jsonl (usage_metadata)"
    ws2.column_dimensions["A"].width = 18
    ws2.column_dimensions["B"].width = 80

    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("experiment_id", help="experiment id (目录名), e.g. exp_junxiu_0424_glm5_or_smoke")
    ap.add_argument("--no-judge", action="store_true", help="不合并 judge 分数")
    args = ap.parse_args()

    rows = compute(args.experiment_id, with_judge=not args.no_judge)
    if not rows:
        print("[warn] 无 run，退出")
        return 1

    out_dir = REPORTS_ROOT / args.experiment_id
    jsonl_path = out_dir / "usage_cost.jsonl"
    xlsx_path  = out_dir / "usage_cost.xlsx"
    write_jsonl(rows, jsonl_path)
    write_xlsx(rows, xlsx_path, args.experiment_id)

    n = len(rows)
    tin = sum(r["input_tokens"]  for r in rows)
    tout = sum(r["output_tokens"] for r in rows)
    total_cost = sum(r["cost_usd"]     for r in rows)
    print(f"\n=== {args.experiment_id} ===")
    print(f"runs:          {n}")
    print(f"input tokens:  {tin:,}")
    print(f"output tokens: {tout:,}")
    print(f"total cost:    ${total_cost:.6f}")
    print(f"avg cost/run:  ${total_cost/n:.6f}")
    print(f"\njsonl: {jsonl_path}")
    print(f"xlsx:  {xlsx_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
