# 视频字幕执行参考

## 1. 产物与真源

每个视频的标准目录规范：

```text
成片/
  epXX-视频名-超清字幕版.mp4                      # 最终对外发布的交付成片
  原片归档/                                       # 加字幕前的原始视频归档
    epXX-视频名-无字幕原片.mov
  中间台/                                         # 统一收拢所有工程中间产物
    epXX-字幕工作/                                # 单集专属中间工程目录
      asr.json                                    # ASR 转写与词级时间戳
      字幕修复时间轴.json                          # 结构化事件时间轴
      epXX-视频名-超清字幕版.ass                  # ASS 字幕源文件
      epXX-视频名-超清字幕版.filter.txt           # 滤镜参数记录
      字幕核对记录.md                             # 核对记录作为中间产物保存在工作目录内！
      font-preview/font-comparison.png            # 字号比对候选图
      contact_sheets/contact_sheet.jpg            # 4×4 抽检接触表
      字幕修复-OCR验收.json                       # 验收报告
```

> **核心原则**：`成片/` 根目录必须保持纯净，仅保留最终可交付的成片视频文件；加字幕前的源片统一收纳进 `成片/原片归档/`；所有工程源文件、时间轴、ASS、抽帧接触表以及 `字幕核对记录.md` 一律统一收拢在 `成片/中间台/<单集>-字幕工作/` 目录中。

文字真源优先级：最终脚本或用户确认台词 > 清晰可辨的声音 > ASR 初稿 > OCR 旧字幕。发现脚本与声音明显冲突时先记录并请求确认，不以 OCR 猜剧情。

## 2. 预检

从已安装的技能目录定位工具：

```bash
SUBTITLE_SKILL_ROOT="${VIDEO_SUBTITLE_SKILL_ROOT:-$HOME/.agents/skills/video-subtitle-workflow}"
SUBTITLE_TOOL="$SUBTITLE_SKILL_ROOT/scripts/video_subtitle_repair.py"
VISION_TOOL="$SUBTITLE_SKILL_ROOT/scripts/macos_vision_ocr.swift"
test -f "$SUBTITLE_TOOL"
test -f "$VISION_TOOL"
ffmpeg -version
ffprobe -version
swift --version
```

不要把技能目录写成固定机器路径。工作目录使用具体视频名，避免不同任务互相覆盖。

记录源片参数：

```bash
ffprobe -v error -show_entries \
  stream=index,codec_type,codec_name,width,height,r_frame_rate,pix_fmt,sample_rate,channels,bit_rate:format=duration,size,bit_rate \
  -of json "/absolute/path/input.mp4"
```

## 3. 系统资源预检

字幕流程的重阶段必须串行。首次处理前，以及 ASR、OCR 扫描、渲染和 OCR 验收各阶段开始前，分别运行：

```bash
SUBTITLE_SKILL_ROOT="${VIDEO_SUBTITLE_SKILL_ROOT:-$HOME/.agents/skills/video-subtitle-workflow}"

python3 "$SUBTITLE_SKILL_ROOT/scripts/resource_preflight.py" \
  --video "$VIDEO" \
  --work-dir "$TASK_WORK" \
  --scan-fps 5 \
  --parallel-jobs 1 \
  --json > "$TASK_WORK/资源预检.json"
```

脚本同时判断：

- `memory_pressure` 给出的当前可用内存比例；
- 按 Whisper Medium、Vision OCR、ffmpeg 单阶段估算的峰值与系统保留量；
- 是否已有 ffmpeg、Vision OCR 或 MLX Whisper 重任务运行；
- 视频分辨率、5fps 预计抽帧数及 PNG 临时文件的保守磁盘上界；
- 工作盘剩余空间与系统 CPU 负载。

退出码 `2` 或报告 `status=block` 时禁止启动重阶段。先等待已有任务结束、关闭非必要高内存程序、释放工作盘空间或改用空间更充足的工作目录，再重新预检。不得通过提高并发、降低系统保留量或忽略报告来硬跑。

`status=caution` 时只允许 `parallel-jobs=1`，每完成一个阶段重新预检。`status=ok` 也只表示当前允许启动一个重阶段，不代表后续阶段无需复查。

长视频、4K 视频或预计运行超过 10 分钟时，运行中每隔约 10 秒查看一次当前任务 RSS 和 `memory_pressure -Q`。系统可用内存低于 10% 时，只终止本次字幕任务启动的精确 PID，保留已有产物，不杀无关进程、不自动重试。内存恢复后重新预检，再决定是否分段处理或继续。

资源预检只做保守启动门禁，不承诺精确 RSS。PNG 预算按未压缩 RGBA 上界估算，因此可能高于实际占用；这是为了避免长视频抽帧把磁盘写满。

## 4. 本地 ASR

项目存在 `docs/harness/rules/local-video-asr-fast-path.md` 时，以该文件为准。当前已验证的 macOS 路径如下：

```bash
TASK_WORK="/absolute/path/字幕工作/视频名"
VIDEO="/absolute/path/input.mp4"
AUDIO="$TASK_WORK/audio.wav"
ASR_JSON="$TASK_WORK/asr.json"
mkdir -p "$TASK_WORK"

ffmpeg -y -loglevel error -i "$VIDEO" -vn -ac 1 -ar 16000 -c:a pcm_s16le "$AUDIO"

WHISPER_SNAPSHOT="$(find "$HOME/.cache/huggingface/hub/models--mlx-community--whisper-medium-mlx/snapshots" \
  -mindepth 1 -maxdepth 1 -type d -print -quit)"
test -n "$WHISPER_SNAPSHOT" || { echo "未找到本地 whisper-medium-mlx snapshot" >&2; exit 1; }

/opt/homebrew/bin/python3.12 - "$AUDIO" "$WHISPER_SNAPSHOT" "$ASR_JSON" <<'PY'
import json
import sys
import mlx_whisper

audio, model_dir, output_json = sys.argv[1:]
result = mlx_whisper.transcribe(
    audio,
    path_or_hf_repo=model_dir,
    language="zh",
    word_timestamps=True,
    verbose=False,
)
with open(output_json, "w", encoding="utf-8") as file:
    json.dump(result, file, ensure_ascii=False, indent=2)
print(result.get("text", "").strip())
for segment in result.get("segments", []):
    print(f"{segment['start']:.2f}-{segment['end']:.2f}: {segment['text'].strip()}")
PY
```

必须给 `path_or_hf_repo` 传本地 snapshot 绝对路径。不要先传 Hugging Face 仓库名试错。

## 5. OCR 扫描与时间轴

```bash
python3 "$SUBTITLE_TOOL" scan \
  --video "$VIDEO" \
  --asr-json "$ASR_JSON" \
  --work-dir "$TASK_WORK/scan" \
  --timeline "$TASK_WORK/字幕修复时间轴.json"
```

逐行核对时间轴：

- `source_text` 只保留 OCR 观察值，`text` 写最终要烧录的整行文字。
- 旧硬字幕存在时保留 `mask=true` 和稳定 `bbox`；渲染器仅在该事件实际时间内对紧贴字框区域执行局部 `delogo` 去字/模糊修补。
- 有对白但无硬字幕时必须使用 `mask=false`，且不写虚构 `bbox`。这类事件只烧录新文字，不模糊、不去字、不改变字幕下方背景。整段视频都没有旧字幕时，最终滤镜不得包含 `delogo` 或背景模糊。
- ASR 有声、OCR 无节点的区间会进入 `unresolved_gaps`。补齐事件或确认无需字幕后，将对应缺口标记为 `resolved=true`。
- OCR 字框异常高、覆盖人物或疑似转场误检时，逐帧重取稳定字框；不要用大框兜底。
- 同一句若 ASR 先开始、OCR 稍后出现，应合并为一个整行事件，并让后段字框遮罩从整句开始覆盖。
- 原硬字幕可能早出现或晚消失。默认遮罩在事件前至少 0.25 秒开启、事件后至少 0.10 秒关闭；逐帧证据优先。
- 两个都需遮罩的相邻字幕事件间隔不超过 0.25 秒时，在空档中点切换并让前后遮罩覆盖整个空档，避免旧字闪回。真实停顿不得自动桥接。
- 长句可自然换行，不要为了单行显示而压扁汉字或缩小全片字号。
- 行末删除 `，。,.`，保留有明确语气作用的 `？！` 等标点。

## 6. 字体与字号校准

只要需要烧录文字就必须执行；无旧字幕时工具会在干净原帧上生成候选，不做背景处理：

```bash
python3 "$SUBTITLE_TOOL" font-preview \
  --video "$VIDEO" \
  --timeline "$TASK_WORK/字幕修复时间轴.json" \
  --output-dir "$TASK_WORK/font-preview"
```

先按画面方向计算字号候选：

- 竖屏：画面高度约 `3.9% / 4.5% / 5.0%`；默认优先看 `4.5%`，不得低于 `3.9%`。
- 横屏：画面高度约 `5.0% / 5.8% / 6.5%`；默认优先看 `5.8%`，不得低于 `5.0%`。
- 方形：画面高度约 `4.5% / 5.2% / 5.8%`。

以 720×1280 竖屏为例，默认约 `58px`；以 1280×720 横屏为例，默认约 `42px`。比例只是候选起点，最终以全分辨率画面的观看效果为准。

分别用 `--font-size` 生成中间档和至少一个更大档候选。打开每张全分辨率候选图比较字形、字重、字宽、字号、阴影和位置，再用 `font-comparison.png` 看整体一致性；不能只看被缩到 240px 宽的接触表。不要直接把 OCR 字框高度当 ASS 字号。选定后回写：

```bash
python3 "$SUBTITLE_TOOL" font-preview \
  --video "$VIDEO" \
  --timeline "$TASK_WORK/字幕修复时间轴.json" \
  --output-dir "$TASK_WORK/font-preview" \
  --font-size 58 \
  --select 'Heiti SC'
```

`58` 只是 720×1280 竖屏示例，必须按实际分辨率计算。字体名同样只是示例。汉字纵向缩放保持 100%；只允许按行做轻微横向缩放。长句超过安全宽度时自然换成两行，不能缩小全片字号。完成所有复核后再将顶层 `reviewed` 设为 `true`。

### 低分辨率防糊与清晰度硬门禁
- **严禁使用模糊滤镜**：在低分辨率视频（短边 `<=720`，如 480p）上必须强制 `blur: 0`！低分辨率下汉字笔画像素极少，1px 高斯模糊即可导致复杂汉字（如“糯”、“擦”、“责”）笔画完全粘连发糊。
- **强制清晰描边**：严禁裸字无描边（`outline: 0`），低分辨率下必须设置硬朗黑色细描边（`outline >= 1.2`，1080p 推荐 `2.0`），确保在任何浅色、复杂反光或暗夜背景下字迹刀锋般锐利。
- **480p 低清成片升规策略**：480p 源片全屏播放必然因像素量不足拉伸发虚；必须优先提醒用户在剪辑工程中改选 1080p 重新导出；若用户要求直接出片，则必须通过 Lanczos 高阶算法将视频升规至 1920×1080 标准画布并以 1080p 规格（64px 锐利描边）烧录，严禁直接输出发虚发糊的 480p 成片。

## 7. 从原片一次渲染

```bash
OUTPUT="/absolute/path/修正版/视频名-完整字幕修正版.mp4"

python3 "$SUBTITLE_TOOL" render \
  --video "$VIDEO" \
  --timeline "$TASK_WORK/字幕修复时间轴.json" \
  --output "$OUTPUT"
```

编码器与性能规范：
- **macOS 默认硬件加速**：默认启用 Apple Silicon Media Engine 硬件加速（`-c:v h264_videotoolbox`，`--encoder auto`）。目标码率自适应源片码率上浮 15%（1080p 保底 12M，4K 保底 30M），将压制速度由原本 CPU 软压的 5~8fps 暴增至 60fps+（耗时由 5 分钟缩短至 20~30 秒），且稳妥通过质量门禁。
- **降级与兼容**：非 macOS 环境或显式传 `--encoder libx264` 时平滑回退为 CPU 软编码（默认 `CRF 10`、`preset medium`）。
- **画质门禁**：成品码率默认不得低于源片的 80%。渲染必须从原始视频开始。门禁失败时提升码率或降低 CRF 后仍从原片重渲染；只有用户明确接受小体积版本时才调整质量门禁。

旧字处理规则：仅对真实旧字幕字框最小外扩，使用局部 `delogo` 去字/模糊修补，再在同一位置写整行字幕。不得把新字直接叠在旧字上，也不得模糊整条底部或使用全宽大底条。无旧字幕事件不运行 `delogo` 或模糊，只写新字幕。

## 8. OCR 验收与人工抽检

```bash
python3 "$SUBTITLE_TOOL" verify \
  --video "$OUTPUT" \
  --timeline "$TASK_WORK/字幕修复时间轴.json" \
  --work-dir "$TASK_WORK/verify" \
  --report "$TASK_WORK/字幕修复-OCR验收.json"
```

逐项查看报告：

- `pass`：OCR 与期望文字达到相似度阈值，仍需抽检关键切换点。
- `manual_review`：定点抽帧目视确认，不能直接视为失败或自动重做。
- `unexpected`：检查是否为旧字闪回、画面内非字幕文字、片头标题或 OCR 误识别。

至少抽检每条字幕中段、所有切换前后、所有 `manual_review`、无旧字幕补写行、长句换行和首尾字幕。确认无重影、无旧字闪回、无双行短暂重叠、无对白漏字、无异常遮挡；无旧字幕区的背景必须与原片一致。用全分辨率帧确认字号不显小，再试听音画同步与音频完整性。

### 多帧合并目检

抽帧后的人工或 Agent 视觉检查统一优先使用多帧接触表（contact sheet），适用于原片扫描复核、字框定位和修正版验收；默认每页 `4×4`、最多 16 帧，按时间从左到右、从上到下排列。几百帧应分页查看，不逐张打开，也不挤成一张不可读的大图。

- 每格在画面外标注视频时间戳与帧编号，保留页号、原帧路径及对应字幕事件的映射；末页不足 16 帧时留空，不重复帧充数。时间戳使用真实取帧时间，不猜测文件序号与时间的关系。
- 合并全部本轮待检帧，不因拼图而减少原定抽检覆盖。切换前后帧保持相邻；多视频或原片／修正版必须明确标注来源，避免串片判断。
- 字幕太小看不清时，优先把字幕区域及周边背景裁成可读的多帧接触表；必要时减少为 `3×3` 或 `2×2`。局部裁图只用于查字、字框和闪回，完整画面用于查异常遮挡与构图。
- 先逐页检查接触表，只对疑似错字、重影、闪回、异常遮挡或缩图无法判断的帧及其相邻帧打开原尺寸复核；不能把“缩小后看不清”记为通过。字体与字号候选仍按第 6 节查看全分辨率图，拼图不能替代字号确认或试听音画同步。
- 优先复用项目已有拼图工具；没有时用 Pillow 或 ffmpeg 等本地图像工具合成，不调用生成式生图。每次只加载一页所需帧，完成后释放内存，避免把数百张原帧同时解码。
- 核对记录写明接触表页数、覆盖时间段或帧范围、疑点帧及原尺寸复核结论；未查看的页不得声称已经检查。

## 9. 核对记录

记录以下事实即可：

```markdown
| 视频 | 时间轴 | 对白事件数 | 旧字幕事件数 | 无旧字幕补写数 | 输出 | 验收 |
| --- | --- | ---: | ---: | ---: | --- | --- |
| input.mp4 | `字幕修复时间轴.json` | 8 | 7 | 1 | `完整字幕修正版.mp4` | OCR 反查 + 定点抽帧通过 |
```

另写明源片与成品的文件体积、视频码率、使用的 CRF、是否从原片直出、各重阶段的资源预检状态，以及所有人工抽检项的结论。没有通过的项应如实列出，不得声明完成。

核对记录统一保存为工作目录下的 `<单集>-字幕核对记录.md` 或 `字幕核对记录.md`，作为完整的工程验收中间产物长期留档，严禁直接输出到成片根目录。

## 10. 确定性极速一键流水线 (pipeline)

针对已有明确视觉预设（如《你家的船》）的连续剧集，推荐使用一键流水线命令：

```bash
python3 "$SUBTITLE_TOOL" pipeline \
  --video "/path/to/无字幕原片.mov" \
  [--timeline "/path/to/已确认时间轴.json"] \
  [--script "/path/to/剧本.md"] \
  --preset "你家的船" \
  --output "/path/to/成片/epXX-超清字幕版.mp4"
```

### 多分辨率自适应规则 (Resolution-Adaptive)

| 分辨率规格 | 对应高度 | 字号 (`0.0605×H`) | 描边 (`0.00363×H`) | 阴影 (`0.0020×H`) | 垂直位置 (`0.899×H`) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **标清 (480p/496p)** | 480~496 | 29~30 px | 1.7~1.8 px | 1.0 px | y ≈ 432~446 (底边) |
| **高清 (720p)** | 720 | 44 px | 2.6 px | 1.5 px | y ≈ 647 (底边) |
| **超清 (1080p)** | 1080 | 65 px | 3.9 px | 2.2 px | y ≈ 971 (底边) |

- **严格遵守防糊门禁**：所有分辨率下强制 `blur: 0`；描边保底 >= 1.5px，保证字迹如刀锋般锐利。
- **靶向反查与接触表自动化**：流水线内置定向单帧抽取（仅抽各对白中段）与多帧 4×4 接触表生成，无需对整片抽数百张 PNG，整机压制与质检可在 20~30 秒内一气呵成。
