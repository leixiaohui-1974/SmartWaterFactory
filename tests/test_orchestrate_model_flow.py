import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'orchestrate_model_flow.py'


class TestOrchestrateModelFlowScript(unittest.TestCase):
    def run_flow(self, *args):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), *args, '--format', 'json'],
            capture_output=True,
            text=True,
            check=True,
            cwd=str(ROOT),
        )
        return json.loads(result.stdout)

    def test_dry_run_uses_lead_and_reviewer_by_default(self):
        data = self.run_flow(
            '--task-type', 'coding',
            '--risk', 'medium',
            '--budget', 'medium',
            '--stage', 'implement',
            '--deadline', 'urgent',
            '--prompt', 'Check the HIL optimizer design',
            '--dry-run',
            '--no-archive',
        )
        self.assertTrue(data['dry_run'])
        self.assertEqual(data['stages'][0]['stage'], 'lead')
        self.assertEqual(data['stages'][1]['stage'], 'reviewer')
        self.assertIn('optional:not_requested', data['skipped'])

    def test_low_budget_keeps_optional_out_of_flow(self):
        data = self.run_flow(
            '--task-type', 'research',
            '--risk', 'low',
            '--budget', 'low',
            '--stage', 'explore',
            '--deadline', 'normal',
            '--prompt', 'Scan approaches for MBD optimization',
            '--dry-run',
            '--run-optional',
            '--no-archive',
        )
        stage_names = [stage['stage'] for stage in data['stages']]
        self.assertEqual(stage_names, ['lead', 'reviewer'])
        self.assertTrue(any(item in data['skipped'] for item in ['optional:not_routed', 'optional:no_handoff_budget']))

    def test_optional_runs_when_requested_and_budget_allows(self):
        data = self.run_flow(
            '--task-type', 'coding',
            '--risk', 'medium',
            '--budget', 'high',
            '--stage', 'implement',
            '--deadline', 'normal',
            '--prompt', 'Review the API flow',
            '--dry-run',
            '--run-optional',
            '--no-archive',
        )
        stage_names = [stage['stage'] for stage in data['stages']]
        self.assertEqual(stage_names, ['lead', 'reviewer', 'optional'])

    def test_template_and_task_spec_are_injected(self):
        hil_doc = next(ROOT.joinpath('docs', 'claude').glob('AquaMind_HIL_*.md'))
        data = self.run_flow(
            '--task-type', 'coding',
            '--risk', 'medium',
            '--budget', 'medium',
            '--stage', 'implement',
            '--deadline', 'urgent',
            '--task-template', 'hil_optimization',
            '--task-spec-file', str(hil_doc),
            '--prompt', 'Review the current HIL optimization route',
            '--dry-run',
            '--no-archive',
        )
        self.assertEqual(data['prompt_bundle']['template_name'], 'hil_optimization')
        self.assertIn('AquaMind_HIL_', data['prompt_bundle']['task_spec_source'])
        self.assertIn('HIL', data['prompt_bundle']['task_prompt'])

    def test_granular_template_is_available(self):
        data = self.run_flow(
            '--task-type', 'coding',
            '--risk', 'medium',
            '--budget', 'medium',
            '--stage', 'implement',
            '--deadline', 'urgent',
            '--task-template', 'hil_code_task',
            '--prompt', 'Implement an HIL API change',
            '--dry-run',
            '--no-archive',
        )
        self.assertEqual(data['prompt_bundle']['template_name'], 'hil_code_task')
        self.assertIn('executable code changes', data['prompt_bundle']['task_prompt'])

    def test_default_archive_writes_report_and_stage_artifacts(self):
        data = self.run_flow(
            '--task-type', 'coding',
            '--risk', 'low',
            '--budget', 'low',
            '--stage', 'implement',
            '--deadline', 'urgent',
            '--prompt', 'Archive this dry run',
            '--dry-run',
        )
        saved_to = data.get('saved_to')
        artifacts = data.get('artifacts', {})
        self.assertTrue(saved_to)
        self.assertTrue(Path(saved_to).exists())
        self.assertIn('prompt_bundle', artifacts)
        self.assertIn('lead', artifacts)
        self.assertIn('reviewer', artifacts)
        for item in [saved_to, *artifacts.values()]:
            Path(item).unlink(missing_ok=True)


if __name__ == '__main__':
    unittest.main()
