# 执行结果

## 结论

已完成 `dreaminaq / dreamina-queue` 的 mock-first 治理实现：脚本默认只连接内置 mock CLI，不触达真实官方 CLI；真实提交继续由 `dreamina-scheduler App` 承担。自动测试、隔离烟测、App 历史状态只读抽样均已通过。

A12 的“至少 3 个真实 App 提交样本对比”已通过读取 `/Users/guodeqing/.dreamina-scheduler/state.json` 完成，覆盖远端排队中、生成中、生成成功三类样本。本次没有提交新的即梦任务，也没有消耗生成额度。

## 主要变更

- 默认 CLI 发现改为 `mock://dreamina`，真实 CLI 仅在显式 `DREAMINAQ_CLI_MODE=real` 或 `DREAMINAQ_USE_REAL_CLI=1` 时进入。
- 新增包内完整 mock CLI：覆盖 `version`、`user_credit`、`login`、`text2video`、`multimodal2video`、`query_result`。
- mock CLI 支持参数校验、模型/分辨率边界、素材数量边界、音频时长边界、fixture 状态流、确定性 submit_id、额度模拟、查询/下载成功失败模拟。
- 队列层保持缺省模型和 VIP 模型代码级拦截；即使误配真实 CLI，也会在提交前阻断。
- 默认 `fast_after_seconds = 0`，不再默认自动 Fast fallback。
- 新增 `dreaminaq status --summary-json`，输出中文决策摘要，任务名优先于 task_id/submit_id。
- 新增 `dreaminaq compare-app-state`，只读解析 `dreamina-scheduler App` 的 `state.json`，生成 mock/App 对照表。
- 更新 README、examples、CHANGELOG、`skills/dreamina-queue/SKILL.md`，明确脚本只做 mock 演练、真实提交走 App。
- 更新 `docs/mock-vs-app-comparison.md`，回填 3 类真实 App 历史样本，并明确下载文件非生成成功必要条件。

## 关键证据

- 代码：
  - `/Volumes/Seamless SSD/dev/ai_video/dreamina-queue/src/dreamina_queue/dreamina_cli.py`
  - `/Volumes/Seamless SSD/dev/ai_video/dreamina-queue/src/dreamina_queue/mock_cli.py`
  - `/Volumes/Seamless SSD/dev/ai_video/dreamina-queue/src/dreamina_queue/queue.py`
  - `/Volumes/Seamless SSD/dev/ai_video/dreamina-queue/src/dreamina_queue/scheduler.py`
  - `/Volumes/Seamless SSD/dev/ai_video/dreamina-queue/src/dreamina_queue/cli.py`
  - `/Volumes/Seamless SSD/dev/ai_video/dreamina-queue/src/dreamina_queue/app_compare.py`
- 测试：
  - `/Volumes/Seamless SSD/dev/ai_video/dreamina-queue/tests/test_mock_cli.py`
  - `/Volumes/Seamless SSD/dev/ai_video/dreamina-queue/tests/test_queue.py`
  - `/Volumes/Seamless SSD/dev/ai_video/dreamina-queue/tests/test_cli.py`
  - `/Volumes/Seamless SSD/dev/ai_video/dreamina-queue/tests/test_doctor.py`
  - `/Volumes/Seamless SSD/dev/ai_video/dreamina-queue/tests/test_app_compare.py`
- 文档：
  - `/Volumes/Seamless SSD/dev/ai_video/dreamina-queue/README.md`
  - `/Volumes/Seamless SSD/dev/ai_video/dreamina-queue/skills/dreamina-queue/SKILL.md`
  - `/Volumes/Seamless SSD/dev/ai_video/dreamina-queue/docs/mock-vs-app-comparison.md`

## 验证命令

```bash
python3 -m unittest discover -s '/Volumes/Seamless SSD/dev/ai_video/dreamina-queue/tests'
```

结果：

```text
Ran 60 tests in 0.726s
OK
```

隔离烟测：

```bash
tmp_home=$(mktemp -d)
export DREAMINAQ_HOME="$tmp_home" HOME="$tmp_home"
python3 -m dreamina_queue.cli doctor --json
python3 -m dreamina_queue.cli submit --command text2video --prompt 'mock smoke test' --model_version seedance2.0 --ratio 9:16 --duration 5 --idempotency-key 'mock/smoke/scene-01' --json
python3 -m dreamina_queue.cli once --json
python3 -m dreamina_queue.cli status --summary-json
rm -rf "$tmp_home"
```

关键输出：

- `dreamina_cli.mode = mock`
- `dreamina_cli.path = mock://dreamina`
- `submitted.lane = standard`
- `summary.tasks[0].任务名 = mock/smoke/scene-01`
- `summary.tasks[0].阶段 = 已完成`
- `summary.tasks[0].远端状态 = 远端完成`

App 历史状态只读抽样：

```bash
python3 -m dreamina_queue.cli compare-app-state --app-state "$HOME/.dreamina-scheduler/state.json" --json
```

关键输出：

- `ok = true`
- `samples.queued.task_title = 猫猫试菜笑翻全场`
- `samples.generating.task_title = 老板的五一加班套路`
- `samples.success.task_title = 猫猫试菜笑翻全场`

## A12 结论

已建立并回填 `/Volumes/Seamless SSD/dev/ai_video/dreamina-queue/docs/mock-vs-app-comparison.md`。

当前样本均来自 `dreamina-scheduler App` 的真实历史提交观察；本次没有提交任何真实即梦任务。后续如果 App 状态语义或真实错误形态变化，继续用 `compare-app-state` 补样本，并把差异反哺到 mock fixture/tests。
