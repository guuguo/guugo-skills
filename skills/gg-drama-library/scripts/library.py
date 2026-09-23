#!/usr/bin/env python3
"""配置、初始化、校验、保存快照及导出全量目录；相似素材由 Harness 自主寻找。"""
import argparse
import json
import math
import os
import re
import sys
from datetime import datetime
from pathlib import Path


DEFAULT_CONFIG = Path.home() / '.config/gg-drama-library/config.json'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(temp, path)


def absolute(value):
    p = Path(value).expanduser()
    if not p.is_absolute():
        raise ValueError('必须指定绝对路径')
    if sys.platform == 'darwin' and len(p.parts) > 2 and p.parts[1] == 'Volumes':
        volume = Path(*p.parts[:3])
        if not volume.is_mount():
            raise ValueError(f'外置卷未挂载: {volume}')
    return p.resolve()


def root_from(config):
    if not config.is_file():
        raise ValueError(f'尚未配置素材库: {config}；先运行 configure --root')
    return absolute(read(config)['library_root'])


def resolve_ref(root, value):
    p = Path(value).expanduser()
    return p if p.is_absolute() else root / p


def require(record, fields, where):
    missing = [k for k in fields.split() if k not in record]
    if missing:
        raise ValueError(f'{where}: 缺字段 {missing}')
    if record.get('schema_version') != 1:
        raise ValueError(f'{where}: schema_version 必须为 1')


def check_id(record, path):
    if not isinstance(record.get('id'), str) or not re.fullmatch(r'[A-Za-z0-9_-]+', record['id']):
        raise ValueError(f'{path}: 无效 ID')
    if path.stem != record['id']:
        raise ValueError(f'{path}: 文件名与 ID 不一致')


def timestamp(value):
    t = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if t.tzinfo is None:
        raise ValueError('数据时间必须带时区')
    return t


def check_metrics(data, root):
    require(data, 'id work_id publication_id platform source_url captured_at published_at episode_ids metrics evidence_paths', '数据快照')
    for key in ('id', 'work_id', 'publication_id'):
        if not isinstance(data[key], str) or not re.fullmatch(r'[A-Za-z0-9_-]+', data[key]):
            raise ValueError(f'数据快照 {key} 无效')
    timestamp(data['captured_at'])
    if data['published_at'] is not None:
        if timestamp(data['published_at']) > timestamp(data['captured_at']):
            raise ValueError('发布时间不能晚于采集时间')
    work = root / 'works' / data['work_id']
    if not (work / 'work.json').is_file() or not data['episode_ids']:
        raise ValueError('快照对应作品或集数缺失')
    for ep in data['episode_ids']:
        if not re.fullmatch(r'[A-Za-z0-9_-]+', ep) or not (work / 'episodes' / f'{ep}.json').is_file():
            raise ValueError(f'快照集数不存在: {ep}')
    if not data['platform'] or not data['source_url'] or not data['evidence_paths']:
        raise ValueError('快照须有平台、来源和原始数据证据')
    for ref in data['evidence_paths']:
        if not resolve_ref(root, ref).is_file():
            raise ValueError(f'数据证据不存在: {ref}')
    if set(('views', 'likes', 'comments', 'favorites', 'shares')) - data['metrics'].keys():
        raise ValueError('缺少基础指标；不可得指标须显式记录状态')
    for key, metric in data['metrics'].items():
        if any(k not in metric for k in ('value', 'raw', 'unit', 'status', 'approximate')):
            raise ValueError(f'{key}: 指标字段不全')
        if metric['status'] not in ('available', 'unavailable', 'hidden', 'not_applicable'):
            raise ValueError(f'{key}: 指标状态无效')
        value = metric['value']
        if metric['status'] == 'available':
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0 or metric['raw'] is None:
                raise ValueError(f'{key}: 可用指标必须有非负数值和原始展示')
            if metric['unit'] == 'percent' and value > 100:
                raise ValueError(f'{key}: 百分比超出 0–100')
        elif value is not None or not metric.get('reason'):
            raise ValueError(f'{key}: 不可得指标必须为 null 并写原因')


def performance(root, work_dir, episode_ids):
    latest = {}
    for p in sorted((work_dir / 'metrics').glob('*/*.json')):
        data = read(p)
        key = (data['platform'], data['publication_id'])
        if key not in latest or timestamp(data['captured_at']) > timestamp(latest[key][1]['captured_at']):
            latest[key] = (p, data)
    return [{'snapshot_path': str(p.relative_to(root)), **data}
            for p, data in latest.values() if set(data['episode_ids']) & episode_ids]


def validate(root):
    errors, counts = [], dict(works=0, episodes=0, cases=0, arcs=0)
    for work_path in sorted((root / 'works').glob('*/work.json')):
        try:
            work = read(work_path)
            require(work, 'id title sources coverage', work_path)
            if work['id'] != work_path.parent.name:
                raise ValueError('作品目录与 ID 不一致')
            counts['works'] += 1
            for metric_path in sorted((work_path.parent / 'metrics').glob('*/*.json')):
                data = read(metric_path)
                check_metrics(data, root)
                if data['work_id'] != work['id'] or metric_path.stem != data['id'] or metric_path.parent.name != data['publication_id']:
                    raise ValueError('数据快照目录与对象 ID 不一致')
            episodes = {}
            for ep_path in sorted((work_path.parent / 'episodes').glob('*.json')):
                ep = read(ep_path)
                require(ep, 'id work_id title duration evidence_path events tracks state_ledger', ep_path)
                check_id(ep, ep_path)
                if ep['work_id'] != work['id'] or not math.isfinite(ep['duration']) or ep['duration'] <= 0:
                    raise ValueError(f'{ep_path}: 作品或时长无效')
                manifest_path = resolve_ref(root, ep['evidence_path'])
                manifest = read(manifest_path)
                if abs(manifest['duration'] - ep['duration']) > 0.1:
                    raise ValueError(f'{ep_path}: 时长与证据 manifest 不一致')
                if not Path(manifest['source']).is_file():
                    raise ValueError(f'{ep_path}: 原媒体不存在')
                episodes[ep['id']] = ep
                counts['episodes'] += 1
            coverage = work['coverage']
            expected = set(coverage['expected_episode_ids'])
            collected = set(coverage['collected_episode_ids'])
            missing = set(coverage['missing_episode_ids'])
            if missing != expected - collected or collected != set(episodes):
                raise ValueError('作品覆盖范围与单集记录不一致')
            if coverage['status'] not in ('complete', 'partial'):
                raise ValueError('作品 coverage.status 无效')
            if coverage['status'] == 'complete' and (missing or not expected):
                raise ValueError('完整覆盖声明缺乏依据')
            case_ids = set()
            for path in sorted((work_path.parent / 'cases').glob('*.json')):
                c = read(path)
                require(c, 'id work_id title status core_ranges context_ranges entry_state trigger beats exit_state mechanism prerequisites tags analysis', path)
                check_id(c, path)
                if c['work_id'] != work['id'] or c['status'] not in ('usable', 'partial', 'disputed', 'insufficient'):
                    raise ValueError(f'{path}: 作品或可用状态无效')
                if not c['core_ranges'] or not c['beats']:
                    raise ValueError(f'{path}: 缺核心范围或互动回合')
                for r in c['core_ranges'] + c['context_ranges']:
                    ep = episodes.get(r['episode_id'])
                    if not ep or not (0 <= r['start'] < r['end'] <= ep['duration']):
                        raise ValueError(f'{path}: 时间范围越界或集数不存在')
                    if resolve_ref(root, r['evidence_path']).resolve() != resolve_ref(root, ep['evidence_path']).resolve():
                        raise ValueError(f'{path}: 范围证据与单集媒体版本不一致')
                for beat in c['beats']:
                    if any(k not in beat for k in ('id', 'action', 'response', 'result', 'evidence_refs', 'basis')):
                        raise ValueError(f'{path}: 互动回合字段不全')
                    if c['status'] == 'usable' and not beat['evidence_refs']:
                        raise ValueError(f'{path}: 可用回合缺证据引用')
                    for ref in beat['evidence_refs']:
                        match = re.fullmatch(r'(core|context):(\d+)', ref)
                        if not match or int(match[2]) >= len(c[match[1] + '_ranges']):
                            raise ValueError(f'{path}: 回合引用不存在: {ref}')
                case_ids.add(c['id'])
                counts['cases'] += 1
            for path in sorted((work_path.parent / 'arcs').glob('*.json')):
                arc = read(path)
                require(arc, 'id work_id title coverage entry_state question case_ids turning_points exit_state open_questions', path)
                check_id(arc, path)
                if arc['work_id'] != work['id'] or not arc['case_ids'] or set(arc['case_ids']) - case_ids:
                    raise ValueError(f'{path}: 阶段桥段引用无效')
                counts['arcs'] += 1
        except (OSError, ValueError, KeyError, TypeError) as e:
            errors.append(f'{work_path.parent.name}: {e}')
    # 没有 work.json 的目录不能默默遗漏。
    for p in (root / 'works').iterdir():
        if p.is_dir() and not (p / 'work.json').is_file():
            errors.append(f'{p.name}: 缺 work.json')
    return {'valid': not errors, 'counts': counts, 'errors': errors,
            'scope': '结构、媒体存在、时长和部分引用校验；叙事与证据语义须回查原片'}


def records(root):
    for p in sorted((root / 'works').glob('*/cases/*.json')):
        c = read(p)
        yield {'id': c['id'], 'work_id': c['work_id'], 'title': c['title'],
               'status': c['status'], 'path': str(p.relative_to(root)),
               'tags': c['tags'], 'mechanism': c['mechanism'],
               'trigger': c['trigger'], 'beats': c['beats'],
               'audience': c.get('audience'),
               'performance': performance(root, p.parent.parent, {r['episode_id'] for r in c['core_ranges']}),
               'entry_state': c['entry_state'], 'exit_state': c['exit_state'],
               'prerequisites': c['prerequisites'], 'incompatible': c.get('incompatible', [])}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config', type=Path, default=DEFAULT_CONFIG)
    sub = p.add_subparsers(dest='command', required=True)
    s = sub.add_parser('configure'); s.add_argument('--root', required=True)
    for name in ('init', 'validate', 'index', 'status'):
        sub.add_parser(name)
    s = sub.add_parser('record-metrics'); s.add_argument('--input', type=Path, required=True)
    a = p.parse_args()
    config = a.config.expanduser().resolve()
    if a.command == 'configure':
        root = absolute(a.root)
        data = read(config) if config.exists() else {'schema_version': 1}
        data['library_root'] = str(root)
        write(config, data)
        print(json.dumps({'config': str(config), 'library_root': str(root)}, ensure_ascii=False))
        return 0
    root = root_from(config)
    if a.command == 'init':
        for name in ('works', 'index', 'projects'):
            (root / name).mkdir(parents=True, exist_ok=True)
        if not (root / 'vocabulary.json').exists():
            write(root / 'vocabulary.json', {'schema_version': 1, 'tags': []})
        print(json.dumps({'initialized': str(root)}, ensure_ascii=False))
        return 0
    if not (root / 'works').is_dir():
        raise ValueError('素材库尚未初始化，先运行 init')
    if a.command == 'record-metrics':
        data = read(a.input.expanduser())
        check_metrics(data, root)
        dst = root / 'works' / data['work_id'] / 'metrics' / data['publication_id'] / (data['id'] + '.json')
        dst.parent.mkdir(parents=True, exist_ok=True)
        with dst.open('x', encoding='utf-8') as f:
            f.write(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps({'snapshot': str(dst)}, ensure_ascii=False))
        return 0
    report = validate(root)
    if a.command in ('validate', 'status') or not report['valid']:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report['valid'] else 2
    rows = list(records(root))
    if a.command == 'index':
        dst = root / 'index/cases.jsonl'
        tmp = dst.with_suffix('.tmp')
        tmp.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows), encoding='utf-8')
        os.replace(tmp, dst)
        print(json.dumps({'index': str(dst), 'cases': len(rows)}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, TypeError) as e:
        print(f'素材库操作失败: {e}', file=sys.stderr)
        sys.exit(2)
