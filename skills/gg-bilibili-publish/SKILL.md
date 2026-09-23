---
name: gg-bilibili-publish
description: 用 BrowserSkill 在用户真实登录的 Chrome 里向 B站创作中心发布 AI 短剧成片或专栏，并维护发布台账。用户提到发B站、B站投稿、B站充电、B站专栏、bilibili 发布、写发布台账、对账 aid/bvid 时使用。
---

# B站发布

用 BrowserSkill 的独立 Agent Window 向 B站创作中心投稿。用户只给自然语言；不要让用户跑命令、填 JSON 或选择正常/维护模式。

## 配置

本机指针在 `~/.config/gg-bilibili-publish/config.json`，与 gg-drama-library / gg-video-analysis 相同：`~/.config/<skill>/config.json`。机器路径不写入本技能。`--config` 可覆盖，不扫描磁盘猜项目。

缺配置时问一次项目根，然后：

```bash
python3 ~/.agents/skills/gg-bilibili-publish/scripts/ledger.py configure --project-root "/绝对路径"
```

有效配置跨任务复用。改配置不搬迁旧台账。外置卷未挂载时停止写入。

字段：`project_root`；相对它解析 `ledger_path`、`log_root`、`staging_root`；`upload_copy_dir` 为 Chrome 可注入的本机副本目录。页面策略在技能内 `scripts/bilibili_publish_profile.json`。

## 按任务读取

| 任务 | 指引 |
| --- | --- |
| 视频投稿、充电专属、续跑、演练 | [视频发布](references/publish-flow.md) |
| 查重、追加、待同步对账、禁止手改成功表 | [台账](references/ledger.md) |
| 普通/充电专栏 | [专栏发布](references/column-publish.md) |
| 选择器失效、`needs_ai_optimization` | [策略修订](references/profile-adaptation.md) |

浏览器一律走 `browser-skill`，不借用用户现有标签。著作权投诉不是本技能。

## 视频发布

1. 读配置和台账；锁定视频、SHA-256、标题及编号依据、简介、普通/充电、合集。标题来自锁定输入，禁止用文件名或“第几条线”猜 B站总集号。
2. 待发成片先归到配置的 `staging_root`（纯 ASCII）。上传前才复制到 `upload_copy_dir`。`/Volumes` 路径会让 Chrome 报 `Not allowed`。
3. 引擎一次跑正常快路径：

```bash
python3 ~/.agents/skills/gg-bilibili-publish/scripts/bilibili_publish_agent.py --manifest /绝对路径/manifest.json
```

4. 返回 `needs_ai_optimization` 时任务未结束：按策略修订更新 profile、跑 `scripts/test_bilibili_publish_agent.py`，用同一 `run-id` 续跑。策略没变禁止原样重试。若已 `possible_submit=true`，续跑只读对账，不得重传或再点投稿。
5. 成功标准：`/x/vu/web/add/v3` 的 `code=0 + aid/bvid`，或后台唯一目标稿件。随后必须由引擎追加台账；没写台账不算完成。`cid` 可 `待同步`。
6. 本条 `upload_copy_dir` 副本在台账写完后删除。

`--stop-before-submit` 仅用户明确授权演练时使用：不写台账、不点投稿。

## 台账

台账是项目事实，落在配置的 `ledger_path`，不进技能仓库。维护方式对齐 gg-drama-library / stock-picking：工具锁内写入，Agent 不手改成功表。

```bash
python3 ~/.agents/skills/gg-bilibili-publish/scripts/ledger.py status
python3 ~/.agents/skills/gg-bilibili-publish/scripts/ledger.py validate
python3 ~/.agents/skills/gg-bilibili-publish/scripts/ledger.py reconcile --sha256 <hash> --cid <cid> --status <状态>
```

成功行只由引擎追加。待同步字段用 `reconcile`。删除/异常行用 `record-exception`。没有投稿成功证据不得声称已发布。禁止主动删除、下架已发布作品；用户当前回合点名平台和作品并要求删除时才执行，并记异常行。

## 硬边界

- 重复就停：同源、同 sha256、同标题、同 aid/bvid 已存在则不再上传。
- 分区页面回显必须是 `娱乐`；合集必须页面实选并读回。
- 禁止用后台/API 提交或补救分区、标签、合集、AI 声明、封面。
- 默认不用智能封面；普通截帧第一张。
- 整次任务最多一次投稿请求。人工接管后立即停止写操作，只读补台账。
- 固定标签、合集映射、充电默认值以当前 profile 为准。
