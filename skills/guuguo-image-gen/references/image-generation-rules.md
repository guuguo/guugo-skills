# 生图规则索引

这是历史兼容入口。优先按图片类型读取更具体的引用文档：

- 设计图、UI mockup、概念图、汇报图、PRD 图、技术方案图：读取 [design-images.md](design-images.md)。
- 脏图去污染、灰度结构重建、恢复干净彩色母版：读取 [clean-image-rebuild.md](clean-image-rebuild.md)。
- 运行时素材、透明 PNG、UI 皮肤、序列帧、大图集、Cocos 资源：读取 [runtime-assets.md](runtime-assets.md)。
- 抠图、切片、alpha 报告、Cocos meta：读取 [script-usage.md](script-usage.md)。

生成后默认不看图、不做图像识别验收。
