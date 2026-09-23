#!/usr/bin/env python3
"""台账配置、校验、对账与异常记录；不写正式项目台账。"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import importlib.util

spec = importlib.util.spec_from_file_location("ledger", Path(__file__).with_name("ledger.py"))
ledger = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = ledger
spec.loader.exec_module(ledger)


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="gg-bili-ledger-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "project"
        self.root.mkdir()
        self.config = Path(self.temp.name) / "config.json"
        self.ledger_path = self.root / "docs/harness/notes/bilibili-publish-record.md"
        self.ledger_path.parent.mkdir(parents=True)
        self.ledger_path.write_text(
            "# B站发布台账\n\n## 已发布作品\n\n"
            "| 发布时间 | 系列 | 作品 | 源文件 | sha256 | 标题 | aid | bvid | cid | 状态 |\n"
            "|---|---|---|---|---|---|---:|---|---:|---|\n\n"
            "## 专栏发布记录\n\n## 删除/异常记录\n",
            encoding="utf-8",
        )
        self.cli(
            "configure",
            "--project-root", str(self.root),
            "--ledger-path", "docs/harness/notes/bilibili-publish-record.md",
            "--upload-copy-dir", str(Path(self.temp.name) / "upload"),
        )

    def cli(self, *args):
        result = subprocess.run(
            [sys.executable, str(Path(__file__).with_name("ledger.py")), "--config", str(self.config), *args],
            capture_output=True, text=True, cwd="/",
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        return json.loads(result.stdout)

    def test_configure_is_independent_of_cwd(self):
        status = self.cli("status")
        self.assertTrue(status["valid"])
        self.assertEqual(status["videos"], 0)

    def test_append_and_reconcile_under_lock(self):
        record = {
            "published_at": "2026-09-11 10:00:00",
            "series": "总裁",
            "work_label": "测试",
            "source_file": "/tmp/a.mp4",
            "sha256": "abc123",
            "title": "第1集｜测试",
            "aid": "1",
            "bvid": "BVTEST",
            "cid": "待同步",
            "status": "投稿接口 code=0；异步字段待同步",
        }
        first = ledger.append_video_ledger(record, self.ledger_path)
        second = ledger.append_video_ledger(record, self.ledger_path)
        self.assertTrue(first["written"])
        self.assertTrue(second["already_present"])
        updated = self.cli("reconcile", "--sha256", "abc123", "--cid", "99", "--status", "开放浏览")
        self.assertEqual(updated["row"]["cid"], "99")
        self.assertEqual(updated["row"]["status"], "开放浏览")
        status = self.cli("status")
        self.assertEqual(status["videos"], 1)
        self.assertEqual(status["pending"], 0)

    def test_record_exception_appends(self):
        self.cli(
            "record-exception",
            "--time", "2026-09-11",
            "--series", "总裁",
            "--title", "误发",
            "--phenomenon", "未捕获投稿请求",
            "--handling", "未记为已发布",
        )
        text = self.ledger_path.read_text(encoding="utf-8")
        self.assertIn("未捕获投稿请求", text.split("## 删除/异常记录", 1)[1])


if __name__ == "__main__":
    unittest.main()
