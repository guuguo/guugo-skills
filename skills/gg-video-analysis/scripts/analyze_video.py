#!/usr/bin/env python3
"""准备有真实时间戳的抽帧证据包，并按独立阶段执行本地 ASR。"""
import argparse
import hashlib
import importlib.util
import json
import math
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def read(p):
    return json.loads(p.read_text(encoding='utf-8'))


def save(p, value):
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def preflight_module(config):
    path = Path(config.get('resource_preflight', '~/.agents/skills/video-subtitle-workflow/scripts/resource_preflight.py')).expanduser()
    if not path.is_file():
        raise ValueError(f'缺资源预检依赖: {path}')
    spec = importlib.util.spec_from_file_location('video_resource_preflight', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def preflight(module, video, out, fps, stage):
    report = module.assess(video, out, fps, 1)
    save(out / f'preflight-{stage}.json', report)
    if report['status'] == 'block':
        raise ValueError(f'{stage} 资源预检阻止启动: {report["blockers"]}')


def run(command, log, module):
    # 输出落磁盘而非长期积在内存，定期只检查自己启动的精确进程。
    with log.open('w', encoding='utf-8') as f:
        child = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=f)
        try:
            while child.poll() is None:
                try:
                    child.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    memory = module.memory_snapshot()
                    rss = subprocess.run(['ps', '-o', 'rss=', '-p', str(child.pid)], capture_output=True, text=True).stdout.strip()
                    print(json.dumps({'pid': child.pid, 'rss_kib': rss, 'free_percent': memory['free_percent']}), flush=True)
                    if memory['free_percent'] is not None and memory['free_percent'] < 10:
                        raise ValueError(f'内存低于 10%，已中止本次进程 {child.pid}；不自动重试')
            if child.returncode:
                raise ValueError(f'命令失败 ({child.returncode})，见 {log}')
        finally:
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()


def check_output(out):
    if not out.is_absolute():
        raise ValueError('输出目录必须为绝对路径')
    if sys.platform == 'darwin' and len(out.parts) > 2 and out.parts[1] == 'Volumes':
        if not Path(*out.parts[:3]).is_mount():
            raise ValueError('输出所在外置卷未挂载')
    if out.exists() and any(out.iterdir()):
        raise ValueError(f'输出目录非空，不覆盖已有证据: {out}')
    out.mkdir(parents=True, exist_ok=True)


def sheets(out, rows, width):
    from PIL import Image, ImageDraw
    pages = []
    for page_no, offset in enumerate(range(0, len(rows), 16), 1):
        group = rows[offset:offset + 16]
        with Image.open(out / group[0]['path']) as first:
            height = max(1, round(first.height * width / first.width))
        label_h, head_h = 25, 32
        canvas = Image.new('RGB', (width * 4, head_h + (height + label_h) * 4), '#202020')
        draw = ImageDraw.Draw(canvas)
        draw.text((8, 8), f'Page {page_no} / {math.ceil(len(rows)/16)} | frame IDs refer to frames.json', fill='white')
        relative = f'sheets/page-{page_no:03d}.jpg'
        for i, row in enumerate(group):
            x, y = (i % 4) * width, head_h + (i // 4) * (height + label_h)
            with Image.open(out / row['path']) as frame:
                frame.thumbnail((width, height))
                canvas.paste(frame, (x, y))
            seconds = row['time']
            stamp = f'{int(seconds//60):02d}:{seconds%60:06.3f}'
            draw.text((x + 5, y + height + 5), f'{row["id"]} | {stamp}', fill='white')
            row['sheet'] = relative
        canvas.save(out / relative, quality=92)
        canvas.close()
        pages.append(relative)
    return pages


def prepare(a, config, module):
    video = a.video.expanduser().resolve(strict=True)
    info = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(video)], text=True))
    stream = next(s for s in info['streams'] if s['codec_type'] == 'video')
    duration = float(stream.get('duration') or info['format']['duration'])
    video_start = float(stream.get('start_time') or 0)
    interval = a.interval if a.interval is not None else config.get('interval', 2.0)
    end = a.end if a.end is not None else duration
    if not all(math.isfinite(v) for v in (interval, a.start, end, duration)) or interval <= 0 or not 0 <= a.start < end <= duration:
        raise ValueError('采样间隔或范围无效，须 0 <= start < end <= duration 且 interval > 0')
    width = config.get('thumbnail_width', 320)
    if not isinstance(width, int) or not 160 <= width <= 1280:
        raise ValueError('thumbnail_width 必须为 160–1280 的整数')
    if a.output:
        out = a.output.expanduser()
    else:
        root = Path(config['analysis_root']).expanduser()
        out = root / f'{video.stem}-{datetime.now():%Y%m%d-%H%M%S-%f}'
    check_output(out)
    out = out.resolve()
    save(out / 'ffprobe.json', info)
    manifest = {'schema_version': 1, 'source': str(video), 'sha256': digest(video), 'duration': duration,
                'video_start_time': video_start, 'parameters': {'start': a.start, 'end': end, 'interval': interval},
                'frames': 'frames.json', 'sheets': [], 'audio': None, 'stages': {'probe': 'complete', 'frames': 'pending', 'asr': 'pending', 'observation': 'pending'}}
    save(out / 'manifest.json', manifest)
    audio = next((s for s in info['streams'] if s['codec_type'] == 'audio'), None)
    if audio:
        preflight(module, video, out, 1 / interval, 'audio')
        run(['ffmpeg', '-nostdin', '-v', 'error', '-i', str(video), '-map', '0:a:0', '-vn', '-ac', '1', '-ar', '16000', '-c:a', 'pcm_s16le', str(out / 'audio.wav')], out / 'audio.log', module)
        manifest['audio'] = {'path': 'audio.wav', 'time_offset': float(audio.get('start_time') or 0) - video_start,
                             'coverage': 'full_audio_stream'}
        manifest['stages']['audio'] = 'complete'
    else:
        manifest['stages']['audio'] = 'absent'
        manifest['stages']['asr'] = 'not_applicable'
    save(out / 'manifest.json', manifest)
    preflight(module, video, out, 1 / interval, 'frames')
    (out / 'frames').mkdir()
    (out / 'sheets').mkdir()
    selection = f'between(t,{a.start},{end})*(isnan(prev_selected_t)+gte(t-prev_selected_t+0.0000001,{interval}))'
    vf = f"setpts=PTS-STARTPTS,select='{selection}',showinfo"
    log = out / 'frames.log'
    run(['ffmpeg', '-nostdin', '-hide_banner', '-i', str(video), '-map', '0:v:0', '-an', '-vf', vf,
         '-fps_mode', 'vfr', '-q:v', '2', str(out / 'frames/frame-%06d.jpg')], log, module)
    timestamps = [float(x) for x in re.findall(r'\bn:\s*\d+.*?\bpts_time:([\d.eE+\-]+)', log.read_text(encoding='utf-8'))]
    paths = sorted((out / 'frames').glob('*.jpg'))
    if not paths or len(paths) != len(timestamps):
        raise ValueError('抽帧文件与实际时间戳数量不一致，不能发布证据包')
    rows = [{'id': f'f{i:06d}', 'time': t, 'source_pts': t + video_start, 'path': str(p.relative_to(out))}
            for i, (p, t) in enumerate(zip(paths, timestamps), 1)]
    manifest['sheets'] = sheets(out, rows, width)
    save(out / 'frames.json', {'schema_version': 1, 'frames': rows})
    manifest['stages']['frames'] = 'complete'
    save(out / 'manifest.json', manifest)
    print(json.dumps({'bundle': str(out), 'frames': len(rows), 'pages': len(manifest['sheets']), 'stages': manifest['stages']}, ensure_ascii=False))


def asr(a, config, module):
    out = a.bundle.expanduser().resolve(strict=True)
    manifest = read(out / 'manifest.json')
    video = Path(manifest['source'])
    if digest(video) != manifest['sha256']:
        raise ValueError('原媒体哈希改变，不能混用证据版本')
    if not manifest['audio']:
        raise ValueError('该原片无音轨，ASR 不适用')
    if (out / 'asr.json').exists():
        raise ValueError('已有 asr.json，保留原始结果，不覆盖')
    model = Path(config['asr_model']).expanduser()
    if not model.is_absolute() or not model.is_dir() or not (model / 'config.json').is_file():
        raise ValueError('缺少有效本地模型 snapshot；禁止传远端仓库名或静默下载')
    python = Path(config['python']).expanduser()
    if not python.is_file():
        raise ValueError('配置的 ASR Python 不存在')
    language = config.get('language', 'zh')
    preflight(module, video, out, 1 / manifest['parameters']['interval'], 'asr')
    code = '''import json,sys,importlib.metadata
from pathlib import Path
import mlx_whisper
audio,model,language,dst=sys.argv[1:]
result=mlx_whisper.transcribe(audio,path_or_hf_repo=model,language=language,word_timestamps=True,verbose=False)
Path(dst).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
Path(dst).with_name('asr-tool.json').write_text(json.dumps({'mlx_whisper':importlib.metadata.version('mlx-whisper')}),encoding='utf-8')
'''
    run([str(python), '-c', code, str(out / manifest['audio']['path']), str(model), language, str(out / 'asr.json')], out / 'asr.log', module)
    result = read(out / 'asr.json')
    if 'segments' not in result:
        raise ValueError('ASR 输出缺 segments，不能标记成功')
    manifest['asr'] = {'path': 'asr.json', 'model_path': str(model), 'language': language,
                       'tools': read(out / 'asr-tool.json'), 'time_offset': manifest['audio']['time_offset']}
    manifest['stages']['asr'] = 'complete'
    save(out / 'manifest.json', manifest)
    print(json.dumps({'bundle': str(out), 'segments': len(result['segments']), 'stage': 'asr_complete'}, ensure_ascii=False))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config', type=Path, default=Path.home() / '.config/gg-video-analysis/config.json')
    sub = p.add_subparsers(dest='command', required=True)
    s = sub.add_parser('prepare')
    s.add_argument('--video', type=Path, required=True)
    s.add_argument('--output', type=Path)
    s.add_argument('--start', type=float, default=0)
    s.add_argument('--end', type=float)
    s.add_argument('--interval', type=float)
    s = sub.add_parser('asr'); s.add_argument('--bundle', type=Path, required=True)
    a = p.parse_args()
    config = read(a.config.expanduser()) if a.config.expanduser().exists() else {}
    module = preflight_module(config)
    (prepare if a.command == 'prepare' else asr)(a, config, module)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, StopIteration, subprocess.CalledProcessError) as e:
        print(f'视频分析未完成: {e}', file=sys.stderr)
        sys.exit(2)
