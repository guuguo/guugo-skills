# 即梦队列脚本治理方案

## 状态

- 状态：draft
- 版本归属：无明确版本
- 最近确认人：用户
- 最近确认时间：2026-07-08

## 目标

把 `dreaminaq / dreamina-queue` 从“可直接替代 App 的生产工具”降级为“完整模拟实验室”，真实提交继续由 `dreamina-scheduler App` 承担。脚本侧先完全 mock 官方 CLI 的输入输出、排队、生成、失败和额度边界，用于 agent 流程演练、状态面板验证和异常覆盖；只有当 mock 行为与 App 真实提交体验足够接近时，才重新讨论是否接入真实提交。

成功后，外部可观察结果是：

- 正式即梦生产只使用 `dreamina-scheduler App` 做真实提交。
- `dreaminaq` 默认只连接 mock CLI，不触达真实官方 CLI，不消耗额度。
- mock CLI 能完整模拟真实 CLI 的主要命令、参数、返回 JSON、stderr、排队状态、生成状态、失败模式和边界错误。
- `dreaminaq` 即使被误配到真实 CLI，也不再可能因缺省模型或错误模型烧 VIP/高消耗额度。
- `dreaminaq` 的自动查询只判断远端是否生成完成，不默认下载本地文件。
- `dreaminaq` 输出给 agent/用户的是“可决策状态摘要”，不是 task_id/submit_id 堆叠。
- 技能只保留薄操作规范，复杂状态、模型白名单、下载策略和队列解释下沉到代码/App。

## 用户与场景

- 目标用户：即梦短视频生产工作流的用户，以及未来用 agent 批量提交即梦任务的执行层。
- 主要场景：
  - 用户继续用 `dreamina-scheduler App` 做正式生产和真实提交。
  - agent 需要演练提交流程、队列状态、异常恢复和面板输出时，调用 `dreaminaq + mock CLI`。
  - 后续对比 mock 输出与 App 真实提交效果，逐步校准 mock。
- 关键用户路径：
  1. 用户准备视频提示词和素材。
  2. agent 先用 `dreaminaq + mock CLI` 演练提交计划、模型门禁、状态面板和异常路径。
  3. mock 结果符合预期后，用户在 `dreamina-scheduler App` 发起真实提交。
  4. App 真实提交后，用后台状态与 mock 状态做对比，补齐 mock 差异。
  5. 任何脚本真实提交都默认禁止，除非未来另起需求并通过 P0 验收。

## 范围

### 做

- 明确短期生产策略：
  - `dreamina-scheduler App` 保持正式生产主入口。
  - `dreaminaq` 不承担正式批量生产；默认只跑 mock CLI。
  - agent 可用脚本演练完整流程，但真实提交必须切回 App。
- 明确 `dreaminaq` 的产品边界：
  - 作为 headless 队列/安全提交层和 mock 实验室，而不是另一个完整 App。
  - mock 模式负责入队、防重复、模型白名单、模拟提交、模拟查询、模拟结果 URL、可选模拟下载。
  - 真实提交能力默认关闭或显式标红为实验/禁用路径。
  - 不在技能里手搓复杂 UI；状态摘要应由命令或 App 固定输出。
- 建设完整 mock CLI：
  - mock CLI 必须兼容官方 CLI 的命令入口：`version`、`user_credit`、`login`、`text2video`、`multimodal2video`、`query_result`。
  - mock CLI 必须校验真实 CLI 的关键参数：`--prompt`、`--image`、`--video`、`--audio`、`--model_version`、`--ratio`、`--duration`、`--video_resolution`、`--submit_id`、`--download_dir`、`--poll`、`--session`。
  - mock CLI 必须模拟真实输入约束：`multimodal2video` 至少一张图片或视频；音频 2-15 秒；图片/视频/音频数量上限；`duration` 4-15 秒；`ratio` 取值；模型取值；VIP 模型识别；普通模型只 720p；VIP 才允许 1080p/4k。
  - mock CLI 必须模拟真实输出结构：成功提交返回 `submit_id`、`gen_status`、`prompt`、`credit_count`、`queue_info`；查询成功返回 `gen_status=success`、`result_url` 或 `result_urls`；排队/生成返回 `queue_info`。
  - mock CLI 必须模拟 stderr / 非 0 退出：未登录、并发限制、合规确认、参数错误、上传失败、网络超时、查询超时、下载超时、远端失败、取消、无结果、未知 submit_id。
  - mock CLI 必须支持场景脚本化：通过环境变量、fixture JSON 或命令参数指定每个 `submit_id` 的状态流，例如 `queued -> generating -> success`、`queued -> timeout -> retry -> success`、`concurrency -> retry`。
  - mock CLI 必须支持确定性输出：同一 fixture、同一输入得到稳定 submit_id、队列位置、结果 URL 和错误。
  - mock CLI 必须能模拟额度：不同模型返回不同 `credit_count`；VIP 场景只用于测试拦截，不允许进入正常成功路径。
  - mock CLI 必须能模拟下载可选：默认 `query_result` 不需要 `--download_dir`；带 `--download_dir` 时可按 fixture 返回下载成功或下载失败。
- 收敛 `dreaminaq` 必须保留的核心能力：
  - `doctor`：检查 CLI、登录、余额、环境。
  - `submit`：入本地队列，保存素材缓存和语义化任务名。
  - `worker/service`：后台提交与查询。
  - `status/task/result/history`：查询队列、任务、结果和历史。
  - 幂等 key：防重复提交同一计划任务。
  - 模型白名单：只允许普通模型，禁止 VIP。
  - 自动查询：远端生成成功即成功，不强制本地下载。
  - 可选下载：用户明确要求本地文件时再下载。
- 削减或降级 `dreaminaq` 的复杂能力：
  - `monitor` 只保留调试用途，不与 App 面板竞争。
  - `scheduler_status` 完整大快照只作为 debug，不直接面向用户。
  - Fast fallback 默认关闭或必须显式启用；普通排队工作流不得自动切 Fast。
  - request hash 严格去重保持高级配置，不作为日常主路径。
- 明确模型与额度硬门禁：
  - 每个付费生成命令必须显式传普通 `model_version`。
  - 禁止 `seedance2.0_vip`、`seedance2.0fast_vip` 或任何包含 `vip` 的模型。
  - 禁止依赖官方 CLI 默认模型。
  - 缺少显式模型时宁可阻塞，不得提交。
- 明确状态语义：
  - `生成中`、`远端排队中`、`查询远端中`、`本地待提交`、`等待重试`、`失败`、`已完成` 必须区分。
  - 下载失败不是生成失败；如果远端已成功但本地下载失败，状态应是“远端完成，本地未下载”。
  - 远端生成成功但没有本地文件，仍是成功。
- 明确任务命名：
  - 提交必须使用语义化幂等 key，例如 `男穿女公主/ep00-红烛不该往里吹/scene-01-红烛异常刺杀`。
  - 面板主信息显示任务名，不以 task_id/submit_id 作为主识别。
- 明确 App 与 CLI 的关系候选方案：
  - 方案 A：继续双轨，App 真实提交，CLI 只做 mock 演练。
  - 方案 B：未来 CLI 作为 App headless 模式，两者读同一任务库和同一模型白名单。
  - 推荐路线：当前采用 A；只有 mock 与 App 真实提交效果足够接近、且另起需求通过验收后，才考虑 B。
- 在 `dreamina-queue` 技能说明中保留薄规范：
  - 带参考图用 `multimodal2video`。
  - 必须语义化 key。
  - 必须显式普通模型。
  - 禁 VIP。
  - 提交后使用固定摘要面板。
  - 远端成功即成功，下载可选。

### 不做

- 不让 `dreaminaq` 在未验收前接管正式批量生产。
- 不让 `dreaminaq` 默认触达真实官方 CLI。
- 不用 mock 成功替代真实 App 提交成功；mock 只证明流程和异常处理。
- 不继续把复杂面板规则堆进技能文本作为主要保障。
- 不让 agent 依赖记忆判断 VIP/普通模型；必须代码层拦截。
- 不默认下载生成结果到本地。
- 不把 `dreaminaq monitor` 做成另一个正式桌面 App。
- 不把 `dreamina-scheduler App` 的任务库和 `~/.dreaminaq` 任务库默认为互通。
- 不自动迁移历史任务或历史失败记录。
- 不把执行过程态写入本需求方案。
- 不追求 mock 覆盖官方未公开私有 API；只模拟官方 CLI 可观察输入输出和已知边界。

## 已确认事实

- 用户当前正式生产仍使用 `dreamina-scheduler App`。
- `dreaminaq / dreamina-queue` 与 `dreamina-scheduler App` 当前不是天然互通的数据系统。
- 本次事故中，`dreaminaq` 暴露出多个生产级问题：
  - 曾误用 `text2video + --image`。
  - 提交后面板不清晰，展示 task_id/submit_id 多于任务语义。
  - 查询结果时默认下载本地文件，导致下载超时被误判为失败。
  - 有效提交的真实命令曾缺少显式 `--model_version`，可能落入官方默认/高消耗模型。
  - 用户在即梦后台观察到任务走了 VIP/高消耗模型。
- 官方 CLI 支持普通与 VIP 模型，VIP 模型名称包含 `_vip`。
- 用户要求：排队普通模型绝对不碰 VIP 模型。
- 用户要求：生成完成即可算成功，本地文件下载不是必须项。
- 用户认为：脚本目前问题多，暂时还是用 `dreamina-scheduler App`。
- 用户确认新的双轨方向：脚本侧完全 mock，调度器 App 做真实提交；等 mock 效果和真实提交效果差不多再考虑后续。
- `dreamina-queue` 目前是独立项目路径：`/Volumes/Seamless SSD/dev/ai_video/dreamina-queue`。
- `dreamina-scheduler App` 目前是独立项目路径：`/Volumes/Seamless SSD/dev/ai_video/dreamina-scheduler`。
- 本方案落地位置为技能项目：`/Users/guodeqing/.agents/sources/skills/guuguo-skills`。

## 推荐假设

- 在新方案下，所有 agent 不应使用 `dreaminaq` 提交正式付费任务；`dreaminaq` 只连 mock CLI。
- `dreaminaq` 可以继续保留为实验工具，用于模拟流程、异常和状态面板。
- `dreaminaq` 最终如果要生产可用，应优先成为 `dreamina-scheduler App` 的 headless 模式，而不是长期维护两套队列产品。
- Fast 模型虽然不是 VIP，但仍可能不符合“普通排队优先”的省钱预期；默认不自动 Fast fallback。
- 技能层只保留操作门禁；凡可由代码判断的安全条件，都必须下沉到代码。

## 待确认问题

| 优先级 | 问题 | 推荐答案 | 不确认的影响 | 状态 |
| --- | --- | --- | --- | --- |
| P0 | 是否立即冻结 `dreaminaq` 的正式付费生产用途？ | 是。脚本只连 mock CLI；真实提交继续用 `dreamina-scheduler App`。 | agent 可能继续用脚本烧额度。 | confirmed |
| P0 | mock CLI 是否必须完整模拟真实 CLI 的输入输出和边界条件？ | 是，至少覆盖官方 CLI 可观察命令、参数、返回 JSON、stderr 和常见失败模式。 | mock 过于玩具化，无法暴露生产问题。 | confirmed |
| P0 | 是否允许普通 Fast `seedance2.0fast` 出现在 mock 默认双通道？ | mock 可模拟；真实默认不自动启用。只有用户明确要求 Fast 时，App 真实提交才考虑普通 Fast。 | 省钱预期与速度预期冲突。 | recommended |
| P1 | 未来是否要把 `dreaminaq` 改成 App 的 headless 模式，共用任务库？ | 中期考虑，短期不做。 | 双轨长期并存会继续制造状态不一致。 | recommended |
| P1 | 是否需要保留 `dreaminaq monitor`？ | 保留为 debug，不作为正式面板。 | 继续投入终端 UI 会分散精力。 | recommended |
| P2 | 历史已烧额度的异常任务是否需要专项复盘台账？ | 可在内容项目另建事故复盘，不放入技能项目方案。 | 方案会变成事故流水账。 | assumed |

## 现有系统事实

- `dreamina-queue` 当前具有：
  - 本地任务库。
  - 素材 blob 缓存。
  - 幂等 key。
  - worker 与 macOS LaunchAgent service。
  - standard/Fast lane 策略。
  - status/history/task/result 查询。
  - result 下载能力。
- `dreamina-queue/tests/fake_dreamina_cli.py` 当前已有简化 fake CLI，但尚未完整模拟官方 CLI 的输入输出和边界。
- `dreamina-scheduler App` 当前具有：
  - 桌面 UI。
  - lane strip / 双通道可视化。
  - 任务列表与操作面板。
  - App 自己的数据结构。
- 两者当前没有明确共享同一任务库、同一状态解释和同一模型白名单。
- `guuguo-skills` 当前没有 `docs/harness/version.md`，本方案不做 harness 初始化或升级。
- `guuguo-skills` 当前已有一个 harness spec：`docs/harness/specs/20260706-mac清理技能/`。

## 约束与风险

- 额度安全是 P0：任何自动化都必须宁可阻塞，不可错提交。
- mock 与真实提交必须明确隔离，避免测试脚本误连真实 CLI。
- mock 如果不够像真实 CLI，会给 agent 错误信心。
- VIP/高消耗模型风险不可只靠 agent 技能文本规避，必须代码层白名单。
- 两套任务库并存会导致用户在 App 看一套状态、agent 在 CLI 看另一套状态。
- 自动 Fast fallback 虽能提速，但可能违反“普通排队/省额度”预期。
- 结果下载失败不应污染生成状态；下载属于后处理。
- 状态面板如果以 task_id/submit_id 为核心，用户无法快速判断生产风险。
- 技能文本过厚会让问题变成“靠提示词遵守”，而不是“系统不能错”。

## 稳定规范引用

- 暂无。当前技能项目尚未初始化 `_stable/`。

## 持久子需求判断

- 是否需要 `sub-*.md`：否
- 判断理由：本期是治理方案和边界定义，不拆执行任务。后续若决定“App/CLI 数据互通”或“CLI 生产化重构”，应另建独立需求，而不是在本方案下维护子规格。
- 如果需要，子需求文件：无

## 验收标准引用

- `acceptance.md`

## 执行交接

- 执行层由用户运行时指定；本需求文档不绑定 Superpowers、普通 agent 或其他执行技能。
- 执行前必须读取 `acceptance.md`。
- 执行完成声明必须回填 `acceptance.md#执行验收记录`，或创建并链接同目录 `result.md`。
- 执行层不得擅自改写本文件的需求事实；如发现事实变化，先记录建议并等待用户确认。

## 变更记录

| 日期 | 变更 | 来源 |
| --- | --- | --- |
| 2026-07-08 | 创建 `dreaminaq` 脚本治理方案草案。 | 用户要求 |
