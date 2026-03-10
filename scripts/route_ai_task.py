#!/usr/bin/env python
"""Route SmartWaterFactory tasks across direct model APIs."""

from __future__ import annotations

import argparse
import json
from typing import Dict, List, Optional

MODELS = {
    "openai_coder": {
        "provider": "openai",
        "model": "gpt-5.2-codex",
        "endpoint": "https://api.openai.com/v1/responses",
        "role": "Hard coding, debugging, refactoring, agentic edits",
    },
    "openai_mini": {
        "provider": "openai",
        "model": "gpt-5-mini",
        "endpoint": "https://api.openai.com/v1/responses",
        "role": "Cheap deterministic rewrites, parsing, glue tasks",
    },
    "claude_review": {
        "provider": "anthropic",
        "model": "claude-sonnet-4-20250514",
        "endpoint": "https://api.anthropic.com/v1/messages",
        "role": "Review, edge cases, readability, architecture prose",
    },
    "claude_opus": {
        "provider": "anthropic",
        "model": "claude-opus-4-1-20250805",
        "endpoint": "https://api.anthropic.com/v1/messages",
        "role": "High-stakes external writing only",
    },
    "gemini_pro": {
        "provider": "google",
        "model": "gemini-2.5-pro",
        "endpoint": "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent",
        "role": "Deep research, non-obvious branching, long-context synthesis",
    },
    "gemini_flash": {
        "provider": "google",
        "model": "gemini-2.5-flash-lite",
        "endpoint": "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent",
        "role": "Cheap scans, extraction, broad sanity checks, bulk parallelism",
    },
}


def pack(name: Optional[str]) -> Optional[Dict[str, str]]:
    if not name:
        return None
    return dict(MODELS[name])



def choose_route(
    task_type: str,
    risk: str,
    budget: str,
    stage: str,
    deadline: str,
    code_complexity: str,
    external_delivery: bool,
) -> Dict[str, object]:
    lead = "openai_coder"
    reviewer: Optional[str] = "claude_review"
    optional: Optional[str] = None
    max_handoffs = 2
    notes: List[str] = []

    if task_type == "coding":
        if budget == "low" and risk == "low" and code_complexity == "low":
            lead = "openai_mini"
            reviewer = "gemini_flash"
            notes.append("Low-risk mechanical coding uses the cheaper OpenAI small model first.")
        else:
            lead = "openai_coder"
            reviewer = "claude_review"
            if budget != "low":
                optional = "gemini_flash"
        notes.append("Keep OpenAI as implementation source of truth for reproducible code edits.")

    elif task_type == "research":
        if budget == "low":
            lead = "gemini_flash"
            reviewer = "openai_mini"
            notes.append("Budget-first research uses Gemini Flash-Lite for wide scans.")
        else:
            lead = "gemini_pro"
            reviewer = "openai_coder" if stage in {"implement", "pre_release"} else "openai_mini"
            if risk == "high" and budget == "high":
                optional = "claude_review"
        notes.append("Convert research output into runnable artifacts only after pruning the search space.")

    elif task_type == "writing":
        lead = "claude_review"
        reviewer = "openai_mini"
        if external_delivery and risk == "high" and budget == "high":
            optional = "claude_opus"
        elif budget != "low":
            optional = "gemini_flash"
        notes.append("Use Claude for narrative quality; use cheaper models for consistency checks.")

    elif task_type == "mixed":
        if stage in {"implement", "pre_release"} or deadline == "urgent":
            lead = "openai_coder"
            reviewer = "claude_review"
            if budget != "low":
                optional = "gemini_flash"
            notes.append("Mixed implementation tasks are code-dominant, so the coding model leads.")
        else:
            lead = "claude_review"
            reviewer = "openai_mini"
            optional = "gemini_pro" if budget == "high" else "gemini_flash"
            notes.append("Mixed design tasks start from specification quality, then compress into code work.")

    if stage == "submission" and external_delivery and risk == "high" and budget != "low":
        optional = "claude_opus"

    if budget == "low":
        max_handoffs = 1
        notes.append("Low-budget mode caps handoffs at one reviewer pass.")
    else:
        notes.append("Default mode allows one lead pass plus one focused reviewer pass.")

    execution_flow = [
        "Freeze acceptance criteria before prompting any API.",
        "Run the lead model once to produce a concrete artifact.",
        "Run the reviewer with a checklist, not an open-ended rewrite.",
    ]
    if optional:
        execution_flow.append("Use the optional model only for a narrow, pre-defined question.")
    execution_flow.append("Merge into one final artifact and validate locally.")

    guardrails = [
        "Prefer cached prompts / repeated system prompts where the provider supports caching.",
        "Use batch APIs only for bulk offline extraction or large review queues.",
        "Avoid premium long-context modes unless the task genuinely needs them.",
        "Do not exceed the planned handoff count unless a concrete defect is found.",
    ]

    return {
        "mode": "direct_api",
        "task_type": task_type,
        "lead": pack(lead),
        "reviewer": pack(reviewer),
        "optional": pack(optional),
        "max_handoffs": max_handoffs,
        "execution_flow": execution_flow,
        "guardrails": guardrails,
        "notes": notes,
        "recommended_env": {
            "OPENAI_API_KEY": "for OpenAI Responses API",
            "ANTHROPIC_API_KEY": "for Anthropic Messages API",
            "GEMINI_API_KEY": "for Gemini Developer API",
        },
    }



def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Route SmartWaterFactory tasks across direct model APIs")
    parser.add_argument("--task-type", choices=["coding", "research", "writing", "mixed"], required=True)
    parser.add_argument("--risk", choices=["low", "medium", "high"], default="medium")
    parser.add_argument("--budget", choices=["low", "medium", "high"], default="medium")
    parser.add_argument("--stage", choices=["explore", "design", "implement", "pre_release", "submission"], default="implement")
    parser.add_argument("--deadline", choices=["urgent", "normal", "relaxed"], default="normal")
    parser.add_argument("--code-complexity", choices=["low", "medium", "high"], default="medium")
    parser.add_argument("--external-delivery", action="store_true")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    return parser.parse_args()



def render_text(result: Dict[str, object]) -> str:
    def model_line(label: str, item: Optional[Dict[str, str]]) -> List[str]:
        if not item:
            return [f"- {label}: None"]
        return [
            f"- {label}: {item['provider']} / {item['model']}",
            f"  endpoint: {item['endpoint']}",
            f"  role: {item['role']}",
        ]

    lines: List[str] = [
        "Direct API Route",
        f"- Mode: {result['mode']}",
        f"- Max handoffs: {result['max_handoffs']}",
    ]
    lines.extend(model_line("Lead", result["lead"]))
    lines.extend(model_line("Reviewer", result["reviewer"]))
    lines.extend(model_line("Optional", result["optional"]))
    lines.append("")
    lines.append("Execution Flow:")
    for index, step in enumerate(result["execution_flow"], start=1):
        lines.append(f"{index}. {step}")
    lines.append("")
    lines.append("Guardrails:")
    for item in result["guardrails"]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("Notes:")
    for item in result["notes"]:
        lines.append(f"- {item}")
    return "\n".join(lines)



def main() -> None:
    args = parse_args()
    result = choose_route(
        task_type=args.task_type,
        risk=args.risk,
        budget=args.budget,
        stage=args.stage,
        deadline=args.deadline,
        code_complexity=args.code_complexity,
        external_delivery=args.external_delivery,
    )
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(render_text(result))


if __name__ == "__main__":
    main()
