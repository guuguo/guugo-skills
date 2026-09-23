# 发布台账

台账是项目事实，路径由 `~/.config/gg-bilibili-publish/config.json` 的 `ledger_path` 定位。技能仓库不保存发布记录。

维护方式对齐 gg-drama-library 的 `library.py` 与 stock-picking 的成交事件：工具锁内写入，禁止用编辑器直接改成功表。

## 工具

```bash
python3 scripts/ledger.py configure --project-root /绝对路径
python3 scripts/ledger.py status
python3 scripts/ledger.py validate
python3 scripts/ledger.py reconcile --sha256 <hash> [--aid <aid>] [--bvid <bvid>] [--cid <cid>] [--status <文本>]
python3 scripts/ledger.py record-exception --time <时间> --series <系列> --title <标题> --phenomenon <现象> --handling <处理>
```

`--config` 可另指配置。缺配置不扫描磁盘。

## 谁写哪一段

| 段落 | 写入方式 |
| --- | --- |
| `## 已发布作品` | 仅引擎 `append_video_ledger`。投稿成功后原子追加。同源 sha256/aid/bvid 已存在则跳过。 |
| 成功行里的 `待同步` | 仅 `reconcile`。用 sha256 或 aid/bvid 定位唯一行后更新 cid/状态。 |
| `## 专栏发布记录` | 专栏流程成功后由 Agent 按同格式追加；无 `dyn_id/rid` 不算完成。 |
| `## 删除/异常记录` | 仅 `record-exception`。用户删除、未确认投稿、串稿都记这里，不改成功行装成没发过。 |

没有投稿成功证据不得追加成功行。演练 `--stop-before-submit` 不得写台账。

## 去重

发布前同时查台账和后台稿件列表。匹配优先级：`aid/bvid/cid` > 源路径 > `sha256` > 标题。标题会改，不能单独当去重依据。

`possible_submit=true` 的旧运行不是成功记录；后台仍无目标稿时不得写成已发布。用户明确授权重发后另写新行，旧运行只留异常记录。

## 校验

`validate` 检查：

- 三个二级标题都在；
- 视频表头为固定 10 列；
- 成功表中未删除身份的 `sha256` / `aid` / `bvid` 不重复；
- 单元格里的身份字段带反引号。

校验失败不得继续依赖该台账投稿。

## 完成条件

- 视频：成功行含源文件、sha256、标题、aid/bvid；cid/合集/开放状态可暂为 `待同步`。
- 专栏：含正文源、分享卡、标题、dyn_id/rid、权限。
- 本条上传副本已从 `upload_copy_dir` 删除。
