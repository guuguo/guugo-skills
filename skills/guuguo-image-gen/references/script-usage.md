# 脚本用法

只在运行时素材需要抠图、切片、alpha 报告、联系表或 Cocos meta 时读取本文件。非素材设计图通常不需要这些脚本。

所有脚本都在技能目录的 `scripts/` 下，默认依赖 Python 3 和 Pillow。若缺 Pillow，先在当前环境安装：

```bash
python3 -m pip install Pillow
```

## 绿幕/品红幕抠图

单体输出：

```bash
python3 scripts/cutout_assets.py \
  --input source.png \
  --output asset.png \
  --key auto \
  --trim \
  --padding 12 \
  --meta cocos
```

自动拆多个连通素材：

```bash
python3 scripts/cutout_assets.py \
  --input sheet.png \
  --output-dir assets_out \
  --split components \
  --key green \
  --prefix icon \
  --target-size 256x256 \
  --contact-sheet assets_out/contact-sheet.png \
  --meta cocos
```

## 已知坐标切图

单张坐标：

```bash
python3 scripts/slice_sprites.py \
  --input sheet.png \
  --output icon.png \
  --box 64,48,500,540 \
  --target-size 256x256 \
  --padding 12 \
  --meta cocos
```

批量 JSON：

```json
[
  {"input":"sheet.png","output":"ui/icon_flower.png","box":[64,48,500,540],"target_size":"256x256","padding":12},
  {"input":"sheet.png","output":"ui/icon_shield.png","box":[548,60,1010,560],"target_size":"256x256","padding":12}
]
```

```bash
python3 scripts/slice_sprites.py --spec slices.json --base-dir . --meta cocos
```

## Alpha 报告（按需）

```bash
python3 scripts/alpha_report.py assets_out --key green --json alpha-report.json
```

需要确定性复核时，重点看 `corner_alpha_ok`、`possible_key_pixels`、`alpha_bbox`。默认不要再额外调用看图工具做图像识别验收。
