# 运行时素材生成规则

适用于单体素材、透明 PNG、UI 皮肤、全屏背景、序列帧、大图集、Cocos 可接入资源。非素材设计图不要加载本文件。

## 透明素材

需要透明 PNG 的单体、UI、道具、序列帧，优先让模型输出纯色绿幕或品红幕背景，再用脚本转 alpha。背景必须纯色、无阴影、无渐变、无地面反射，主体不能使用色键色。

绿幕提示词片段：

```text
Create the requested game asset on a perfectly flat solid #00ff00 chroma-key background.
The background must be one uniform color with no shadows, gradients, texture, reflections, floor plane, or lighting variation.
Keep the subject fully separated from the background with crisp edges and generous padding.
Do not use #00ff00 anywhere in the subject.
No cast shadow, no contact shadow, no reflection, no watermark, and no text unless explicitly requested.
```

品红幕提示词片段：

```text
Create the requested game asset on a perfectly flat solid #ff00ff chroma-key background.
The background must be one uniform color with no shadows, gradients, texture, reflections, floor plane, or lighting variation.
Keep the subject fully separated from the background with crisp edges and generous padding.
Do not use #ff00ff anywhere in the subject.
No cast shadow, no contact shadow, no reflection, no watermark, and no text unless explicitly requested.
```

## 序列帧 / 大图集

- 同一张图里每帧间隔充足，按从左到右、从上到下排列。
- 每帧主体大小、朝向、锚点尽量一致。
- 不要让特效跨帧粘连。
- 需要透明输出时，背景仍用统一绿幕或品红幕。

## UI 皮肤

按钮底、卡片底、面板底、进度条轨道/填充可以九宫格，但必须写合理边距。四角、描边、高光区域要有足够宽度，中心区域尽量平滑，避免拉伸时变形。

UI 皮肤默认不烘入会变化的文字、数值、状态、解锁文案；这些内容应由运行时渲染。

车辆、人物、建筑、图标、插画、背景禁止九宫格拉伸。

## macOS App 图标

macOS App 图标的生图源文件默认使用 `1024×1024` 正方形 PNG，并采用“全画布源图”方案：

- 视觉背景和主体必须铺满整个正方形画布，四角保持不透明；不要在源图内部预画圆角矩形、squircle、外框、底板或第二层 App 图标容器。
- 不要给整个图标留透明安全边、白边或大面积空白边距。macOS 会在 Launchpad、Dock 和 Finder 中自行施加系统形状与裁切；源图若已带一层圆角容器，会产生明显的“双层套娃框”。
- 核心符号放在画布中央安全区，建议占画布宽高的约 `45%–65%`；背景、纹理和光影可以延伸到画布边缘，但关键信息不要贴近边缘。
- 设计阶段保留 `1024×1024` 母版；接入时再确定性缩放并生成 `.iconset` / `.icns`。不要让生图模型直接伪造多尺寸图标集。
- 若项目明确要求透明菜单栏图标、状态栏模板图标或独立悬浮 glyph，不适用本规则；这类素材应单独生成透明 PNG/PDF，不要与 App 图标母版混用。

推荐提示词约束：

```text
Create a full-bleed 1024×1024 macOS app icon source image.
The artwork and background must extend to all four edges with opaque corners.
Do not draw a rounded-square app tile, squircle container, outer frame, transparent padding, white border, or nested icon plate.
Keep the primary symbol centered within a safe area; macOS will apply the final system mask.
No text, watermark, mockup, drop shadow outside the canvas, or device frame.
```

## 全屏背景

全屏背景可直接生成 9:16、16:9 或项目指定尺寸，不需要色键。提示词按用途明确是否需要“无 UI、无文字、无主角、中心留空或前景留空”，方便运行时叠加角色与控件。

## 后处理与接入

需要抠图、切片、alpha 报告、联系表或 Cocos meta 时，读取 [script-usage.md](script-usage.md) 并运行对应脚本。

临时草图、标注图、参考图、`.codex/generated_images/**` 不能直接接入运行时，必须复制或处理到项目资源目录。

默认不看图验收。素材后处理需要确定性报告时，输出联系表、alpha 报告或切片报告。
