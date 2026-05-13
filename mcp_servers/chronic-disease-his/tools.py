#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HIS tool definitions + fake handler logic.
8 tools, all fake; they only record what the model called and with which args.
"""

import json
import os
from typing import Any, Dict, List

import mcp.types as types

from session import HISSession


# ====================================================================
# Tool definitions (inputSchema)
# ====================================================================

TOOL_DEFINITIONS: List[types.Tool] = [
    types.Tool(
        name="update_diagnosis",
        description="Record or update diagnoses. Pass a list of diagnoses; each entry has a name and a type (primary/secondary).",
        inputSchema={
            "type": "object",
            "properties": {
                "diagnosis_list": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Diagnosis name, e.g. 'Stage 2 hypertension, high risk'",
                            },
                            "type": {
                                "type": "string",
                                "enum": ["primary", "secondary"],
                                "description": "Diagnosis type",
                            },
                        },
                        "required": ["name", "type"],
                    },
                    "description": "Diagnosis list",
                },
            },
            "required": ["diagnosis_list"],
        },
    ),
    types.Tool(
        name="create_prescription",
        description="Issue a prescription. Record one drug order with drug name, dose, frequency, duration, and route.",
        inputSchema={
            "type": "object",
            "properties": {
                "drug_name": {
                    "type": "string",
                    "description": "Generic drug name, e.g. 'Valsartan', 'Atorvastatin calcium tablets'",
                },
                "dose": {
                    "type": "string",
                    "description": "Single dose, e.g. '80mg', '10mg'",
                },
                "frequency": {
                    "type": "string",
                    "description": "Dosing frequency, e.g. 'qd', 'bid', 'tid', 'qn'",
                },
                "duration": {
                    "type": "string",
                    "description": "Treatment duration, e.g. '30 days', 'long-term', '2 weeks'",
                },
                "route": {
                    "type": "string",
                    "description": "Route of administration, e.g. 'po' (oral), 'iv' (intravenous), 'sc' (subcutaneous)",
                },
            },
            "required": ["drug_name", "dose", "frequency", "duration", "route"],
        },
    ),
    types.Tool(
        name="order_lab_test",
        description="Order a laboratory test. Record the lab investigation to be performed.",
        inputSchema={
            "type": "object",
            "properties": {
                "test_name": {
                    "type": "string",
                    "description": "Lab test name, e.g. 'Glycated hemoglobin (HbA1c)', 'Liver and renal function', 'Full lipid panel'",
                },
                "urgency": {
                    "type": "string",
                    "enum": ["routine", "stat"],
                    "description": "Urgency level; defaults to routine",
                },
            },
            "required": ["test_name"],
        },
    ),
    types.Tool(
        name="order_imaging",
        description="Order an imaging study. Record the imaging examination to be performed.",
        inputSchema={
            "type": "object",
            "properties": {
                "modality": {
                    "type": "string",
                    "description": "Modality, e.g. 'X-ray', 'CT', 'MRI', 'Ultrasound', 'ECG'",
                },
                "body_part": {
                    "type": "string",
                    "description": "Body region, e.g. 'Chest', 'Head', 'Heart', 'Abdomen'",
                },
                "indication": {
                    "type": "string",
                    "description": "Indication / purpose, e.g. 'Assess cardiac structure and function'",
                },
            },
            "required": ["modality", "body_part", "indication"],
        },
    ),
    types.Tool(
        name="create_follow_up_plan",
        description="Create a follow-up plan. Set the follow-up interval, items to monitor, and lifestyle advice.",
        inputSchema={
            "type": "object",
            "properties": {
                "interval": {
                    "type": "string",
                    "description": "Follow-up interval, e.g. '2 weeks', '1 month', '3 months'",
                },
                "items": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Items to check / monitor at follow-up, e.g. ['Blood pressure monitoring', 'Fasting blood glucose', 'Repeat liver and renal function']",
                },
                "lifestyle_advice": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Lifestyle advice, e.g. ['Low-salt diet <6g/day', '150 min of aerobic exercise per week']",
                },
            },
            "required": ["interval", "items"],
        },
    ),
    types.Tool(
        name="submit_referral",
        description="Submit a referral. Refer the patient to another department or a higher-level hospital.",
        inputSchema={
            "type": "object",
            "properties": {
                "department": {
                    "type": "string",
                    "description": "Referral target department, e.g. 'Cardiology', 'Endocrinology', 'Tertiary hospital'",
                },
                "urgency": {
                    "type": "string",
                    "enum": ["routine", "urgent"],
                    "description": "Referral urgency",
                },
                "reason": {
                    "type": "string",
                    "description": "Reason for referral, e.g. 'Poor BP control; needs further evaluation for secondary hypertension'",
                },
            },
            "required": ["department", "urgency", "reason"],
        },
    ),
    types.Tool(
        name="get_pending_orders",
        description="View all orders entered so far (diagnoses, prescriptions, investigations, follow-up plan, etc.) for review before submission.",
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
    types.Tool(
        name="submit_orders",
        description=(
            "Confirm and submit all entered orders. Cannot be modified after submission. "
            "A complete and detailed analysis_conclusion is required at submission, "
            "covering diagnostic reasoning, risk stratification, treatment choices, "
            "investigation/follow-up plan, and referral considerations."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "case_id": {
                    "type": "string",
                    "description": "Case identifier, e.g. 'HIS_HTN_011'. Fill in if known; used for result archiving.",
                },
                "confirm": {
                    "type": "boolean",
                    "description": "Confirm submission. Must be true.",
                },
                "analysis_conclusion": {
                    "type": "string",
                    "description": (
                        "Final analytic conclusion. Be as detailed as possible; at minimum cover: "
                        "key clinical judgement / diagnostic reasoning, risk stratification or severity, "
                        "rationale for pharmacologic and non-pharmacologic treatment, investigation/monitoring plan, "
                        "follow-up plan, and any need for up-referral."
                    ),
                },
            },
            "required": ["confirm", "analysis_conclusion"],
        },
    ),
]


# ====================================================================
# Tool handlers
# ====================================================================

def handle_update_diagnosis(session: HISSession, args: Dict[str, Any]) -> Dict[str, Any]:
    diagnosis_list = args.get("diagnosis_list", [])
    if not diagnosis_list:
        result = {"status": "error", "message": "diagnosis_list cannot be empty"}
        session.log_call("update_diagnosis", args, result)
        return result

    session.records["diagnoses"] = diagnosis_list
    result = {
        "status": "recorded",
        "diagnosis_count": len(diagnosis_list),
        "diagnoses": [d.get("name", "") for d in diagnosis_list],
    }
    session.log_call("update_diagnosis", args, result)
    return result


def handle_create_prescription(session: HISSession, args: Dict[str, Any]) -> Dict[str, Any]:
    rx = {
        "drug_name": args.get("drug_name", ""),
        "dose": args.get("dose", ""),
        "frequency": args.get("frequency", ""),
        "duration": args.get("duration", ""),
        "route": args.get("route", ""),
    }
    session.records["prescriptions"].append(rx)
    rx_id = "Rx{:03d}".format(len(session.records["prescriptions"]))
    result = {
        "status": "recorded",
        "prescription_id": rx_id,
        "drug_name": rx["drug_name"],
        "dose": rx["dose"],
        "frequency": rx["frequency"],
    }
    session.log_call("create_prescription", args, result)
    return result


def handle_order_lab_test(session: HISSession, args: Dict[str, Any]) -> Dict[str, Any]:
    order = {
        "test_name": args.get("test_name", ""),
        "urgency": args.get("urgency", "routine"),
    }
    session.records["lab_orders"].append(order)
    order_id = "Lab{:03d}".format(len(session.records["lab_orders"]))
    result = {
        "status": "recorded",
        "order_id": order_id,
        "test_name": order["test_name"],
        "urgency": order["urgency"],
    }
    session.log_call("order_lab_test", args, result)
    return result


def handle_order_imaging(session: HISSession, args: Dict[str, Any]) -> Dict[str, Any]:
    order = {
        "modality": args.get("modality", ""),
        "body_part": args.get("body_part", ""),
        "indication": args.get("indication", ""),
    }
    session.records["imaging_orders"].append(order)
    order_id = "Img{:03d}".format(len(session.records["imaging_orders"]))
    result = {
        "status": "recorded",
        "order_id": order_id,
        "modality": order["modality"],
        "body_part": order["body_part"],
    }
    session.log_call("order_imaging", args, result)
    return result


def handle_create_follow_up_plan(session: HISSession, args: Dict[str, Any]) -> Dict[str, Any]:
    plan = {
        "interval": args.get("interval", ""),
        "items": args.get("items", []),
        "lifestyle_advice": args.get("lifestyle_advice", []),
    }
    session.records["follow_up_plan"] = plan
    result = {
        "status": "recorded",
        "interval": plan["interval"],
        "item_count": len(plan["items"]),
        "advice_count": len(plan.get("lifestyle_advice", [])),
    }
    session.log_call("create_follow_up_plan", args, result)
    return result


def handle_submit_referral(session: HISSession, args: Dict[str, Any]) -> Dict[str, Any]:
    referral = {
        "department": args.get("department", ""),
        "urgency": args.get("urgency", "routine"),
        "reason": args.get("reason", ""),
    }
    session.records["referrals"].append(referral)
    ref_id = "Ref{:03d}".format(len(session.records["referrals"]))
    result = {
        "status": "recorded",
        "referral_id": ref_id,
        "department": referral["department"],
        "urgency": referral["urgency"],
    }
    session.log_call("submit_referral", args, result)
    return result


def handle_get_pending_orders(session: HISSession, args: Dict[str, Any]) -> Dict[str, Any]:
    result = {
        "status": "ok",
        "case_id": session.case_id,
        "patient_loaded": session.patient_loaded,
        "submitted": session.submitted,
        "pending_orders": {
            "diagnoses": session.records["diagnoses"],
            "prescriptions": session.records["prescriptions"],
            "lab_orders": session.records["lab_orders"],
            "imaging_orders": session.records["imaging_orders"],
            "follow_up_plan": session.records["follow_up_plan"],
            "referrals": session.records["referrals"],
        },
        "summary": {
            "diagnosis_count": len(session.records["diagnoses"]),
            "prescription_count": len(session.records["prescriptions"]),
            "lab_order_count": len(session.records["lab_orders"]),
            "imaging_order_count": len(session.records["imaging_orders"]),
            "has_follow_up": bool(session.records["follow_up_plan"]),
            "referral_count": len(session.records["referrals"]),
        },
    }
    session.log_call("get_pending_orders", args, result)
    return result


def handle_submit_orders(session: HISSession, args: Dict[str, Any]) -> Dict[str, Any]:
    if session.submitted:
        result = {"status": "error", "message": "Orders already submitted; cannot submit again."}
        session.log_call("submit_orders", args, result)
        return result

    confirm = args.get("confirm", False)
    if not confirm:
        result = {"status": "error", "message": "Set confirm=true to confirm submission."}
        session.log_call("submit_orders", args, result)
        return result

    analysis_conclusion = str(args.get("analysis_conclusion", "")).strip()
    if not analysis_conclusion:
        result = {
            "status": "error",
            "message": "analysis_conclusion is required before submission; provide a complete, detailed analytic conclusion.",
        }
        session.log_call("submit_orders", args, result)
        return result

    case_id = str(args.get("case_id", "")).strip()
    if case_id and not session.case_id:
        session.case_id = case_id

    session.records["analysis_conclusion"] = analysis_conclusion
    session.submitted = True
    session.log_call("submit_orders", args, {
        "status": "submitted",
        "analysis_conclusion_chars": len(analysis_conclusion),
    })

    # flush to JSONL
    session.flush_to_jsonl()

    result = {
        "status": "submitted",
        "case_id": session.case_id,
        "message": "All orders submitted; case record has been saved.",
        "analysis_conclusion_chars": len(analysis_conclusion),
        "summary": {
            "diagnosis_count": len(session.records["diagnoses"]),
            "prescription_count": len(session.records["prescriptions"]),
            "lab_order_count": len(session.records["lab_orders"]),
            "imaging_order_count": len(session.records["imaging_orders"]),
            "has_follow_up": bool(session.records["follow_up_plan"]),
            "referral_count": len(session.records["referrals"]),
        },
    }
    return result


# ====================================================================
# Dispatch
# ====================================================================

_HANDLER_MAP = {
    "update_diagnosis": handle_update_diagnosis,
    "create_prescription": handle_create_prescription,
    "order_lab_test": handle_order_lab_test,
    "order_imaging": handle_order_imaging,
    "create_follow_up_plan": handle_create_follow_up_plan,
    "submit_referral": handle_submit_referral,
    "get_pending_orders": handle_get_pending_orders,
    "submit_orders": handle_submit_orders,
}


def dispatch(tool_name: str, arguments: Dict[str, Any],
             session: HISSession) -> Dict[str, Any]:
    """Dispatch by tool name to the corresponding handler.

    Uses atomic_call() to make the read-modify-write transactional:
    parallel subagent MCP processes won't lose each other's updates.
    """
    handler = _HANDLER_MAP.get(tool_name)
    with session.atomic_call():
        if handler is None:
            result = {"status": "error", "message": "Unknown tool: {}".format(tool_name)}
            session.log_call(tool_name, arguments, result)
            return result
        return handler(session, arguments)
