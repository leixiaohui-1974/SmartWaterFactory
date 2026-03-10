import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'route_ai_task.py'


class TestRouteAITaskScript(unittest.TestCase):
    def run_route(self, *args):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), *args, '--format', 'json'],
            capture_output=True,
            text=True,
            check=True,
            cwd=str(ROOT),
        )
        return json.loads(result.stdout)

    def test_coding_route_prefers_codex_and_claude(self):
        data = self.run_route(
            '--task-type', 'coding',
            '--risk', 'medium',
            '--budget', 'medium',
            '--stage', 'implement',
            '--deadline', 'urgent',
        )
        self.assertEqual(data['mode'], 'direct_api')
        self.assertEqual(data['lead']['model'], 'gpt-5.2-codex')
        self.assertEqual(data['reviewer']['model'], 'claude-sonnet-4-20250514')

    def test_low_budget_research_prefers_flash_lite(self):
        data = self.run_route(
            '--task-type', 'research',
            '--risk', 'low',
            '--budget', 'low',
            '--stage', 'explore',
            '--deadline', 'normal',
        )
        self.assertEqual(data['lead']['model'], 'gemini-2.5-flash-lite')
        self.assertEqual(data['reviewer']['model'], 'gpt-5-mini')
        self.assertEqual(data['max_handoffs'], 1)

    def test_high_risk_external_writing_enables_opus(self):
        data = self.run_route(
            '--task-type', 'writing',
            '--risk', 'high',
            '--budget', 'high',
            '--stage', 'submission',
            '--deadline', 'normal',
            '--external-delivery',
        )
        self.assertEqual(data['lead']['model'], 'claude-sonnet-4-20250514')
        self.assertEqual(data['optional']['model'], 'claude-opus-4-1-20250805')


if __name__ == '__main__':
    unittest.main()
