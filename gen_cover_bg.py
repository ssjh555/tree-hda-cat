"""生成首页全屏背景图 cover_bg.png —— 树洞猫咪主题场景
画面：晨曦柔光渐变天空 + 右侧大树（树洞里坐着一只小猫）+ 梦幻光斑 + 飘落花瓣
配色与聊天页统一：暖米/柔粉/淡紫/薄荷绿治愈系
"""
from PIL import Image, ImageDraw, ImageFilter
import random
import math

W, H = 1920, 1080
random.seed(2026)

# ====== 1. 晨曦渐变天空：顶部暖米 → 中段柔粉 → 底部薄荷绿 ======
img = Image.new("RGB", (W, H))
d = ImageDraw.Draw(img)
stops = [
    (0.00, (250, 246, 238)),   # 暖米 #FAF6EE
    (0.30, (248, 238, 232)),   # 柔杏
    (0.55, (244, 228, 230)),   # 淡粉 #F4E4E6
    (0.78, (234, 240, 236)),   # 淡绿
    (1.00, (228, 244, 236)),   # 薄荷绿 #E4F4EC
]
for y in range(H):
    t = y / H
    for i in range(len(stops) - 1):
        t0, c0 = stops[i]
        t1, c1 = stops[i + 1]
        if t0 <= t <= t1:
            k = (t - t0) / (t1 - t0) if t1 > t0 else 0
            r = int(c0[0] + (c1[0] - c0[0]) * k)
            g = int(c0[1] + (c1[1] - c0[1]) * k)
            b = int(c0[2] + (c1[2] - c0[2]) * k)
            d.line([(0, y), (W, y)], fill=(r, g, b))
            break

# ====== 2. 柔光晕染圆斑（水彩感） ======
blobs = [
    (300, 200, 420, (255, 250, 240, 42)),
    (1500, 180, 380, (245, 225, 240, 35)),
    (960, 500, 500, (255, 245, 235, 25)),
    (1700, 700, 400, (240, 235, 250, 30)),
    (200, 800, 380, (235, 245, 240, 32)),
]
for cx, cy, r, color in blobs:
    blob = Image.new("RGBA", (r * 2, r * 2), (0, 0, 0, 0))
    ImageDraw.Draw(blob).ellipse([0, 0, r * 2, r * 2], fill=color)
    blob = blob.filter(ImageFilter.GaussianBlur(100))
    img.paste(blob, (cx - r, cy - r), blob)

# ====== 3. 大树（右侧，树干+树洞+树冠） ======
tree = Image.new("RGBA", (W, H), (0, 0, 0, 0))
td = ImageDraw.Draw(tree)
TX = 1520  # 树干中心X
trunk_color = (150, 125, 145, 38)  # 柔紫棕，低透明度
td.polygon([(TX - 55, 1080), (TX - 42, 600), (TX - 35, 400), (TX - 28, 260),
            (TX + 28, 260), (TX + 35, 400), (TX + 42, 600), (TX + 55, 1080)],
           fill=trunk_color)
# 树枝
td.line([(TX - 10, 420), (TX - 130, 330), (TX - 190, 290)], fill=trunk_color, width=18)
td.line([(TX + 10, 380), (TX + 120, 300), (TX + 170, 270)], fill=trunk_color, width=16)
td.line([(TX, 300), (TX - 60, 200), (TX - 80, 160)], fill=trunk_color, width=14)
td.line([(TX, 280), (TX + 70, 190), (TX + 90, 150)], fill=trunk_color, width=13)

# 树洞：椭圆暗口（猫咪的家）
hole_cx, hole_cy = TX - 5, 560
td.ellipse([hole_cx - 52, hole_cy - 65, hole_cx + 52, hole_cy + 65],
           fill=(90, 70, 100, 55))
td.ellipse([hole_cx - 44, hole_cy - 56, hole_cx + 44, hole_cy + 56],
           fill=(70, 52, 82, 60))

# ====== 4. 树洞里的小猫剪影 ======
cat = Image.new("RGBA", (W, H), (0, 0, 0, 0))
cd = ImageDraw.Draw(cat)
ccx, ccy = hole_cx, hole_cy + 8
cat_color = (45, 35, 55, 150)  # 深紫灰，清晰但不刺眼
# 身体：蜷缩椭圆
cd.ellipse([ccx - 30, ccy - 12, ccx + 30, ccy + 32], fill=cat_color)
# 头：圆
cd.ellipse([ccx - 18, ccy - 38, ccx + 18, ccy - 6], fill=cat_color)
# 左耳
cd.polygon([(ccx - 17, ccy - 32), (ccx - 13, ccy - 48), (ccx - 6, ccy - 36)], fill=cat_color)
# 右耳
cd.polygon([(ccx + 6, ccy - 36), (ccx + 13, ccy - 48), (ccx + 17, ccy - 32)], fill=cat_color)
# 尾巴：绕身体的弧线
cd.arc([ccx + 18, ccy + 5, ccx + 52, ccy + 42], start=90, end=270, fill=cat_color, width=9)
# 猫眼：两个小亮点
cd.ellipse([ccx - 10, ccy - 26, ccx - 6, ccy - 21], fill=(255, 240, 180, 200))
cd.ellipse([ccx + 6, ccy - 26, ccx + 10, ccy - 21], fill=(255, 240, 180, 200))
cat = cat.filter(ImageFilter.GaussianBlur(1.5))
tree = Image.alpha_composite(tree, cat)

# ====== 5. 树冠：多层柔色圆团 ======
canopy_colors = [
    (170, 190, 165, 32),  # 柔绿
    (185, 175, 200, 28),  # 柔紫
    (200, 180, 175, 25),  # 柔粉棕
    (175, 195, 180, 30),  # 薄荷
]
canopy_blobs = [
    (TX, 180, 260), (TX - 180, 240, 200), (TX + 170, 230, 210),
    (TX - 100, 120, 180), (TX + 100, 130, 190), (TX - 240, 160, 150),
    (TX + 240, 170, 160), (TX - 60, 60, 140), (TX + 60, 70, 150),
    (TX - 300, 280, 120), (TX + 300, 290, 130),
]
for i, (cx, cy, r) in enumerate(canopy_blobs):
    color = canopy_colors[i % len(canopy_colors)]
    c = Image.new("RGBA", (r * 2, r * 2), (0, 0, 0, 0))
    ImageDraw.Draw(c).ellipse([0, 0, r * 2, r * 2], fill=color)
    c = c.filter(ImageFilter.GaussianBlur(45))
    tree.paste(c, (cx - r, cy - r), c)

tree = tree.filter(ImageFilter.GaussianBlur(2))
img = Image.alpha_composite(img.convert("RGBA"), tree)

# ====== 6. 梦幻光斑（bokeh） ======
bokeh_colors = [(255, 250, 235), (255, 235, 220), (240, 230, 250), (230, 245, 235)]
for _ in range(35):
    x = random.randint(50, W - 50)
    y = random.randint(50, H - 150)
    r = random.randint(12, 45)
    color = random.choice(bokeh_colors)
    alpha = random.randint(18, 50)
    b = Image.new("RGBA", (r * 2, r * 2), (0, 0, 0, 0))
    bd = ImageDraw.Draw(b)
    bd.ellipse([r // 3, r // 3, r * 2 - r // 3, r * 2 - r // 3],
               fill=(color[0], color[1], color[2], alpha))
    b = b.filter(ImageFilter.GaussianBlur(r // 4))
    img.paste(b, (x - r, y - r), b)

# ====== 7. 飘落花瓣/叶片 ======
petal_colors = [(230, 180, 190, 60), (200, 215, 190, 55), (220, 195, 210, 50)]
for _ in range(25):
    x = random.randint(100, W - 100)
    y = random.randint(80, H - 200)
    size = random.randint(6, 14)
    color = random.choice(petal_colors)
    p = Image.new("RGBA", (size * 4, size * 4), (0, 0, 0, 0))
    pd = ImageDraw.Draw(p)
    ang = random.uniform(0, math.pi)
    pd.ellipse([size, size // 2, size * 3, size * 2 + size // 2], fill=color)
    p = p.rotate(math.degrees(ang), expand=True)
    p = p.filter(ImageFilter.GaussianBlur(1))
    img.paste(p, (x, y), p)

# ====== 8. 底部草地柔影 ======
ground = Image.new("RGBA", (W, 200), (0, 0, 0, 0))
gd = ImageDraw.Draw(ground)
gd.ellipse([-200, 60, W + 200, 320], fill=(200, 220, 200, 25))
ground = ground.filter(ImageFilter.GaussianBlur(40))
img.paste(ground, (0, H - 200), ground)

# ====== 9. 顶部柔光（晨曦感） ======
light = Image.new("RGBA", (W, H), (0, 0, 0, 0))
ld = ImageDraw.Draw(light)
ld.polygon([(0, 0), (W // 2, 0), (W // 4, H // 2), (0, H // 3)], fill=(255, 250, 235, 18))
light = light.filter(ImageFilter.GaussianBlur(120))
img = Image.alpha_composite(img, light)

# ====== 10. 整体柔化 + 极淡白纱（保证文字可读） ======
img = img.filter(ImageFilter.GaussianBlur(1.0))
veil = Image.new("RGBA", (W, H), (255, 255, 255, 22))
img = Image.alpha_composite(img, veil)

img = img.convert("RGB")
img.save("cover_bg.png", "PNG", quality=95)
print("COVER_BG_OK size:", img.size)