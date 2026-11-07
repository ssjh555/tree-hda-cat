"""生成治愈系树洞猫咪头像 cat_avatar.png"""
from PIL import Image, ImageDraw

SIZE = 400
img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

# 背景圆：淡薄荷绿
d.ellipse([10, 10, SIZE - 10, SIZE - 10], fill=(232, 245, 238, 255))

cx, cy = SIZE // 2, SIZE // 2 + 20  # 脸部中心

# ---- 耳朵（先画，被脸盖住底部） ----
ear_color = (245, 200, 170, 255)   # 暖橘
ear_inner = (250, 220, 200, 255)   # 内耳浅粉
# 左耳
d.polygon([(cx - 110, cy - 60), (cx - 130, cy - 170), (cx - 40, cy - 120)], fill=ear_color)
d.polygon([(cx - 100, cy - 75), (cx - 115, cy - 150), (cx - 55, cy - 115)], fill=ear_inner)
# 右耳
d.polygon([(cx + 110, cy - 60), (cx + 130, cy - 170), (cx + 40, cy - 120)], fill=ear_color)
d.polygon([(cx + 100, cy - 75), (cx + 115, cy - 150), (cx + 55, cy - 115)], fill=ear_inner)

# ---- 脸：大圆，暖米橘色 ----
face_r = 130
d.ellipse([cx - face_r, cy - face_r, cx + face_r, cy + face_r], fill=(247, 222, 190, 255))

# ---- 腮红：两侧淡粉 ----
blush = (250, 200, 200, 160)
d.ellipse([cx - 110, cy + 10, cx - 60, cy + 45], fill=blush)
d.ellipse([cx + 60, cy + 10, cx + 110, cy + 45], fill=blush)

# ---- 眼睛：闭眼微笑弧线（治愈感） ----
eye_w, eye_h = 5, 5
eye_color = (90, 70, 60, 255)
# 左眼弧线
d.arc([cx - 75, cy - 40, cx - 25, cy + 5], start=20, end=160, fill=eye_color, width=eye_w)
# 右眼弧线
d.arc([cx + 25, cy - 40, cx + 75, cy + 5], start=20, end=160, fill=eye_color, width=eye_w)

# ---- 鼻子：小三角粉鼻 ----
nose_color = (230, 150, 150, 255)
d.polygon([(cx - 10, cy + 25), (cx + 10, cy + 25), (cx, cy + 40)], fill=nose_color)

# ---- 嘴：从鼻子向下的两条小弧线 ----
mouth_color = (180, 130, 110, 255)
d.arc([cx - 25, cy + 35, cx, cy + 60], start=0, end=90, fill=mouth_color, width=3)
d.arc([cx, cy + 35, cx + 25, cy + 60], start=90, end=180, fill=mouth_color, width=3)

# ---- 胡须：左右各三根 ----
whisker = (200, 180, 160, 220)
wl = [(-95, -15), (-95, 5), (-95, 25)]
for dy in [-15, 5, 25]:
    d.line([(cx - 80, cy + dy), (cx - 140, cy + dy - 8)], fill=whisker, width=3)
    d.line([(cx + 80, cy + dy), (cx + 140, cy + dy - 8)], fill=whisker, width=3)

# ---- 头顶小装饰：三片小叶子（薄荷绿呼应主题） ----
leaf = (160, 210, 180, 255)
d.polygon([(cx - 8, cy - 145), (cx - 30, cy - 185), (cx + 2, cy - 160)], fill=leaf)
d.polygon([(cx + 2, cy - 150), (cx + 25, cy - 190), (cx + 10, cy - 155)], fill=leaf)
d.polygon([(cx - 2, cy - 155), (cx - 5, cy - 200), (cx + 6, cy - 158)], fill=(140, 195, 165, 255))

img.save("cat_avatar.png")
print("已生成 cat_avatar.png")