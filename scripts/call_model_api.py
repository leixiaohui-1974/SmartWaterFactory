#!/usr/bin/env python
"""Direct API caller for OpenAI, Anthropic, and Gemini."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from typing import Dict, Optional, Tuple

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from route_ai_task import MODELS  # noqa: E402


def get_text(path: Optional[str], inline: Optional[str]) -> str:
    if path:
        with open(path, 'r', encoding='utf-8') as handle:
            return handle.read()
    if inline is not None:
        return inline
    raise ValueError('Either --prompt or --prompt-file is required')



def merge_system_and_prompt(system: Optional[str], prompt: str) -> str:
    if not system:
        return prompt
    return f"System:\n{system}\n\nUser:\n{prompt}"



def build_openai_request(model: str, prompt: str, system: Optional[str], max_output_tokens: int, temperature: float) -> Tuple[str, Dict[str, str], Dict[str, object]]:
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        raise EnvironmentError('OPENAI_API_KEY is not set')
    body: Dict[str, object] = {
        'model': model,
        'input': merge_system_and_prompt(system, prompt),
        'max_output_tokens': max_output_tokens,
        'temperature': temperature,
    }
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }
    return 'https://api.openai.com/v1/responses', headers, body



def build_anthropic_request(model: str, prompt: str, system: Optional[str], max_output_tokens: int, temperature: float) -> Tuple[str, Dict[str, str], Dict[str, object]]:
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        raise EnvironmentError('ANTHROPIC_API_KEY is not set')
    body: Dict[str, object] = {
        'model': model,
        'max_tokens': max_output_tokens,
        'temperature': temperature,
        'messages': [
            {
                'role': 'user',
                'content': prompt,
            }
        ],
    }
    if system:
        body['system'] = system
    headers = {
        'x-api-key': api_key,
        'anthropic-version': '2023-06-01',
        'Content-Type': 'application/json',
    }
    return 'https://api.anthropic.com/v1/messages', headers, body



def build_gemini_request(model: str, prompt: str, system: Optional[str], max_output_tokens: int, temperature: float) -> Tuple[str, Dict[str, str], Dict[str, object]]:
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        raise EnvironmentError('GEMINI_API_KEY is not set')
    body: Dict[str, object] = {
        'contents': [
            {
                'role': 'user',
                'parts': [{'text': merge_system_and_prompt(system, prompt)}],
            }
        ],
        'generationConfig': {
            'temperature': temperature,
            'maxOutputTokens': max_output_tokens,
        },
    }
    headers = {'Content-Type': 'application/json'}
    endpoint = f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}'
    return endpoint, headers, body



def build_request(alias: str, prompt: str, system: Optional[str], max_output_tokens: int, temperature: float) -> Tuple[str, Dict[str, str], Dict[str, object], str]:
    if alias not in MODELS:
        raise KeyError(f'Unknown model alias: {alias}')
    info = MODELS[alias]
    provider = info['provider']
    model = info['model']
    if provider == 'openai':
        endpoint, headers, body = build_openai_request(model, prompt, system, max_output_tokens, temperature)
    elif provider == 'anthropic':
        endpoint, headers, body = build_anthropic_request(model, prompt, system, max_output_tokens, temperature)
    elif provider == 'google':
        endpoint, headers, body = build_gemini_request(model, prompt, system, max_output_tokens, temperature)
    else:
        raise ValueError(f'Unsupported provider: {provider}')
    return endpoint, headers, body, provider



def execute_request(endpoint: str, headers: Dict[str, str], body: Dict[str, object]) -> Dict[str, object]:
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(body).encode('utf-8'),
        headers=headers,
        method='POST',
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.loads(response.read().decode('utf-8'))



def extract_text(provider: str, payload: Dict[str, object]) -> str:
    if provider == 'openai':
        if isinstance(payload.get('output_text'), str):
            return payload['output_text']
        chunks = []
        for item in payload.get('output', []) or []:
            for content in item.get('content', []) or []:
                text = content.get('text') or content.get('output_text')
                if text:
                    chunks.append(text)
        return '\n'.join(chunks).strip()
    if provider == 'anthropic':
        chunks = []
        for item in payload.get('content', []) or []:
            text = item.get('text')
            if text:
                chunks.append(text)
        return '\n'.join(chunks).strip()
    if provider == 'google':
        chunks = []
        for candidate in payload.get('candidates', []) or []:
            content = candidate.get('content', {})
            for part in content.get('parts', []) or []:
                text = part.get('text')
                if text:
                    chunks.append(text)
        return '\n'.join(chunks).strip()
    return ''



def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Call model APIs directly')
    parser.add_argument('--model-alias', choices=sorted(MODELS.keys()), required=True)
    parser.add_argument('--prompt')
    parser.add_argument('--prompt-file')
    parser.add_argument('--system')
    parser.add_argument('--system-file')
    parser.add_argument('--max-output-tokens', type=int, default=1200)
    parser.add_argument('--temperature', type=float, default=0.2)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--raw-json', action='store_true')
    return parser.parse_args()



def main() -> None:
    args = parse_args()
    prompt = get_text(args.prompt_file, args.prompt)
    system = get_text(args.system_file, args.system) if (args.system_file or args.system is not None) else None

    if args.dry_run:
        provider = MODELS[args.model_alias]['provider']
        if provider == 'openai' and not os.environ.get('OPENAI_API_KEY'):
            os.environ['OPENAI_API_KEY'] = 'dry-run-openai-key'
        elif provider == 'anthropic' and not os.environ.get('ANTHROPIC_API_KEY'):
            os.environ['ANTHROPIC_API_KEY'] = 'dry-run-anthropic-key'
        elif provider == 'google' and not os.environ.get('GEMINI_API_KEY'):
            os.environ['GEMINI_API_KEY'] = 'dry-run-gemini-key'

    endpoint, headers, body, provider = build_request(
        args.model_alias,
        prompt,
        system,
        args.max_output_tokens,
        args.temperature,
    )
    if args.dry_run:
        safe_headers = dict(headers)
        for key in list(safe_headers):
            if 'key' in key.lower() or 'authorization' in key.lower():
                safe_headers[key] = '<redacted>'
        print(json.dumps({
            'alias': args.model_alias,
            'provider': provider,
            'endpoint': endpoint,
            'headers': safe_headers,
            'body': body,
        }, ensure_ascii=False, indent=2))
        return

    payload = execute_request(endpoint, headers, body)
    if args.raw_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(extract_text(provider, payload))


if __name__ == '__main__':
    main()
