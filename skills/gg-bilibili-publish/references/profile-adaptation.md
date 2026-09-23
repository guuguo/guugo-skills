# 页面策略修订

引擎返回 `needs_ai_optimization` 时，按失败字段改 `scripts/bilibili_publish_profile.json`，不要改发布流程正文。

## 步骤

1. 只读失败字段的最小 DOM：所属表单项、可见值、可交互祖先、浮层。禁止全页 snapshot 漫扫，禁止按 DOM 序号盲点。
2. 判断是选错项、事件未触发、平台异步覆盖、控件未挂载还是选择器过期。
3. 只改对应选择器、语义文案或计时；提升 `profile_revision`，写清 `last_evidence_update`。
4. 运行：

```bash
python3 scripts/test_bilibili_publish_agent.py
```

5. 用同一 `run-id` 续跑。策略哈希和 revision 都没变时，引擎拒绝原样重试。
6. 上一轮已写入 `possible_submit=true`：续跑只能后台查重与对账，禁止上传和点击投稿。

## 可改 / 不可改

可改：`selectors`、个别 `timing`、失败字段的触发方式。

不可改：分区目标 `娱乐`、一次投稿、合集必须页面实选、禁用 API 补救、默认不用智能封面。这些是流程不变量，不因单次 DOM 变化改写。

`fixed_tags` 与 `season_map` 是账号设置，换账号或换合集时改 profile，不要为一次失败临时改标签集合。
