#!/usr/bin/env python3
"""AI 内部使用的 B站视频发布自动化引擎。

用户不直接运行本工具。AI 将自然语言发布意图锁定为 manifest 后调用它：
正常页面一次批处理；已知异常自动做针对性恢复；未知异常输出最小证据，
供 AI 更新 profile 后续跑同一 BrowserSkill session。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any, Callable, Sequence


def _load_ledger():
    spec = spec_from_file_location("gg_bilibili_ledger", Path(__file__).with_name("ledger.py"))
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_ledger = _load_ledger()
DEFAULT_CONFIG = _ledger.DEFAULT_CONFIG
DEFAULT_PROFILE = Path(__file__).with_name("bilibili_publish_profile.json")
BROWSER_SKILL_BIN = Path.home() / ".local/bin/bsk"
AI_DISCLOSURE = "本作品为AI生成短剧，人物与剧情均为虚构演绎，仅供娱乐。"
load_workspace = _ledger.load_workspace
escape_markdown_cell = _ledger.escape_markdown_cell


def append_video_ledger(record: dict[str, Any], ledger_path: Path) -> dict[str, Any]:
    try:
        return _ledger.append_video_ledger(record, ledger_path)
    except ValueError as exc:
        raise PreflightError(str(exc), {"path": str(ledger_path)}) from exc


class PublishError(RuntimeError):
    code = "publish_error"
    exit_code = 1

    def __init__(self, message: str, evidence: dict[str, Any] | None = None):
        super().__init__(message)
        self.evidence = evidence or {}


class PreflightError(PublishError):
    code = "preflight_failed"
    exit_code = 2


class DuplicateError(PublishError):
    code = "duplicate_detected"
    exit_code = 78


class ExternalBlocker(PublishError):
    code = "external_blocker"
    exit_code = 76


class NeedsAIOptimization(PublishError):
    code = "needs_ai_optimization"
    exit_code = 75


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def stable_hash(value: Any) -> str:
    return hashlib.sha256(compact_json(value).encode()).hexdigest()


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    with temporary.open("w", encoding="utf-8") as file_obj:
        file_obj.write(content)
        file_obj.flush()
        os.fsync(file_obj.fileno())
    temporary.replace(path)
    try:
        directory_fd = os.open(path.parent, os.O_RDONLY)
        os.fsync(directory_fd)
        os.close(directory_fd)
    except OSError:
        pass


def process_alive(pid: Any) -> bool:
    try:
        value = int(pid)
        if value <= 0:
            return False
        os.kill(value, 0)
        return True
    except (TypeError, ValueError, ProcessLookupError):
        return False
    except PermissionError:
        return True


def claim_manifest_run(
    manifest_hash: str,
    proposed_run_id: str,
    log_root: Path,
    explicit_run_id: bool = False,
) -> tuple[str, bool]:
    """按 manifest 原子互斥；崩溃后新调用自动接管旧 run。"""
    inflight_root = log_root / "inflight"
    inflight_root.mkdir(parents=True, exist_ok=True)
    lock_dir = inflight_root / f"{manifest_hash}.lock"
    owner_path = lock_dir / "owner.json"
    try:
        lock_dir.mkdir()
    except FileExistsError:
        try:
            owner = load_json(owner_path)
        except PreflightError as exc:
            raise PreflightError("manifest 发布锁损坏，禁止绕过后另起投稿", {"lock": str(lock_dir)}) from exc
        existing_run_id = str(owner.get("run_id") or "")
        if owner.get("manifest_hash") != manifest_hash or not existing_run_id:
            raise PreflightError("manifest 发布锁身份不完整，禁止继续", {"lock": str(lock_dir)})
        if process_alive(owner.get("pid")):
            raise PreflightError(
                "相同发布输入已有正在执行的进程，禁止并发投稿",
                {"run_id": existing_run_id, "pid": owner.get("pid"), "lock": str(lock_dir)},
            )
        state_path = log_root / existing_run_id / "state.json"
        result_path = log_root / existing_run_id / "result.json"
        if state_path.exists():
            if explicit_run_id and proposed_run_id != existing_run_id:
                raise PreflightError("指定 run-id 与相同 manifest 的未完成任务不一致", {"existing_run_id": existing_run_id})
            atomic_write(owner_path, compact_json({
                "manifest_hash": manifest_hash, "run_id": existing_run_id,
                "pid": os.getpid(), "claimed_at_utc": utc_now(), "adopted": True,
            }) + "\n")
            return existing_run_id, True
        if result_path.exists() or not state_path.exists():
            owner_path.unlink(missing_ok=True)
            try:
                lock_dir.rmdir()
            except OSError as exc:
                raise PreflightError("无法清理无状态的过期 manifest 发布锁", {"lock": str(lock_dir)}) from exc
            return claim_manifest_run(manifest_hash, proposed_run_id, log_root, explicit_run_id)
    if explicit_run_id and not (log_root / proposed_run_id / "state.json").exists():
        lock_dir.rmdir()
        raise PreflightError("指定了 run-id，但没有可续跑状态；禁止把它当成新任务启动", {"run_id": proposed_run_id})
    atomic_write(owner_path, compact_json({
        "manifest_hash": manifest_hash, "run_id": proposed_run_id,
        "pid": os.getpid(), "claimed_at_utc": utc_now(), "adopted": False,
    }) + "\n")
    return proposed_run_id, False


def release_manifest_run(manifest_hash: str, run_id: str, log_root: Path) -> None:
    lock_dir = log_root / "inflight" / f"{manifest_hash}.lock"
    owner_path = lock_dir / "owner.json"
    if not owner_path.exists():
        return
    owner = load_json(owner_path)
    if owner.get("manifest_hash") != manifest_hash or owner.get("run_id") != run_id:
        raise PublishError("拒绝释放不属于当前任务的 manifest 发布锁", {"lock": str(lock_dir)})
    owner_path.unlink()
    lock_dir.rmdir()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PreflightError(f"JSON 不可读：{path}: {exc}") from exc
    if not isinstance(value, dict):
        raise PreflightError(f"JSON 顶层必须是对象：{path}")
    return value


def first_present(mapping: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = mapping.get(key)
        if value is not None:
            return value
    return None


@dataclass
class AttemptClock:
    now: Callable[[], float] = time.monotonic
    task_started: float = field(init=False)
    round_started: float | None = None
    round_number: int = 0
    external_latency_seconds: float = 0.0
    external_evidence: list[dict[str, Any]] = field(default_factory=list)
    markers: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.task_started = self.now()

    def start_round(self) -> int:
        self.round_number += 1
        self.round_started = self.now()
        self.markers = {"page_open_command": self.round_started}
        self.external_latency_seconds = 0.0
        self.external_evidence = []
        return self.round_number

    def mark(self, name: str) -> float:
        value = self.now()
        self.markers[name] = value
        return value

    def round_elapsed(self) -> float:
        if self.round_started is None:
            return 0.0
        return self.now() - self.round_started

    def task_elapsed(self) -> float:
        return self.now() - self.task_started

    def restore(self, state: dict[str, Any], wall_downtime_seconds: float = 0.0) -> None:
        now_value = self.now()
        task_elapsed = float(state.get("task_elapsed_seconds") or 0.0) + max(0.0, wall_downtime_seconds)
        round_elapsed = float(state.get("round_elapsed_seconds") or 0.0) + max(0.0, wall_downtime_seconds)
        self.task_started = now_value - task_elapsed
        self.round_started = now_value - round_elapsed
        self.round_number = int(state.get("round") or 1)
        self.external_latency_seconds = float(state.get("external_latency_seconds") or 0.0)
        self.external_evidence = list(state.get("external_evidence") or [])
        previous_markers = state.get("markers") or {}
        self.markers = {
            key: self.round_started + float(relative_seconds)
            for key, relative_seconds in previous_markers.items()
        }

    def classify(self, timing: dict[str, Any]) -> str:
        elapsed = self.round_elapsed()
        failure = float(timing["attempt_failure_seconds"])
        grace = min(float(timing.get("external_grace_seconds", 0)), self.external_latency_seconds)
        if elapsed > failure + grace:
            return "attempt_failed"
        if elapsed > float(timing["normal_sla_seconds"]):
            return "over_one_minute"
        return "within_one_minute"

    def add_external_evidence(self, kind: str, seconds: float, **details: Any) -> None:
        seconds = max(0.0, float(seconds))
        self.external_latency_seconds += seconds
        self.external_evidence.append({"kind": kind, "seconds": round(seconds, 3), **details})

    def wall_markers(self) -> dict[str, float]:
        if self.round_started is None:
            return {}
        return {key: round(value - self.round_started, 3) for key, value in self.markers.items()}


class AuditLog:
    def __init__(self, root: Path, run_id: str):
        self.run_id = run_id
        self.directory = root / run_id
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / "audit.jsonl"
        self.result_path = self.directory / "result.json"
        self.state_path = self.directory / "state.json"

    def emit(self, event: str, **details: Any) -> None:
        record = {"timestamp_utc": utc_now(), "run_id": self.run_id, "event": event, **details}
        with self.path.open("a", encoding="utf-8") as file_obj:
            file_obj.write(compact_json(record) + "\n")

    def save_state(self, state: dict[str, Any]) -> None:
        atomic_write(self.state_path, compact_json(state) + "\n")

    def save_result(self, result: dict[str, Any]) -> None:
        atomic_write(self.result_path, compact_json(result) + "\n")


class BrowserSkillClient:
    def __init__(self, session: str, audit: AuditLog, clock: AttemptClock, timing: dict[str, Any]):
        self.session = session
        self.audit = audit
        self.clock = clock
        self.timing = timing
        self.command_count = 0
        self.submit_request_count = 0
        self.phase = "initializing"
        self.capture_key: str | None = None
        self.capture_filter: str | None = None

    @staticmethod
    def _run(arguments: list[str], timeout: float = 30.0, expect_json: bool = True) -> dict[str, Any]:
        try:
            proc = subprocess.run(
                [str(BROWSER_SKILL_BIN), *arguments], text=True, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, check=False, timeout=max(1.0, timeout) + 5,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise PublishError("BrowserSkill 命令未返回，检查扩展连接后再继续") from exc
        if proc.returncode != 0:
            raise PublishError("BrowserSkill 命令失败，先检查当前 Agent Window；不要盲目重试")
        if not expect_json:
            return {}
        try:
            return json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise PublishError("BrowserSkill JSON 响应不可解析") from exc

    @classmethod
    def start_session(cls, name: str) -> str:
        result = cls._run(['session', 'start', '--name', name, '--no-focus', '--json'])
        session = result.get('session_id')
        if not isinstance(session, str) or not session:
            raise PublishError('BrowserSkill 未返回新 session')
        return session

    def _session_command(self, arguments: list[str], timeout: float = 30.0) -> dict[str, Any]:
        return self._run([*arguments, '--session', self.session, '--json'], timeout)

    def health(self) -> dict[str, Any]:
        status = self._run(['status', '--json'])
        if not status.get('browsers'):
            raise PublishError('BrowserSkill 未连接浏览器，先在扩展中确认连接', status)
        sessions = self._run(['session', 'list', '--json'])
        if not any(item.get('session_id') == self.session for item in sessions):
            raise PublishError('BrowserSkill session 已不存在；不能在原发布流程上静默新建窗口')
        self.audit.emit('browser_skill_health', status={'daemon_version': status.get('daemon_version'), 'browsers': len(status.get('browsers', []))})
        return status

    def _evaluate_raw(self, code: str, timeout: float = 120.0) -> Any:
        data = self._session_command(['evaluate', code], timeout=timeout)
        value = data.get('value')
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return value

    def _install_capture(self, url_fragment: str) -> None:
        key = '__bsk_bilibili_' + uuid.uuid4().hex
        script = r'''
const key=CAPTURE_KEY,target=CAPTURE_TARGET;
const store={entries:[],fetch:window.fetch,open:XMLHttpRequest.prototype.open,send:XMLHttpRequest.prototype.send};
const add=value=>{if(value.url.includes(target))store.entries.push(value);};
window.fetch=async function(input,init){
 const request=new Request(input,init),response=await store.fetch.apply(this,arguments);
 if(request.url.includes(target)){let body='';try{body=await response.clone().text();}catch(_){ }add({url:request.url,status:response.status,body});}
 return response;
};
XMLHttpRequest.prototype.open=function(method,url){this.__bskBili={method,url:String(url)};return store.open.apply(this,arguments);};
XMLHttpRequest.prototype.send=function(body){const request=this.__bskBili;if(request&&request.url.includes(target))this.addEventListener('loadend',()=>{let text='';try{text=this.responseText||'';}catch(_){ }add({url:request.url,status:this.status,body:text});},{once:true});return store.send.apply(this,arguments);};
window[key]=store;return JSON.stringify({ok:true});
'''.replace('CAPTURE_KEY', json.dumps(key)).replace('CAPTURE_TARGET', json.dumps(url_fragment))
        result = self._evaluate_raw('(()=>{' + script + '})()', timeout=15)
        if not isinstance(result, dict) or not result.get('ok'):
            raise PublishError('BrowserSkill 投稿响应捕获未就绪')
        self.capture_key, self.capture_filter = key, url_fragment

    def _captured_entries(self) -> list[dict[str, Any]]:
        if not self.capture_key:
            return []
        entries = self._evaluate_raw(
            '(()=>{return JSON.stringify((window[' + json.dumps(self.capture_key) + ']?.entries||[]).slice(-10));})()',
            timeout=15,
        )
        return entries if isinstance(entries, list) else []

    def _restore_capture(self) -> None:
        if not self.capture_key:
            return
        self._evaluate_raw('(()=>{' + r'''
const store=window[CAPTURE_KEY];
if(store){window.fetch=store.fetch;XMLHttpRequest.prototype.open=store.open;XMLHttpRequest.prototype.send=store.send;}
return JSON.stringify({ok:true});
'''.replace('CAPTURE_KEY', json.dumps(self.capture_key)) + '})()', timeout=15)
        self.capture_key, self.capture_filter = None, None

    def _agent_tabs(self) -> list[dict[str, Any]]:
        return self._session_command(['tab', 'list', '--scope', 'agent'], timeout=15).get('tabs', [])

    def command(self, action: str, args: dict[str, Any], timeout: float = 120.0) -> dict[str, Any]:
        self.command_count += 1
        if self.clock.round_started is not None and self.phase not in {"preflight", "backend_duplicate_check"}:
            grace = min(
                float(self.timing.get("external_grace_seconds", 0)),
                self.clock.external_latency_seconds,
            )
            remaining = float(self.timing["attempt_failure_seconds"]) + grace - self.clock.round_elapsed()
            timeout = min(timeout, max(1.0, remaining))
        started = time.monotonic()
        started_epoch = time.time()
        error: Any = None
        try:
            if action == 'navigate':
                body = self._session_command(['navigate', args['url'], '--timeout', f'{max(1, int(timeout))}s'], timeout)
            elif action == 'evaluate':
                body = self._session_command(['evaluate', args['code']], timeout)
            elif action == 'upload':
                command = ['upload', '--selector', args['selector']]
                for path in args['files']:
                    command.extend(['--file', path])
                body = self._session_command(command, timeout)
            elif action == 'click':
                body = self._session_command(['click', '--selector', args['selector']], timeout)
            elif action == 'close_tab':
                tabs = self._agent_tabs()
                if len(tabs) > 1:
                    active = next((tab for tab in tabs if tab.get('active')), tabs[-1])
                    body = self._session_command(['tab', 'close', str(active['tab_id'])], timeout)
                else:
                    body = {'closed': False, 'reason': 'single_agent_tab_reused'}
            elif action == 'select_existing_tab':
                wanted = args['url']
                tab = next((item for item in self._agent_tabs() if item.get('url', '').startswith(wanted)), None)
                if not tab:
                    raise PublishError('当前 BrowserSkill session 中找不到续跑投稿页')
                self._session_command(['tab', 'select', str(tab['tab_id'])], timeout)
                body = {'url': tab['url'], 'tabId': tab['tab_id']}
            elif action == 'network':
                cmd = args.get('cmd')
                if cmd == 'start':
                    if not args.get('filter'):
                        raise PublishError('BrowserSkill 响应捕获必须限制到已知投稿路径')
                    self._install_capture(args['filter'])
                    body = {'started': True}
                elif cmd == 'list':
                    fragment = args.get('filter') or self.capture_filter or ''
                    body = {'requests': [
                        {'requestId': f'capture-{index}', 'url': item.get('url'), 'status': item.get('status')}
                        for index, item in enumerate(self._captured_entries()) if fragment in item.get('url', '')
                    ]}
                elif cmd == 'detail':
                    try:
                        index = int(str(args['requestId']).removeprefix('capture-'))
                        item = self._captured_entries()[index]
                    except (ValueError, IndexError, KeyError):
                        raise PublishError('投稿响应捕获不存在') from None
                    body = {'responseBody': item.get('body')}
                elif cmd == 'stop':
                    self._restore_capture()
                    body = {'stopped': True}
                else:
                    raise PublishError('Unsupported BrowserSkill network command')
            elif action == 'stop_session':
                self._run(['session', 'stop', self.session], timeout, expect_json=False)
                body = {'closed': True}
            else:
                raise PublishError('Unsupported BrowserSkill action: ' + action)
        except (PublishError, RuntimeError) as exc:
            body = None
            error = str(exc)
        elapsed = time.monotonic() - started
        slow = elapsed >= float(self.timing.get("slow_command_seconds", 10))
        external_kind = None
        if slow and action in {"upload", "navigate", "network"} and body is not None:
            external_kind = f"{action}_latency"
            file_bytes = 0
            for file_name in args.get("files") or []:
                try:
                    file_bytes += Path(file_name).stat().st_size
                except OSError:
                    pass
            self.clock.add_external_evidence(
                external_kind, elapsed, phase=self.phase, action=action,
                started_epoch=round(started_epoch, 3), finished_epoch=round(time.time(), 3),
                response_ok=True, file_bytes=file_bytes or None,
            )
        safe_args = {
            key: value
            for key, value in args.items()
            if key in {"url", "selector", "cmd", "filter", "requestId"}
        }
        if "files" in args:
            safe_args["files"] = [Path(item).name for item in args["files"]]
        self.audit.emit(
            "browser_skill_command",
            action=action,
            sequence=self.command_count,
            round=self.clock.round_number,
            phase=self.phase,
            args=safe_args,
            timeout_seconds=round(timeout, 3),
            elapsed_seconds=round(elapsed, 3),
            slow_external_candidate=slow,
            external_evidence_kind=external_kind,
            ok=body is not None,
            error=error or (body or {}).get("error"),
        )
        if body is None:
            raise PublishError(f"BrowserSkill {action} 无响应：{error}", {"action": action, "elapsed": elapsed})
        return body

    def evaluate_json(self, code: str, timeout: float = 120.0) -> Any:
        data = self.command("evaluate", {"code": code}, timeout=timeout)
        value = data.get("value")
        if value is None:
            return None
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return value


def validate_profile(profile: dict[str, Any]) -> None:
    required = {"upload_url", "archive_url", "upload_input", "selectors", "semantic", "fixed_tags", "timing"}
    missing = sorted(required - set(profile))
    if missing:
        raise PreflightError("页面策略缺少字段", {"missing": missing})
    if len(profile["fixed_tags"]) != 8 or len(set(profile["fixed_tags"])) != 8:
        raise PreflightError("固定标签必须恰好 8 个且不重复")


def validate_manifest(
    manifest: dict[str, Any],
    profile: dict[str, Any],
    require_authorization: bool = True,
    verify_video: bool = True,
) -> dict[str, Any]:
    required = ["video", "sha256", "title", "title_basis", "description", "series", "work_label", "publish_type"]
    missing = [key for key in required if not manifest.get(key)]
    if missing:
        raise PreflightError("发布输入未锁定", {"missing": missing})
    if require_authorization:
        authorization = manifest.get("authorization") or {}
        if authorization.get("action") != "publish_bilibili_video" or not authorization.get("user_request"):
            raise PreflightError("缺少当前任务的用户发布授权证据")

    video = Path(str(manifest["video"])).expanduser().resolve()
    declared_sha = str(manifest["sha256"]).lower()
    if len(declared_sha) != 64 or any(char not in "0123456789abcdef" for char in declared_sha):
        raise PreflightError("sha256 必须是 64 位十六进制字符串")
    actual_sha = declared_sha
    if verify_video:
        if not video.is_file():
            raise PreflightError(f"视频不存在：{video}")
        actual_sha = sha256_file(video)
        if actual_sha.lower() != declared_sha:
            raise PreflightError("视频 SHA-256 与锁定输入不一致", {"expected": manifest["sha256"], "actual": actual_sha})
    title = str(manifest["title"]).strip()
    if not title or len(title) > 80:
        raise PreflightError("标题为空或超过 80 字", {"length": len(title)})
    if AI_DISCLOSURE not in str(manifest["description"]):
        raise PreflightError("简介缺少固定 AI 声明")
    if manifest["publish_type"] not in {"normal", "charge"}:
        raise PreflightError("publish_type 必须是 normal 或 charge")

    season = manifest.get("season")
    mapped_season = profile.get("season_map", {}).get(manifest["series"])
    no_season = season is False
    if no_season:
        season = None
    elif season is None and mapped_season:
        season = mapped_season
    if not no_season and (not isinstance(season, str) or not season.strip()):
        raise PreflightError("目标合集必须是非空字符串，或显式设为 false 表示不加入合集")
    if isinstance(season, str):
        season = season.strip()

    normalized = {
        **manifest,
        "video": str(video),
        "sha256": actual_sha,
        "title": title,
        "season": season,
        "partition": profile["semantic"]["partition_value"],
        "tags": list(profile["fixed_tags"]),
    }
    if manifest["publish_type"] == "charge":
        charge = manifest.get("charge") or {}
        preview_end = charge.get("preview_end", "00:00:05")
        payment = charge.get("payment", "包月付费")
        tier = charge.get("tier", "30元档")
        if not all(isinstance(value, str) and value.strip() for value in (preview_end, payment, tier)):
            raise PreflightError("充电试看、付费方式和档位必须是非空字符串")
        parts = preview_end.split(":")
        if len(parts) != 3 or any(not part.isdigit() for part in parts) or int(parts[1]) >= 60 or int(parts[2]) >= 60:
            raise PreflightError("充电试看时间必须是 HH:MM:SS")
        normalized["charge"] = {
            "preview_end": preview_end.strip(),
            "payment": payment.strip(),
            "tier": tier.strip(),
        }
    return normalized


def detect_local_duplicate(manifest: dict[str, Any], ledger_path: Path) -> None:
    try:
        _ledger.detect_local_duplicate(manifest, ledger_path)
    except _ledger.DuplicateDetected as exc:
        raise DuplicateError(str(exc), exc.evidence) from exc
    except ValueError as exc:
        raise PreflightError(str(exc), {"path": str(ledger_path)}) from exc


def staged_path(manifest: dict[str, Any], upload_copy_dir: Path | None = None) -> Path:
    stage_dir = upload_copy_dir or (Path.home() / "Downloads/platform-publish")
    suffix = Path(manifest["video"]).suffix.lower() or ".mp4"
    return stage_dir / f"bili-{manifest['sha256'][:16]}{suffix}"


def stage_video(manifest: dict[str, Any], upload_copy_dir: Path | None = None) -> Path:
    source = Path(manifest["video"])
    target = staged_path(manifest, upload_copy_dir)
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists() or target.stat().st_size != source.stat().st_size:
        shutil.copy2(source, target)
    return target


def probe_video(path: Path) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            [
                "ffprobe", "-v", "error", "-show_entries",
                "format=duration,size:stream=codec_type,codec_name,width,height",
                "-of", "json", str(path),
            ],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            check=False, timeout=15,
        )
    except subprocess.TimeoutExpired as exc:
        raise PreflightError("ffprobe 前置检查 15 秒未返回", {"path": str(path)}) from exc
    if proc.returncode != 0:
        raise PreflightError("ffprobe 无法读取视频", {"path": str(path), "error": proc.stderr.strip()})
    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise PreflightError("ffprobe 输出不可解析", {"path": str(path)}) from exc
    video_streams = [stream for stream in result.get("streams", []) if stream.get("codec_type") == "video"]
    duration = float((result.get("format") or {}).get("duration") or 0)
    if not video_streams or duration <= 0:
        raise PreflightError("文件不是可发布视频或时长无效", {"path": str(path), "probe": result})
    return result


def selector_js(profile: dict[str, Any]) -> str:
    return compact_json(profile["selectors"])


def common_js(profile: dict[str, Any], manifest: dict[str, Any]) -> str:
    config = compact_json(
        {
            "selectors": profile["selectors"],
            "semantic": profile["semantic"],
            "timing": profile["timing"],
            "title": manifest["title"],
            "description": manifest["description"],
            "tags": manifest["tags"],
            "season": manifest.get("season"),
            "publish_type": manifest["publish_type"],
            "charge": manifest.get("charge"),
            "upload_task_title": f"bili-{manifest['sha256'][:16]}",
            "cover_mode": (
                "custom"
                if manifest["title"] in profile.get("custom_cover_titles", [])
                else "platform_first_frame"
            ),
        }
    )
    return f"""
const cfg={config};
const sleep=(ms)=>new Promise(r=>setTimeout(r,ms));
const visible=(e)=>!!e&&!!(e.offsetWidth||e.offsetHeight||e.getClientRects().length)&&getComputedStyle(e).visibility!==\"hidden\";
const norm=(s)=>(s||\"\").replace(/\\s+/g,\"\").trim();
const one=(selectors,root=document)=>{{for(const s of selectors||[]){{const e=[...root.querySelectorAll(s)].find(visible);if(e)return e;}}return null;}};
const textNodes=(root=document)=>[...root.querySelectorAll(\"label,button,div,span,p,li,[role=option]\")].filter(visible);
const exactText=(wanted,root=document)=>{{const w=norm(wanted);return textNodes(root).filter(e=>norm(e.textContent)===w).sort((a,b)=>a.childElementCount-b.childElementCount)[0]||null;}};
const containingText=(wanted,root=document)=>{{const w=norm(wanted);return textNodes(root).filter(e=>norm(e.textContent).includes(w)).sort((a,b)=>norm(a.textContent).length-norm(b.textContent).length||a.childElementCount-b.childElementCount)[0]||null;}};
const setter=(el,value)=>{{const proto=el instanceof HTMLTextAreaElement?HTMLTextAreaElement.prototype:HTMLInputElement.prototype;const d=Object.getOwnPropertyDescriptor(proto,\"value\");if(d&&d.set)d.set.call(el,value);else el.value=value;el.dispatchEvent(new Event(\"input\",{{bubbles:true}}));el.dispatchEvent(new Event(\"change\",{{bubbles:true}}));}};
const fillEditable=(el,value)=>{{el.focus();const sel=getSelection();const range=document.createRange();range.selectNodeContents(el);sel.removeAllRanges();sel.addRange(range);document.execCommand(\"insertText\",false,value);el.dispatchEvent(new Event(\"input\",{{bubbles:true}}));}};
const formItem=(label)=>{{const text=exactText(label)||containingText(label);if(!text)return null;for(const s of cfg.selectors.form_item||[]){{const item=text.closest(s);if(item)return item;}}return text.parentElement||null;}};
const activePopup=()=>{{const nodes=[];for(const s of cfg.selectors.popover||[])for(const e of document.querySelectorAll(s))if(visible(e))nodes.push(e);return nodes[nodes.length-1]||null;}};
const optionText=(wanted)=>{{const popup=activePopup();return (popup&&(exactText(wanted,popup)||containingText(wanted,popup)))||exactText(wanted)||containingText(wanted);}};
const selectedValue=(root,selectors=[])=>{{if(!root)return \"\";const explicit=one(selectors,root);if(explicit)return explicit.textContent||explicit.value||\"\";const select=root.querySelector(\"select\");if(select)return select.selectedOptions?.[0]?.textContent||select.value||\"\";const active=[...root.querySelectorAll(\"[aria-selected=true],[aria-checked=true],input:checked,.selected,.active,.checked\")].filter(visible).sort((a,b)=>a.childElementCount-b.childElementCount)[0];if(active)return active.closest(\"label,[role=option],[class*=option],[class*=select]\")?.textContent||active.textContent||\"\";return \"\";}};
const clickable=(el)=>el?.closest(\"label,button,[role=button],li,[class*=radio],[class*=checkbox],[class*=select-item],[class*=option]\")||el;
const safeClick=(el)=>{{if(!el)return false;const target=clickable(el)||el;if(typeof target.click===\"function\"){{target.click();return true;}}target.dispatchEvent?.(new MouseEvent(\"click\",{{bubbles:true,cancelable:true,view:window}}));return true;}};
const cleanUnexpectedTags=async(allowed)=>{{
  const allowedSet=new Set(allowed||[]);
  const passes=Number(cfg.timing.tag_cleanup_passes||3);
  const settle=Number(cfg.timing.tag_cleanup_settle_ms||200);
  for(let pass=0;pass<passes;pass++){{
    const entries=[...document.querySelectorAll(cfg.selectors.visible_tags.join(\",\"))].filter(visible);
    const extras=entries.filter(el=>!allowedSet.has((el.textContent||\"\").trim()));
    if(!extras.length){{await sleep(settle);continue;}}
    for(const el of extras){{const parent=el.parentElement;const close=one(cfg.selectors.tag_remove,parent)||parent?.querySelector(\"svg\")?.parentElement;safeClick(close);}}
    await sleep(settle);
  }}
  return [...document.querySelectorAll(cfg.selectors.visible_tags.join(\",\"))].filter(visible).map(el=>(el.textContent||\"\").trim()).filter(value=>!allowedSet.has(value));
}};
const aiStatementRoot=()=>document.querySelector(\".statement-content\");
const aiStatementOption=(root)=>[...(root?.querySelectorAll(\"li.bcc-option\")||[])].find(e=>norm(e.textContent)===norm(cfg.semantic.ai_declaration))||null;
const aiStatementSelected=(root)=>{{const input=root?.querySelector(\".bcc-select-input-inner\");return norm(input?.value)===norm(cfg.semantic.ai_declaration)||norm(input?.getAttribute(\"value\"))===norm(cfg.semantic.ai_declaration);}};
const seasonTrigger=()=>one(cfg.selectors.season_trigger);
const seasonOption=(trigger,wanted)=>{{const scope=trigger?.closest(\".season-select,.video-season\")||document;return [...scope.querySelectorAll(\".season-item\")].find(e=>norm(e.querySelector(\".season-item-title\")?.textContent)===norm(wanted))||null;}};
const seasonSelected=()=>{{const triggers=[...document.querySelectorAll(\".video-season .season-enter\")].filter(visible);const selected=triggers.find(e=>norm(e.textContent)!==norm(\"请选择合集\"))||triggers[0];const label=selected?.querySelector(\".season-enter-text\");return label?.getAttribute(\"title\")||label?.textContent||selected?.textContent||\"\";}};
const checked=(el)=>{{const root=el?.closest(\"label,[class*=radio],[class*=checkbox]\")||el;const input=root?.querySelector?.(\"input\");return input?input.checked:(root?.getAttribute?.(\"aria-checked\")===\"true\"||/checked|active|selected/.test(root?.className||\"\"));}};
const moreSettingsLabel=()=>[...document.querySelectorAll(\".form .title .label\")].filter(visible).find(e=>norm(e.textContent).startsWith(norm(\"更多设置\")))||null;
const chargeRoot=()=>[...document.querySelectorAll(\".charging-pay-wrapper\")].find(visible)||null;
const chargeEnabled=(scope)=>!!scope?.querySelector(\".switch-container-active\");
const openChargeSection=async()=>{{if(!chargeRoot()){{safeClick(moreSettingsLabel());await sleep(180);}}return chargeRoot();}};
const setChargePreview=async(scope,value)=>{{const input=one(cfg.selectors.charge_preview,scope);if(input){{setter(input,value);return true;}}const selector=scope?.querySelector(\".duration-picker-selector\");if(!selector)return false;if(norm(selector.textContent)===norm(value))return true;let popup=[...scope.querySelectorAll(\".picker-popup-container\")].find(visible);if(!popup){{safeClick(selector);await sleep(100);popup=[...scope.querySelectorAll(\".picker-popup-container\")].find(visible);}}const panels=[...(popup?.querySelectorAll(\".picker-popup-panel-select-wrp\")||[])];const parts=value.split(\":\").map(Number);if(panels.length!==3||parts.some(Number.isNaN))return false;for(let i=0;i<3;i++){{const selected=panels[i].querySelector(\".time-selected\");if(selected&&Number(norm(selected.textContent))===parts[i])continue;const option=[...panels[i].querySelectorAll(\".picker-popup-panel-select-item\")].find(e=>visible(e)&&!e.classList.contains(\"time-select-disabled\")&&Number(norm(e.textContent))===parts[i]);if(!option)return false;safeClick(option);await sleep(50);}}safeClick(document.querySelector(\".video-basic-wrp .form .title\")||document.body);await sleep(100);return norm(selector.textContent)===norm(value);}};
const chargePaymentSelected=(scope,value)=>!!scope&&!!containingText(value,scope);
const chargeTierSelected=(scope,value)=>{{const selected=scope?.querySelector(\".charge-level .select-controller,.charge-level .select-item-cont\");return !!selected&&norm(selected.textContent).includes(norm(value));}};
const setChargeTier=async(scope,value)=>{{if(chargeTierSelected(scope,value))return true;const trigger=scope?.querySelector(\".charge-level .select-controller\");if(!trigger)return false;safeClick(trigger);await sleep(Number(cfg.timing.popover_wait_ms));const option=optionText(value);if(!option)return false;safeClick(option);await sleep(80);return chargeTierSelected(scope,value);}};
const snippet=(el)=>el?{{tag:el.tagName,class:String(el.className||\"\"),text:(el.textContent||\"\").trim().slice(0,180),outer:el.outerHTML.slice(0,900)}}:null;
"""


def build_ready_script(profile: dict[str, Any], manifest: dict[str, Any], editor: bool = False) -> str:
    timeout_key = "editor_timeout_seconds" if editor else "ready_timeout_seconds"
    upload_selector = json.dumps(profile["upload_input"], ensure_ascii=False)
    required = ["title", "description", "tag_input"]
    return f"""
(async()=>{{
{common_js(profile, manifest)}
const deadline=Date.now()+Number(cfg.timing.{timeout_key})*1000;
let state=null;
while(Date.now()<deadline){{
  const draftAction=one(cfg.selectors.{"draft_resume" if editor else "draft_discard"}||[]);
  if(draftAction&&visible(draftAction)){{safeClick(draftAction);await sleep(180);}}
  state={{url:location.href,upload:!!document.querySelector({upload_selector}),nodes:{{}}}};
  for(const key of {compact_json(required)}) state.nodes[key]=!!one(cfg.selectors[key]);
  const ok={str(editor).lower()}?Object.values(state.nodes).every(Boolean):(location.href==={json.dumps(profile['upload_url'])}&&state.upload);
  if(ok)return JSON.stringify({{ok:true,state}});
  await sleep(120);
}}
return JSON.stringify({{ok:false,stage:{json.dumps('editor_ready' if editor else 'upload_ready')},state}});
}})()
"""


def build_upload_progress_script() -> str:
    return """
(()=>{
const probe="uploadProgressProbe";
const text=(document.querySelector(".file-item")?.innerText||"").trim();
const inner=document.querySelector(".file-item-content-progress-inner");
const tasks=[...document.querySelectorAll(".task-status .text")].map(e=>(e.textContent||"").trim()).filter(Boolean);
const percentMatch=text.match(/(\\d+(?:\\.\\d+)?)%/);
const percent=percentMatch?Number(percentMatch[1]):0;
const sizeMatch=text.match(/已经上传：([\\d.]+)MB\\/([\\d.]+)MB/);
const uploaded=sizeMatch?Number(sizeMatch[1]):0;
const total=sizeMatch?Number(sizeMatch[2]):0;
const stuck=/0\\.0MB\\/0\\.0MB/.test(text)||(total===0&&percent===0&&/pending/.test(inner?.className||""));
const completedDirectly=tasks.some(t=>/上传完成|已完成/.test(t))||/success/.test(inner?.className||"")||/上传完成/.test(text);
const started=total>0||percent>0||uploaded>0||completedDirectly;
const complete=completedDirectly||(started&&(percent>=100||(!tasks.some(t=>t==="上传中..."||t==="等待上传")&&total>0)));
return JSON.stringify({probe,text:text.slice(0,240),tasks,percent,uploaded,total,stuck,started,complete,inner:inner?.className||""});
})()
"""


def build_batch_script(profile: dict[str, Any], manifest: dict[str, Any]) -> str:
    return f"""
(async()=>{{
{common_js(profile, manifest)}
const scriptStarted=performance.now();const uploadInput=one([cfg.upload_input]);if(uploadInput)uploadInput.dispatchEvent(new Event("change",{{bubbles:true}}));const editorDeadline=Date.now()+Number(cfg.timing.editor_timeout_seconds)*1000;
const editorKeys=[\"title\",\"description\",\"tag_input\"];
while(Date.now()<editorDeadline&&editorKeys.some(key=>!one(cfg.selectors[key]))){{
  const resume=one(cfg.selectors.draft_resume||[]);
  if(resume&&visible(resume)){{safeClick(resume);await sleep(180);}}
  else await sleep(120);
}}
const editorWaitMs=performance.now()-scriptStarted;const missingEditor=editorKeys.filter(key=>!one(cfg.selectors[key]));
if(missingEditor.length)return JSON.stringify({{ok:false,actions:[],failures:missingEditor.map(field=>({{field,reason:\"editor_node_missing\"}})),editorWaitMs,batchElapsedMs:performance.now()-scriptStarted}});
const actions=[];const failures=[];
const uploadTasks=[...document.querySelectorAll((cfg.selectors.upload_task||[]).join(\",\"))].filter(visible);
const uploadTaskTitles=uploadTasks.map(e=>(e.getAttribute(\"title\")||\"\").trim());
const uploadIdentityOk=uploadTasks.length===1&&uploadTaskTitles[0]===cfg.upload_task_title;
if(!uploadIdentityOk)return JSON.stringify({{ok:false,actions,failures:[{{field:\"upload_identity\",reason:\"queue_not_unique_or_wrong_file\",evidence:{{expected:cfg.upload_task_title,actual:uploadTaskTitles}}}}],editorWaitMs,batchElapsedMs:performance.now()-scriptStarted}});
const coverDeadline=Date.now()+Number(cfg.timing.cover_ready_wait_seconds||0)*1000;
let coverMissing=one(cfg.selectors.cover_missing);let cover=one(cfg.selectors.cover_candidate);
const customCover=cfg.cover_mode===\"custom\";
const coverReady=()=>!one(cfg.selectors.cover_missing)&&!!one(cfg.selectors.cover_main)&&(customCover||!!one(cfg.selectors.cover_selected));
while(!coverReady()&&!cover&&Date.now()<coverDeadline){{await sleep(120);coverMissing=one(cfg.selectors.cover_missing);cover=one(cfg.selectors.cover_candidate);}}
if(!coverReady()&&cover&&!customCover){{cover.click();actions.push(\"cover_first_frame\");await sleep(120);}}
else if(!coverReady())failures.push({{field:\"cover\",reason:customCover?\"custom_cover_missing\":\"candidate_missing\",evidence:snippet(coverMissing)}});

const title=one(cfg.selectors.title);if(title){{setter(title,cfg.title);const partTitle=one(cfg.selectors.part_title);if(partTitle)setter(partTitle,cfg.title);actions.push(\"title\");}}else failures.push({{field:\"title\",reason:\"node_missing\"}});
const desc=one(cfg.selectors.description);if(desc){{fillEditable(desc,cfg.description);actions.push(\"description\");}}else failures.push({{field:\"description\",reason:\"node_missing\"}});

const aiRoot=aiStatementRoot();const ai=exactText(cfg.semantic.ai_declaration)||containingText(cfg.semantic.ai_declaration);
if(aiRoot&&aiStatementOption(aiRoot)){{if(!aiStatementSelected(aiRoot)){{safeClick(aiRoot.querySelector(\".bcc-select-input-wrap,.bcc-select-input-inner\"));await sleep(80);safeClick(aiStatementOption(aiRoot));await sleep(80);}}actions.push(\"ai_declaration\");}}
else if(ai){{if(!checked(ai))safeClick(ai);actions.push(\"ai_declaration\");await sleep(80);}}else failures.push({{field:\"ai_declaration\",reason:\"node_missing\"}});

await cleanUnexpectedTags([]);
const tagInput=one(cfg.selectors.tag_input);
if(tagInput){{for(const tag of cfg.tags){{setter(tagInput,tag);tagInput.dispatchEvent(new KeyboardEvent(\"keydown\",{{key:\"Enter\",code:\"Enter\",keyCode:13,which:13,bubbles:true}}));tagInput.dispatchEvent(new KeyboardEvent(\"keyup\",{{key:\"Enter\",code:\"Enter\",keyCode:13,which:13,bubbles:true}}));await sleep(Number(cfg.timing.tag_event_gap_ms));}}await cleanUnexpectedTags(cfg.tags);actions.push(\"tags\");}}
else failures.push({{field:\"tags\",reason:\"input_missing\"}});

if(cfg.season){{const trigger=seasonTrigger();const seasonNotAvailable=document.querySelector(".video-season-tip")||containingText("开通合集功能需满足")||containingText("未开通合集");if(trigger){{if(!trigger.classList.contains(\"season-enter-active\"))safeClick(trigger);await sleep(Number(cfg.timing.popover_wait_ms));const option=seasonOption(trigger,cfg.season)||optionText(cfg.season);if(option){{safeClick(option);actions.push(\"season\");}}else failures.push({{field:\"season\",reason:\"option_missing\",evidence:snippet(trigger)}});}}else if(seasonNotAvailable){{actions.push(\"season_skipped_account_unqualified\");}}else failures.push({{field:\"season\",reason:\"trigger_missing\"}});}}

const partitionItem=formItem(cfg.semantic.partition_label);if(partitionItem){{if(norm(selectedValue(partitionItem,cfg.selectors.partition_selected))!==norm(cfg.semantic.partition_value)){{const trigger=one([\".select-controller\",\"[class*=select]\",\"[role=button]\"],partitionItem);trigger?.click();await sleep(Number(cfg.timing.popover_wait_ms));const option=optionText(cfg.semantic.partition_value);if(option)clickable(option)?.click();else failures.push({{field:\"partition\",reason:\"option_missing\",evidence:snippet(activePopup()||partitionItem)}});}}actions.push(\"partition\");}}else failures.push({{field:\"partition\",reason:\"section_missing\"}});

const chargeScope=await openChargeSection();const charge=chargeScope?(exactText(cfg.semantic.charge_enabled,chargeScope)||containingText(cfg.semantic.charge_enabled,chargeScope)):null;
if(cfg.publish_type===\"charge\"){{if(charge){{if(!chargeEnabled(chargeScope))safeClick(chargeScope.querySelector(\".switch-container\")||charge);actions.push(\"charge_enabled\");await sleep(180);if(!await setChargePreview(chargeScope,cfg.charge.preview_end))failures.push({{field:\"charge\",reason:\"preview_control_missing\"}});if(!chargePaymentSelected(chargeScope,cfg.charge.payment))failures.push({{field:\"charge\",reason:\"payment_missing\"}});if(!await setChargeTier(chargeScope,cfg.charge.tier))failures.push({{field:\"charge\",reason:\"tier_missing\"}});actions.push(\"charge_terms\");}}else failures.push({{field:\"charge\",reason:\"control_missing\"}});}}
else if(charge&&chargeEnabled(chargeScope)){{safeClick(chargeScope.querySelector(\".switch-container\")||charge);actions.push(\"charge_disabled\");await sleep(100);}}
document.activeElement?.blur?.();document.dispatchEvent(new KeyboardEvent(\"keydown\",{{key:\"Escape\",bubbles:true}}));
return JSON.stringify({{ok:failures.length===0,actions,failures,editorWaitMs,batchElapsedMs:performance.now()-scriptStarted}});
}})()
"""


def build_check_script(profile: dict[str, Any], manifest: dict[str, Any]) -> str:
    return f"""
(()=>{{
{common_js(profile, manifest)}
const title=one(cfg.selectors.title);const partTitle=one(cfg.selectors.part_title);const desc=one(cfg.selectors.description);
const tags=[...document.querySelectorAll(cfg.selectors.visible_tags.join(\",\"))].filter(visible).map(e=>(e.textContent||\"\").trim());
const partition=formItem(cfg.semantic.partition_label);const season=formItem(cfg.semantic.season_label)||seasonTrigger()?.parentElement;
const aiRoot=aiStatementRoot();const ai=exactText(cfg.semantic.ai_declaration)||containingText(cfg.semantic.ai_declaration);
const coverOk=!!one(cfg.selectors.cover_main)&&!one(cfg.selectors.cover_missing)&&(cfg.cover_mode===\"custom\"||!!one(cfg.selectors.cover_selected));
const uploadTasks=[...document.querySelectorAll((cfg.selectors.upload_task||[]).join(\",\"))].filter(visible);
const uploadTaskTitles=uploadTasks.map(e=>(e.getAttribute(\"title\")||\"\").trim());
const uploadIdentityOk=uploadTasks.length===1&&uploadTaskTitles[0]===cfg.upload_task_title;
let submit=null,submitSelector=null;for(const selector of cfg.selectors.submit||[]){{const candidate=[...document.querySelectorAll(selector)].find(visible);if(candidate){{submit=candidate;submitSelector=selector;break;}}}}
const values={{title:title?.value||\"\",partTitle:partTitle?.value||\"\",description:desc?.innerText||desc?.textContent||\"\",tags,partition:selectedValue(partition,cfg.selectors.partition_selected),season:seasonSelected()||selectedValue(season,cfg.selectors.season_selected),aiChecked:aiStatementSelected(aiRoot)||checked(ai),coverOk,uploadTaskTitles,submitEnabled:!!submit&&!submit.disabled}};
const seasonNotAvailable=document.querySelector(".video-season-tip")||containingText("开通合集功能需满足")||containingText("未开通合集");
const checks={{upload_identity:uploadIdentityOk,title:values.title.trim()===cfg.title,part_title:!partTitle||values.partTitle.trim()===cfg.title,description:norm(values.description)===norm(cfg.description),tags:tags.length===cfg.tags.length&&cfg.tags.every(t=>tags.includes(t)),partition:norm(values.partition)===norm(cfg.semantic.partition_value),season:seasonNotAvailable?true:(cfg.season?norm(values.season)===norm(cfg.season):(!norm(values.season)||norm(values.season)===norm("请选择合集"))),ai_declaration:values.aiChecked,cover:coverOk,submit:values.submitEnabled}};
const chargeScope=chargeRoot();const charge=chargeScope?(exactText(cfg.semantic.charge_enabled,chargeScope)||containingText(cfg.semantic.charge_enabled,chargeScope)):null;
if(cfg.publish_type===\"charge\"){{const preview=chargeScope?.querySelector(\".duration-picker-selector\")||one(cfg.selectors.charge_preview,chargeScope);checks.charge=!!charge&&chargeEnabled(chargeScope)&&chargePaymentSelected(chargeScope,cfg.charge.payment)&&chargeTierSelected(chargeScope,cfg.charge.tier)&&!!preview&&norm(preview.value||preview.textContent)===norm(cfg.charge.preview_end);}}
// 普通投稿页可能完全不渲染充电设置；控件缺席即表示未开启充电，不能误报失败。
else checks.charge=!charge||!checked(charge);
const issues=Object.entries(checks).filter(([,ok])=>!ok).map(([field])=>({{field,reason:\"total_check_failed\",evidence:field===\"partition\"?snippet(partition):field===\"season\"?snippet(season):null}}));
return JSON.stringify({{ok:issues.length===0,checks,values,issues,submitSelector}});
}})()
"""


def build_repair_script(profile: dict[str, Any], manifest: dict[str, Any], fields: Sequence[str]) -> str:
    # 字段集合来自唯一总检；所有失败字段仍在一次 evaluate 中恢复，不跨 Agent 回合逐项操作。
    field_list = sorted(set(fields))
    return f"""
(async()=>{{
{common_js(profile, manifest)}
const fields={compact_json(field_list)};const actions=[];const failures=[];
if(fields.includes(\"cover\")){{if(cfg.cover_mode===\"custom\"){{if(one(cfg.selectors.cover_main)&&!one(cfg.selectors.cover_missing))actions.push(\"cover_existing_custom\");else failures.push({{field:\"cover\",reason:\"custom_cover_missing\"}});}}else{{const candidate=one(cfg.selectors.cover_candidate);if(candidate){{candidate.click();actions.push(\"cover\");await sleep(120);}}else failures.push({{field:\"cover\",reason:\"candidate_missing\"}});}}}}
if(fields.includes(\"title\")||fields.includes(\"part_title\")){{const el=one(cfg.selectors.title);if(el){{setter(el,cfg.title);const partTitle=one(cfg.selectors.part_title);if(partTitle)setter(partTitle,cfg.title);actions.push(\"title\");}}else failures.push({{field:\"title\",reason:\"node_missing\"}});}}
if(fields.includes(\"description\")){{const el=one(cfg.selectors.description);if(el){{fillEditable(el,cfg.description);actions.push(\"description\");}}else failures.push({{field:\"description\",reason:\"node_missing\"}});}}
if(fields.includes(\"ai_declaration\")){{const root=aiStatementRoot();const option=aiStatementOption(root);const el=exactText(cfg.semantic.ai_declaration)||containingText(cfg.semantic.ai_declaration);if(root&&option){{if(!aiStatementSelected(root)){{safeClick(root.querySelector(\".bcc-select-input-wrap,.bcc-select-input-inner\"));await sleep(80);safeClick(option);await sleep(80);}}actions.push(\"ai_declaration\");}}else if(el){{if(!checked(el))safeClick(el);actions.push(\"ai_declaration\");}}else failures.push({{field:\"ai_declaration\",reason:\"node_missing\"}});}}
if(fields.includes(\"tags\")){{await cleanUnexpectedTags(cfg.tags);const now=[...document.querySelectorAll(cfg.selectors.visible_tags.join(\",\"))].filter(visible).map(e=>(e.textContent||\"\").trim());const missing=cfg.tags.filter(t=>!now.includes(t));const input=one(cfg.selectors.tag_input);if(input){{for(const tag of missing){{setter(input,tag);input.dispatchEvent(new KeyboardEvent(\"keydown\",{{key:\"Enter\",code:\"Enter\",keyCode:13,which:13,bubbles:true}}));input.dispatchEvent(new KeyboardEvent(\"keyup\",{{key:\"Enter\",code:\"Enter\",keyCode:13,which:13,bubbles:true}}));await sleep(Number(cfg.timing.tag_event_gap_ms));}}await cleanUnexpectedTags(cfg.tags);actions.push(\"tags\");}}else failures.push({{field:\"tags\",reason:\"input_missing\"}});}}
if(fields.includes(\"season\")&&cfg.season){{const trigger=seasonTrigger();if(trigger){{if(!trigger.classList.contains(\"season-enter-active\"))safeClick(trigger);await sleep(Number(cfg.timing.popover_wait_ms));const option=seasonOption(trigger,cfg.season)||optionText(cfg.season);if(option){{safeClick(option);actions.push(\"season\");}}else failures.push({{field:\"season\",reason:\"option_missing\"}});}}else failures.push({{field:\"season\",reason:\"trigger_missing\"}});}}
if(fields.includes(\"partition\")){{const item=formItem(cfg.semantic.partition_label);if(item){{const trigger=one([\".select-controller\",\"[class*=select]\",\"[role=button]\"],item);trigger?.click();await sleep(Number(cfg.timing.popover_wait_ms));const option=optionText(cfg.semantic.partition_value);if(option){{clickable(option)?.click();actions.push(\"partition\");}}else failures.push({{field:\"partition\",reason:\"option_missing\"}});}}else failures.push({{field:\"partition\",reason:\"section_missing\"}});}}
if(fields.includes(\"charge\")){{const scope=await openChargeSection();const charge=scope?(exactText(cfg.semantic.charge_enabled,scope)||containingText(cfg.semantic.charge_enabled,scope)):null;if(charge){{if(cfg.publish_type===\"normal\"){{if(chargeEnabled(scope))safeClick(scope.querySelector(\".switch-container\")||charge);actions.push(\"charge_disabled\");}}else{{if(!chargeEnabled(scope))safeClick(scope.querySelector(\".switch-container\")||charge);await sleep(180);if(!await setChargePreview(scope,cfg.charge.preview_end))failures.push({{field:\"charge\",reason:\"preview_control_missing\"}});if(!chargePaymentSelected(scope,cfg.charge.payment))failures.push({{field:\"charge\",reason:\"payment_missing\"}});if(!await setChargeTier(scope,cfg.charge.tier))failures.push({{field:\"charge\",reason:\"tier_missing\"}});actions.push(\"charge\");}}}}else if(cfg.publish_type===\"normal\"){{actions.push(\"charge_absent_normal\");}}else failures.push({{field:\"charge\",reason:\"control_missing\"}});}}
document.activeElement?.blur?.();document.dispatchEvent(new KeyboardEvent(\"keydown\",{{key:\"Escape\",bubbles:true}}));
return JSON.stringify({{ok:failures.length===0,requestedFields:fields,actions,failures}});
}})()
"""


def build_diagnostic_script(profile: dict[str, Any], manifest: dict[str, Any], issues: Sequence[dict[str, Any]]) -> str:
    fields = [issue.get("field") for issue in issues]
    return f"""
(()=>{{
{common_js(profile, manifest)}
const fields={compact_json(fields)};const evidence={{url:location.href,title:document.title,fields:{{}}}};
for(const field of fields){{let node=null;if(field===\"title\")node=one(cfg.selectors.title);else if(field===\"part_title\")node=one(cfg.selectors.part_title);else if(field===\"description\")node=one(cfg.selectors.description);else if(field===\"tags\")node=one(cfg.selectors.tag_input);else if(field===\"season\")node=formItem(cfg.semantic.season_label)||one(cfg.selectors.season_trigger);else if(field===\"partition\")node=formItem(cfg.semantic.partition_label);else if(field===\"ai_declaration\")node=containingText(cfg.semantic.ai_declaration);else if(field===\"cover\")node=one(cfg.selectors.cover_missing)||one(cfg.selectors.cover_candidate);else if(field===\"charge\")node=containingText(cfg.semantic.charge_settings)||containingText(cfg.semantic.charge_enabled);evidence.fields[field]=snippet(node);}}
return JSON.stringify(evidence);
}})()
"""


def build_archive_script() -> str:
    return """
(async()=>{const items=[];let complete=false,total=null,pages=0;for(let pn=1;pn<=20;pn++){pages=pn;let payload;try{const response=await fetch(`https://member.bilibili.com/x/web/archives?pn=${pn}&ps=50&status=all`,{credentials:'include'});payload=await response.json();if(!response.ok)return JSON.stringify({ok:false,reason:'http_error',status:response.status,pn});}catch(error){return JSON.stringify({ok:false,reason:'fetch_or_json_error',message:String(error),pn});}if(payload?.code!==0)return JSON.stringify({ok:false,reason:'api_error',code:payload?.code,message:payload?.message,pn});const data=payload?.data;if(!data||typeof data!=='object')return JSON.stringify({ok:false,reason:'data_missing',pn});let page=data.arc_audits||data.archives||data.list||data.items;if(!Array.isArray(page)){if(Number(data?.page?.count??data?.page?.total??data?.total)===0||(!data.arc_audits&&!data.archives)){page=[];}else{return JSON.stringify({ok:false,reason:'page_items_missing',keys:Object.keys(data),pn});}}const count=Number(data?.page?.count??data?.page?.total??data?.total);if(Number.isFinite(count))total=count;items.push(...page);if((total!==null&&items.length>=total)||page.length<50){complete=true;break;}}return JSON.stringify({ok:complete,reason:complete?null:'pagination_incomplete',items,total,pages});})()
"""


def archive_items(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    if isinstance(payload.get("items"), list):
        return payload["items"]
    data = payload.get("data")
    if isinstance(data, dict):
        for key in ("arc_audits", "archives", "list", "items"):
            if isinstance(data.get(key), list):
                return data[key]
    return []


def archive_record(item: dict[str, Any]) -> dict[str, Any]:
    """Return the archive payload across old and new Bilibili response shapes."""
    archive = item.get("archive") or item.get("Archive")
    return archive if isinstance(archive, dict) else item


def archive_timestamp(item: dict[str, Any]) -> float | None:
    archive = archive_record(item)
    for key in ("ctime", "pubtime", "created", "submit_time", "upload_time"):
        value = archive.get(key) if isinstance(archive, dict) else None
        if value is None:
            value = item.get(key)
        try:
            timestamp = float(value)
        except (TypeError, ValueError):
            continue
        if timestamp > 10_000_000_000:
            timestamp /= 1000
        return timestamp
    return None


def optimization_fields(state: dict[str, Any]) -> list[str]:
    evidence = ((state.get("optimization_request") or {}).get("evidence") or {})
    issues = evidence.get("issues") if isinstance(evidence, dict) else None
    if not isinstance(issues, list):
        return []
    return sorted(
        {
            str(issue.get("field"))
            for issue in issues
            if isinstance(issue, dict) and issue.get("field")
        }
    )


class BilibiliPublisher:
    def __init__(
        self,
        manifest: dict[str, Any],
        profile: dict[str, Any],
        audit: AuditLog,
        run_id: str,
        session: str,
        resume_state: dict[str, Any] | None = None,
        client_factory: Callable[..., BrowserSkillClient] = BrowserSkillClient,
        ledger_path: Path | None = None,
        profile_path: Path = DEFAULT_PROFILE,
        stop_before_submit: bool = False,
        upload_copy_dir: Path | None = None,
    ):
        self.manifest = manifest
        self.profile = profile
        self.audit = audit
        self.run_id = run_id
        self.session = session
        if ledger_path is None:
            raise PreflightError("发布引擎需要 ledger_path")
        self.ledger_path = ledger_path
        self.profile_path = profile_path
        self.stop_before_submit = stop_before_submit
        self.upload_copy_dir = upload_copy_dir
        self.clock = AttemptClock()
        self.client = client_factory(session, audit, self.clock, profile["timing"])
        self.resume_state = resume_state or {}
        if self.resume_state:
            saved_at_epoch = float(self.resume_state.get("saved_at_epoch") or time.time())
            wall_downtime = max(0.0, time.time() - saved_at_epoch)
            if self.resume_state.get("reason") == "needs_ai_optimization":
                wall_downtime = 0.0
            self.clock.restore(self.resume_state, wall_downtime_seconds=wall_downtime)
        self.submitted = bool(self.resume_state.get("submitted"))
        self.possible_submit = bool(self.resume_state.get("possible_submit") or self.submitted)
        self.submit_intent_epoch = float(self.resume_state.get("submit_intent_epoch") or 0.0)
        self.confirmed_result = self.resume_state.get("confirmed_result") if isinstance(self.resume_state.get("confirmed_result"), dict) else None
        self.client.submit_request_count = int(self.resume_state.get("submit_request_count") or 0)
        self.client.command_count = int(self.resume_state.get("command_count") or 0)

    def preflight(self, skip_duplicate: bool = False) -> Path:
        self.client.phase = "preflight"
        if not skip_duplicate:
            detect_local_duplicate(self.manifest, self.ledger_path)
        probe = probe_video(Path(self.manifest["video"]))
        staged = stage_video(self.manifest, self.upload_copy_dir)
        self.audit.emit(
            "preflight_complete",
            video=self.manifest["video"],
            staged_video=str(staged),
            sha256=self.manifest["sha256"],
            title=self.manifest["title"],
            title_basis=self.manifest["title_basis"],
            season=self.manifest.get("season"),
            publish_type=self.manifest["publish_type"],
            profile_revision=self.profile.get("profile_revision"),
            profile_sha256=hashlib.sha256(compact_json(self.profile).encode()).hexdigest(),
            probe=probe,
        )
        return staged

    def backend_duplicate_check(self, allow_existing: bool = False) -> list[dict[str, Any]]:
        self.client.phase = "backend_duplicate_check"
        navigation_timeout = int(self.profile["timing"].get("archive_navigation_timeout_seconds", 30))
        self.client.command(
            "navigate",
            {"url": self.profile["archive_url"], "newTab": True, "group_title": "B站视频发布"},
            timeout=navigation_timeout,
        )
        evaluate_timeout = int(self.profile["timing"].get("archive_evaluate_timeout_seconds", 30))
        payload = self.client.evaluate_json(build_archive_script(), timeout=evaluate_timeout)
        if not isinstance(payload, dict) or not payload.get("ok"):
            evidence = payload if isinstance(payload, dict) else {"payload_type": type(payload).__name__}
            if evidence.get("code") == -101:
                raise ExternalBlocker("B站后台登录态失效，查重无法完成", evidence)
            raise PublishError("B站后台查重未完整成功，禁止继续投稿", evidence)
        duplicates = []
        for item in archive_items(payload):
            title = first_present(item, "title", "archive_title") or archive_record(item).get("title")
            if title == self.manifest["title"]:
                duplicates.append(item)
        self.audit.emit("backend_duplicate_check", duplicate_count=len(duplicates), title=self.manifest["title"])
        try:
            self.client.command("close_tab", {})
        except Exception:
            pass
        if duplicates and not allow_existing:
            raise DuplicateError("B站后台已存在同标题目标稿件", {"items": duplicates[:3]})
        return duplicates

    def runtime_state(self, reason: str, optimization_request: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "session": self.session,
            "manifest": self.manifest,
            "manifest_hash": stable_hash(self.manifest),
            "round": self.clock.round_number,
            "phase": self.client.phase,
            "reason": reason,
            "saved_at_epoch": time.time(),
            "task_elapsed_seconds": round(self.clock.task_elapsed(), 3),
            "round_elapsed_seconds": round(self.clock.round_elapsed(), 3),
            "external_latency_seconds": round(self.clock.external_latency_seconds, 3),
            "external_evidence": self.clock.external_evidence,
            "timing_status": self.clock.classify(self.profile["timing"]),
            "markers": self.clock.wall_markers(),
            "command_count": self.client.command_count,
            "submit_request_count": self.client.submit_request_count,
            "possible_submit": self.possible_submit,
            "submitted": self.submitted,
            "submit_intent_epoch": self.submit_intent_epoch or None,
            "confirmed_result": self.confirmed_result,
            "optimization_request": optimization_request,
            "profile": str(self.profile_path),
            "profile_revision": self.profile.get("profile_revision"),
            "profile_sha256": stable_hash(self.profile),
        }

    def persist_runtime_state(self, reason: str, optimization_request: dict[str, Any] | None = None) -> None:
        state = self.runtime_state(reason, optimization_request)
        self.audit.save_state(state)
        self.audit.emit("runtime_state_saved", reason=reason, phase=self.client.phase,
                        possible_submit=self.possible_submit, submitted=self.submitted)

    def require_active_attempt(self, stage: str) -> None:
        if self.timing_checkpoint(stage) != "attempt_failed":
            return
        raise NeedsAIOptimization(
            "本轮超过 5 分钟，已记录失败；AI 必须优化耗时策略后进入新轮次",
            {"issues": [{"field": "timing", "reason": "attempt_exceeded_five_minutes"}],
             "markers": self.clock.wall_markers(), "external_evidence": self.clock.external_evidence},
        )

    def timing_checkpoint(self, stage: str) -> str:
        status = self.clock.classify(self.profile["timing"])
        self.audit.emit(
            "timing_checkpoint",
            stage=stage,
            round=self.clock.round_number,
            status=status,
            elapsed_seconds=round(self.clock.round_elapsed(), 3),
            external_latency_seconds=round(self.clock.external_latency_seconds, 3),
        )
        return status

    def open_upload_round(self) -> dict[str, Any]:
        round_number = self.clock.start_round()
        self.client.phase = "open_upload"
        self.persist_runtime_state("round_started_before_navigation")
        result = self.client.command(
            "navigate",
            {"url": self.profile["upload_url"], "newTab": True},
            timeout=30,
        )
        self.clock.mark("page_opened")
        self.audit.emit("round_started", round=round_number, navigation=result)
        time.sleep(1.2)
        ready_timeout = int(self.profile["timing"].get("ready_timeout_seconds", 15)) + 10
        ready = self.client.evaluate_json(build_ready_script(self.profile, self.manifest, editor=False), timeout=ready_timeout)
        self.audit.emit("ready_check", round=round_number, result=ready)
        if not ready or not ready.get("ok"):
            raise NeedsAIOptimization("投稿页未就绪", ready or {})
        self.persist_runtime_state("upload_page_ready")
        return result

    def _evaluate_after_navigation(self, code: str, timeout: float, *, stage: str) -> Any:
        """Upload often reloads the SPA; a long evaluate across that navigation detaches."""
        attempts = max(1, int(self.profile["timing"].get("post_upload_evaluate_attempts", 3)))
        settle = float(self.profile["timing"].get("post_upload_settle_seconds", 2.5))
        last_error: Exception | None = None
        for attempt in range(1, attempts + 1):
            try:
                return self.client.evaluate_json(code, timeout=timeout)
            except PublishError as exc:
                message = str(exc)
                retryable = "Detached" in message
                if not retryable or attempt >= attempts:
                    raise
                last_error = exc
                self.audit.emit("post_upload_evaluate_retry", stage=stage, attempt=attempt, error=message)
                if settle > 0:
                    time.sleep(settle)
        if last_error:
            raise last_error
        return None

    def upload_and_fill(self, staged: Path) -> dict[str, Any]:
        self.require_active_attempt("before_upload")
        self.client.phase = "upload"
        upload_started = time.monotonic()
        self.client.command("upload", {"selector": self.profile["upload_input"], "files": [str(staged)]}, timeout=120)
        upload_elapsed = time.monotonic() - upload_started
        self.persist_runtime_state("upload_command_returned")
        self.require_active_attempt("before_batch")
        self.client.command("evaluate", {"code": f"""
        (() => {{
            const input = document.querySelector({json.dumps(self.profile["upload_input"])});
            if (input) input.dispatchEvent(new Event("change", {{bubbles: true}}));
        }})()
        """})
        settle = float(self.profile["timing"].get("post_upload_settle_seconds", 2.5))
        if settle > 0:
            time.sleep(settle)
        self.wait_for_upload_transfer()
        self.client.phase = "batch_fill"
        batch_timeout = int(self.profile["timing"].get("batch_evaluate_timeout_seconds", 45))
        batch = self._evaluate_after_navigation(
            build_batch_script(self.profile, self.manifest),
            timeout=batch_timeout,
            stage="batch_fill",
        )
        batch_elapsed_ms = float((batch or {}).get("batchElapsedMs") or 0)
        editor_wait_ms = float((batch or {}).get("editorWaitMs") or batch_elapsed_ms)
        marker_back_seconds = max(0.0, batch_elapsed_ms - editor_wait_ms) / 1000
        self.clock.markers["editor_ready"] = self.clock.now() - marker_back_seconds
        self.audit.emit(
            "editor_ready", editor_wait_ms=round(editor_wait_ms, 3),
            upload_elapsed_seconds=round(upload_elapsed, 3), combined_with_batch=True,
        )
        self.clock.mark("batch_finished")
        self.audit.emit("batch_finished", result=batch)
        if not batch:
            raise NeedsAIOptimization("批处理没有返回结果")
        if not batch.get("ok"):
            raise NeedsAIOptimization(
                "批处理未完整成功；本轮立即止损，禁止带着已知失败进入总检或逐项修补",
                {"issues": batch.get("failures") or [], "batch": batch},
            )
        self.persist_runtime_state("batch_finished")
        return batch

    def read_upload_progress(self) -> dict[str, Any]:
        result = self.client.evaluate_json(build_upload_progress_script(), timeout=8)
        return result if isinstance(result, dict) else {}

    def wait_for_upload_transfer(self) -> dict[str, Any]:
        """File input success is not Bilibili transfer. 0.0MB/0.0MB pending never grows covers."""
        start_timeout = float(self.profile["timing"].get("upload_progress_timeout_seconds", 45))
        complete_timeout = float(self.profile["timing"].get("upload_complete_timeout_seconds", 180))
        started_at = time.monotonic()
        last: dict[str, Any] = {}
        start_deadline = started_at + start_timeout
        while True:
            last = self.read_upload_progress()
            if last.get("started") or last.get("complete"):
                break
            if time.monotonic() >= start_deadline:
                raise ExternalBlocker(
                    "B站上传停在 0.0MB/0.0MB，扩展可能无法把本地文件交给页面上传器",
                    last,
                )
            time.sleep(1)
        self.audit.emit("upload_bytes_started", progress=last)
        complete_deadline = time.monotonic() + complete_timeout
        while True:
            last = self.read_upload_progress()
            if last.get("complete"):
                elapsed = time.monotonic() - started_at
                self.clock.add_external_evidence("upload_transfer", elapsed, phase="upload", percent=last.get("percent"))
                self.audit.emit("upload_transfer_complete", progress=last, elapsed_seconds=round(elapsed, 3))
                return last
            if time.monotonic() >= complete_deadline:
                raise NeedsAIOptimization("视频已开始上传但未在时限内完成", {"progress": last})
            time.sleep(1)

    def resume_existing_editor(self) -> bool:
        if not self.resume_state:
            return False
        if self.resume_state.get("phase") in {"backend_duplicate_check", "open_upload", "upload"}:
            return False
        self.client.phase = "resume_editor"
        try:
            # 续跑必须按固定 BrowserSkill 会话接管既有投稿页，不能要求该页恰好位于
            # Chrome 前台；否则选中既有标签会失败并开启新的上传轮次。
            found = self.client.command(
                "select_existing_tab",
                {"url": self.profile["upload_url"]},
                timeout=15,
            )
        except PublishError as exc:
            self.audit.emit("resume_tab_missing", error=str(exc))
            return False
        found_url = str((found or {}).get("url") or "")
        if not found_url.startswith(self.profile["upload_url"]):
            self.audit.emit(
                "resume_tab_url_mismatch",
                expected=self.profile["upload_url"],
                actual=found_url,
                found=found,
            )
            return False
        try:
            progress = self.read_upload_progress()
        except PublishError as exc:
            self.audit.emit("resume_upload_progress_unreadable", error=str(exc))
            return False
        if progress.get("stuck") and not progress.get("started"):
            self.audit.emit("resume_upload_stuck_zero", progress=progress)
            return False
        if not progress.get("complete"):
            self.audit.emit("resume_upload_incomplete", progress=progress)
            return False
        previous_failed = (
            self.resume_state.get("timing_status") == "attempt_failed"
            or optimization_fields(self.resume_state) == ["timing"]
            or self.clock.classify(self.profile["timing"]) == "attempt_failed"
        )
        if previous_failed:
            self.audit.emit(
                "attempt_failed_before_resume",
                failed_round=self.clock.round_number,
                elapsed_seconds=round(self.clock.round_elapsed(), 3),
            )
            self.clock.start_round()
            self.clock.mark("page_opened")
        editor_timeout = float(self.profile["timing"].get("editor_timeout_seconds", 90)) + 5
        editor = self.client.evaluate_json(build_ready_script(self.profile, self.manifest, editor=True), timeout=editor_timeout)
        self.audit.emit("resume_editor_check", found=found, result=editor)
        return bool(editor and editor.get("ok"))

    def reconcile_after_possible_submit(self) -> dict[str, Any]:
        self.client.phase = "read_only_reconciliation"
        duplicates = self.backend_duplicate_check(allow_existing=True)
        if not duplicates:
            raise NeedsAIOptimization(
                "上一轮可能已经提交，但后台暂未出现唯一稿件；只允许继续只读对账",
                {"submitted": self.submitted, "submit_request_count": self.client.submit_request_count},
            )
        if len(duplicates) != 1:
            raise NeedsAIOptimization(
                "后台存在多条同标题稿件，不能猜测本次目标；只允许继续只读对账",
                {"duplicate_count": len(duplicates), "items": duplicates[:3]},
            )
        item = duplicates[0]
        timestamp = archive_timestamp(item)
        if timestamp is None and not self.client.submit_request_count:
            raise NeedsAIOptimization(
                "后台唯一同标题稿件缺少时间戳，也没有投稿请求证据；不能猜测为本次成功",
                {"submit_intent_epoch": self.submit_intent_epoch, "item_keys": sorted(item)},
            )
        if timestamp and self.submit_intent_epoch and timestamp < self.submit_intent_epoch - 300:
            raise NeedsAIOptimization(
                "唯一同标题稿件早于本次提交意图，不能当作本次成功",
                {"archive_timestamp": timestamp, "submit_intent_epoch": self.submit_intent_epoch},
            )
        archive = archive_record(item)
        aid = first_present(archive, "aid", "id")
        bvid = first_present(archive, "bvid")
        result = {
            "ok": bool(aid and bvid),
            "source": "backend_resume_reconciliation",
            "aid": str(aid) if aid else None,
            "bvid": str(bvid) if bvid else None,
            "item": item,
            "submit_request_count": self.client.submit_request_count,
            "run_id": self.run_id,
            "session": self.session,
            "audit_log": str(self.audit.path),
        }
        if not result["ok"]:
            raise NeedsAIOptimization("后台已有同标题稿件但 aid/bvid 尚未同步；继续只读对账", result)
        self.audit.emit("publish_reconciled_without_resubmit", result=result, archive_timestamp=timestamp)
        return self.finalize_success(result)

    def total_check_with_recovery(self) -> dict[str, Any]:
        self.require_active_attempt("before_total_check")
        self.client.phase = "total_check"
        check = self.client.evaluate_json(build_check_script(self.profile, self.manifest), timeout=20)
        self.clock.mark("total_check_finished")
        self.audit.emit("total_check", result=check)
        if check and check.get("ok"):
            self.persist_runtime_state("total_check_passed")
            return check

        issues = (check or {}).get("issues") or [{"field": "unknown", "reason": "empty_check"}]
        fields = [issue.get("field", "unknown") for issue in issues]
        known = set(self.profile.get("recovery_order") or []) | {"description", "ai_declaration", "tags", "season", "partition", "cover", "title", "part_title", "charge"}
        if any(field not in known for field in fields):
            diagnostic = self.client.evaluate_json(build_diagnostic_script(self.profile, self.manifest, issues), timeout=20)
            raise NeedsAIOptimization("出现未知总检失败字段", {"issues": issues, "diagnostic": diagnostic})

        self.audit.emit("optimization_started", source="total_check", fields=fields, evidence=issues)
        self.require_active_attempt("before_targeted_repair")
        self.client.phase = "targeted_repair"
        repair = self.client.evaluate_json(build_repair_script(self.profile, self.manifest, fields), timeout=45)
        self.audit.emit("optimization_applied", fields=fields, result=repair)
        recheck = self.client.evaluate_json(build_check_script(self.profile, self.manifest), timeout=20)
        self.audit.emit("optimization_verified", fields=fields, result=recheck)
        if recheck and recheck.get("ok"):
            return recheck
        diagnostic = self.client.evaluate_json(build_diagnostic_script(self.profile, self.manifest, (recheck or {}).get("issues") or issues), timeout=20)
        raise NeedsAIOptimization(
            "已知恢复策略验证失败，需要 AI 更新页面策略后续跑",
            {"issues": (recheck or {}).get("issues") or issues, "diagnostic": diagnostic},
        )

    def submit_once(self, check: dict[str, Any] | None = None) -> dict[str, Any]:
        if self.possible_submit or self.submitted or self.client.submit_request_count:
            raise PublishError("同一任务禁止重复提交")
        self.require_active_attempt("before_submit")
        self.client.phase = "submit"
        self.client.command("network", {"cmd": "start", "filter": "/x/vu/web/add/v3"}, timeout=10)
        self.require_active_attempt("after_network_start_before_submit")
        submit_selector = (check or {}).get("submitSelector")
        if submit_selector not in self.profile["selectors"]["submit"]:
            raise PublishError("总检没有返回可复用的提交选择器，禁止点击", {"submit_selector": submit_selector})
        self.possible_submit = True
        self.submit_intent_epoch = time.time()
        self.persist_runtime_state("submit_intent_write_ahead")
        self.clock.mark("submit_click_command")
        self.client.command("click", {"selector": submit_selector}, timeout=15)
        self.submitted = True
        self.persist_runtime_state("submit_click_returned")
        self.clock.mark("submit_clicked")
        self.audit.emit("submit_clicked", selector=submit_selector)
        focus_window = float(self.profile["timing"].get("post_submit_focus_window_seconds", 12))
        self.audit.emit(
            "foreground_focus_required",
            upload_url=self.profile["upload_url"],
            window_seconds=focus_window,
            instruction="主代理必须用 Computer Use 将 Chrome 中本次投稿标签页带到前台；禁止再次点击投稿",
        )
        time.sleep(focus_window)
        requests = self.client.command("network", {"cmd": "list", "filter": "/x/vu/web/add/v3"}, timeout=15)
        matched = [item for item in requests.get("requests", []) if "/x/vu/web/add/v3" in item.get("url", "")]
        self.client.submit_request_count += len(matched)
        if matched:
            self.persist_runtime_state("submit_request_observed")
        if len(matched) > 1:
            raise PublishError("检测到多个投稿请求", {"count": len(matched)})
        if matched:
            request_id = matched[-1].get("requestId") or matched[-1].get("id")
            if not request_id:
                return {"ok": False, "source": "network", "requests": matched, "reason": "request_id_missing"}
            detail = self.client.command("network", {"cmd": "detail", "requestId": request_id}, timeout=15)
            response = first_present(detail, "responseBody", "response", "body")
            if isinstance(response, str):
                try:
                    response = json.loads(response)
                except json.JSONDecodeError:
                    pass
            payload = response if isinstance(response, dict) else detail
            code = first_present(payload, "code")
            data = payload.get("data") if isinstance(payload, dict) else None
            aid = first_present(payload, "aid") or (data or {}).get("aid")
            bvid = first_present(payload, "bvid") or (data or {}).get("bvid")
            if code == 0 and aid and bvid:
                self.clock.mark("code_zero")
                result = {"ok": True, "source": "add_v3", "aid": str(aid), "bvid": str(bvid), "response": payload}
                self.confirmed_result = result
                self.persist_runtime_state("submission_code_zero")
                return result
        return {"ok": False, "source": "network", "requests": matched}

    def ledger_record(self, result: dict[str, Any]) -> dict[str, Any]:
        if result.get("source") == "add_v3":
            status = "投稿接口 code=0；异步字段待同步"
        else:
            status = "后台唯一目标稿件只读对账确认；未取得投稿接口响应；异步字段待同步"
        return {
            "published_at": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S"),
            "series": self.manifest["series"], "work_label": self.manifest["work_label"],
            "source_file": self.manifest["video"], "sha256": self.manifest["sha256"],
            "title": self.manifest["title"], "aid": result.get("aid"), "bvid": result.get("bvid"),
            "cid": "待同步", "status": status,
        }

    def finalize_success(self, result: dict[str, Any]) -> dict[str, Any]:
        record = self.ledger_record(result)
        ledger = append_video_ledger(record, self.ledger_path)
        result.update({"ledger_record": record, "ledger_write": ledger})
        self.audit.emit("publish_accepted", result=result)
        self.audit.save_result(result)
        try:
            staged = staged_path(self.manifest, self.upload_copy_dir)
            staged.unlink(missing_ok=True)
            self.audit.emit("staged_file_removed", path=str(staged))
        except OSError as exc:
            self.audit.emit(
                "staged_file_remove_failed",
                path=str(staged_path(self.manifest, self.upload_copy_dir)),
                error=str(exc),
            )
        try:
            self.client.phase = "cleanup"
            self.client.command("stop_session", {}, timeout=10)
            self.audit.emit("session_closed")
        except PublishError as exc:
            self.audit.emit("session_close_failed", error=str(exc))
        return result

    def stop_before_submit_result(self, check: dict[str, Any]) -> dict[str, Any]:
        """保存真实页面演练的终点证据；此分支绝不产生投稿意图或台账记录。"""
        if self.possible_submit or self.submitted or self.client.submit_request_count:
            raise PublishError(
                "投稿前演练出现已有投稿意图或请求，禁止将其当作未投稿结果",
                {
                    "possible_submit": self.possible_submit,
                    "submitted": self.submitted,
                    "submit_request_count": self.client.submit_request_count,
                },
            )
        self.client.phase = "simulation_stopped_before_submit"
        self.clock.mark("simulation_stopped_before_submit")
        self.persist_runtime_state("simulation_stopped_before_submit")
        result = {
            "ok": True,
            "simulation": True,
            "stopped_before_submit": True,
            "run_id": self.run_id,
            "session": self.session,
            "timing_status": self.clock.classify(self.profile["timing"]),
            "elapsed_seconds": round(self.clock.round_elapsed(), 3),
            "task_elapsed_seconds": round(self.clock.task_elapsed(), 3),
            "task_timing_status": (
                "over_one_minute"
                if self.clock.task_elapsed() > float(self.profile["timing"]["normal_sla_seconds"])
                else "within_one_minute"
            ),
            "markers": self.clock.wall_markers(),
            "command_count": self.client.command_count,
            "submit_request_count": self.client.submit_request_count,
            "total_check": check,
            "audit_log": str(self.audit.path),
            "session_left_open": True,
            "ledger_write": {"written": False, "reason": "simulation_stopped_before_submit"},
        }
        self.audit.emit("simulation_stopped_before_submit", result=result)
        self.audit.save_result(result)
        return result

    def save_recoverable_state(self, error: NeedsAIOptimization) -> None:
        request = {"message": str(error), "evidence": error.evidence}
        self.persist_runtime_state("needs_ai_optimization", request)
        self.audit.emit("needs_ai_optimization", state=self.runtime_state("needs_ai_optimization", request))

    def run(self) -> dict[str, Any]:
        if self.confirmed_result and self.confirmed_result.get("ok"):
            self.audit.emit("resume_from_persisted_code_zero", result=self.confirmed_result)
            return self.finalize_success(dict(self.confirmed_result))
        staged = self.preflight(skip_duplicate=self.possible_submit)
        self.client.health()
        if self.resume_state and (self.possible_submit or self.submitted or self.client.submit_request_count):
            return self.reconcile_after_possible_submit()
        # 同一锁定草稿在上一轮已经完成后台查重后，先恢复编辑页，避免查重页抢走
        # BrowserSkill 的当前 Agent Window 标签，造成无谓重传或在错误页面空等。若查重本身失败，
        # state.phase 会保留为 backend_duplicate_check，下面仍会先重新查重。
        prior_duplicate_check = bool(self.resume_state) and self.resume_state.get("phase") not in {
            "preflight", "backend_duplicate_check",
        }
        resumed = self.resume_existing_editor() if prior_duplicate_check else False
        if resumed:
            self.audit.emit("resume_uses_prior_duplicate_check", prior_phase=self.resume_state.get("phase"))
        else:
            self.backend_duplicate_check()
            resumed = self.resume_existing_editor()
        if resumed:
            if self.resume_state.get("reason") == "needs_ai_optimization":
                self.clock.start_round()
            self.audit.emit("resume_same_draft", round=self.clock.round_number)
            fields = optimization_fields(self.resume_state)
            editor_missing = any(
                issue.get("reason") == "editor_node_missing"
                for issue in ((self.resume_state.get("optimization_request") or {}).get("evidence") or {}).get("issues") or []
                if isinstance(issue, dict)
            )
            if fields and fields != ["timing"] and not editor_missing:
                batch = self.client.evaluate_json(build_repair_script(self.profile, self.manifest, fields), timeout=45)
                self.audit.emit("resume_targeted_repair", fields=fields, result=batch)
            elif fields == ["timing"]:
                batch = {"ok": True, "actions": [], "reason": "strategy_updated_after_timing_failure"}
                self.audit.emit("resume_after_timing_optimization", result=batch)
            else:
                self.client.phase = "batch_fill"
                batch_timeout = int(self.profile["timing"].get("batch_evaluate_timeout_seconds", 45))
                batch = self._evaluate_after_navigation(
                    build_batch_script(self.profile, self.manifest),
                    timeout=batch_timeout,
                    stage="resume_batch_fill",
                )
                self.audit.emit("batch_finished", result=batch, resumed=True)
            self.clock.mark("batch_finished")
        else:
            self.open_upload_round()
            batch = self.upload_and_fill(staged)
        if not batch or not batch.get("ok"):
            raise NeedsAIOptimization(
                "批处理未完整成功；本轮立即止损，禁止继续总检或逐字段修补",
                {"issues": (batch or {}).get("failures") or [], "batch": batch},
            )
        self.require_active_attempt("batch_complete")
        check = self.total_check_with_recovery()
        self.require_active_attempt("total_check_complete")
        if self.stop_before_submit:
            return self.stop_before_submit_result(check)
        result = self.submit_once(check)
        timing_status = self.clock.classify(self.profile["timing"])
        result.update(
            {
                "run_id": self.run_id,
                "session": self.session,
                "timing_status": timing_status,
                "elapsed_seconds": round(self.clock.round_elapsed(), 3),
                "task_elapsed_seconds": round(self.clock.task_elapsed(), 3),
                "task_timing_status": (
                    "over_one_minute"
                    if self.clock.task_elapsed() > float(self.profile["timing"]["normal_sla_seconds"])
                    else "within_one_minute"
                ),
                "markers": self.clock.wall_markers(),
                "command_count": self.client.command_count,
                "submit_request_count": self.client.submit_request_count,
                "total_check": check,
                "audit_log": str(self.audit.path),
            }
        )
        if not result.get("ok"):
            raise NeedsAIOptimization("投稿请求结果未确认；只能只读查重，禁止补点", result)
        return self.finalize_success(result)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI 内部 B站视频发布引擎")
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--dry-run", action="store_true", help="只做本地输入、台账和脚本生成验证")
    parser.add_argument(
        "--stop-before-submit",
        action="store_true",
        help="真实页面演练至唯一总检通过后停止；绝不点击立即投稿或写发布台账",
    )
    parser.add_argument("--run-id", help="AI 续跑时复用 run id；用户无需接触")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        workspace = load_workspace(args.config)
    except ValueError as exc:
        raise PreflightError(str(exc), {"config": str(args.config)}) from exc
    profile = load_json(args.profile.resolve())
    validate_profile(profile)
    raw_manifest = load_json(args.manifest.resolve())
    manifest = validate_manifest(
        raw_manifest, profile, require_authorization=not args.dry_run, verify_video=False,
    )

    if args.dry_run:
        manifest = validate_manifest(raw_manifest, profile, require_authorization=False, verify_video=True)
        detect_local_duplicate(manifest, workspace.ledger_path)
        probe = probe_video(Path(manifest["video"]))
        generated = {
            "ready": build_ready_script(profile, manifest),
            "batch": build_batch_script(profile, manifest),
            "check": build_check_script(profile, manifest),
        }
        result = {
            "ok": True,
            "dry_run": True,
            "manifest": manifest,
            "probe": probe,
            "generated_script_bytes": {key: len(value.encode()) for key, value in generated.items()},
        }
        print(compact_json(result))
        return 0

    manifest_hash = stable_hash(manifest)
    publication_identity_hash = stable_hash({"platform": "bilibili", "sha256": manifest["sha256"]})
    log_root = workspace.log_root
    proposed_run_id = args.run_id or f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    run_id, adopted_run = claim_manifest_run(
        publication_identity_hash, proposed_run_id, log_root, explicit_run_id=bool(args.run_id),
    )
    audit = AuditLog(log_root, run_id)
    resume_state: dict[str, Any] | None = None
    verification_input = raw_manifest
    if args.run_id or adopted_run:
        if not audit.state_path.exists():
            raise PreflightError("指定了 run-id，但没有可续跑状态；禁止把它当成新任务启动", {"run_id": run_id})
        resume_state = load_json(audit.state_path)
        previous_manifest = resume_state.get("manifest") or {}
        previous_manifest_hash = resume_state.get("manifest_hash") or stable_hash(previous_manifest)
        if adopted_run and not args.run_id:
            if previous_manifest_hash != stable_hash(manifest):
                audit.emit(
                    "auto_adopt_uses_previous_locked_manifest",
                    incoming_manifest_hash=stable_hash(manifest), previous_manifest_hash=previous_manifest_hash,
                )
            manifest = previous_manifest
            manifest_hash = previous_manifest_hash
            verification_input = previous_manifest
        elif previous_manifest_hash != stable_hash(manifest):
            raise PreflightError("续跑完整输入与上一轮锁定输入不一致", {"run_id": run_id})
        possible_submit = bool(resume_state.get("possible_submit") or resume_state.get("submitted") or resume_state.get("submit_request_count"))
        previous_profile_hash = resume_state.get("profile_sha256")
        current_profile_hash = hashlib.sha256(compact_json(profile).encode()).hexdigest()
        previous_revision = int(resume_state.get("profile_revision") or 0)
        current_revision = int(profile.get("profile_revision") or 0)
        requires_profile_upgrade = resume_state.get("reason") == "needs_ai_optimization"
        if not possible_submit and requires_profile_upgrade and (
            previous_profile_hash == current_profile_hash or current_revision <= previous_revision
        ):
            raise PreflightError(
                "异常续跑前页面策略没有有效升级；禁止原样重复失败动作",
                {
                    "run_id": run_id,
                    "previous_revision": previous_revision,
                    "current_revision": current_revision,
                },
            )
        session = str(resume_state.get("session") or "")
        if not session:
            raise PreflightError("续跑状态缺少 BrowserSkill session；只能先只读核对，禁止重新投稿", {"run_id": run_id})
        audit.emit("resume_requested", round=resume_state.get("round"), session=session, adopted_run=adopted_run)
    else:
        session = BrowserSkillClient.start_session(f"bilibili-publish-{run_id}")
    if resume_state and isinstance(resume_state.get("confirmed_result"), dict):
        manifest = resume_state.get("manifest") or manifest
    else:
        try:
            verified_manifest = validate_manifest(
                verification_input, profile, require_authorization=True, verify_video=True,
            )
        except PreflightError:
            release_manifest_run(publication_identity_hash, run_id, log_root)
            raise
        if stable_hash(verified_manifest) != manifest_hash:
            release_manifest_run(publication_identity_hash, run_id, log_root)
            raise PreflightError("视频核验后的完整输入哈希发生变化，禁止继续")
        manifest = verified_manifest
    publisher = BilibiliPublisher(
        manifest, profile, audit, run_id, session, resume_state=resume_state,
        ledger_path=workspace.ledger_path,
        profile_path=args.profile.resolve(),
        stop_before_submit=args.stop_before_submit,
        upload_copy_dir=workspace.upload_copy_dir,
    )
    try:
        result = publisher.run()
    except NeedsAIOptimization as exc:
        publisher.save_recoverable_state(exc)
        payload = {
            "ok": False,
            "code": exc.code,
            "message": str(exc),
            "evidence": exc.evidence,
            "run_id": run_id,
            "session": session,
            "state": str(audit.state_path),
            "instruction_for_ai": "基于失败字段最小证据更新 profile，运行测试后用同一 run-id 续跑；先只读查重，禁止重复投稿。",
        }
        print(compact_json(payload))
        return exc.exit_code
    except (PreflightError, DuplicateError, ExternalBlocker) as exc:
        if not publisher.possible_submit:
            if isinstance(exc, (PreflightError, DuplicateError)):
                release_manifest_run(publication_identity_hash, run_id, log_root)
            raise
        adaptive_error = NeedsAIOptimization(
            "提交意图已写入后发生异常；只能只读对账，禁止再次投稿",
            {"issues": [{"field": "submit_state", "reason": "possible_submit"}],
             "source_code": exc.code, "source_message": str(exc), "source_evidence": exc.evidence},
        )
        publisher.save_recoverable_state(adaptive_error)
        print(compact_json({
            "ok": False, "code": adaptive_error.code, "message": str(adaptive_error),
            "evidence": adaptive_error.evidence, "run_id": run_id, "session": session,
            "state": str(audit.state_path),
            "instruction_for_ai": "使用同一 run-id 只读对账；禁止点击提交、重新上传或创建新任务。",
        }))
        return adaptive_error.exit_code
    except PublishError as exc:
        adaptive_error = NeedsAIOptimization(
            "自动化步骤出现未覆盖异常，需要 AI 基于证据更新策略后续跑",
            {"source_code": exc.code, "source_message": str(exc), "source_evidence": exc.evidence},
        )
        publisher.save_recoverable_state(adaptive_error)
        payload = {
            "ok": False,
            "code": adaptive_error.code,
            "message": str(adaptive_error),
            "evidence": adaptive_error.evidence,
            "run_id": run_id,
            "session": session,
            "state": str(audit.state_path),
            "instruction_for_ai": "读取失败证据，仅修改对应页面策略并跑回归；使用同一 run-id 续跑，不得重复投稿。",
        }
        print(compact_json(payload))
        return adaptive_error.exit_code
    release_manifest_run(publication_identity_hash, run_id, log_root)
    print(compact_json(result))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PublishError as exc:
        print(
            compact_json({"ok": False, "code": exc.code, "message": str(exc), "evidence": exc.evidence}),
            file=sys.stderr,
        )
        raise SystemExit(exc.exit_code)
