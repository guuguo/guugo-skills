# 素材数据契约 v1

所有 JSON 使用 UTF-8。顶层分析对象带 `schema_version: 1`。路径写库内相对路径；现有原媒体和外部证据允许绝对路径引用，不复制原文件。稳定 ID 用字母、数字、下划线和连字符；标题保留中文。

## 目录与真源

```text
<library_root>/
  works/<work_id>/
    work.json
    episodes/<episode_id>.json
    cases/<case_id>.json
    arcs/<arc_id>.json
    metrics/<publication_id>/<snapshot_id>.json
    evidence/<episode_id>/<analysis-run>/
  vocabulary.json
  index/cases.jsonl
  projects/<project_id>/
    profile.json
    queries/<query_id>.json
    adaptations/<query_id>.md
```

JSON 是事实与分析的持久真源，阅读时由 Agent 展开为完整中文桥段；不要另维护内容不同步的桥段 Markdown 副本。索引可删除重建。人物对白属于证据引用，不批量复制无关完整作品文本。

视频表现快照字段及采集规则见 [数据快照与爆款依据](performance-data.md)。index/cases.jsonl 是供 Harness 浏览的全量目录，包含路径、触发、互动回合、标签、状态、受众及相关发布条目最新快照，不做查询匹配、排名或截断。选择依靠 Harness 阅读完整真源；保留全部数据历史，不把视频数据当桥段独立表现。

## 通用证据与分析记录

范围对象：`{episode_id, start, end, evidence_path, role}`，单位为原片播放秒数，`0 <= start < end <= duration`。`role` 可为 core/context/setup/payoff；时间须来自该版本，不能混用合集版与分集版。

主张对象：`{text, basis, evidence_refs, uncertainty}`。`basis` 为 observed/explicit/inferred/unknown，证据引用指向范围及帧、ASR segment 或观察项 ID；推断记录依据和其他可能解释。声线编号不自动等于角色 ID。

每个分析对象保留 `analysis: {created_at, model, method_version, evidence_paths, limitations}`。模型不提供精确版本时写实际可知名称或 unknown，不编版本。已有记录修订保留变更原因和旧分析快照，不重跑未变媒体。

## 作品 work.json

必填：`schema_version, id, title, sources, coverage`。

- `sources[]`：来源链接或本地入口、平台、作者、获取日期、版本、类型（正片/合集/试看/预告/解说/评论）、实际获取状态。另记已知处理许可及限制；未知单列。
- `coverage`：`status` 为 partial/complete；`expected_episode_ids`、`collected_episode_ids`、`missing_episode_ids`；完结未知写 `series_finished: null`。complete 指声明范围完整，不等于作品已完结。
- `characters[]`：角色 ID、别名、行为证据，身份不确定保留未知。
- `content_profile`、`audience`：从已分析单集汇总的内容/受众分类，注明覆盖集数和分歧。用内容适配推断，不冒充真实观众统计。

## 单集 episodes/<id>.json

必填：`schema_version, id, work_id, title, duration, evidence_path, events, tracks, state_ledger`。

- `evidence_path` 指向 gg-video-analysis 的 `manifest.json`；duration 对齐该媒体版本。另记发布序号、版本 ID、材料类型与证据覆盖范围。
- `events[]`：`id, ranges[], actor, action, recipient, result, basis`。按原片呈现顺序写可核对事件，在 action 中保留具体场景、对白及说话人、动作与可见反应；铺垫、转场和结果不能压成同一个结局摘要。未知主体或结果明确写未知。闪回标 `story_time` 与 `replays_event_id`；未知故事时间保留 null。
- `tracks[]`：`subject, dimension, nodes[]`。节点记录 `event_id, time, before, after, basis, evidence_refs`。四类轨道分别是角色情绪、A→B 的关系、预期观众体验、剧情状态。
- `state_ledger`：每个角色当前所知/所信/误解、观众所知、关系状态、承诺、物件归属、开放问题；分别保存当集视角与后见解释。
- `coverage`：已查看接触表页、密集复核范围、音频是否直接听审、未观察区域；ASR 覆盖全音轨不等于已完整听审。
- `content_profile`、`audience`：保存 gg-video-analysis 的分类对象及依据，观察 ID 通过本集 evidence_path 定位；新做的完整分析均填写，旧数据缺失视为未分类。真实观众数据另存 audience_metrics，含来源、日期和统计范围。

情绪优先用有证据的状态变化。需要数值曲线时，先为每维定义量表及锚点；unknown 用 null。平滑绘图不能新增证据。

## 桥段 cases/<id>.json

必填：`schema_version, id, work_id, title, status, core_ranges, context_ranges, entry_state, trigger, beats, exit_state, mechanism, prerequisites, tags, analysis`。

- `status` 为 usable/partial/disputed/insufficient；只把 usable 默认作为直接参考，其他结果显示限制。
- `core_ranges[]` 与 `context_ranges[]` 均为范围对象，可跨集；理解范围不能凭固定前后五秒替代叙事判断。
- `entry_state/exit_state` 分别记录事情、角色认知和双向关系；不能省成“更甜”。
- `beats[]` 至少包含一个可读回合：`id, action, response, result, evidence_refs, basis`，按实际过程保留铺垫、互动、转接与后果；不存在的回应不补造。目标、感知、主动权与代价仅在有依据时分析，不能与可见行动混成事实。`evidence_refs` 使用 `core:0` 或 `context:0` 这样的范围引用（零基下标）；具体帧/ASR/观察项 ID 放该范围的可选 `anchors` 字段，语义与锚点由 Agent 回查。允许过程停在明确未完成状态。
- `beats` 的粒度按 [完整过程与呼吸节奏](ingest-analysis.md#完整过程与呼吸节奏) 判断：生活动作、无对白反应或等待也可独立成拍；场景、动作与对白先后写入 action，实际反应与停留写入 response，后果及转接写入 result，不存在的项明确写无或未观察。引用须定位到本拍对应的 core/context 子范围，无法精确定位时记录已知范围及限制；不能所有拍仅引用整集而声称逐拍已核实。无需另建一套逐镜脚本字段。
- events/每拍的 action 中逐句标明说话人、采用对白、可确定的听话对象、声音类型及同期画面，response 对应可见回应；使用角色 ID 或已确认称呼，未知单独标注。沿用原观察的证据引用与时间精度，不能只复制字幕而丢失声画对应，也不能将同场不同人的台词统一归给 actor。没有观察到与确认没有发生须区分。
- `mechanism`：仅为兼容现有存储与索引保留；新采集写 `{}`。不再要求生成 summary、essential_beats、replaceable_surface 等抽象机制或替换建议。旧记录不自动删除或重写；历史机制不作为原作事实，引用前须回到事件与证据。
- `prerequisites`：记录原作实际发生的必要前情、当时关系、知识和资源；因果依赖未确认时标推断或未知，不以“理解上一集”替代具体事实。新采集不填写用于创作适配的 `incompatible`，适配与改造判断留在项目查询记录。
- `tags`：对象，维度包括 form/genre/function/relationship/behavior/emotion/rhythm/production/audience，各值为字符串数组。
- `audience`：该桥段的核心/次级受众、兴趣、情绪需求、年龄/人生阶段、观看场景、定位和不适配偏好，沿用视频分析分类结构；依据用本桥段范围引用，并保留对应单集的观察引用。按桥段本身判断，不盲目继承整剧定位。未知或旧记录未分析可不填；新分析需给出判断或 unknown 原因。
- `production`：记录原片时长、在场人数、场景及实际动作/对白顺序；复杂度判断须有依据。新采集不写改造时长或制作建议。
- `connections[]`：关联事件/桥段/阶段及 explicit_cause/necessary_condition/echo/possible_relation 类型、依据。不能把时间接近当因果。

## 全剧阶段 arcs/<id>.json

必填：`schema_version, id, work_id, title, coverage, entry_state, question, case_ids, turning_points, exit_state, open_questions`。

保存剧情线与感情线各自的目标、阻力、信息、代价和人物选择；阶段边界依据状态改变，不能平均按集数分段。`coverage` 说明涉及哪些集、是否缺集、结论范围；未完结作品只标“截至已收集范围”。关键转折绑定桥段和事件。

## 词表与项目资料

`vocabulary.json`：`schema_version`、`tags[]`；每项包含 ID、维度、定义、别名、正反例与 candidate/active 状态。先阅读现有标签定义，确认概念差异后再增加候选标签；标签服务资料组织，一次反馈不自动变成通用规则。

`profile.json`：项目真源引用及读取日期、人物行为原则、当前关系/知识状态、目标状态、目标受众、硬条件、软偏好、制作约束。缺资料写 unknown，不把某一项目偏好固化成技能规则。

`queries/<id>.json`：原需求、解析与假设、搜索路径与实际阅读范围、候选 case ID、每条语义相似处/差异/证据/缺口、选中结果及反馈。探索记录以阅读过的作品、桥段、关联线索和具体判断依据为主。拒绝原因区分“不喜欢”“人物不适合”“制作不可行”。创意发散写 `ideas[]`，每项记录 `id, reference_case_ids, premise, interaction, appeal, assumptions, user_feedback`；无真实参考时 reference_case_ids 为空，明确标纯 AI 构思。user_feedback 只记实际反馈，表示有兴趣不等于人已定稿。

AI 灵感与原作事实独立存储。已有 adaptations 可继续保留，仅在用户另行要求完整改造时写新稿；不为本轮灵感需求自动生成改稿、推进既定剧情或覆盖项目正式脚本。

跨集迁移与组合的 ideas，reference_case_ids 可一对多或多对一；在 interaction/assumptions 中写借用的具体回合、原作依赖、目标场景新建的理由与因果衔接，不增加新的索引或匹配算法。旧案例分析过粗时仅在本轮提案注明证据限制；未经实际复核，不批量重写原作记录。
