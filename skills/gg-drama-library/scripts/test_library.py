"""用临时合成记录验证库行为；不写入正式素材库。"""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('library', Path(__file__).with_name('library.py'))
library = importlib.util.module_from_spec(spec)
spec.loader.exec_module(library)


class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='gg-library-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / '中文 素材库'
        self.config = Path(self.temp.name) / 'config.json'
        self.cli('configure', '--root', str(self.root))
        self.cli('init')
        self.work = self.root / 'works/demo'
        self.source = Path(self.temp.name) / 'source.mp4'
        self.source.write_bytes(b'synthetic fixture, not real video')
        for ep in ['ep01', 'ep02']:
            evidence = f'works/demo/evidence/{ep}/manifest.json'
            library.write(self.root / evidence, {'duration': 10, 'source': str(self.source)})
            library.write(self.work / f'episodes/{ep}.json', {'schema_version': 1, 'id': ep, 'work_id': 'demo', 'title': ep, 'duration': 10, 'evidence_path': evidence, 'events': [], 'tracks': [], 'state_ledger': {}})
        library.write(self.work / 'work.json', {'schema_version': 1, 'id': 'demo', 'title': '合成测试', 'sources': [], 'coverage': {'status': 'complete', 'expected_episode_ids': ['ep01','ep02'], 'collected_episode_ids': ['ep01','ep02'], 'missing_episode_ids': []}})
        self.case = {'schema_version': 1, 'id': 'c01', 'work_id': 'demo', 'title': '协作初遇', 'status': 'usable', 'core_ranges': [{'episode_id': ep, 'start': 1, 'end': 3, 'evidence_path': f'works/demo/evidence/{ep}/manifest.json', 'role': 'core'} for ep in ['ep01','ep02']], 'context_ranges': [], 'entry_state': '陌生', 'trigger': '共同任务', 'beats': [{'id': 'b1', 'action': '协作', 'response': '配合', 'result': '认可', 'evidence_refs': ['core:0','core:1'], 'basis': 'observed'}], 'exit_state': '认可', 'mechanism': {'summary': '能力被看见'}, 'prerequisites': [], 'tags': {'function': ['初遇']}, 'analysis': {}}
        self.persist()

    def cli(self, *args):
        result = subprocess.run([sys.executable, str(Path(__file__).with_name('library.py')), '--config', str(self.config), *args], capture_output=True, text=True, cwd='/')
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        return json.loads(result.stdout)

    def persist(self):
        library.write(self.work / 'cases/c01.json', self.case)

    def catalog(self):
        index = self.cli('index')
        return [json.loads(line) for line in Path(index['index']).read_text().splitlines()]

    def test_cross_episode_and_config_independent_of_cwd(self):
        self.assertTrue(self.cli('validate')['valid'])
        self.assertEqual(self.cli('index')['cases'], 1)

    def test_range_and_episode_boundary(self):
        self.case['core_ranges'][0]['end'] = 11
        self.persist()
        self.assertFalse(library.validate(self.root)['valid'])

    def test_wrong_media_version(self):
        self.case['core_ranges'][0]['evidence_path'] = self.case['core_ranges'][1]['evidence_path']
        self.persist()
        self.assertFalse(library.validate(self.root)['valid'])

    def test_dangling_beat_reference(self):
        self.case['beats'][0]['evidence_refs'] = ['core:9']
        self.persist()
        self.assertFalse(library.validate(self.root)['valid'])

    def test_catalog_keeps_all_cases_statuses_and_actions(self):
        self.case['trigger'] = '突遇暴雨'
        self.case['beats'][0]['action'] = '把伞倾向对方，自己半边肩膀淋湿'
        for i in range(16):
            case = {**self.case, 'id': f'c{i+1:02d}', 'status': 'partial' if i == 15 else 'usable'}
            library.write(self.work / f'cases/{case["id"]}.json', case)
        rows = self.catalog()
        self.assertEqual(len(rows), 16)
        self.assertEqual(rows[-1]['status'], 'partial')
        self.assertEqual(rows[0]['trigger'], self.case['trigger'])
        self.assertEqual(rows[0]['beats'], self.case['beats'])

    def test_rebuild_catalog_reads_current_source(self):
        self.cli('index')
        self.case['title'] = '边界尊重'; self.persist()
        self.assertEqual(self.catalog()[0]['title'], '边界尊重')

    def test_reconfigure_keeps_old_library(self):
        other = Path(self.temp.name) / '另一个库'
        self.cli('configure', '--root', str(other)); self.cli('init')
        self.assertEqual(self.cli('status')['counts']['cases'], 0)
        self.assertTrue((self.work / 'cases/c01.json').is_file())

    def test_audience_is_preserved_in_catalog(self):
        self.case['audience'] = {'status': 'inferred', 'core': [{'label': '偏好慢节奏日常互动的观众', 'rationale': '协作后逐步认可', 'evidence_refs': ['core:0']}]}
        self.persist()
        row = self.catalog()[0]
        self.assertEqual(row['audience'], self.case['audience'])

    def metric_fixture(self):
        evidence = self.root / 'metrics-evidence.txt'
        evidence.write_text('Synthetic source snapshot: views=12000, other metrics unavailable')
        metrics = {k: {'value': None, 'raw': None, 'unit': 'count', 'status': 'unavailable', 'approximate': False, 'reason': '测试来源未提供'} for k in ['views','likes','comments','favorites','shares']}
        metrics['views'] = {'value': 12000, 'raw': '1.2万', 'unit': 'count', 'status': 'available', 'approximate': True}
        return {'schema_version': 1, 'id': 's01', 'work_id': 'demo', 'publication_id': 'demo_video', 'platform': 'test', 'source_url': 'https://example.com/video/demo', 'captured_at': '2026-09-08T10:00:00+08:00', 'published_at': None, 'episode_ids': ['ep01'], 'metrics': metrics, 'evidence_paths': [str(evidence)]}

    def test_metrics_append_latest_and_no_overwrite(self):
        data = self.metric_fixture()
        source = Path(self.temp.name) / 'metrics.json'
        library.write(source, data)
        first = self.cli('record-metrics', '--input', str(source))
        data['id'] = 's02'; data['captured_at'] = '2026-09-08T11:00:00+08:00'
        data['metrics']['views']['value'] = 14000
        data['metrics']['views']['raw'] = '1.4万'
        library.write(source, data)
        self.cli('record-metrics', '--input', str(source))
        self.assertEqual(library.read(Path(first['snapshot']))['metrics']['views']['value'], 12000)
        found = self.catalog()[0]
        self.assertEqual(found['performance'][0]['id'], 's02')
        self.assertIsNone(found['performance'][0]['metrics']['likes']['value'])
        result = subprocess.run([sys.executable, str(Path(__file__).with_name('library.py')), '--config', str(self.config), 'record-metrics', '--input', str(source)],capture_output=True,text=True)
        self.assertEqual(result.returncode, 2)

    def test_metrics_unknown_is_not_zero_and_episode_must_exist(self):
        data = self.metric_fixture()
        data['metrics']['likes']['value'] = 0
        with self.assertRaises(ValueError):
            library.check_metrics(data, self.root)
        data = self.metric_fixture(); data['episode_ids'] = ['missing']
        with self.assertRaises(ValueError):
            library.check_metrics(data, self.root)


if __name__ == '__main__':
    unittest.main()
