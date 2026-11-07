import urllib.request
from PIL import Image

candidates = [
    # 柔和水彩纹理
    "https://images.unsplash.com/photo-1518895949257-7621c3c786d7?q=80&w=1280&auto=format&fit=crop",
    # 米色纸张纹理（极简）
    "https://images.unsplash.com/photo-1499195333224-3ce974eecb47?q=80&w=1280&auto=format&fit=crop",
    # 柔和粉彩渐变
    "https://images.unsplash.com/photo-1518066000714-58c45f1a2c0a?q=80&w=1280&auto=format&fit=crop",
    # 柔和光线/晨光
    "https://images.unsplash.com/photo-1470252649378-9c29740c9fa8?q=80&w=1280&auto=format&fit=crop",
    # 淡雅植物/绿叶柔光
    "https://images.unsplash.com/photo-1465146344425-f00d5f5c8f07?q=80&w=1280&auto=format&fit=crop",
    # 柔和奶油色织物
    "https://images.unsplash.com/photo-1524758631624-e2822e304c36?q=80&w=1280&auto=format&fit=crop",
]

def check(img):
    small = img.resize((50, 50))
    px = list(small.getdata())
    avg = tuple(sum(p[i] for p in px) // len(px) for i in range(3))
    bright = sum(avg) // 3
    sat = max(avg) - min(avg)  # 饱和度近似
    return avg, bright, sat

for url in candidates:
    name = url.split("?")[0].split("/")[-1]
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp, open("bg_warm.jpg", "wb") as f:
            f.write(resp.read())
        img = Image.open("bg_warm.jpg").convert("RGB")
        img.thumbnail((1280, 1280))
        img.save("bg_warm.jpg", quality=82)
        avg, bright, sat = check(img)
        ok = bright >= 160 and sat <= 70  # 明亮 + 柔和低饱和
        print(f"OK {name} size={img.size} avg=RGB{avg} bright={bright} sat={sat} pass={ok}")
        if ok:
            print("PASSED")
            break
    except Exception as e:
        print(f"FAIL {name}: {e}")