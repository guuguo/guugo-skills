# 执行参考

## 本机配置

使用 gg 系列的 `~/.config/<skill>/config.json` 方式，配置不随仓库分发。示例字段（值由本机探测与用户指定生成）：

```json
{
  "schema_version": 1,
  "analysis_root": "/指定的分析证据目录",
  "python": "/本机/python3",
  "asr_model": "/已缓存模型/snapshots/实际版本",
  "language": "zh",
  "resource_preflight": "~/.agents/skills/video-subtitle-workflow/scripts/resource_preflight.py",
  "interval": 2.0,
  "thumbnail_width": 320
}
```

`analysis_root` 仅用于独立调用的默认输出。gg-drama-library 传 `--output` 时覆盖它，不创建第二份素材库。未配置根目录但指定 output 可以完成 prepare；缺本地模型时只保留视觉和音轨证据，报告 ASR 未完成。模型绝不传远端仓库名。

## 命令

从技能目录运行，或将脚本写成绝对路径。使用已验证且安装 Pillow 的 Python。

```bash
python3 scripts/analyze_video.py prepare --video /绝对路径/原片.mp4 --output /绝对路径/新证据目录
python3 scripts/analyze_video.py asr --bundle /绝对路径/新证据目录
python3 scripts/analyze_video.py prepare --video /绝对路径/原片.mp4 --output /绝对路径/密集复核 --start 12 --end 16 --interval 0.2
```

默认 prepare 覆盖整个视频；范围模式仍以原片时间为坐标。ffmpeg 的选帧过滤器保留实际解码帧时间，manifest 同时保存 seek 请求范围与实际采样时间；不从图片文件名猜时码。媒体流起点记录于 ffprobe，解码时间归一为播放起点零。

`prepare` 保存 ffprobe、SHA-256、16kHz 单声道 PCM（有音轨时）、JPEG 原尺寸帧、分页接触表、frames.json、manifest.json。无音轨时明确记录 absent，不生成伪转写。ASR 当前转写整条原片音轨，即使视觉包只覆盖局部，也要说明两者范围不同。

初次稀疏采样默认每 2 秒最多取一帧，仅用于定位；短视频关键动作需按事件密集复查。不要把 2 秒设为所有内容的充分精度。

## 资源与复用

资源门禁复用字幕技能的现有脚本，prepare 的音轨提取和抽帧前、asr 前分别运行并保存报告。block 不运行重任务；任务串行。4K、长视频或预计超过十分钟时，约每十秒检查本任务 RSS 和系统内存余量；低于 10% 时终止本次精确 PID，保留已完成文件，不自动重试。

工具执行子进程时执行同样的低内存中止检查。分段分析可减小临时文件，但不得降低预检的内存阈值来绕过 block。预检针对完整视频估算磁盘，局部抽帧可能被保守阻止，报告这一限制。

复用前对比 manifest 中原片哈希、时长、参数、输出是否齐全。ASR 脚本发现已有 asr.json 会拒绝覆盖；需要重新分析时开独立目录，不能假装沿用旧分析。缺失败阶段保留待完成状态，不重跑成功阶段。

## Agent 视听校对

抽帧既用于看动作，也用于直接阅读烧录字幕。逐页查看接触表并对照 ASR；遇到明显不通的词、人名或同音字，主动回到对应画面确认，修正后再用于剧情分析。清晰对白字幕通常比本轮 ASR 猜词更直接，不能有清楚文字却只把错误挂成“待确认”。

原始识别、画面实际写法、校对后采用文本分别保留。根据画面和已确认上下文能确定的错误，由 Agent 直接纠正并给依据；仅凭“这样更顺”不能改写原话。字幕本身可能有错或与声音不同，冲突时分开记 screen_text 与 heard_text（实际听过才填），必要时局部听审；仍不能确定就保留候选与原因。

旁白、角色对白、标题和手机内文字分清。屏幕生成乱码不能自动修成剧情；异常但确实存在的对白/字幕也不能因像提示词就删掉。代词和说话人结合指代对象、画面与称呼判断，不能仅因题材统一替换。原始 ASR 的空段、重复段或尾句截断由 Agent 判读，不能拿截断残词补剧情。

校对必须同时核对位置：句子的声音起止、字幕出现区间、某张帧的可见时刻是不同证据。只有一个抽样帧时记录其实际时刻，不推定字幕精准起止；沿用 ASR 时间时标为未重新对齐，修改文字不生成假的词级时间戳。原片 ffprobe 时长与页面时长不一致时分别记录并检查版本完整性，不拉伸时间轴凑页面数字。

清晰画面由 Agent 直接读；看不清先原尺寸/字幕区域，缺短句再按需补帧，OCR 仅作辅助。调用 OCR 时优先项目现有 `scripts/macos_vision_ocr.swift` 并核对其用法，不新增纠错算法。将校对条目和覆盖范围写入 observations.json，在 review.md 简述改了什么和未决项；下游读取校对文本，不能继续传播已经确认的 ASR 错词。

## 继承来源

本规范参考 `video-subtitle-workflow` 的本地 Whisper、资源门禁、4×4 接触表、疑点原尺寸复核与真实时间戳映射；保留原技能实现和行为，不修改其字幕链路。抽帧工具为通用证据采样补充，不替代项目现有字幕专用工具。
