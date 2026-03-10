#!/usr/bin/env python
"""Orchestrate direct model API calls using project routing policy."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from call_model_api import build_request, execute_request, extract_text, get_text  # noqa: E402
from route_ai_task import MODELS, choose_route  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = REPO_ROOT / 'prompts' / 'task_templates.json'
CLAUDE_DOCS_DIR = REPO_ROOT / 'docs' / 'claude'
DEFAULT_ARCHIVE_DIR = REPO_ROOT / 'outputs' / 'ai_runs'

DEFAULT_REVIEWER_CHECKLIST = """Review only with this checklist:
1. correctness defects
2. missing edge cases
3. readability or maintainability risks
4. whether the lead output should be kept or revised
Return concise, actionable findings."""

DEFAULT_OPTIONAL_QUESTION = """Do a narrow sanity check only:
- identify missing edge cases
- identify any cheaper model substitution for the same quality bar
- do not rewrite the full artifact"""


def load_templates() -> Dict[str, Dict[str, str]]:
    if not TEMPLATE_PATH.exists():
        return {}
    return json.loads(TEMPLATE_PATH.read_text(encoding='utf-8'))


def slugify(value: str) -> str:
    value = re.sub(r'[^A-Za-z0-9._-]+', '-', value.strip())
    value = value.strip('-._')
    return value or 'task'


def maybe_seed_dry_run_keys(alias: str, dry_run: bool) -> None:
    if not dry_run:
        return
    provider = MODELS[alias]['provider']
    if provider == 'openai' and not os.environ.get('OPENAI_API_KEY'):
        os.environ['OPENAI_API_KEY'] = 'dry-run-openai-key'
    elif provider == 'anthropic' and not os.environ.get('ANTHROPIC_API_KEY'):
        os.environ['ANTHROPIC_API_KEY'] = 'dry-run-anthropic-key'
    elif provider == 'google' and not os.environ.get('GEMINI_API_KEY'):
        os.environ['GEMINI_API_KEY'] = 'dry-run-gemini-key'


def redact_headers(headers: Dict[str, str]) -> Dict[str, str]:
    safe = dict(headers)
    for key in list(safe):
        if 'key' in key.lower() or 'authorization' in key.lower():
            safe[key] = '<redacted>'
    return safe


def invoke_model(alias: str, prompt: str, system: Optional[str], max_output_tokens: int, temperature: float, dry_run: bool) -> Dict[str, object]:
    maybe_seed_dry_run_keys(alias, dry_run)
    endpoint, headers, body, provider = build_request(alias, prompt, system, max_output_tokens, temperature)
    result: Dict[str, object] = {
        'alias': alias,
        'provider': provider,
        'model': MODELS[alias]['model'],
        'endpoint': endpoint,
        'request_headers': redact_headers(headers),
        'request_body': body,
    }
    if dry_run:
        result['response_text'] = ''
        result['dry_run'] = True
        return result

    payload = execute_request(endpoint, headers, body)
    result['dry_run'] = False
    result['raw_response'] = payload
    result['response_text'] = extract_text(provider, payload)
    return result


def build_reviewer_prompt(task_prompt: str, lead_text: str, checklist: str) -> str:
    return "\n".join([
        'Task to review:',
        task_prompt,
        '',
        'Lead model output:',
        lead_text,
        '',
        checklist.strip(),
    ])


def build_optional_prompt(task_prompt: str, lead_text: str, reviewer_text: str, question: str) -> str:
    return "\n".join([
        'Original task:',
        task_prompt,
        '',
        'Lead output:',
        lead_text,
        '',
        'Reviewer output:',
        reviewer_text,
        '',
        question.strip(),
    ])


def synthesize_summary(route: Dict[str, object], stages: List[Dict[str, object]], skipped: List[str]) -> Dict[str, object]:
    lead_stage = next((item for item in stages if item['stage'] == 'lead'), None)
    reviewer_stage = next((item for item in stages if item['stage'] == 'reviewer'), None)
    optional_stage = next((item for item in stages if item['stage'] == 'optional'), None)
    return {
        'lead_model': route['lead']['model'] if route.get('lead') else None,
        'reviewer_model': route['reviewer']['model'] if route.get('reviewer') else None,
        'optional_model': route['optional']['model'] if route.get('optional') else None,
        'lead_preview': (lead_stage or {}).get('response_text', '')[:400],
        'reviewer_preview': (reviewer_stage or {}).get('response_text', '')[:400],
        'optional_preview': (optional_stage or {}).get('response_text', '')[:400],
        'skipped': skipped,
        'final_guidance': 'Use the lead output as the base artifact; apply reviewer findings before acting on it.',
    }


def find_alias_by_model_name(model_name: str) -> str:
    for alias, value in MODELS.items():
        if value['model'] == model_name:
            return alias
    raise KeyError(f'No alias found for model: {model_name}')


def resolve_task_spec(task_spec_file: Optional[str], task_spec_name: Optional[str]) -> Tuple[str, Optional[str]]:
    if task_spec_file:
        path = Path(task_spec_file)
        if not path.is_absolute():
            path = REPO_ROOT / path
    elif task_spec_name:
        path = CLAUDE_DOCS_DIR / task_spec_name
    else:
        return '', None

    if not path.exists():
        raise FileNotFoundError(f'Task spec not found: {path}')
    return path.read_text(encoding='utf-8', errors='replace'), str(path)


def merge_system_prompt(base_system: Optional[str], template_system: Optional[str]) -> Optional[str]:
    parts = [item.strip() for item in [template_system or '', base_system or ''] if item and item.strip()]
    return '\n\n'.join(parts) if parts else None


def compose_task_prompt(user_prompt: str, template_prelude: Optional[str], task_spec_text: str, task_spec_source: Optional[str]) -> str:
    blocks: List[str] = []
    if template_prelude:
        blocks.append(template_prelude.strip())
    blocks.append('Primary task:\n' + user_prompt.strip())
    if task_spec_text:
        source_line = f'Task spec source: {task_spec_source}' if task_spec_source else 'Task spec source: inline'
        blocks.append(source_line + '\n\n' + task_spec_text.strip())
    return '\n\n'.join(blocks)


def build_archive_path(archive_dir: Path, task_type: str, template_name: Optional[str], dry_run: bool) -> Path:
    archive_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    middle = template_name or task_type
    suffix = 'dryrun' if dry_run else 'live'
    return archive_dir / f'{stamp}_{slugify(middle)}_{suffix}.json'


def render_stage_markdown(stage: Dict[str, object]) -> str:
    body = [
        f"# {stage['stage'].title()} Stage",
        '',
        f"- Alias: `{stage['alias']}`",
        f"- Provider: `{stage['provider']}`",
        f"- Model: `{stage['model']}`",
        f"- Endpoint: `{stage['endpoint']}`",
        f"- Dry run: `{stage.get('dry_run', False)}`",
        '',
        '## Request Headers',
        '```json',
        json.dumps(stage.get('request_headers', {}), ensure_ascii=False, indent=2),
        '```',
        '',
        '## Request Body',
        '```json',
        json.dumps(stage.get('request_body', {}), ensure_ascii=False, indent=2),
        '```',
        '',
        '## Response Text',
        '```text',
        str(stage.get('response_text', '')),
        '```',
    ]
    return '\n'.join(body) + '\n'


def render_prompt_bundle_markdown(report: Dict[str, object]) -> str:
    bundle = report['prompt_bundle']
    body = [
        '# Prompt Bundle',
        '',
        f"- Template: `{bundle.get('template_name') or '-'}`",
        f"- Task spec source: `{bundle.get('task_spec_source') or '-'}`",
        '',
        '## System Prompt',
        '```text',
        str(bundle.get('system_prompt') or ''),
        '```',
        '',
        '## Task Prompt',
        '```text',
        str(bundle.get('task_prompt') or ''),
        '```',
        '',
        '## Reviewer Checklist',
        '```text',
        str(bundle.get('reviewer_checklist') or ''),
        '```',
        '',
        '## Optional Question',
        '```text',
        str(bundle.get('optional_question') or ''),
        '```',
    ]
    return '\n'.join(body) + '\n'


def write_artifact_bundle(report: Dict[str, object], json_path: Path) -> Dict[str, str]:
    artifacts: Dict[str, str] = {}
    prompt_path = json_path.with_name(json_path.stem + '.prompt_bundle.md')
    prompt_path.write_text(render_prompt_bundle_markdown(report), encoding='utf-8')
    artifacts['prompt_bundle'] = str(prompt_path)

    for stage in report['stages']:
        stage_path = json_path.with_name(json_path.stem + f".{stage['stage']}.md")
        stage_path.write_text(render_stage_markdown(stage), encoding='utf-8')
        artifacts[str(stage['stage'])] = str(stage_path)
    return artifacts


def save_report(report: Dict[str, object], output_file: Optional[str], archive_dir: Optional[str], auto_archive: bool, write_stage_artifacts: bool) -> Tuple[Optional[str], Dict[str, str]]:
    path: Optional[Path] = None
    if output_file:
        path = Path(output_file)
        if not path.is_absolute():
            path = REPO_ROOT / path
    elif auto_archive:
        archive_root = Path(archive_dir) if archive_dir else DEFAULT_ARCHIVE_DIR
        if not archive_root.is_absolute():
            archive_root = REPO_ROOT / archive_root
        path = build_archive_path(archive_root, str(report['route']['task_type']), report['prompt_bundle'].get('template_name'), bool(report['dry_run']))

    if not path:
        return None, {}

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    artifacts = write_artifact_bundle(report, path) if write_stage_artifacts else {}
    return str(path), artifacts


def parse_args() -> argparse.Namespace:
    templates = load_templates()
    parser = argparse.ArgumentParser(description='Orchestrate direct model API calls with route-aware cost control')
    parser.add_argument('--task-type', choices=['coding', 'research', 'writing', 'mixed'], required=True)
    parser.add_argument('--risk', choices=['low', 'medium', 'high'], default='medium')
    parser.add_argument('--budget', choices=['low', 'medium', 'high'], default='medium')
    parser.add_argument('--stage', choices=['explore', 'design', 'implement', 'pre_release', 'submission'], default='implement')
    parser.add_argument('--deadline', choices=['urgent', 'normal', 'relaxed'], default='normal')
    parser.add_argument('--code-complexity', choices=['low', 'medium', 'high'], default='medium')
    parser.add_argument('--external-delivery', action='store_true')
    parser.add_argument('--prompt')
    parser.add_argument('--prompt-file')
    parser.add_argument('--system')
    parser.add_argument('--system-file')
    parser.add_argument('--task-template', choices=sorted(templates.keys()))
    parser.add_argument('--task-spec-file')
    parser.add_argument('--task-spec-name')
    parser.add_argument('--reviewer-checklist')
    parser.add_argument('--reviewer-checklist-file')
    parser.add_argument('--optional-question')
    parser.add_argument('--optional-question-file')
    parser.add_argument('--skip-reviewer', action='store_true')
    parser.add_argument('--run-optional', action='store_true')
    parser.add_argument('--max-output-tokens', type=int, default=1600)
    parser.add_argument('--temperature', type=float, default=0.2)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--output-file')
    parser.add_argument('--archive-dir', default=str(DEFAULT_ARCHIVE_DIR))
    parser.add_argument('--no-archive', action='store_true')
    parser.add_argument('--no-stage-artifacts', action='store_true')
    parser.add_argument('--format', choices=['text', 'json'], default='text')
    return parser.parse_args()


def render_text(report: Dict[str, object]) -> str:
    lines = [
        'Model Orchestration Report',
        f"- Task type: {report['route']['task_type']}",
        f"- Template: {report['prompt_bundle'].get('template_name') or '-'}",
        f"- Task spec: {report['prompt_bundle'].get('task_spec_source') or '-'}",
        f"- Max handoffs: {report['route']['max_handoffs']}",
        f"- Dry run: {report['dry_run']}",
        '',
        'Stages:',
    ]
    for stage in report['stages']:
        lines.append(f"- {stage['stage']}: {stage['alias']} / {stage['model']}")
    if report['skipped']:
        lines.append('')
        lines.append('Skipped:')
        for item in report['skipped']:
            lines.append(f'- {item}')
    if report.get('artifacts'):
        lines.append('')
        lines.append('Artifacts:')
        for key, value in report['artifacts'].items():
            lines.append(f'- {key}: {value}')
    lines.append('')
    lines.append('Final Guidance:')
    lines.append(f"- {report['summary']['final_guidance']}")
    return '\n'.join(lines)


def main() -> None:
    args = parse_args()
    templates = load_templates()
    user_prompt = get_text(args.prompt_file, args.prompt)
    base_system_prompt = get_text(args.system_file, args.system) if (args.system_file or args.system is not None) else None
    task_spec_text, task_spec_source = resolve_task_spec(args.task_spec_file, args.task_spec_name)
    template = templates.get(args.task_template or '', {})

    task_prompt = compose_task_prompt(user_prompt, template.get('prompt_prelude'), task_spec_text, task_spec_source)
    system_prompt = merge_system_prompt(base_system_prompt, template.get('system_prompt'))
    reviewer_checklist = get_text(args.reviewer_checklist_file, args.reviewer_checklist) if (args.reviewer_checklist_file or args.reviewer_checklist is not None) else template.get('reviewer_checklist', DEFAULT_REVIEWER_CHECKLIST)
    optional_question = get_text(args.optional_question_file, args.optional_question) if (args.optional_question_file or args.optional_question is not None) else template.get('optional_question', DEFAULT_OPTIONAL_QUESTION)

    route = choose_route(
        task_type=args.task_type,
        risk=args.risk,
        budget=args.budget,
        stage=args.stage,
        deadline=args.deadline,
        code_complexity=args.code_complexity,
        external_delivery=args.external_delivery,
    )

    remaining_handoffs = int(route['max_handoffs'])
    stages: List[Dict[str, object]] = []
    skipped: List[str] = []

    lead_alias = find_alias_by_model_name(route['lead']['model'])
    lead_result = invoke_model(lead_alias, task_prompt, system_prompt, args.max_output_tokens, args.temperature, args.dry_run)
    lead_result['stage'] = 'lead'
    stages.append(lead_result)

    reviewer_text = ''
    reviewer_info = route.get('reviewer')
    if args.skip_reviewer or not reviewer_info or remaining_handoffs <= 0:
        skipped.append('reviewer')
    else:
        reviewer_alias = find_alias_by_model_name(reviewer_info['model'])
        reviewer_prompt = build_reviewer_prompt(task_prompt, str(lead_result.get('response_text', '')), reviewer_checklist)
        reviewer_result = invoke_model(reviewer_alias, reviewer_prompt, None, args.max_output_tokens, min(args.temperature, 0.15), args.dry_run)
        reviewer_result['stage'] = 'reviewer'
        stages.append(reviewer_result)
        reviewer_text = str(reviewer_result.get('response_text', ''))
        remaining_handoffs -= 1

    optional_info = route.get('optional')
    if not args.run_optional:
        skipped.append('optional:not_requested')
    elif not optional_info:
        skipped.append('optional:not_routed')
    elif remaining_handoffs <= 0:
        skipped.append('optional:no_handoff_budget')
    else:
        optional_alias = find_alias_by_model_name(optional_info['model'])
        optional_prompt = build_optional_prompt(task_prompt, str(lead_result.get('response_text', '')), reviewer_text, optional_question)
        optional_result = invoke_model(optional_alias, optional_prompt, None, args.max_output_tokens, min(args.temperature, 0.1), args.dry_run)
        optional_result['stage'] = 'optional'
        stages.append(optional_result)
        remaining_handoffs -= 1

    report = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'dry_run': args.dry_run,
        'route': route,
        'prompt_bundle': {
            'template_name': args.task_template,
            'task_spec_source': task_spec_source,
            'system_prompt': system_prompt,
            'task_prompt': task_prompt,
            'reviewer_checklist': reviewer_checklist,
            'optional_question': optional_question,
        },
        'stages': stages,
        'skipped': skipped,
        'summary': synthesize_summary(route, stages, skipped),
    }
    saved, artifacts = save_report(
        report,
        args.output_file,
        args.archive_dir,
        auto_archive=not args.no_archive,
        write_stage_artifacts=not args.no_stage_artifacts,
    )
    if saved:
        report['saved_to'] = saved
    if artifacts:
        report['artifacts'] = artifacts

    if args.format == 'json':
        print(json.dumps(report, ensure_ascii=True, indent=2))
    else:
        print(render_text(report))
        if saved:
            print(f'\nSaved report: {saved}')


if __name__ == '__main__':
    main()
