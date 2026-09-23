# 视频证据包 v1

```text
bundle/
  manifest.json
  ffprobe.json
  preflight-audio.json
  preflight-frames.json
  audio.wav                    有音轨时
  frames.json
  frames/frame-000001.jpg ...
  sheets/page-001.jpg ...
  asr.json                     ASR 实际成功时
  preflight-asr.json            调用 ASR 后
  observations.json            Agent 视听分析后
  review.md                    Agent 视听分析后
```

manifest：`schema_version, source, sha256, duration, video_start_time, parameters, frames, sheets, audio, stages`。阶段状态只反映实际完成；处理失败时已有产物留存，禁止把目录存在当成功。

frames.json：`frames[]`，每条 `id, time, source_pts, path, sheet`。time 是归一化原片播放时间；source_pts 按原视频流 start_time 恢复，异常非零时间轴需结合 ffprobe 复核。选帧时间精度由帧率和 time_base 决定，不能宣称毫秒测量精度。

asr.json：保留 mlx_whisper 原始 `text, segments, words` 等输出。另在 manifest 记录模型路径、语言、实际可获取的工具版本和覆盖范围。ASR 原始时间以提取音轨起点为零；映射原片播放时间须加 manifest.asr.time_offset（音频流起点减视频流起点），不能默认所有音视频流同时开始。原始文本不得直接覆盖为人工校正文；校正项写观察记录，含 raw、corrected、依据。

observations.json：

```json
{
  "schema_version": 1,
  "source_sha256": "与 manifest 一致",
  "reviewed_sheets": [],
  "listened_ranges": [],
  "observations": [],
  "content_profile": {"form": [], "genre": [], "relationship": [], "tone": []},
  "audience": {"status": "unknown", "scope": "", "core": [], "secondary": [], "interests": [], "emotional_needs": [], "age_life_stage": [], "viewing_context": [], "positioning": [], "mismatches": [], "limitations": []},
  "limitations": []
}
```

每条 observation 记录 `id, start, end, actor, action_or_text, basis, frame_ids, asr_segment_ids, uncertainty`。basis 为 observed/explicit/inferred/unknown；actor 可以 unknown。推断必须给出支持和缺口，不能把摘要再引用为原片证据。

有对白的观察须在同一条 action_or_text 内对应记录：采用对白、逐句说话人、可确定的听话对象、画内对白/画外音/旁白或未知、该句发生时镜头中的人物与动作、可见回应。多人轮流说话时分条或逐句标明归属，不能用一个 actor 将整段“父母讨论”都归给同一人；镜头拍到的人不自动等于说话人，说话人也不自动等于叙述者。跨镜头的一句话保留声音持续与画面切换顺序，不强行一语一句一镜。归属由 Agent 根据实际视听证据判断，不能按字幕顺序、角色性别或 ASR 声线编号机械分配。

校对文字通过对应对白与证据定位关联上述观察，再传给下游。已知的字幕可见时刻、观察窗口和画面描述直接复用，不因缺精确起止就全部改成“待核验”；未确定说话人、未观察反应、未听审与确实无对白/无反应分别写明。缺少的是哪一项就标哪一项，不补写猜测，也不丢掉已确认内容。

桥段采集或节奏分析的 observations 按原片呈现顺序保留场景、动作、对白及其先后/重叠、反应停留和转场；无对白的生活过程也属于观察，不把多个场景压成一条结局摘要。在 action_or_text 中写实际声画过程，时间范围与证据对应；原速观看或直接听审后才能确认的停顿、语气、环境声和持续时间，须注明核验方式及范围。稀疏帧只证明采样时刻，不能据此填满中间动作或推定停留秒数；ASR 空段不等于原片静默。未核实节奏写入 uncertainty/limitations，传给下游。

Agent 校对后，可在 observations.json 保存 `text_review`：`scope`、`entries[]`、`limitations[]`。每条记 `asr_segment_ids`、`raw_asr`、`screen_text`、`text`（采用文本）、`evidence`（帧路径/ID 与实际时刻）、`time_basis`、`decision`（corrected/confirmed/unresolved）及原因。没有 ASR 的画面识读 raw_asr 为 null。不确定的采用文本可为 null，不把未见字幕补成原文。旧观察引用原始错词时，保留旧版，再按已核对内容修正相关观察与下游分析；不修改 asr.json 或旧帧。

`scope` 声明是已核对的局部条目还是完整对白，查看全部稀疏帧不等于逐句字幕完整覆盖。发生原片/页面时长冲突时，在 manifest 的核对说明和 review.md 分别记录测量值、来源与待核查范围。

完整内容分析保存 `content_profile` 和 `audience`，分组标签、依据和观察引用遵循 [内容与受众分类](audience-classification.md)。预处理脚本不填分析结论；旧证据包缺分类字段时视为尚未分析，不擅自补造。

review.md 写清：使用了哪些来源、看过页数与时间范围、密集复核点、直接听审范围、确认的事实、推断和未解决项。没有听过音频不得声称语气/音乐结论；没有看过的接触表页不得声称已检查。所有未解疑点传给下游，由下游决定是否局部可用。
