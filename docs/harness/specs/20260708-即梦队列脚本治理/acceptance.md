# 验收标准

## 状态

- 状态：complete
- P0 是否已由用户确认：是
- 最近确认时间：2026-07-08

## 验收表

| 编号 | 对应来源 | 验收条件 | 重要性 | 证据要求 | 状态 |
| --- | --- | --- | --- | --- | --- |
| A1 | `plan.md#范围` | `dreaminaq` 默认连接 mock CLI；正式真实提交只走 `dreamina-scheduler App`。 | P0 | 配置/README/技能说明；执行记录中脚本测试使用 mock CLI；无脚本真实提交。 | passed |
| A2 | `plan.md#范围` | mock CLI 覆盖官方 CLI 命令：`version`、`user_credit`、`login`、`text2video`、`multimodal2video`、`query_result`。 | P0 | 自动测试逐命令覆盖；输出结构与真实 CLI 可观察结构一致。 | passed |
| A3 | `plan.md#范围` | mock CLI 覆盖关键参数校验：素材、模型、比例、时长、分辨率、submit_id、download_dir、poll、session。 | P0 | 参数化测试覆盖合法/非法输入；非法输入返回非 0 或真实风格错误。 | passed |
| A4 | `plan.md#范围` | mock CLI 覆盖模型边界：普通模型、Fast、mini、VIP；VIP 只用于测试拦截，不进入正常成功路径。 | P0 | 自动测试覆盖 `_vip` 被队列层阻塞，mock 可返回 VIP 成本用于断言不会提交。 | passed |
| A5 | `plan.md#范围` | mock CLI 覆盖状态流：提交成功、远端排队、生成中、生成成功、生成失败、取消、未知 submit_id。 | P0 | fixture 测试覆盖 `queued -> generating -> success`、`fail`、`cancel`、`unknown submit_id`。 | passed |
| A6 | `plan.md#范围` | mock CLI 覆盖错误模式：未登录、并发限制、合规确认、参数错误、上传失败、网络超时、查询超时、下载超时。 | P0 | 自动测试覆盖 stdout/stderr/exit code；调度器能给出正确中文状态。 | passed |
| A7 | `plan.md#范围` | mock CLI 支持确定性 fixture：同一输入和 fixture 得到稳定 submit_id、队列位置、结果 URL、错误。 | P0 | 固定 fixture 重复运行两次，输出一致。 | passed |
| A8 | `plan.md#范围` | mock CLI 支持可选下载：默认不需要 `--download_dir`；带 `--download_dir` 时可模拟下载成功或失败。 | P0 | 自动测试覆盖无下载成功、下载成功、下载失败三种。 | passed |
| A9 | `plan.md#范围` | `dreaminaq` 真实 CLI 路径被隔离：mock 模式下不会调用真实官方 CLI，不消耗额度。 | P0 | 测试中断言调用路径为 mock；无真实 submit_id；余额不变化或不查询真实余额。 | passed |
| A10 | `plan.md#范围` | `dreaminaq` 即使误连真实 CLI，也必须代码层阻塞缺省模型和 VIP 模型。 | P0 | 自动测试覆盖缺少 `model_version`、`*_vip`，attempt 数为 0。 | passed |
| A11 | `plan.md#范围` | 状态摘要以中文任务名为主，展示本地队伍、远端占用、远端排队/生成、下一步、异常；task_id/submit_id 只放技术详情。 | P0 | `dreaminaq status --summary-json` 或等价输出；mock 多状态人工检查。 | passed |
| A12 | `plan.md#范围` | mock 演练结果与 App 真实提交结果建立对比表；差异被记录并反哺 mock。 | P1 | 至少 3 个真实 App 提交样本对比：排队中、生成中、成功。 | passed |
| A13 | `plan.md#范围` | Fast fallback 默认关闭或仅在 mock/用户明确要求时启用；真实 App 提交不由脚本自动切 Fast。 | P0 | 配置默认值/测试；无用户明确要求时 lane 不自动切 fast。 | passed |
| A14 | `plan.md#范围` | 技能文本瘦身：只保留操作门禁和双轨边界，不承载复杂状态解释算法。 | P1 | `skills/dreamina-queue/SKILL.md` 人工检查；复杂状态由命令输出或 App 提供。 | passed |

## 不作为通过依据

- mock 只返回单一 success，不能模拟排队、生成、失败和边界。
- mock 输出结构不像真实 CLI，导致调度器逻辑只在玩具环境里通过。
- 只在技能文本里写“不要 VIP”，但代码仍允许提交。
- 只靠 agent 口头承诺不用默认模型。
- 状态面板继续以 task_id/submit_id 为主。
- 自动查询仍默认下载本地文件。
- 远端生成成功但本地下载失败时仍标成生成失败。
- `dreaminaq` 和 App 状态混用，未说明数据不互通。
- Fast fallback 仍在用户未明确要求时自动触发。
- 实现者自称修好了，但没有自动测试和真实命令记录证据。

## 待确认验收

| 编号 | 问题 | 推荐答案 | 风险 | 状态 |
| --- | --- | --- | --- | --- |
| QA1 | 是否立即冻结 `dreaminaq` 正式付费用途？ | 是，脚本只走 mock；真实提交只走 App。 | 未冻结会继续暴露额度风险。 | confirmed |
| QA2 | mock CLI 是否必须完整模拟真实 CLI 的输入输出和边界条件？ | 是。 | mock 玩具化会误导 agent。 | confirmed |
| QA3 | 普通 Fast `seedance2.0fast` 是否允许进入默认真实双通道？ | 默认不允许；mock 可模拟，真实提交由用户在 App 决定。 | 与“普通排队省钱”预期冲突。 | recommended |
| QA4 | 是否要求未来 CLI 与 App 共用任务库后才允许 CLI 接管正式生产？ | 推荐是。 | 两套任务库并存会继续混乱。 | open |

## 执行验收记录

> 执行完成后必须回填。本节记录最终证据，不记录运行过程态。证据较多时，创建同目录 `result.md` 并在此链接。

- 执行状态：complete
- 执行方式：修改 `/Volumes/Seamless SSD/dev/ai_video/dreamina-queue` 代码、测试、README、技能说明和对比表。
- 执行时间：2026-07-08
- 执行者/会话：Codex 当前会话
- 关联提交/PR/变更摘要：未提交；仓库当前整体未跟踪。
- 详细结果文件：`result.md`

### 验收项结果

| 编号 | 状态 | 实际证据 | 说明 |
| --- | --- | --- | --- |
| A1-A11, A13-A14 | passed | `python3 -m unittest discover -s '/Volumes/Seamless SSD/dev/ai_video/dreamina-queue/tests'` 通过；隔离烟测通过；详见 `result.md`。 | mock-first 实现、模型门禁、下载可选、中文摘要、技能瘦身均已落地。 |
| A12 | passed | `python3 -m dreamina_queue.cli compare-app-state --app-state "$HOME/.dreamina-scheduler/state.json" --json` 返回 `ok=true`；`docs/mock-vs-app-comparison.md` 已回填 3 类真实 App 历史样本。 | 样本覆盖远端排队中、生成中、生成成功；本次没有提交新的即梦任务。 |

### 验证命令与结果

| 命令/检查 | 结果 | 关键输出或证据位置 |
| --- | --- | --- |
| `python3 -m unittest discover -s '/Volumes/Seamless SSD/dev/ai_video/dreamina-queue/tests'` | pass | `Ran 60 tests in 0.726s` / `OK` |
| 隔离 `DREAMINAQ_HOME` 烟测：`doctor` + `submit` + `once` + `status --summary-json` | pass | `dreamina_cli.mode=mock`、`dreamina_cli.path=mock://dreamina`、summary 任务名与阶段正确；详见 `result.md` |
| `python3 -m dreamina_queue.cli compare-app-state --app-state "$HOME/.dreamina-scheduler/state.json" --json` | pass | `ok=true`；抽到 `queued`、`generating`、`success` 三类真实 App 历史样本 |

### 独立审查

- Spec review：本次按 A1-A14 自检，全部通过。
- Code review：未做外部独立 review。
- 人工验收：待用户确认。

### 未验证项与风险

- 本次没有提交任何真实即梦生成任务。
- 本方案没有迁移 App/CLI 数据。
- `dreaminaq` 已改为默认 mock 演练，不声明可替代 App 真实提交。
- A12 使用 App 历史状态只读抽样完成；后续如果 App 真实表现变化，仍需继续补样本反哺 mock。
