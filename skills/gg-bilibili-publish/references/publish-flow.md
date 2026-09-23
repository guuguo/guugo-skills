# 视频发布

用 BrowserSkill 在独立 Agent Window 中走 B站投稿页。专栏见 [专栏发布](column-publish.md)。

## 引擎

AI 先在计时外锁定输入，再调用：

```bash
python3 scripts/bilibili_publish_agent.py --manifest /绝对路径/manifest.json
```

可选：`--config`、`--profile`、`--run-id`、`--dry-run`、`--stop-before-submit`。

引擎按平台 + 源视频 `sha256` 建跨进程 in-flight 锁，并用完整 `manifest_hash` 锁定字段。同一源视频同时只能有一个进程；崩溃后新调用接管旧状态。`possible_submit=true` 后永远只读对账。

正常路径由引擎批处理。异常探索必须沉淀为 profile 更新，见 [策略修订](profile-adaptation.md)。

计时保留本轮墙钟和任务总墙钟。总墙钟超过 60 秒记超时，任务继续；单次尝试超过 300 秒记本轮失败并优化后续跑。最终结果必须输出两者。

## 不可带病提交

1. 台账和后台任一已存在同源、同 sha256、同标题、同 aid/bvid，停止上传。
2. 上传卡 `0/0` 或 `Not allowed`：先让用户给扩展「允许访问文件网址」。
3. 八项总检不过暂缓投稿，按恢复阶梯继续，直到通过。只有验证码、登录失效、扩展权限、平台不可用才请用户介入。
4. `提交中...` 时先看 `/x/vu/web/add/v3`；`code=0 + aid/bvid` 或后台唯一目标稿件才算成功。不得补点。
5. 合集只能页面「加入合集」实选并读回。
6. 分区目标为 `娱乐`。当前页常无「粉丝创作」二级项；后台结果不能反推规则。
7. 后台/API 只用于查重、提交后核验、读合集/分区参数。禁止用它设分区、标签、合集、AI 声明、封面或发布后补救编辑。
8. 投稿页必须同时满足 `https://member.bilibili.com/platform/upload/video/frame` 和上传控件已挂载。12 秒仍不满足则关任务标签、新开投稿页。
9. 默认不点「智能封面」。普通截帧未自动应用时点第一张。
10. 用户声明已手动点击或发布后，停止所有写操作，只读补台账。

## 准备

1. `bsk status --json` 需存在已连接浏览器；引擎会创建并记录本次独立 BrowserSkill session。
2. 成片先到配置 `staging_root`，排队、sha256、ffprobe 在此完成。上传前复制到 `upload_copy_dir`。台账写完立刻删除该副本。
3. 微信直给成片视为可信来源，不做完整 ASR/抽帧。未知剧集时最多截开头 12–15 秒做一次本地 ASR 匹配。

## 最短路径

干净投稿页 -> 上传控件挂载 -> 单条上传 -> 普通截帧第一张已应用 -> 一次填表 -> 最后锁定分区 -> 一次总检 -> 写 `possible_submit` -> 点一次 `立即投稿` -> 读受理结果 -> 原子写台账。

表单顺序：封面 -> 标题/简介 -> AI 声明 -> 清空可见旧标签并打 profile 中的固定标签 -> 合集 -> 分区。

每条都从新开投稿页开始，不用成功页「再投一个」。

## 充电专属

仅用户明确要求时开启。试看默认 `00:00:05`，付费默认 `包月付费` + `30元档`。总检额外读开关、试看、档位。

## 字段要点

- 标题：等可见输入框挂载；`fill` 失败只允许对该框原生 setter + `input/change`，禁止改 Vue。队列只显示文件名且无编辑入口时不硬停，提交后核验稿件标题。
- 分区：其他字段完成后再选；读回必须为 `娱乐`。
- 简介：填 `.ql-editor`，读回 `video-basic.desc`。不要填 `mention-hidden-input`。
- 标签：以 `.label-item-v2-content` 为准，集合与 profile `fixed_tags` 完全一致，顺序可被平台重排。
- 合集：点 `.video-season .season-enter`，读回目标合集名。映射见 profile `season_map`。
- 封面：候选出现但仍 `.cover-empty.failed` 时点第一张。首帧黑场/糊脸/主体被裁才抽一张本地原帧上传。
- 提交：关浮层，点 `.submit-add` 一次。主代理如需前台核验，只能聚焦本次 BrowserSkill Agent Window，严禁再点投稿。

## 提交前总检

| 项 | 必须是 |
|---|---|
| 标题 | 外层正式标题；可编辑分P 也必须一致 |
| 分区 | `娱乐` |
| AI 声明 | `含AI生成内容` |
| 简介 | 与锁定简介规范化后一致 |
| 标签 | 页面可见集合与 profile 完全一致 |
| 合集 | profile 映射的目标名，或用户明确不加入 |
| 封面 | 正式封面预览在，无 `.cover-empty.failed` |
| 发布类型 | 普通稿充电关闭；充电稿含试看和档位 |

任一项不对就恢复，不提交。简介须含：`本作品为AI生成短剧，人物与剧情均为虚构演绎，仅供娱乐。`

## 核验

```js
await (await fetch("https://member.bilibili.com/x/web/archives?pn=1&ps=20&status=all", {credentials:"include"})).json()
await (await fetch("https://member.bilibili.com/x2/creative/web/season/aid?id=<aid>", {credentials:"include"})).json()
```

成功：接口 `code=0 + aid/bvid`，或后台唯一目标稿。`cid/state_desc/合集` 暂不可查标 `待同步`，下次发布前 `reconcile`。合集最终缺失只记录，禁止删除重发或接口补加。

## 故障

| 现象 | 处理 |
|---|---|
| 上传 `Not allowed` | 停，处理扩展文件权限 |
| URL 被 SPA 拉回充电计划页 | 关标签，新开投稿页 |
| 标签少 1 个或有残留 | 以可见 DOM 清空重打 |
| 分区漂到影视等 | 最后再锁娱乐；失败走恢复阶梯 |
| 点击后无投稿请求 | 不补点；新页查重，无稿记待同步 |
| 后台分区与规则不一致 | 记录异常；禁止按后台改规则 |

结束时关闭本任务 BrowserSkill session，只关闭自己的 Agent Window。
