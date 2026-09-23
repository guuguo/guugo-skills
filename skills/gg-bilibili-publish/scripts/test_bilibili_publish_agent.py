from __future__ import annotations

import hashlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from bilibili_publish_agent import (
    AI_DISCLOSURE,
    AttemptClock,
    NeedsAIOptimization,
    DuplicateError,
    ExternalBlocker,
    BilibiliPublisher,
    AuditLog,
    PublishError,
    PreflightError,
    build_batch_script,
    build_archive_script,
    build_check_script,
    build_diagnostic_script,
    build_ready_script,
    build_repair_script,
    claim_manifest_run,
    append_video_ledger,
    detect_local_duplicate,
    load_json,
    main,
    optimization_fields,
    probe_video,
    release_manifest_run,
    validate_manifest,
    validate_profile,
)


PROFILE_PATH = SCRIPTS / "bilibili_publish_profile.json"


class FakeTime:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


class FakeWebBridgeClient:
    def __init__(self, session, audit, clock, timing):
        self.session = session
        self.audit = audit
        self.clock = clock
        self.timing = timing
        self.command_count = 0
        self.submit_request_count = 0
        self.phase = "fake"
        self.commands = []
        self.evaluations = []

    def health(self):
        return {"running": True, "extension_connected": True}

    def command(self, action, args, timeout=120):
        self.command_count += 1
        self.commands.append((action, args))
        if action == "network" and args.get("cmd") == "list":
            return {"requests": [{"requestId": "request-1", "url": "https://member.bilibili.com/x/vu/web/add/v3"}]}
        if action == "network" and args.get("cmd") == "detail":
            return {"responseBody": {"code": 0, "data": {"aid": 123, "bvid": "BVTEST"}}}
        return {"success": True, "url": args.get("url")}

    def evaluate_json(self, code, timeout=120):
        self.command_count += 1
        if "/x/web/archives" in code:
            self.evaluations.append("duplicate_check")
            return {"ok": True, "items": [], "total": 0, "pages": 1}
        if "uploadProgressProbe" in code:
            self.evaluations.append("upload_progress")
            return {
                "probe": "uploadProgressProbe",
                "stuck": False,
                "started": True,
                "complete": True,
                "percent": 100,
                "uploaded": 10,
                "total": 10,
                "tasks": ["上传完成"],
            }
        if "const deadline=" in code:
            self.evaluations.append("ready")
            return {"ok": True, "state": {}}
        if "const actions=[];const failures=[];" in code:
            self.evaluations.append("batch")
            return {"ok": True, "actions": []}
        if "const checks=" in code:
            self.evaluations.append("total_check")
            return {"ok": True, "checks": {"all": True}, "issues": [], "submitSelector": ".submit-add"}
        raise AssertionError("unexpected evaluate script")


class SlowNetworkStartClient(FakeWebBridgeClient):
    def command(self, action, args, timeout=120):
        if action == "network" and args.get("cmd") == "start":
            self.clock.now.advance(2)
        return super().command(action, args, timeout)


class BilibiliPublishAgentTest(unittest.TestCase):
    def setUp(self) -> None:
        self.profile = load_json(PROFILE_PATH)
        self.profile["timing"]["post_upload_settle_seconds"] = 0
        self.profile["timing"]["upload_progress_timeout_seconds"] = 0
        self.profile["timing"]["upload_complete_timeout_seconds"] = 0
        validate_profile(self.profile)

    def make_manifest(self, video: Path) -> dict:
        sha = hashlib.sha256(video.read_bytes()).hexdigest()
        return {
            "schema_version": 1,
            "video": str(video),
            "sha256": sha,
            "title": "第32集｜顾总今天陪小满玩",
            "title_basis": "B站总台账连续集号；系列分线不进入标题编号",
            "description": f"顾总陪小满玩。\n\n{AI_DISCLOSURE}",
            "series": "总裁",
            "work_label": "主线·陪小满玩",
            "publish_type": "normal",
            "authorization": {
                "action": "publish_bilibili_video",
                "user_request": "发布这个视频到 B站"
            }
        }

    def make_ledger(self, directory: str | Path) -> Path:
        ledger = Path(directory) / "ledger.md"
        ledger.write_text(
            "# B站发布台账\n\n## 已发布作品\n\n"
            "| 发布时间 | 系列 | 作品 | 源文件 | sha256 | 标题 | aid | bvid | cid | 状态 |\n"
            "|---|---|---|---|---|---|---:|---|---:|---|\n\n"
            "## 专栏发布记录\n\n## 删除/异常记录\n",
            encoding="utf-8",
        )
        return ledger

    def make_config(self, directory: str | Path, ledger: Path | None = None) -> Path:
        root = Path(directory)
        ledger = ledger or self.make_ledger(root)
        config = root / "config.json"
        config.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "project_root": str(root),
                    "ledger_path": str(ledger),
                    "log_root": str(root / "logs"),
                    "staging_root": str(root / "staging"),
                    "upload_copy_dir": str(root / "upload"),
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return config

    def test_new_run_discards_stale_draft_and_resume_keeps_same_draft(self) -> None:
        manifest = validate_manifest(
            self.make_manifest(Path(__file__)),
            self.profile,
            verify_video=False,
        )
        fresh = build_ready_script(self.profile, manifest, editor=False)
        ready = build_ready_script(self.profile, manifest, editor=True)
        batch = build_batch_script(self.profile, manifest)
        self.assertIn("cfg.selectors.draft_discard", fresh)
        self.assertNotIn("cfg.selectors.draft_resume", fresh)
        self.assertIn("cfg.selectors.draft_resume", ready)
        self.assertIn("safeClick(draftAction)", ready)
        self.assertIn("cfg.selectors.draft_resume", batch)
        self.assertIn("safeClick(resume)", batch)
        self.assertIn("upload_identity", batch)
        self.assertIn("queue_not_unique_or_wrong_file", batch)
        self.assertIn(f'"upload_task_title":"bili-{manifest["sha256"][:16]}"', batch)

    def test_attempt_clock_records_sla_then_five_minute_failure(self) -> None:
        fake = FakeTime()
        clock = AttemptClock(now=fake)
        clock.start_round()
        timing = {"normal_sla_seconds": 60, "attempt_failure_seconds": 300, "external_grace_seconds": 180}

        fake.advance(59.9)
        self.assertEqual("within_one_minute", clock.classify(timing))
        fake.advance(0.2)
        self.assertEqual("over_one_minute", clock.classify(timing))
        fake.advance(240)
        self.assertEqual("attempt_failed", clock.classify(timing))

    def test_external_latency_extends_five_minute_boundary_but_not_sla(self) -> None:
        fake = FakeTime()
        clock = AttemptClock(now=fake)
        clock.start_round()
        clock.add_external_evidence("upload_latency", 12, status=200)
        timing = {"normal_sla_seconds": 60, "attempt_failure_seconds": 300, "external_grace_seconds": 180}

        fake.advance(301)
        self.assertEqual("over_one_minute", clock.classify(timing))
        fake.advance(12)
        self.assertEqual("attempt_failed", clock.classify(timing))

        clock.start_round()
        self.assertEqual(0, clock.external_latency_seconds)
        self.assertEqual([], clock.external_evidence)

    def test_resume_restores_elapsed_time_including_ai_optimization_downtime(self) -> None:
        fake = FakeTime()
        clock = AttemptClock(now=fake)
        clock.restore(
            {
                "task_elapsed_seconds": 55,
                "round_elapsed_seconds": 55,
                "round": 2,
                "markers": {"page_opened": 0, "batch_finished": 40},
                "external_latency_seconds": 0,
            },
            wall_downtime_seconds=10,
        )
        timing = {"normal_sla_seconds": 60, "attempt_failure_seconds": 300, "external_grace_seconds": 180}

        self.assertEqual(65, clock.round_elapsed())
        self.assertEqual("over_one_minute", clock.classify(timing))
        self.assertEqual(2, clock.round_number)
        self.assertEqual(40, clock.markers["batch_finished"] - clock.round_started)

    def test_manifest_requires_title_basis_and_authorization(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            video = Path(directory) / "video.mp4"
            video.write_bytes(b"video")
            manifest = self.make_manifest(video)
            manifest.pop("title_basis")
            with self.assertRaises(PreflightError):
                validate_manifest(manifest, self.profile)

            manifest = self.make_manifest(video)
            manifest.pop("authorization")
            with self.assertRaises(PreflightError):
                validate_manifest(manifest, self.profile)

    def test_manifest_never_infers_episode_from_series_line(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            video = Path(directory) / "line-six.mp4"
            video.write_bytes(b"video")
            manifest = self.make_manifest(video)
            normalized = validate_manifest(manifest, self.profile)
            self.assertEqual("第32集｜顾总今天陪小满玩", normalized["title"])
            self.assertIn("不进入标题编号", normalized["title_basis"])

    def test_manifest_requires_locked_season_and_typed_charge_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            video = Path(directory) / "video.mp4"
            video.write_bytes(b"video")
            manifest = self.make_manifest(video)
            manifest["series"] = "未知系列"
            with self.assertRaises(PreflightError):
                validate_manifest(manifest, self.profile)

            for bad_value in (5, {"bad": True}, ["bad"]):
                manifest = self.make_manifest(video)
                manifest["publish_type"] = "charge"
                manifest["charge"] = {"preview_end": "00:00:05", "payment": bad_value, "tier": "30元档"}
                with self.subTest(bad_value=bad_value):
                    with self.assertRaises(PreflightError):
                        validate_manifest(manifest, self.profile)

    def test_local_ledger_duplicate_blocks_sha_or_source_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "ledger.md"
            manifest = {"sha256": "abc123", "video": "/tmp/target.mp4"}
            ledger.write_text("| /tmp/target.mp4 | abc123 |", encoding="utf-8")
            with self.assertRaises(DuplicateError):
                detect_local_duplicate(manifest, ledger)

    def test_probe_video_rejects_invalid_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            invalid = Path(directory) / "invalid.mp4"
            invalid.write_bytes(b"not a video")
            with self.assertRaises(PreflightError):
                probe_video(invalid)

    def test_dry_run_accepts_real_video_and_generates_all_browser_phases(self) -> None:
        if not shutil.which("ffmpeg"):
            self.skipTest("ffmpeg is unavailable")
        with tempfile.TemporaryDirectory() as directory:
            video = Path(directory) / "tiny.mp4"
            generated = subprocess.run(
                [
                    "ffmpeg",
                    "-v",
                    "error",
                    "-f",
                    "lavfi",
                    "-i",
                    "color=c=black:s=64x64:d=0.25",
                    "-pix_fmt",
                    "yuv420p",
                    str(video),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(0, generated.returncode, generated.stderr)
            manifest = self.make_manifest(video)
            manifest_path = Path(directory) / "manifest.json"
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
            stdout = io.StringIO()

            config = self.make_config(directory)
            with redirect_stdout(stdout):
                return_code = main([
                    "--config", str(config),
                    "--manifest", str(manifest_path),
                    "--dry-run",
                ])

            result = json.loads(stdout.getvalue())
            self.assertEqual(0, return_code)
            self.assertTrue(result["ok"])
            self.assertTrue(result["dry_run"])
            self.assertEqual({"ready", "batch", "check"}, set(result["generated_script_bytes"]))

    def test_generated_scripts_are_batch_oriented_and_diagnostic_is_targeted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            video = Path(directory) / "video.mp4"
            video.write_bytes(b"video")
            manifest = validate_manifest(self.make_manifest(video), self.profile)

            batch = build_batch_script(self.profile, manifest)
            check = build_check_script(self.profile, manifest)
            diagnostic = build_diagnostic_script(self.profile, manifest, [{"field": "partition"}])

            self.assertIn("for(const tag of cfg.tags)", batch)
            self.assertIn("cleanUnexpectedTags(cfg.tags)", batch)
            self.assertIn("tag_cleanup_passes", batch)
            self.assertIn("editorDeadline", batch)
            self.assertIn("const checks=", check)
            self.assertIn("const safeClick=", batch)
            self.assertIn("safeClick(close)", batch)
            self.assertIn("cover_ready_wait_seconds", batch)
            self.assertIn('const customCover=cfg.cover_mode==="custom"', batch)
            self.assertIn('cfg.cover_mode==="custom"||!!one(cfg.selectors.cover_selected)', check)
            self.assertIn("description:norm(values.description)===norm(cfg.description)", check)
            self.assertIn("else checks.charge=!charge||!checked(charge)", check)
            self.assertIn("submitSelector", check)
            self.assertIn("partition:selectedValue(partition,cfg.selectors.partition_selected)", check)
            self.assertIn("season:seasonSelected()||selectedValue(season,cfg.selectors.season_selected)", check)
            self.assertIn("season_skipped_account_unqualified", batch)
            self.assertIn("seasonNotAvailable", check)
            self.assertNotIn("[data-reporter-id=\\\"82\\\"]", json.dumps(self.profile["selectors"]))
            self.assertIn("img:not(.add-icon)", json.dumps(self.profile["selectors"]["cover_main"]))
            self.assertIn('fields=["partition"]', diagnostic)
            self.assertNotIn("document.documentElement.outerHTML", diagnostic)

    def test_custom_cover_title_preserves_uploaded_cover_without_platform_selected_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            video = Path(directory) / "video.mp4"
            video.write_bytes(b"video")
            manifest = self.make_manifest(video)
            manifest["title"] = "充电番外04｜承砚，我来接你回家"
            normalized = validate_manifest(manifest, self.profile)

            batch = build_batch_script(self.profile, normalized)
            check = build_check_script(self.profile, normalized)
            repair = build_repair_script(self.profile, normalized, ["cover"])

            self.assertIn('"cover_mode":"custom"', batch)
            self.assertIn('"cover_mode":"custom"', check)
            self.assertIn('"cover_mode":"custom"', repair)
            self.assertIn('"cover_existing_custom"', repair)
            self.assertIn('"custom_cover_missing"', repair)

    def test_generated_browser_scripts_have_valid_javascript_syntax(self) -> None:
        if not shutil.which("node"):
            self.skipTest("node is unavailable")
        with tempfile.TemporaryDirectory() as directory:
            video = Path(directory) / "video.mp4"
            video.write_bytes(b"video")
            manifest = validate_manifest(self.make_manifest(video), self.profile)
            scripts = [
                build_archive_script(),
                build_ready_script(self.profile, manifest, editor=False),
                build_ready_script(self.profile, manifest, editor=True),
                build_batch_script(self.profile, manifest),
                build_check_script(self.profile, manifest),
                build_repair_script(self.profile, manifest, ["tags", "partition"]),
                build_diagnostic_script(self.profile, manifest, [{"field": "partition"}]),
            ]
            for index, script in enumerate(scripts):
                with self.subTest(index=index):
                    result = subprocess.run(
                        ["node", "--check"],
                        input=script,
                        text=True,
                        capture_output=True,
                        check=False,
                    )
                    self.assertEqual(0, result.returncode, result.stderr)

    def test_repair_script_is_gated_by_failed_fields(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            video = Path(directory) / "video.mp4"
            video.write_bytes(b"video")
            manifest = validate_manifest(self.make_manifest(video), self.profile)
            repair = build_repair_script(self.profile, manifest, ["partition"])

            self.assertIn('const fields=["partition"]', repair)
            self.assertIn('fields.includes("partition")', repair)
            self.assertIn('fields.includes("tags")', repair)

    def test_resume_state_with_submit_evidence_cannot_submit_again(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            video = Path(directory) / "video.mp4"
            video.write_bytes(b"video")
            manifest = validate_manifest(self.make_manifest(video), self.profile)
            audit = AuditLog(Path(directory) / "logs", "run")
            publisher = BilibiliPublisher(
                manifest,
                self.profile,
                audit,
                "run",
                "session",
                resume_state={"submitted": True, "submit_request_count": 1},
                ledger_path=self.make_ledger(directory),
            )

            with self.assertRaises(PublishError):
                publisher.submit_once({"submitSelector": ".submit-add"})

    def test_submit_intent_is_written_before_click_and_blocks_resume(self) -> None:
        class ClickTimeoutClient(FakeWebBridgeClient):
            def command(self, action, args, timeout=120):
                if action == "click":
                    raise PublishError("click timeout after request may have left browser")
                return super().command(action, args, timeout)

        with tempfile.TemporaryDirectory() as directory:
            video = Path(directory) / "video.mp4"
            video.write_bytes(b"video")
            manifest = validate_manifest(self.make_manifest(video), self.profile)
            audit = AuditLog(Path(directory) / "logs", "run")
            publisher = BilibiliPublisher(
                manifest, self.profile, audit, "run", "session",
                client_factory=ClickTimeoutClient, ledger_path=self.make_ledger(directory),
            )
            publisher.clock.start_round()

            with self.assertRaises(PublishError):
                publisher.submit_once({"submitSelector": ".submit-add"})

            state = json.loads(audit.state_path.read_text(encoding="utf-8"))
            self.assertTrue(state["possible_submit"])
            self.assertFalse(state["submitted"])
            self.assertEqual("submit_intent_write_ahead", state["reason"])
            self.assertEqual(hashlib.sha256(json.dumps(manifest, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest(), state["manifest_hash"])

            resumed = BilibiliPublisher(
                manifest, self.profile, audit, "run", "session",
                resume_state=state, client_factory=FakeWebBridgeClient,
                ledger_path=self.make_ledger(directory),
            )
            with self.assertRaises(PublishError):
                resumed.submit_once({"submitSelector": ".submit-add"})

    def test_ledger_append_is_atomic_and_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ledger = self.make_ledger(directory)
            record = {
                "published_at": "2026-07-17 12:00:00", "series": "总裁", "work_label": "主线",
                "source_file": "/tmp/a.mp4", "sha256": "sha-test", "title": "标题",
                "aid": "123", "bvid": "BVTEST", "cid": "待同步", "status": "code=0",
            }
            first = append_video_ledger(record, ledger)
            second = append_video_ledger(record, ledger)
            text = ledger.read_text(encoding="utf-8")
            self.assertTrue(first["written"])
            self.assertTrue(second["already_present"])
            self.assertEqual(1, text.count("sha-test"))
            self.assertLess(text.index("sha-test"), text.index("## 专栏发布记录"))

    def test_ledger_concurrent_appends_preserve_both_rows(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ledger = self.make_ledger(directory)
            records = []
            for number in (1, 2):
                records.append({
                    "published_at": "2026-07-17 12:00:00", "series": "总裁", "work_label": f"主线{number}",
                    "source_file": f"/tmp/{number}.mp4", "sha256": f"sha-{number}", "title": f"标题{number}",
                    "aid": f"aid-{number}", "bvid": f"BV{number}", "cid": "待同步", "status": "code=0",
                })
            with ThreadPoolExecutor(max_workers=2) as pool:
                list(pool.map(lambda record: append_video_ledger(record, ledger), records))
            content = ledger.read_text(encoding="utf-8")
            self.assertIn("`sha-1`", content)
            self.assertIn("`sha-2`", content)

    def test_manifest_lock_blocks_concurrency_and_adopts_crashed_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_hash = "a" * 64
            run_id, adopted = claim_manifest_run(manifest_hash, "run-old", root)
            self.assertEqual("run-old", run_id)
            self.assertFalse(adopted)
            with self.assertRaises(PreflightError):
                claim_manifest_run(manifest_hash, "run-concurrent", root)

            state_dir = root / "run-old"
            state_dir.mkdir(parents=True)
            (state_dir / "state.json").write_text('{"possible_submit":true}', encoding="utf-8")
            owner = root / "inflight" / f"{manifest_hash}.lock" / "owner.json"
            owner_data = json.loads(owner.read_text(encoding="utf-8"))
            owner_data["pid"] = 99999999
            owner.write_text(json.dumps(owner_data), encoding="utf-8")

            adopted_run, adopted = claim_manifest_run(manifest_hash, "run-new", root)
            self.assertEqual("run-old", adopted_run)
            self.assertTrue(adopted)
            release_manifest_run(manifest_hash, "run-old", root)

    def test_resume_extracts_only_failed_fields_for_targeted_repair(self) -> None:
        state = {
            "optimization_request": {
                "evidence": {
                    "issues": [
                        {"field": "partition", "reason": "option_missing"},
                        {"field": "tags", "reason": "one_missing"},
                        {"field": "partition", "reason": "still_wrong"},
                    ]
                }
            }
        }
        self.assertEqual(["partition", "tags"], optimization_fields(state))

    def test_normal_orchestration_batches_once_checks_once_and_submits_once(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            video = Path(directory) / "video.mp4"
            video.write_bytes(b"video")
            manifest = validate_manifest(self.make_manifest(video), self.profile)
            audit = AuditLog(Path(directory) / "logs", "run")
            publisher = BilibiliPublisher(
                manifest,
                self.profile,
                audit,
                "run",
                "session",
                client_factory=FakeWebBridgeClient,
                ledger_path=self.make_ledger(directory),
            )

            with patch.object(publisher, "preflight", return_value=video), patch("bilibili_publish_agent.time.sleep"):
                result = publisher.run()

            self.assertTrue(result["ok"])
            self.assertEqual("123", result["aid"])
            self.assertEqual("BVTEST", result["bvid"])
            self.assertEqual(1, publisher.client.evaluations.count("batch"))
            self.assertEqual(1, publisher.client.evaluations.count("total_check"))
            self.assertEqual(1, sum(1 for action, _ in publisher.client.commands if action == "click"))
            self.assertEqual(1, result["submit_request_count"])
            self.assertTrue(result["ledger_write"]["written"])
            events = [json.loads(line) for line in audit.path.read_text(encoding="utf-8").splitlines()]
            focus_events = [event for event in events if event["event"] == "foreground_focus_required"]
            self.assertEqual(1, len(focus_events))
            self.assertEqual(
                self.profile["timing"]["post_submit_focus_window_seconds"],
                focus_events[0]["window_seconds"],
            )

    def test_real_page_rehearsal_stops_after_total_check_without_submit_or_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            video = Path(directory) / "video.mp4"
            video.write_bytes(b"video")
            manifest = validate_manifest(self.make_manifest(video), self.profile)
            ledger = self.make_ledger(directory)
            audit = AuditLog(Path(directory) / "logs", "run")
            publisher = BilibiliPublisher(
                manifest, self.profile, audit, "run", "session",
                client_factory=FakeWebBridgeClient, ledger_path=ledger,
                stop_before_submit=True,
            )

            with patch.object(publisher, "preflight", return_value=video):
                result = publisher.run()

            self.assertTrue(result["ok"])
            self.assertTrue(result["simulation"])
            self.assertTrue(result["stopped_before_submit"])
            self.assertEqual(0, result["submit_request_count"])
            self.assertIn("task_elapsed_seconds", result)
            self.assertEqual("within_one_minute", result["task_timing_status"])
            self.assertEqual(0, sum(1 for action, _ in publisher.client.commands if action == "click"))
            self.assertEqual(0, sum(1 for action, _ in publisher.client.commands if action == "network"))
            self.assertEqual(1, publisher.client.evaluations.count("batch"))
            self.assertEqual(1, publisher.client.evaluations.count("total_check"))
            self.assertNotIn(manifest["sha256"], ledger.read_text(encoding="utf-8"))
            saved = json.loads(audit.result_path.read_text(encoding="utf-8"))
            self.assertTrue(saved["stopped_before_submit"])

    def test_resume_same_editor_uses_completed_prior_duplicate_check(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            video = Path(directory) / "video.mp4"
            video.write_bytes(b"video")
            manifest = validate_manifest(self.make_manifest(video), self.profile)
            audit = AuditLog(Path(directory) / "logs", "run")
            publisher = BilibiliPublisher(
                manifest, self.profile, audit, "run", "session",
                resume_state={"phase": "batch_fill", "round": 1},
                client_factory=FakeWebBridgeClient, ledger_path=self.make_ledger(directory),
                stop_before_submit=True,
            )
            with patch.object(publisher, "preflight", return_value=video):
                result = publisher.run()

            self.assertTrue(result["stopped_before_submit"])
            self.assertNotIn("duplicate_check", publisher.client.evaluations)
            self.assertIn("ready", publisher.client.evaluations)

    def test_resume_existing_editor_rejects_wrong_tab_url(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            video = Path(directory) / "video.mp4"
            video.write_bytes(b"video")
            manifest = validate_manifest(self.make_manifest(video), self.profile)
            publisher = BilibiliPublisher(
                manifest, self.profile, AuditLog(Path(directory) / "logs", "run"), "run", "session",
                resume_state={"phase": "batch_fill", "round": 1},
                client_factory=FakeWebBridgeClient, ledger_path=self.make_ledger(directory),
            )
            publisher.client.command = Mock(return_value={
                "success": True,
                "url": self.profile["archive_url"],
                "tabId": 123,
            })
            publisher.client.evaluate_json = Mock(side_effect=AssertionError("错误页面不应等待编辑器"))

            self.assertFalse(publisher.resume_existing_editor())
            publisher.client.command.assert_called_once_with(
                "select_existing_tab",
                {"url": self.profile["upload_url"]},
                timeout=15,
            )
            publisher.client.evaluate_json.assert_not_called()

    def test_resume_existing_editor_uses_session_upload_tab_without_foreground_requirement(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            video = Path(directory) / "video.mp4"
            video.write_bytes(b"video")
            manifest = validate_manifest(self.make_manifest(video), self.profile)
            publisher = BilibiliPublisher(
                manifest, self.profile, AuditLog(Path(directory) / "logs", "run"), "run", "session",
                resume_state={"phase": "batch_fill", "round": 1},
                client_factory=FakeWebBridgeClient, ledger_path=self.make_ledger(directory),
            )
            publisher.client.command = Mock(return_value={
                "success": True,
                "url": self.profile["upload_url"],
                "tabId": 550,
            })
            publisher.client.evaluate_json = Mock(side_effect=[
                {"started": True, "complete": True, "stuck": False},
                {"ok": True},
            ])

            self.assertTrue(publisher.resume_existing_editor())
            publisher.client.command.assert_called_once_with(
                "select_existing_tab",
                {"url": self.profile["upload_url"]},
                timeout=15,
            )

    def test_stuck_zero_upload_progress_is_external_blocker(self) -> None:
        class StuckUploadClient(FakeWebBridgeClient):
            def evaluate_json(self, code, timeout=120):
                if "uploadProgressProbe" in code:
                    self.evaluations.append("upload_progress")
                    return {
                        "probe": "uploadProgressProbe",
                        "stuck": True,
                        "started": False,
                        "complete": False,
                        "percent": 0,
                        "uploaded": 0,
                        "total": 0,
                        "text": "已经上传：0.0MB/0.0MB",
                        "tasks": ["上传中..."],
                    }
                return super().evaluate_json(code, timeout)

        with tempfile.TemporaryDirectory() as directory:
            video = Path(directory) / "video.mp4"
            video.write_bytes(b"video")
            manifest = validate_manifest(self.make_manifest(video), self.profile)
            publisher = BilibiliPublisher(
                manifest, self.profile, AuditLog(Path(directory) / "logs", "run"), "run", "session",
                client_factory=StuckUploadClient, ledger_path=self.make_ledger(directory),
            )
            with patch.object(publisher, "preflight", return_value=video), patch("bilibili_publish_agent.time.sleep"):
                with self.assertRaises(ExternalBlocker):
                    publisher.run()
            self.assertNotIn("batch", publisher.client.evaluations)

    def test_upload_retries_detached_batch_evaluate_then_succeeds(self) -> None:
        class DetachThenOkClient(FakeWebBridgeClient):
            def evaluate_json(self, code, timeout=120):
                if "const actions=[];const failures=[];" in code:
                    self.evaluations.append("batch")
                    if self.evaluations.count("batch") == 1:
                        raise PublishError(
                            'WebBridge evaluate 失败：{"code":"extension_error","message":"Detached while handling command."}'
                        )
                    return {"ok": True, "actions": ["title"], "failures": [], "editorWaitMs": 10, "batchElapsedMs": 20}
                return super().evaluate_json(code, timeout)

        with tempfile.TemporaryDirectory() as directory:
            video = Path(directory) / "video.mp4"
            video.write_bytes(b"video")
            manifest = validate_manifest(self.make_manifest(video), self.profile)
            audit = AuditLog(Path(directory) / "logs", "run")
            publisher = BilibiliPublisher(
                manifest, self.profile, audit, "run", "session",
                client_factory=DetachThenOkClient, ledger_path=self.make_ledger(directory),
            )
            with patch.object(publisher, "preflight", return_value=video), patch("bilibili_publish_agent.time.sleep"):
                result = publisher.run()
            self.assertTrue(result["ok"])
            self.assertEqual(2, publisher.client.evaluations.count("batch"))
            events = [json.loads(line) for line in audit.path.read_text(encoding="utf-8").splitlines()]
            self.assertTrue(any(event["event"] == "post_upload_evaluate_retry" for event in events))

    def test_batch_evaluate_timeout_covers_cover_wait(self) -> None:
        timing = load_json(PROFILE_PATH)["timing"]
        self.assertGreaterEqual(
            int(timing["batch_evaluate_timeout_seconds"]),
            int(timing["cover_ready_wait_seconds"]),
        )

    def test_batch_failure_stops_before_total_check(self) -> None:
        class BatchFailureClient(FakeWebBridgeClient):
            def evaluate_json(self, code, timeout=120):
                if "const actions=[];const failures=[];" in code:
                    self.evaluations.append("batch")
                    return {"ok": False, "actions": [], "failures": [{"field": "season", "reason": "option_missing"}]}
                return super().evaluate_json(code, timeout)

        with tempfile.TemporaryDirectory() as directory:
            video = Path(directory) / "video.mp4"
            video.write_bytes(b"video")
            manifest = validate_manifest(self.make_manifest(video), self.profile)
            publisher = BilibiliPublisher(
                manifest, self.profile, AuditLog(Path(directory) / "logs", "run"), "run", "session",
                client_factory=BatchFailureClient, ledger_path=self.make_ledger(directory),
            )
            with patch.object(publisher, "preflight", return_value=video):
                with self.assertRaises(NeedsAIOptimization):
                    publisher.run()
            self.assertNotIn("total_check", publisher.client.evaluations)

    def test_success_cannot_complete_when_ledger_write_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            video = Path(directory) / "video.mp4"
            video.write_bytes(b"video")
            manifest = validate_manifest(self.make_manifest(video), self.profile)
            broken_ledger = Path(directory) / "broken-ledger.md"
            broken_ledger.write_text("# missing section", encoding="utf-8")
            audit = AuditLog(Path(directory) / "logs", "run")
            publisher = BilibiliPublisher(
                manifest, self.profile, audit, "run", "session",
                client_factory=FakeWebBridgeClient, ledger_path=broken_ledger,
            )

            with patch.object(publisher, "preflight", return_value=video), patch("bilibili_publish_agent.time.sleep"):
                with self.assertRaises(PreflightError):
                    publisher.run()

            state = json.loads(audit.state_path.read_text(encoding="utf-8"))
            self.assertTrue(state["possible_submit"])
            self.assertTrue(state["submitted"])
            self.assertEqual("submission_code_zero", state["reason"])
            self.assertEqual("123", state["confirmed_result"]["aid"])
            self.assertEqual("BVTEST", state["confirmed_result"]["bvid"])
            self.assertFalse(audit.result_path.exists())

            valid_ledger = self.make_ledger(directory)
            valid_ledger.replace(broken_ledger)
            video.unlink()
            resumed = BilibiliPublisher(
                manifest, self.profile, audit, "run", "session", resume_state=state,
                client_factory=FakeWebBridgeClient, ledger_path=broken_ledger,
            )
            with patch.object(resumed, "preflight", return_value=video):
                result = resumed.run()
            self.assertTrue(result["ledger_write"]["written"])
            self.assertEqual(0, sum(1 for action, _ in resumed.client.commands if action == "click"))

    def test_network_start_crossing_five_minutes_cannot_click(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            video = Path(directory) / "video.mp4"
            video.write_bytes(b"video")
            manifest = validate_manifest(self.make_manifest(video), self.profile)
            publisher = BilibiliPublisher(
                manifest, self.profile, AuditLog(Path(directory) / "logs", "run"), "run", "session",
                client_factory=SlowNetworkStartClient, ledger_path=self.make_ledger(directory),
            )
            fake = FakeTime()
            publisher.clock = AttemptClock(now=fake)
            publisher.client.clock = publisher.clock
            publisher.clock.start_round()
            fake.advance(299)

            with self.assertRaises(NeedsAIOptimization):
                publisher.submit_once({"submitSelector": ".submit-add"})
            self.assertEqual(0, sum(1 for action, _ in publisher.client.commands if action == "click"))

    def test_reconciliation_rejects_multiple_same_title_items(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            video = Path(directory) / "video.mp4"
            video.write_bytes(b"video")
            manifest = validate_manifest(self.make_manifest(video), self.profile)
            audit = AuditLog(Path(directory) / "logs", "run")
            state = {"possible_submit": True, "submit_intent_epoch": 1000}
            publisher = BilibiliPublisher(
                manifest, self.profile, audit, "run", "session", resume_state=state,
                client_factory=FakeWebBridgeClient, ledger_path=self.make_ledger(directory),
            )
            with patch.object(publisher, "backend_duplicate_check", return_value=[{"title": manifest["title"]}, {"title": manifest["title"]}]):
                with self.assertRaises(NeedsAIOptimization):
                    publisher.reconcile_after_possible_submit()

    def test_backend_api_error_never_becomes_empty_duplicate_result(self) -> None:
        class ApiErrorClient(FakeWebBridgeClient):
            def evaluate_json(self, code, timeout=120):
                if "/x/web/archives" in code:
                    return {"ok": False, "reason": "api_error", "code": -101, "message": "账号未登录"}
                return super().evaluate_json(code, timeout)

        with tempfile.TemporaryDirectory() as directory:
            video = Path(directory) / "video.mp4"
            video.write_bytes(b"video")
            manifest = validate_manifest(self.make_manifest(video), self.profile)
            publisher = BilibiliPublisher(
                manifest, self.profile, AuditLog(Path(directory) / "logs", "run"), "run", "session",
                client_factory=ApiErrorClient, ledger_path=self.make_ledger(directory),
            )
            with self.assertRaises(PublishError):
                publisher.backend_duplicate_check()

    def test_backend_duplicate_check_uses_profile_navigation_timeout(self) -> None:
        class TimeoutCaptureClient(FakeWebBridgeClient):
            def command(self, action, args, timeout=120):
                if action == "navigate":
                    self.navigation_timeout = timeout
                return super().command(action, args, timeout)

        with tempfile.TemporaryDirectory() as directory:
            video = Path(directory) / "video.mp4"
            video.write_bytes(b"video")
            manifest = validate_manifest(self.make_manifest(video), self.profile)
            publisher = BilibiliPublisher(
                manifest, self.profile, AuditLog(Path(directory) / "logs", "run"), "run", "session",
                client_factory=TimeoutCaptureClient, ledger_path=self.make_ledger(directory),
            )

            publisher.backend_duplicate_check()
            self.assertEqual(
                self.profile["timing"]["archive_navigation_timeout_seconds"],
                publisher.client.navigation_timeout,
            )

    def test_backend_duplicate_check_uses_profile_evaluate_timeout(self) -> None:
        class TimeoutCaptureClient(FakeWebBridgeClient):
            def evaluate_json(self, code, timeout=120):
                if "/x/web/archives" in code:
                    self.evaluate_timeout = timeout
                return super().evaluate_json(code, timeout)

        with tempfile.TemporaryDirectory() as directory:
            video = Path(directory) / "video.mp4"
            video.write_bytes(b"video")
            profile = json.loads(json.dumps(self.profile))
            profile["timing"]["archive_evaluate_timeout_seconds"] = 47
            manifest = validate_manifest(self.make_manifest(video), profile)
            publisher = BilibiliPublisher(
                manifest, profile, AuditLog(Path(directory) / "logs", "run"), "run", "session",
                client_factory=TimeoutCaptureClient, ledger_path=self.make_ledger(directory),
            )

            publisher.backend_duplicate_check()
            self.assertEqual(47, publisher.client.evaluate_timeout)

    def test_backend_duplicate_and_reconciliation_support_capital_archive(self) -> None:
        class CapitalArchiveClient(FakeWebBridgeClient):
            def evaluate_json(self, code, timeout=120):
                if "/x/web/archives" in code:
                    return {
                        "ok": True,
                        "items": [{
                            "Archive": {
                                "title": "第32集｜顾总今天陪小满玩",
                                "aid": 123,
                                "bvid": "BVTEST",
                                "ctime": 1200,
                            }
                        }],
                        "total": 1,
                        "pages": 1,
                    }
                return super().evaluate_json(code, timeout)

        with tempfile.TemporaryDirectory() as directory:
            video = Path(directory) / "video.mp4"
            video.write_bytes(b"video")
            manifest = validate_manifest(self.make_manifest(video), self.profile)
            publisher = BilibiliPublisher(
                manifest,
                self.profile,
                AuditLog(Path(directory) / "logs", "run"),
                "run",
                "session",
                resume_state={"possible_submit": True, "submit_intent_epoch": 1000},
                client_factory=CapitalArchiveClient,
                ledger_path=self.make_ledger(directory),
            )

            duplicates = publisher.backend_duplicate_check(allow_existing=True)
            self.assertEqual(1, len(duplicates))
            result = publisher.reconcile_after_possible_submit()
            self.assertEqual("123", result["aid"])
            self.assertEqual("BVTEST", result["bvid"])
            self.assertTrue(result["ledger_write"]["written"])

    def test_charge_manifest_gets_fixed_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            video = Path(directory) / "charge.mp4"
            video.write_bytes(b"video")
            manifest = self.make_manifest(video)
            manifest["publish_type"] = "charge"
            normalized = validate_manifest(manifest, self.profile)

            self.assertEqual("00:00:05", normalized["charge"]["preview_end"])
            self.assertEqual("包月付费", normalized["charge"]["payment"])
            self.assertEqual("30元档", normalized["charge"]["tier"])

    def test_charge_custom_values_are_used_by_batch_and_check(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            video = Path(directory) / "charge.mp4"
            video.write_bytes(b"video")
            manifest = self.make_manifest(video)
            manifest["publish_type"] = "charge"
            manifest["charge"] = {"preview_end": "00:00:09", "payment": "单集付费", "tier": "50元档"}
            normalized = validate_manifest(manifest, self.profile)
            batch = build_batch_script(self.profile, normalized)
            check = build_check_script(self.profile, normalized)

            for expected in ("00:00:09", "单集付费", "50元档"):
                self.assertIn(expected, batch)
                self.assertIn(expected, check)

    def test_five_minute_checkpoint_stops_before_more_writes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            video = Path(directory) / "video.mp4"
            video.write_bytes(b"video")
            manifest = validate_manifest(self.make_manifest(video), self.profile)
            audit = AuditLog(Path(directory) / "logs", "run")
            publisher = BilibiliPublisher(
                manifest, self.profile, audit, "run", "session",
                client_factory=FakeWebBridgeClient, ledger_path=self.make_ledger(directory),
            )
            fake = FakeTime()
            publisher.clock = AttemptClock(now=fake)
            publisher.client.clock = publisher.clock
            publisher.clock.start_round()
            fake.advance(301)

            with self.assertRaises(NeedsAIOptimization):
                publisher.require_active_attempt("before_write")


if __name__ == "__main__":
    unittest.main()
