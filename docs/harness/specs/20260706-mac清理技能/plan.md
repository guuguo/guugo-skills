# gg-clean-mac：macOS 清理诊断技能

## 状态

- 状态：draft
- 版本归属：无明确版本
- 最近确认人：用户
- 最近确认时间：2026-07-06

## 目标

在个人技能仓库 `guuguo-skills` 中新增 `gg-clean-mac` 技能，用于快速扫描 macOS 磁盘与交换内存问题，识别常见超级占用源，给出安全、分层的清理建议，并在每次扫描后更新“电脑印象”，让后续扫描优先命中本机长期反复出现的问题。

成功后，用户可以通过调用 `gg-clean-mac` 快速获得：

- 当前磁盘空间、swap、内存压力和最可疑进程的简明结论。
- 快速模式下的重点大户列表，而不是全盘慢扫。
- 对企业微信、微信、飞书等聊天/办公软件占用的解释，并优先引导到 App 内清理。
- 基于历史“电脑印象”的加速扫描路径和风险提示。

## 用户与场景

- 目标用户：本机用户，以及未来在同一台 Mac 上协助用户排查空间/内存问题的 agent。
- 主要场景：
  - 电脑空间不足，需要快速知道主要空间被谁占了。
  - swap 暴涨，需要快速定位最可疑进程。
  - 定期巡检，记录哪些工具经常膨胀。
  - 决定哪些缓存可以清、哪些数据必须让用户到 App 内清理。
- 关键用户路径：
  1. 用户说“电脑空间不够了 / swap 高 / 快速清理一下”。
  2. agent 使用 `gg-clean-mac`。
  3. 快速模式先读电脑印象和固定重点路径，再补充必要系统指标。
  4. 输出按“可直接清理 / 建议 App 内清理 / 谨慎处理 / 不建议动”分组。
  5. 多轮清理过程中在对话内维护“本轮清理看板”。
  6. 清理结束后只把摘要写入电脑印象，记录本次高频大户与结论。

## 范围

### 做

- 新增技能目录：`skills/gg-clean-mac/`。
- 新增 `skills/gg-clean-mac/SKILL.md`，定义触发条件、扫描流程、快速模式、输出格式、清理边界和电脑印象更新规则。
- 新增 `skills/gg-clean-mac/references/`，至少放置：
  - `interaction-protocol.md`：多轮清理对话协议、确认语法、候选项编号规则和误操作防护。
  - `computer-impression-schema.md`：电脑印象 JSON schema、字段说明、更新/裁剪规则和示例。
  - `mac-cleaning-targets.md`：常见 macOS 大户路径知识库，包含来源、用途、风险、重建方式、网络/VPN 成本。
  - `commands.md`：只读扫描命令、快速模式命令、深度模式命令和安全清理命令候选。
- 可选新增 `skills/gg-clean-mac/scripts/`，放置只读扫描脚本或汇总脚本；脚本必须默认不删除文件。
- 设计快速模式：
  - 先查 `df -h`、`sysctl vm.swapusage`、`top`/`ps` 中的内存大户。
  - 优先扫描历史电脑印象中的重点路径。
  - 优先扫描本机已知高频大户：`~/Library/Containers/com.tencent.WeWorkMac`、`~/Library/Containers/com.tencent.xinWeChat`、`~/.cache/uv`、`~/.codex`、`~/.antigravity_cockpit`、`~/.gemini`、`~/Library/Application Support/Claude/vm_bundles`、`~/.espressif`、`~/Library/Caches`、`~/Library/Application Support/LarkShell`。
  - 限制扫描深度，避免默认全盘 `du` 卡住很久。
  - 快速模式只加速“收集证据与组织决策信息”，不加速或跳过清理确认。
- 设计深度模式：
  - 用户明确要求时，再做用户目录顶层、`~/Library`、隐藏开发目录和大文件扫描。
  - 深度模式仍默认只读。
- 设计电脑印象机制：
  - 每次扫描后更新一个本机画像文件：`~/.agents/state/gg-clean-mac/computer-impression.json`。
  - 电脑印象权威源采用 JSON，不采用 Markdown 作为主状态文件；JSON 更适合脚本读取、排序、更新、去重和后续快速扫描。
  - Markdown 只作为展示输出或临时报告格式，不作为长期状态的第二份来源，避免 JSON/Markdown 双写不一致。
  - 电脑印象采用“一个文件 + 多层结构化印象”，不是只记一句总结。
  - 顶层结构包含 `machine_summary`、`hotspots`、`preferences`、`recent_scans`、`known_incidents`。
  - `machine_summary` 记录机器总体特征：磁盘大小、常见瓶颈、主要开发栈、常见大户类型。
  - `hotspots` 记录重点路径：路径、上次大小、历史最大值、类别、风险等级、推荐处理方式、是否经常复发、上次扫描时间。
  - `preferences` 记录用户偏好和禁区：例如企业微信/微信只提示 App 内清理，认证配置不动。
  - `recent_scans` 只保留最近 5-10 次扫描摘要，用来判断趋势，不保存完整扫描输出。
  - `known_incidents` 记录已知处理经验：例如 ChatGPT 曾 28G swapped、`semble[mcp]` 曾大量复活、`~/.cache/uv` 曾 21G。
  - 后续快速模式优先扫描 `hotspots` 和 `known_incidents` 相关路径/进程。
- 设计多轮清理看板：
  - 单次清理可能跨多轮对话；清理过程中的“本轮目标、候选项、已确认、已清理、暂缓、下一步”只在对话内维护。
  - 不把运行过程态、逐步操作流水账或未完成任务清单写入电脑印象。
  - 本轮结束后，将结论性摘要写入 `recent_scans`、`hotspots`、`known_incidents` 或 `preferences`。
- 设计清理交互协议：
  - 每轮输出候选项必须有稳定编号，例如 `1`、`2`、`3`；编号只在本轮对话看板内有效。
  - 用户确认清理必须指向具体编号或具体路径，例如 `清理 1`、`清理 1 3`、`跳过 2`、`暂缓 4`、`深扫 5`。
  - 用户泛泛说“都清了”“帮我清理”“可以”时，不能视为对所有候选项的授权；必须追问具体编号。
  - 对 App 内清理项，确认动作应是“说明路径 + 引导 App 内入口”，不得转成命令行删除。
  - 每次执行前复述即将执行的命令/动作、预计释放、风险和重建成本。
  - 执行后立即复查对应路径大小或系统可用空间，并更新对话内看板。
- 设计候选项输出模板：
  - 编号：
  - 路径：
  - 当前大小：
  - 这是什么：
  - 从哪来：
  - 干嘛用：
  - 删除影响：
  - 重建方式：
  - 网络/VPN 成本：
  - 建议动作：
  - 确认方式：
- 明确清理建议分级：
  - 可直接清：构建缓存、下载缓存、工具缓存、旧备份、临时目录。
  - 建议 App 内清理：企业微信、微信、飞书/Lark、Claude/ChatGPT 类应用重要数据。
  - 谨慎处理：会话数据库、账号配置、虚拟机镜像、SDK 工具链、历史会话。
  - 不建议动：认证文件、配置、正在使用的数据库、用户聊天原始数据。
- 输出必须用中文，给出“预计可回收空间”和“建议先做哪几步”。
- 每个候选项必须尽量说明：
  - 这是什么：目录/文件属于哪个 App、工具链、包管理器、运行时或聊天软件。
  - 从哪来：由什么安装、下载、运行、缓存或同步动作产生。
  - 干嘛用：用于缓存、离线包、编译工具链、虚拟机镜像、聊天文件、会话记录、索引数据库等。
  - 删除影响：删除后会影响哪些功能，是否会丢历史、登录态、离线能力或构建速度。
  - 重建方式：自动重建 / App 内重新下载 / 包管理器重新拉取 / 需要重新安装 SDK / 不可可靠重建。
  - 重建成本：是否需要联网、是否可能访问外网、是否可能消耗 VPN 流量、预计下载量或时间级别。
  - 建议动作：命令行清理、App 内清理、仅归档、暂不处理或需要用户进一步确认。
- 首版常见目录知识库必须至少覆盖：
  - `~/.cache/uv`：uv/Python 工具与依赖缓存；通常可用 `uv cache clean` 清理；重建需要重新下载 Python 包，可能访问外网/PyPI 或镜像源，可能消耗 VPN。
  - `~/Library/Caches/Homebrew`：Homebrew 下载和 API 缓存；通常可用 `brew cleanup` 或清理 downloads；重建需要联网访问 Homebrew/GitHub/bottle 源，可能消耗外网/VPN。
  - `~/Library/Caches/go-build`：Go 编译缓存；可用 `go clean -cache`；重建通常不额外下载依赖，但会消耗 CPU 时间重新编译。
  - `~/Library/Caches/ms-playwright`：Playwright 浏览器缓存；删除后运行测试会重新下载浏览器，通常访问外网/CDN，可能消耗大量网络/VPN。
  - `~/Library/Caches/JetBrains`：JetBrains IDE 缓存/索引/Toolbox 缓存；删除后 IDE 会重建索引或重新下载组件，可能消耗 CPU、磁盘和网络。
  - `~/Library/Caches/semble`：`semble[mcp]` 相关缓存；删除后相关 MCP 可能重新构建/下载依赖，需结合父进程判断。
  - `~/.codex`：Codex 配置、会话、归档、备份、日志、生成图片；只能建议清旧备份/归档/临时文件，不能动 auth/config/当前会话数据库。
  - `~/.antigravity_cockpit`：Antigravity/Codex cockpit 实例、会话、备份和运行时；可建议清旧备份/归档，但需避免账号和实例配置。
  - `~/.gemini`：Gemini/Antigravity 数据、浏览器 profile、录制、备份；浏览器录制和旧备份较像清理候选，账号/oauth 配置不可动。
  - `~/.espressif`：ESP-IDF/ESP32 工具链、下载包和 Python 环境；`dist` 下载包缓存较可清，`tools` 删除会影响 ESP32 开发，重建需下载交叉编译器，可能很大且走外网/VPN。
  - `~/Library/Application Support/Claude/vm_bundles`：Claude 本地 VM/rootfs 镜像；删除可能导致 Claude Code/本地 VM 重新下载或重建，消耗大流量，可能外网/VPN。
  - `~/Library/Containers/com.tencent.WeWorkMac`：企业微信聊天/文件/数据库；默认只解释占用并引导 App 内存储清理，不命令行删除。
  - `~/Library/Containers/com.tencent.xinWeChat`：微信聊天/文件/小程序数据；默认只解释占用并引导 App 内清理，不命令行删除。
  - `~/Library/Application Support/LarkShell`：飞书/Lark 本地数据、缓存、搜索数据库和小程序/页面资源；优先 App 内清理或谨慎处理。
- 所有实际清理行为都必须经过用户确认；技能优化目标是更快给出足够确认的信息，而不是更快执行删除。

### 不做

- 不在技能默认流程中删除文件。
- 不默认执行 `rm -rf`、清空聊天数据、删除 App 数据目录或修改系统设置。
- 不因“快速模式”跳过任何清理确认。
- 不把企业微信、微信这类聊天数据当普通缓存直接清理。
- 不要求 root 权限作为默认路径。
- 不把本技能做成通用跨平台清理器；本期只针对 macOS。
- 不维护复杂运行态系统或任务 ledger；扫描结果只更新电脑印象和给用户结论。

## 已确认事实

- 技能名为 `gg-clean-mac`。
- 技能放在个人技能项目 `guuguo-skills` 中，与 `gg-harness` 同一项目文件夹内。
- 需要有快速模式。
- 每次扫描后需要更新“电脑印象”。
- 未来扫描要基于电脑印象加速，优先找常发生的重点问题。
- 企业微信这类占用应给出说明，尽量引导用户去 App 内清理。
- 清理行为无论风险高低都需要用户确认；快速模式的价值是更快形成可确认的候选清单和证据。
- 最近一次本机扫描已发现以下长期大户：
  - `~/Library/Containers/com.tencent.WeWorkMac` 约 50G。
  - `~/Library/Containers/com.tencent.xinWeChat` 约 19G。
  - `~/.cache/uv` 约 21G。
  - `~/.codex` 约 21G。
  - `~/.antigravity_cockpit` 约 16G。
  - `~/.gemini` 约 8.9G。
  - `~/.espressif` 约 6.3G。
  - `~/Library/Application Support/Claude/vm_bundles` 约 6.3G。
  - `~/Library/Caches/JetBrains` 约 5.3G。

## 推荐假设

- 电脑印象保存到用户级状态目录：`~/.agents/state/gg-clean-mac/computer-impression.json`，避免写入技能源码仓库，也避免污染当前 workspace。
- 电脑印象以 JSON 作为唯一长期源文件；如需要 Markdown，总是从 JSON 或本次扫描结果生成展示，不手工维护第二份状态。
- 技能源码可以附带一份“印象文件格式说明”，但真实印象文件应在本机用户状态目录中更新。
- 快速模式默认控制在 10-30 秒内，必要时宁可给出“未深扫”的提示。
- 深度模式可以允许 1-5 分钟扫描，但必须提前告知用户。
- 技能应优先输出“解释和建议”，只有用户明确确认具体清理项后才进入删除动作；用户泛泛说“帮我清理”也不能视为对所有项目的授权。
- 对低风险缓存也必须确认，但输出应提供路径、大小、来源、用途、风险、预期回收空间、建议命令、重建方式、网络/VPN 流量成本，降低用户确认成本。
- 可清理缓存建议先采用工具命令或安全目录级建议，例如 `uv cache clean`、`go clean -cache`、`brew cleanup`，而不是直接删除未知目录。
- 本技能不需要维护 `sub-*.md`，电脑印象机制作为本需求内的长期能力即可；未来如果要把“印象格式”做成跨技能稳定契约，再独立提稳定规范。

## 待确认问题

| 优先级 | 问题 | 推荐答案 | 不确认的影响 | 状态 |
| --- | --- | --- | --- | --- |
| P1 | 电脑印象实际保存路径是否采用 `~/.agents/state/gg-clean-mac/computer-impression.json`？ | 采用该路径；源码仓库只放格式说明。 | 后续实现时可能把个人机器状态误写进技能仓库。 | confirmed |
| P1 | 技能是否允许在用户逐项确认后执行安全清理命令？ | 允许，但必须逐项确认路径/命令；默认只读；“快速模式”不得跳过确认。 | 技能只能扫描，不能完成清理闭环。 | open |
| P1 | 快速模式是否以“已知重点路径 + 系统指标”为主，而不是全盘扫描？ | 是。 | 快速模式可能变慢，失去价值。 | open |
| P2 | 是否需要输出 Markdown 表格和“建议优先级”固定格式？ | 需要，方便每次对比。 | 输出风格可能不稳定。 | assumed |
| P2 | 是否需要支持英文系统路径但中文解释？ | 需要。 | 可读性下降。 | assumed |

## 现有系统事实

- 目标项目路径：`/Users/guodeqing/.agents/sources/skills/guuguo-skills`。
- 当前项目已有技能：
  - `skills/gg-skills-governor/`
  - `skills/gg-ai-native-startup-playbook/`
  - `skills/gg-child-psychology-for-content/`
  - `skills/gg-fact-driven-ai-methodology/`
  - `skills/gg-harness/`
  - `skills/guuguo-image-gen/`
- 当前项目没有根 `AGENTS.md`。
- 当前项目没有 `docs/harness/version.md`，视为 harness 未初始化或 unknown。
- 当前项目已有旧技术方案目录：`docs/tech-plan/20260619-gg-harness-light/`。
- 当前 git 工作区已有大量未提交变更，本需求执行层不得覆盖或回滚这些变更。

## 约束与风险

- 清理技能具有数据破坏风险，默认必须只读扫描。
- 清理确认是硬边界：速度优化只能减少用户判断成本，不能减少确认步骤。
- “可重建”不能只写一句可重建，必须说明重建代价；涉及外网依赖、模型、浏览器、SDK、包缓存时，要提示可能消耗网络带宽或 VPN 流量。
- 电脑印象不得变成任务系统或流水账；单轮清理的过程态留在对话内，只有结束摘要进入 JSON。
- 企业微信、微信、飞书、Claude、ChatGPT 等 App 目录可能含聊天、登录、数据库或本地工作状态，不能粗暴删除。
- `~/.codex`、`~/.antigravity_cockpit`、`.gemini` 中可能有历史会话和账号状态；清理建议要区分备份、归档、日志、会话、认证配置。
- `~/.espressif` 是 ESP-IDF/ESP32 工具链目录；删除后会影响嵌入式开发，需要提示可重装成本。
- 电脑印象文件会记录本机路径、应用使用习惯、历史问题和处理偏好，属于个人机器画像；不得上传或写入公开仓库。
- 快速模式若完全依赖旧印象，可能漏掉新问题；因此仍要保留最低限度的系统指标和用户目录顶层探测。

## 稳定规范引用

- 暂无。项目尚未初始化 `docs/harness/specs/_stable/`。

## 持久子需求判断

- 是否需要 `sub-*.md`：否
- 判断理由：本期的快速模式、电脑印象、清理分级都属于同一个技能的核心能力，不具备独立版本/独立验收/独立外部契约；作为 `plan.md` 与 `acceptance.md` 条目即可。
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
| 2026-07-06 | 创建 `gg-clean-mac` 技能规划草案。 | 用户要求与本机磁盘/swap 扫描结果 |
