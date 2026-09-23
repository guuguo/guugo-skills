# 视频数据快照与爆款依据

采集视频时同步尝试采集该发布条目的表现数据，视频和数据可来自不同可核对入口，但须匹配同一 platform + publication_id。无法获取不阻止保存可用视频；记录不可得原因，不能标成零或爆款。

## 采哪些数据

- 来源：平台、发布条目 ID、URL、账号 ID/名称、标题、发布时间、采集时间（带时区）、对应集数或合集范围。
- 公开表现：播放/观看、点赞、评论、收藏、分享；B 站投币、弹幕等平台特有指标原样单列，不冒充跨平台同义指标。
- 已有合法后台权限时：曝光、完播率、平均观看时长、跳出/留存、流量来源、新增关注等；标明统计窗口、指标定义、分母及单位。外部作品无后台权限就标不可得，不推算成真实数据。
- 已知账号背景：采集时粉丝数、同账号近期可比视频表现，记录来源和时间。真实观众画像仍独立保存，不与内容受众推断混用。
- 每项保留页面/API 原始展示值。诸如“1.2万”可保存近似值 12000，但 approximate=true，不能写成精确计数。

## 快照文件

`works/<work_id>/metrics/<publication_id>/<snapshot_id>.json`，只追加，不覆盖。以发布条目为单位，一集多平台/重发不合并；合集数据不分摊给其中单集或桥段。

必填：`schema_version:1, id, work_id, publication_id, platform, source_url, captured_at, published_at, episode_ids, metrics, evidence_paths`。id 和 publication_id 用稳定安全 ID；发布时间未知可为 null。episode_ids 为本作品已登记集数，合集列出覆盖集数，另记 scope=compilation。

`evidence_paths` 为库内相对或本地绝对路径，指向截图、页面摘录或 API 原始响应。页面摘录须含来源、采集时间和原始指标，不以 AI 摘要替代原始数值证据。

`metrics` 按指标名组织，每项为：

```json
{
  "value": 12000,
  "raw": "1.2万",
  "unit": "count",
  "status": "available",
  "approximate": true
}
```

status 为 available/unavailable/hidden/not_applicable；后三种 value=null、raw=null 或真实展示值，另写 reason。常用键 views/likes/comments/favorites/shares/coins/danmaku/impressions/completion_rate/avg_watch_seconds/followers；单位 count/percent/seconds，百分比按 0–100 表达。比率/时长加 window、definition，必要时 denominator。零须确为观察到的 0。

默认 metrics 至少有 views、likes、comments、favorites、shares，取不到的保留状态。不得凭其他互动量反推播放量。

执行：`python3 scripts/library.py record-metrics --input /绝对路径/快照.json`。脚本检查范围、数值、时间和证据存在，写入新快照；同 ID 已存在拒绝覆盖。后续重采使用新 ID，不因指标下降改掉历史记录。当前命令负责落盘，不是平台爬虫；实际采集由 Agent 调用现有来源工具。

## 怎样称为爆款

先核对内容/受众相似，再在同平台、可比内容形态、发布时间或发布后时长范围内比较；优先提供同作者近期可比样本，再按有数据的同赛道样本补充。给出比较样本链接或快照 ID、样本数、时间窗口、所用指标、分位/倍数/排名及计算方法。

没有统一适合所有平台的播放门槛，不硬编码“超过某数就是爆款”。只有绝对高播放而无可比基线时标“高播放参考，爆款程度待比较”；播放不可得但点赞高时准确说“高互动”，不替换口径。数据采集较早或与现在相隔较久时显示日期，不能声称实时表现。

爆款判断保存在查询结果的 performance_assessment 中，引用使用的快照与基线，不把主观布尔标签写成永久事实。用户指定阈值时注明“按用户筛选口径”。不把整条视频的表现归因于一个桥段、某个动作或某种受众标签；这些原因只作分析假设。

若库里没有“相似且有充分数据依据”的参考，直接报告缺口。可以补充相似但数据不足的真实案例，必须单列状态；不伪造案例或让用户先挑创作方向。
