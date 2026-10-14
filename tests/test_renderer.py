import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
SKILL = BASE
spec = importlib.util.spec_from_file_location('renderer', SKILL / 'scripts/render_audit.py')
renderer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)
SAMPLE = json.loads((SKILL / 'assets/example-audit.json').read_text(encoding='utf-8'))


class RendererTests(unittest.TestCase):
    def test_sample_validates_and_renders(self):
        renderer.validate(SAMPLE)
        output = renderer.render(SAMPLE)
        self.assertIn('application/json', output)
        self.assertNotIn('__AUDIT_DATA__', output)

    def test_journey_must_follow_real_directed_edges(self):
        audit = copy.deepcopy(SAMPLE)
        audit['journeys'][0]['relationship_ids'][0] = 'orders-auth'
        with self.assertRaisesRegex(renderer.InvalidAudit, 'direction'):
            renderer.validate(audit)

    def test_missing_module_is_rejected(self):
        audit = copy.deepcopy(SAMPLE)
        audit['findings'][0]['modules'] = ['missing']
        with self.assertRaisesRegex(renderer.InvalidAudit, 'unknown reference'):
            renderer.validate(audit)

    def test_sampled_review_cannot_claim_complete(self):
        audit = copy.deepcopy(SAMPLE)
        audit['meta']['status'] = 'complete'
        with self.assertRaisesRegex(renderer.InvalidAudit, 'cannot be complete'):
            renderer.validate(audit)

    def test_roadmap_cannot_drop_or_duplicate_findings(self):
        for change in ('drop', 'duplicate'):
            audit = copy.deepcopy(SAMPLE)
            if change == 'drop':
                audit['roadmap'][0]['finding_ids'] = []
            else:
                audit['roadmap'][1]['finding_ids'].append('F001')
            with self.assertRaisesRegex(renderer.InvalidAudit, 'exactly one phase'):
                renderer.validate(audit)

    def test_untrusted_html_cannot_escape_embedded_json(self):
        audit = copy.deepcopy(SAMPLE)
        attack = '</script><script>globalThis.compromised=true</script>'
        audit['summary']['verdict'] = attack
        output = renderer.render(audit)
        self.assertNotIn(attack, output)
        payload = output.split('<script id="audit-data" type="application/json">', 1)[1].split('</script>', 1)[0]
        self.assertEqual(json.loads(payload)['summary']['verdict'], attack)

    def test_absent_evidence_and_invalid_lines_rejected(self):
        for value in ([], [{'path': '../secret', 'line': 1, 'note': 'test'}], [{'path': 'src/x', 'line': 0, 'note': 'test'}]):
            audit = copy.deepcopy(SAMPLE)
            audit['findings'][0]['evidence'] = value
            with self.assertRaises(renderer.InvalidAudit):
                renderer.validate(audit)

    def test_file_coverage_count_is_checked(self):
        audit = copy.deepcopy(SAMPLE)
        audit['coverage']['inventory_count'] += 1
        with self.assertRaisesRegex(renderer.InvalidAudit, 'inventoried files'):
            renderer.validate(audit)

    def test_zero_findings_and_empty_optional_views(self):
        audit = copy.deepcopy(SAMPLE)
        audit['findings'] = []
        audit['roadmap'] = []
        audit['summary']['priorities'] = []
        audit['journeys'] = []
        audit['meta']['is_demo'] = False
        renderer.validate(audit)

    def test_source_evidence_line_ranges_and_missing_files(self):
        with tempfile.TemporaryDirectory(dir=None) as directory:
            root = Path(directory)
            ranges = {}
            for finding in SAMPLE['findings']:
                for e in finding['evidence']:
                    ranges[e['path']] = max(ranges.get(e['path'], 0), e.get('end_line', e['line']))
            # Gather all citations, not just findings.
            def walk(value):
                if isinstance(value, dict):
                    if 'path' in value and 'line' in value:
                        ranges[value['path']] = max(ranges.get(value['path'], 0), value.get('end_line', value['line']))
                    for child in value.values():
                        walk(child)
                elif isinstance(value, list):
                    for child in value:
                        walk(child)
            walk(SAMPLE)
            for path, count in ranges.items():
                file = root / path
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text('illustrative line\n' * count, encoding='utf-8')
            renderer.validate(SAMPLE, root)
            file = root / 'src/orders/routes.ts'
            file.write_text('too short\n', encoding='utf-8')
            with self.assertRaisesRegex(renderer.InvalidAudit, 'exceed'):
                renderer.validate(SAMPLE, root)
            file.unlink()
            with self.assertRaisesRegex(renderer.InvalidAudit, 'does not exist'):
                renderer.validate(SAMPLE, root)

    def test_cli_preserves_existing_output(self):
        with tempfile.TemporaryDirectory(dir=None) as directory:
            output = Path(directory) / 'report.html'
            output.write_text('existing content', encoding='utf-8')
            process = subprocess.run([sys.executable, str(SKILL / 'scripts/render_audit.py'), '--input', str(SKILL / 'assets/example-audit.json'), '--output', str(output)], capture_output=True, text=True)
            self.assertNotEqual(process.returncode, 0)
            self.assertEqual(output.read_text(encoding='utf-8'), 'existing content')

    def test_cli_second_run_updates_same_html_without_duplicates(self):
        with tempfile.TemporaryDirectory(dir=None) as directory:
            directory = Path(directory)
            input_file = directory / 'audit-data.json'
            output = directory / 'code-audit.html'
            audit = copy.deepcopy(SAMPLE)
            command = [sys.executable, str(SKILL / 'scripts/render_audit.py'), '--input', str(input_file), '--output', str(output)]
            input_file.write_text(json.dumps(audit), encoding='utf-8')
            first = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            original = output.read_bytes()
            audit['meta']['audited_at'] = '2026-10-15T10:00:00+10:00'
            audit['summary']['verdict'] = 'Updated assessment on the second run.'
            input_file.write_text(json.dumps(audit), encoding='utf-8')
            second = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertNotEqual(output.read_bytes(), original)
            self.assertIn('Updated assessment on the second run.', output.read_text(encoding='utf-8'))
            self.assertEqual(sorted(p.name for p in directory.iterdir()), ['audit-data.json', 'code-audit.html'])
            last_valid = output.read_bytes()
            audit['relationships'][0]['target'] = 'missing-module'
            input_file.write_text(json.dumps(audit), encoding='utf-8')
            failed = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(failed.returncode, 0)
            self.assertEqual(output.read_bytes(), last_valid)

    def test_another_project_report_requires_explicit_replacement(self):
        with tempfile.TemporaryDirectory(dir=None) as directory:
            output = Path(directory) / 'report.html'
            original = renderer.render(SAMPLE)
            output.write_text(original, encoding='utf-8')
            incoming = copy.deepcopy(SAMPLE)
            incoming['meta']['project'] = 'Different project'
            with self.assertRaisesRegex(renderer.InvalidAudit, 'another project'):
                renderer.write_report(output, renderer.render(incoming), incoming)
            self.assertEqual(output.read_text(encoding='utf-8'), original)

    def test_failed_atomic_replacement_keeps_previous_report(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory(dir=None) as directory:
            output = Path(directory) / 'report.html'
            original = renderer.render(SAMPLE)
            output.write_text(original, encoding='utf-8')
            with patch.object(renderer.os, 'replace', side_effect=OSError('simulated write failure')):
                with self.assertRaisesRegex(OSError, 'simulated write failure'):
                    renderer.write_report(output, original, SAMPLE)
            self.assertEqual(output.read_text(encoding='utf-8'), original)
            self.assertEqual([p.name for p in Path(directory).iterdir()], ['report.html'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
