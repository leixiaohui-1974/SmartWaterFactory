import json
import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'call_model_api.py'


class TestCallModelAPIScript(unittest.TestCase):
    def test_dry_run_outputs_openai_request_shape(self):
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                '--model-alias', 'openai_mini',
                '--prompt', 'hello',
                '--dry-run',
            ],
            capture_output=True,
            text=True,
            check=False,
            cwd=str(ROOT),
            env={**os.environ, 'OPENAI_API_KEY': 'test-openai-key'},
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload['provider'], 'openai')
        self.assertIn('/v1/responses', payload['endpoint'])
        self.assertEqual(payload['body']['model'], 'gpt-5-mini')

    def test_dry_run_outputs_gemini_request_shape(self):
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                '--model-alias', 'gemini_flash',
                '--prompt', 'hello',
                '--dry-run',
            ],
            capture_output=True,
            text=True,
            check=False,
            cwd=str(ROOT),
            env={**os.environ, 'GEMINI_API_KEY': 'test-gemini-key'},
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload['provider'], 'google')
        self.assertIn('generateContent', payload['endpoint'])
        self.assertEqual(payload['body']['contents'][0]['parts'][0]['text'], 'hello')


if __name__ == '__main__':
    unittest.main()
