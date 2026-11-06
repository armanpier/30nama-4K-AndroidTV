import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import arabic_reshaper
from bidi.algorithm import get_display

branding_dir = "branding_assets"
os.makedirs(branding_dir, exist_ok=True)

FONT_BOLD = r"C:\Windows\Fonts\arialbd.ttf"
FONT_REGULAR = r"C:\Windows\Fonts\arial.ttf"

def reshape_fa(text):
    return get_display(arabic_reshaper.reshape(text))

# -------------------------------------------------------------
# 1. Android TV Leanback Banner (320x180, RGB)
# -------------------------------------------------------------
bw, bh = 320, 180
b_im = Image.new("RGB", (bw, bh), (10, 14, 22))
b_draw = ImageDraw.Draw(b_im)

# Horizontal subtle gradient
for x in range(bw):
    t = x / float(bw)
    r = int(12 * (1 - t) + 24 * t)
    g = int(16 * (1 - t) + 32 * t)
    b = int(26 * (1 - t) + 48 * t)
    b_draw.line([(x, 0), (x, bh)], fill=(r, g, b))

# Gold glow on left
glow = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
g_draw = ImageDraw.Draw(glow)
g_draw.ellipse([-40, 20, 140, 160], fill=(245, 197, 24, 60))
glow = glow.filter(ImageFilter.GaussianBlur(30))
b_im.paste(glow.convert("RGB"), (0, 0), glow)
b_draw = ImageDraw.Draw(b_im)

# Gold logo circle on left
cx, cy = 60, 90
b_draw.ellipse([cx - 40, cy - 40, cx + 40, cy + 40], outline=(245, 197, 24, 255), width=3)
b_draw.ellipse([cx - 36, cy - 36, cx + 36, cy + 36], fill=(16, 22, 34))
f_badge = ImageFont.truetype(FONT_BOLD, 22)
b_draw.text((cx, cy - 8), "30", font=f_badge, fill=(245, 197, 24, 255), anchor="mm")
f_badge_sub = ImageFont.truetype(FONT_BOLD, 12)
b_draw.text((cx, cy + 12), "NAMA", font=f_badge_sub, fill=(255, 255, 255, 230), anchor="mm")

# Title on right
f_title = ImageFont.truetype(FONT_BOLD, 36)
b_draw.text((120, 60), "30NAMA", font=f_title, fill=(245, 197, 24, 255), anchor="lm")

# 4K ULTRA HD pill
b_draw.rounded_rectangle([120, 95, 225, 120], radius=5, fill=(245, 197, 24, 255))
f_pill = ImageFont.truetype(FONT_BOLD, 14)
b_draw.text((172, 107), "4K ULTRA HD", font=f_pill, fill=(10, 14, 22, 255), anchor="mm")

# Android TV label
f_sub = ImageFont.truetype(FONT_REGULAR, 13)
b_draw.text((122, 140), "Android TV Edition", font=f_sub, fill=(180, 195, 215, 220), anchor="lm")

# Thin outer gold border
b_draw.rectangle([0, 0, bw - 1, bh - 1], outline=(245, 197, 24, 180), width=1)

banner_path = os.path.join(branding_dir, "banner_320x180.png")
b_im.save(banner_path, "PNG")
print(f"Generated Banner: {banner_path} ({b_im.size})")

# -------------------------------------------------------------
# 2. Splash Screen (1920x1080, JPEG)
# -------------------------------------------------------------
sw, sh = 1920, 1080
s_im = Image.new("RGB", (sw, sh), (10, 14, 22))
s_draw = ImageDraw.Draw(s_im)

for y in range(sh):
    t = y / float(sh)
    r = int(10 * (1 - t * 0.4))
    g = int(14 * (1 - t * 0.3) + 4 * t)
    b = int(22 * (1 - t * 0.2) + 8 * t)
    s_draw.line([(0, y), (sw, y)], fill=(r, g, b))

# Center 30NAMA logo
scx, scy = sw // 2, sh // 2 - 50

# Subtle golden aura
s_glow = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
sg_draw = ImageDraw.Draw(s_glow)
sg_draw.ellipse([scx - 300, scy - 300, scx + 300, scy + 300], fill=(245, 197, 24, 30))
s_glow = s_glow.filter(ImageFilter.GaussianBlur(80))
s_im.paste(s_glow.convert("RGB"), (0, 0), s_glow)
s_draw = ImageDraw.Draw(s_im)

f_splash_logo = ImageFont.truetype(FONT_BOLD, 120)
s_draw.text((scx, scy), "30NAMA", font=f_splash_logo, fill=(245, 197, 24, 255), anchor="mm")

# 4K ULTRA HD Badge
s_draw.rounded_rectangle([scx - 140, scy + 90, scx + 140, scy + 145], radius=12, fill=(245, 197, 24, 255))
f_splash_4k = ImageFont.truetype(FONT_BOLD, 32)
s_draw.text((scx, scy + 117), "4K ULTRA HD", font=f_splash_4k, fill=(10, 14, 22, 255), anchor="mm")

# Persian Tagline
f_splash_fa = ImageFont.truetype(FONT_BOLD, 34)
s_draw.text((scx, scy + 200), reshape_fa("سینما در خانه شما"), font=f_splash_fa, fill=(220, 230, 245, 230), anchor="mm")

splash_path = os.path.join(branding_dir, "splash_1920x1080.jpg")
s_im.save(splash_path, "JPEG", quality=92)
print(f"Generated Splash: {splash_path} ({s_im.size})")

# -------------------------------------------------------------
# 3. App Icons (OK=36, 8X=48, Dw=72, M2=96, Gd=144, 5p=192)
# -------------------------------------------------------------
base_icon_path = r"plugin.video.30nama\icon.png"
base_icon = Image.open(base_icon_path).convert("RGBA")

icon_sizes = {
    "OK.png": (36, 36),
    "8X.png": (48, 48),
    "Dw.png": (72, 72),
    "M2.png": (96, 96),
    "Gd.png": (144, 144),
    "5p.png": (192, 192),
}

for name, size in icon_sizes.items():
    resized = base_icon.resize(size, Image.Resampling.LANCZOS)
    out_p = os.path.join(branding_dir, name)
    resized.save(out_p, "PNG")
    print(f"Generated Icon {name}: {size}")

print("All branding assets generated successfully!")
