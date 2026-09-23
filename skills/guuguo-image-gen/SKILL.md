---
name: guuguo-image-gen
description: 通用 AI 生图素材与设计图生成偏好，也可按 guuguo_image_gen 触发。Use when generating or processing bitmap assets or design images for games, short videos, UI mockups, visual concepts, Cocos Creator, sprite sheets, transparent PNGs, chroma-key green/magenta backgrounds, cutout assets, animation frame sheets, nine-slice UI skins, report/PRD/technical visuals, or when the user asks for “生图规范 / 设计图 / 参考图生成 / 图生图 / 抠图 / 切图 / 素材接入 / 透明底 / 绿幕 / 品红幕 / 脏图去污染 / 灰度重建 / 干净母版 / sprite / Cocos meta”. In Codex, use $imagegen/image_gen directly; outside Codex or when image_gen is unavailable, delegate generation through the codex-guuguo alias.
---

# guuguo_image_gen

## 最小原则

真正生成或改造位图图片时，必须走真实生图后端。不要用 SVG、HTML/CSS、占位图或脚本假装完成 AI 生图；脚本只做确定性后处理。

## 生成后端选择

- 在 Codex 内，且 `$imagegen` 技能与 `image_gen` 工具可用时，必须使用 `$imagegen` 及其内置 `image_gen` 工具生成或编辑图片。
- 在 Codex 以外的客户端，或当前环境没有 `image_gen` 工具时，必须通过用户 shell 里的 `codex-guuguo` alias 委托 Codex 生成图片，不要自行改用其他模型或占位方案。
- `codex-guuguo` 是交互式 zsh alias；从脚本或非交互 shell 调用时使用 `zsh -lic 'codex-guuguo exec ...'`。
- 外部委托时，把本技能已整理好的用途、比例/尺寸、文案、禁止项、参考图角色、输出目录和需要读取的引用文档一起写进 prompt。需要传参考图文件时，使用 Codex CLI 的 `-i /path/to/image` 参数；多个参考图就重复 `-i`。
- ⚠️ **参数顺序坑**：`-i/--image <FILE>...` 是可变参数(variadic)，会贪婪吞掉其后所有 token。**PROMPT 必须放在 `-i` 之前**（即 `codex-guuguo exec [flags] -C "$PWD" "PROMPT" -i a.png -i b.png`）；若把 PROMPT 写在 `-i` 后面，它会被当成图片路径，Codex 收不到 prompt 转而读 stdin，报 `No prompt provided via stdin`。
- 委托生图建议加 `--dangerously-bypass-approvals-and-sandbox`（在已外部沙箱的环境），让 Codex 能联网生图、写文件、不卡审批确认。
- 外部委托命令默认使用当前项目目录作为工作目录，并要求 Codex 最终返回生成图片路径。示例：

```bash
# PROMPT 放在 flag 之后、-i 之前；参考图用 -i 追加在最末，多张重复 -i
zsh -lic 'codex-guuguo exec --dangerously-bypass-approvals-and-sandbox -C "$PWD" "使用 guuguo-image-gen 技能生成一张 16:9 汇报封面。请读取 references/design-images.md 的设计图规则，调用 image_gen 真实生图，输出到 docs/generated-assets/，最终只返回图片路径和必要说明。" -i ref1.png -i ref2.png'
```

- 如果 `codex-guuguo` 不存在或执行失败，明确告诉用户外部委托不可用；不要声称已经生成图片。Codex 后端偶发 `429 Too Many Requests` / `503 Service Unavailable`（生图限流或服务临时不可用），属服务端故障：如实告知并稍后重试，不要伪造产物或改用占位方案。

先按用途分类，再按需读取引用文档：

- 脏图去污染、连续参考后画面发灰发糊、需要恢复干净母版：读取 [clean-image-rebuild.md](references/clean-image-rebuild.md)。
- 设计图：UI mockup、玩法/场景概念图、风格探索图、宣发视觉、汇报图、PRD 图、技术方案图。读取 [design-images.md](references/design-images.md)。
- 运行时素材：单体素材、透明 PNG、UI 皮肤、全屏背景、序列帧、大图集、Cocos 可接入资源。读取 [runtime-assets.md](references/runtime-assets.md)。
- 抠图、切片、alpha 报告、Cocos meta：只在需要运行脚本时读取 [script-usage.md](references/script-usage.md)。
- 历史入口 [image-generation-rules.md](references/image-generation-rules.md) 仅作为索引；优先读取上面更具体的文档。

## 参考图规则

用户给到参考图、草图、截图、风格图、角色图、产品图或上一版生成图时，生成环节必须按实际后端的图像输入流程处理：

- 如果参考图已经在对话上下文中可见，直接标注为 `reference image`、`edit target` 或 `supporting input`。
- 如果在 Codex 内且参考图只是本地路径，先用 `view_image` 打开，让它进入上下文，再调用 `$imagegen`。
- 如果在外部客户端委托 `codex-guuguo`，不要只转述图片内容；把本地参考图路径通过 `-i` 传给 `codex-guuguo exec`，并在 prompt 里说明每张图的角色。
- 提示词必须说明每张图的角色，例如“图 1 作为风格参考，图 2 作为构图参考”。
- 不要只把参考图文字概括后做纯文生图。

## 省积分规则

生成完成后默认不调用 `view_image`、不主动回看生成结果、不做图像识别验收。默认只交付生成结果路径和必要说明。

素材类如需 alpha 报告、联系表或切片报告，可运行确定性脚本；这不等同于默认看图复核。

## 默认流程

1. 判断图片类型：设计图、运行时素材，或已有图片编辑。
2. 读取对应引用文档；脏图去污染任务先走 `clean-image-rebuild.md`，不要把普通编辑继续叠在脏底图上。
3. 收集用途、比例/尺寸、文案、禁止项，以及参考图角色。
4. 按“生成后端选择”调用 `$imagegen` 或通过 `codex-guuguo` 委托生成或编辑图片。
5. 如需后处理，再读取脚本文档并处理到项目资源目录。
6. 最终说明输出路径、是否使用参考图、每张参考图角色。

## 输出位置

不要把具体项目、角色或路径写死。每次按当前仓库规范选择输入输出；找不到项目规范时，默认把源图放 `docs/generated-assets/` 或 `assets/raw-sheets/`，运行时 PNG 放 `assets/resources/`。
