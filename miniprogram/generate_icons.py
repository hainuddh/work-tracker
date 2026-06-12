#!/usr/bin/env python3
"""生成小程序 tabBar 图标（24x24 像素，64x64 用于更清晰）"""
from PIL import Image, ImageDraw, ImageFont
import os

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "icons")
os.makedirs(OUTPUT_DIR, exist_ok=True)

SIZE = 64  # 图标尺寸
COLOR_NORMAL = (153, 153, 153)     # #999999 灰色
COLOR_ACTIVE = (68, 114, 196)      # #4472C4 蓝色

# 每个 tab 的图标内容: (文件名前缀, 描述, 绘图函数)
ICONS = [
    ("home", "房子/首页", lambda d, s: _draw_house(d, s)),
    ("people", "人头/老板", lambda d, s: _draw_people(d, s)),
    ("note", "笔记本/日志", lambda d, s: _draw_note(d, s)),
    ("chart", "图表/统计", lambda d, s: _draw_chart(d, s)),
]


def _draw_house(d: ImageDraw, s: int):
    # 简单房子图标
    cx, cy = s // 2, s // 2
    r = s * 0.35
    # 屋顶
    d.polygon([(cx, cy - r), (cx - r * 1.2, cy - r * 0.1), (cx + r * 1.2, cy - r * 0.1)], outline="black", width=3)
    # 屋身
    d.rectangle([cx - r, cy - r * 0.1, cx + r, cy + r * 0.8], outline="black", width=3)
    # 门
    d.rectangle([cx - r * 0.25, cy + r * 0.1, cx + r * 0.25, cy + r * 0.8], outline="black", width=2)


def _draw_people(d: ImageDraw, s: int):
    cx, cy = s // 2, s // 2
    r = s * 0.15
    # 头
    d.ellipse([cx - r, cy - r * 1.5, cx + r, cy - r * 0.3], outline="black", width=3)
    # 身体
    d.arc([cx - r * 1.5, cy - r * 0.2, cx + r * 1.5, cy + r * 1.5], 0, 180, fill="black", width=3)
    # 小臂
    d.line([(cx - r * 1.5, cy + r * 0.3), (cx - r * 2, cy + r * 0.8)], fill="black", width=2)
    d.line([(cx + r * 1.5, cy + r * 0.3), (cx + r * 2, cy + r * 0.8)], fill="black", width=2)


def _draw_note(d: ImageDraw, s: int):
    cx, cy = s // 2, s // 2
    w, h = s * 0.4, s * 0.5
    # 本子
    d.rectangle([cx - w, cy - h, cx + w, cy + h], outline="black", width=3)
    # 横线
    for i in range(3):
        y = cy - h * 0.4 + i * h * 0.4
        d.line([(cx - w * 0.8, y), (cx + w * 0.8, y)], fill="black", width=2)


def _draw_chart(d: ImageDraw, s: int):
    cx, cy = s // 2, s // 2
    w, h = s * 0.45, s * 0.4
    # 坐标轴
    d.line([(cx - w, cy + h), (cx - w, cy - h), (cx + w, cy - h)], fill="black", width=3)
    # 柱状图
    bar_w = s * 0.08
    heights = [h * 0.4, h * 0.7, h * 0.5, h * 0.9]
    for i, bh in enumerate(heights):
        x = cx - w + i * (w * 2 / 4) + w * 0.05
        d.rectangle([x, cy + h - bh, x + bar_w, cy + h], outline="black", width=2)


# 生成所有图标
for prefix, desc, draw_fn in ICONS:
    for color, suffix in [(COLOR_NORMAL, ""), (COLOR_ACTIVE, "-active")]:
        img = Image.new("RGBA", (SIZE, SIZE), (*color, 0))
        draw = ImageDraw.Draw(img)
        draw_fn(draw, SIZE)
        # 转为 RGB（小程序不需要 alpha）
        rgb = Image.new("RGB", (SIZE, SIZE), (255, 255, 255))
        rgb.paste(img, mask=img.split()[3])
        out_path = os.path.join(OUTPUT_DIR, f"{prefix}{suffix}.png")
        rgb.save(out_path, "PNG")
        print(f"Generated: {out_path}")

print("Done!")
