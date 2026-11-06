import os
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import arabic_reshaper
from bidi.algorithm import get_display

art_dir = r"plugin.video.30nama\resources\art"
os.makedirs(art_dir, exist_ok=True)

WIDTH, HEIGHT = 600, 900

FONT_BOLD = r"C:\Windows\Fonts\arialbd.ttf"
FONT_REGULAR = r"C:\Windows\Fonts\arial.ttf"

def reshape_fa(text):
    return get_display(arabic_reshaper.reshape(text))

def hex_to_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def draw_gradient(draw, width, height, c_top, c_mid, c_bot):
    r1, g1, b1 = hex_to_rgb(c_top)
    r2, g2, b2 = hex_to_rgb(c_mid)
    r3, g3, b3 = hex_to_rgb(c_bot)
    
    mid_y = int(height * 0.45)
    for y in range(height):
        if y < mid_y:
            t = y / float(mid_y)
            r = int(r1 * (1 - t) + r2 * t)
            g = int(g1 * (1 - t) + g2 * t)
            b = int(b1 * (1 - t) + b2 * t)
        else:
            t = (y - mid_y) / float(height - mid_y)
            r = int(r2 * (1 - t) + r3 * t)
            g = int(g2 * (1 - t) + g3 * t)
            b = int(b2 * (1 - t) + b3 * t)
        draw.line([(0, y), (width, y)], fill=(r, g, b, 255))

def draw_icon(draw, cx, cy, icon_type, color=(245, 197, 24, 255)):
    # Draw high-quality geometric vector silhouettes
    gold = color
    white = (255, 255, 255, 240)
    
    if icon_type == "clapper": # New Releases
        # Clapperboard body
        draw.rectangle([cx - 70, cy - 10, cx + 70, cy + 80], fill=(20, 25, 35, 240), outline=gold, width=4)
        # Clapper top angled
        draw.rectangle([cx - 70, cy - 45, cx + 70, cy - 12], fill=gold)
        # Stripes
        for offset in [-50, -15, 20, 55]:
            draw.polygon([(cx + offset, cy - 45), (cx + offset + 15, cy - 45), 
                          (cx + offset + 5, cy - 12), (cx + offset - 10, cy - 12)], fill=(20, 25, 35, 255))
        # Small play triangle in center
        draw.polygon([(cx - 15, cy + 15), (cx - 15, cy + 55), (cx + 25, cy + 35)], fill=gold)

    elif icon_type == "film": # Movies
        # Film reel outer circle
        draw.ellipse([cx - 65, cy - 65, cx + 65, cy + 65], outline=gold, width=6)
        draw.ellipse([cx - 20, cy - 20, cx + 20, cy + 20], fill=gold)
        # Holes
        for angle in [0, 60, 120, 180, 240, 300]:
            rad = math.radians(angle)
            hx = cx + int(42 * math.cos(rad))
            hy = cy + int(42 * math.sin(rad))
            draw.ellipse([hx - 12, hy - 12, hx + 12, hy + 12], fill=(15, 18, 24, 255), outline=gold, width=2)

    elif icon_type == "tv": # Series
        # TV frame
        draw.rounded_rectangle([cx - 75, cy - 45, cx + 75, cy + 55], radius=12, fill=(20, 25, 35, 240), outline=gold, width=4)
        # Antenna
        draw.line([(cx - 30, cy - 75), (cx, cy - 45)], fill=gold, width=4)
        draw.line([(cx + 30, cy - 75), (cx, cy - 45)], fill=gold, width=4)
        # Screen lines / signal
        draw.rounded_rectangle([cx - 60, cy - 35, cx + 60, cy + 45], radius=6, outline=(255, 255, 255, 120), width=2)
        draw.polygon([(cx - 12, cy - 12), (cx - 12, cy + 22), (cx + 18, cy + 5)], fill=gold)

    elif icon_type == "flame": # Top 10
        # Crown / Trophy
        draw.polygon([(cx - 60, cy + 45), (cx + 60, cy + 45), (cx + 45, cy + 70), (cx - 45, cy + 70)], fill=gold)
        # Big "10" badge
        draw.rounded_rectangle([cx - 65, cy - 60, cx + 65, cy + 35], radius=16, fill=(20, 25, 35, 240), outline=gold, width=4)
        f_num = ImageFont.truetype(FONT_BOLD, 64)
        draw.text((cx, cy - 18), "10", font=f_num, fill=gold, anchor="mm")

    elif icon_type == "star": # Suggested
        # 5-pointed star
        points = []
        for i in range(10):
            r = 65 if i % 2 == 0 else 30
            ang = math.radians(i * 36 - 90)
            points.append((cx + int(r * math.cos(ang)), cy + int(r * math.sin(ang))))
        draw.polygon(points, fill=gold, outline=(255, 255, 255, 200))

    elif icon_type == "search": # Search
        # Magnifying glass
        draw.ellipse([cx - 50, cy - 55, cx + 20, cy + 15], outline=gold, width=8)
        # Glass handle
        draw.line([(cx + 15, cy + 10), (cx + 60, cy + 55)], fill=gold, width=12)
        # Inner lens sparkle
        draw.ellipse([cx - 28, cy - 33, cx - 12, cy - 17], fill=(255, 255, 255, 180))

    elif icon_type == "bolt": # Direct 4K
        # 4K box with lightning bolt
        draw.rounded_rectangle([cx - 75, cy - 50, cx + 75, cy + 50], radius=14, fill=(20, 25, 35, 240), outline=gold, width=4)
        f_4k = ImageFont.truetype(FONT_BOLD, 52)
        draw.text((cx, cy), "4K", font=f_4k, fill=gold, anchor="mm")

    elif icon_type == "user": # Account
        # Head
        draw.ellipse([cx - 30, cy - 60, cx + 30, cy], fill=gold)
        # Shoulders
        draw.chord([cx - 60, cy + 5, cx + 60, cy + 90], start=180, end=360, fill=gold)
        # Star crown above
        draw.polygon([(cx - 15, cy - 70), (cx, cy - 90), (cx + 15, cy - 70), (cx, cy - 65)], fill=(255, 255, 255, 230))

    elif icon_type == "settings": # Settings
        # Cog wheel
        draw.ellipse([cx - 45, cy - 45, cx + 45, cy + 45], outline=gold, width=12)
        draw.ellipse([cx - 18, cy - 18, cx + 18, cy + 18], fill=gold)
        for ang in range(0, 360, 45):
            rad = math.radians(ang)
            tx = cx + int(52 * math.cos(rad))
            ty = cy + int(52 * math.sin(rad))
            draw.ellipse([tx - 10, ty - 10, tx + 10, ty + 10], fill=gold)

cards = [
    ("new_releases.png", "#0a1128", "#001f54", "#034078", "clapper", "NEW RELEASES", "جدیدترین‌ها", "آخرین فیلم‌ها و قسمت‌های سریال"),
    ("movies.png", "#1a080a", "#3d0c11", "#6a141d", "film", "MOVIES", "فیلم‌های سینمایی", "آرشیو کامل با کیفیت‌های بلوری و 4K"),
    ("series.png", "#0f0c20", "#22194d", "#3f2b96", "tv", "SERIES", "سریال‌های برتر", "فهرست کامل فصل‌ها با استریم روان"),
    ("top_10.png", "#241400", "#4d2c00", "#804b00", "flame", "TOP 10", "۱۰ عنوان برتر", "محبوب‌ترین عناوین منتخب هفته"),
    ("suggested.png", "#001c18", "#003d35", "#066657", "star", "SUGGESTED", "پیشنهادهای ویژه", "شاهکارهای سینمایی دست‌چین شده"),
    ("search.png", "#0d1b2a", "#1b263b", "#415a77", "search", "SEARCH", "جستجوی پیشرفته", "جستجو بر اساس نام فارسی یا انگلیسی"),
    ("direct_url.png", "#02182b", "#06385a", "#0d6394", "bolt", "4K DIRECT PLAY", "پخش مستقیم 4K", "استریم آنی لینک دانلود MKV و MP4"),
    ("account.png", "#1c1405", "#38290a", "#5e4511", "user", "MY ACCOUNT", "حساب کاربری", "مشاهده اشتراک طلایی و وضعیت کاربر"),
    ("settings.png", "#16181a", "#282c30", "#3f464d", "settings", "SETTINGS", "تنظیمات افزونه", "زیرنویس، سرورها، کیفیت و پلیر"),
]

for filename, c_top, c_mid, c_bot, icon_name, en_title, fa_title, subtext in cards:
    im = Image.new("RGBA", (WIDTH, HEIGHT), (10, 14, 20, 255))
    draw = ImageDraw.Draw(im)
    
    # 1. Background gradient
    draw_gradient(draw, WIDTH, HEIGHT, c_top, c_mid, c_bot)
    
    # 2. Bottom shadow vignette
    vignette = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    v_draw = ImageDraw.Draw(vignette)
    for y in range(HEIGHT // 3, HEIGHT):
        factor = (y - HEIGHT // 3) / float(HEIGHT * 2 // 3)
        alpha = int(240 * (factor ** 1.5))
        v_draw.line([(0, y), (WIDTH, y)], fill=(8, 11, 16, alpha))
    im = Image.alpha_composite(im, vignette)
    draw = ImageDraw.Draw(im)
    
    # 3. Ambient glow behind icon
    glow = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    g_draw = ImageDraw.Draw(glow)
    cx, cy = WIDTH // 2, HEIGHT // 2 - 60
    g_draw.ellipse([cx - 160, cy - 160, cx + 160, cy + 160], fill=(245, 197, 24, 45))
    glow = glow.filter(ImageFilter.GaussianBlur(50))
    im = Image.alpha_composite(im, glow)
    draw = ImageDraw.Draw(im)
    
    # 4. Icon glass circle container
    draw.ellipse([cx - 110, cy - 110, cx + 110, cy + 110], fill=(15, 20, 30, 160), outline=(245, 197, 24, 180), width=3)
    
    # 5. Draw Vector Icon
    draw_icon(draw, cx, cy, icon_name, color=(245, 197, 24, 255))
    
    # 6. Top brand pill "30NAMA • 4K"
    pill_w, pill_h = 170, 38
    pill_x1 = WIDTH // 2 - pill_w // 2
    pill_y1 = 45
    draw.rounded_rectangle([pill_x1, pill_y1, pill_x1 + pill_w, pill_y1 + pill_h], radius=19, fill=(0, 0, 0, 160), outline=(245, 197, 24, 140), width=2)
    f_pill = ImageFont.truetype(FONT_BOLD, 16)
    draw.text((WIDTH // 2, pill_y1 + pill_h // 2), "30NAMA  •  4K", font=f_pill, fill=(245, 197, 24, 240), anchor="mm")
    
    # 7. English Title
    f_en = ImageFont.truetype(FONT_BOLD, 42)
    draw.text((WIDTH // 2, HEIGHT - 240), en_title, font=f_en, fill=(255, 255, 255, 255), anchor="mm")
    
    # 8. Golden divider
    div_w = 90
    draw.line([(WIDTH // 2 - div_w, HEIGHT - 195), (WIDTH // 2 + div_w, HEIGHT - 195)], fill=(245, 197, 24, 220), width=3)
    
    # 9. Persian Title (Reshaped + BiDi for clean connected Nastaliq/Naskh)
    f_fa = ImageFont.truetype(FONT_BOLD, 36)
    fa_shaped = reshape_fa(fa_title)
    draw.text((WIDTH // 2, HEIGHT - 145), fa_shaped, font=f_fa, fill=(245, 245, 245, 250), anchor="mm")
    
    # 10. Subtitle Description
    f_sub = ImageFont.truetype(FONT_REGULAR, 20)
    sub_shaped = reshape_fa(subtext)
    draw.text((WIDTH // 2, HEIGHT - 85), sub_shaped, font=f_sub, fill=(180, 190, 205, 210), anchor="mm")
    
    # 11. Rounded outer border for the card
    draw.rounded_rectangle([14, 14, WIDTH - 15, HEIGHT - 15], radius=28, outline=(255, 255, 255, 45), width=3)
    
    # Save
    out_path = os.path.join(art_dir, filename)
    im.save(out_path, "PNG", optimize=True)
    print(f"Generated card: {out_path} ({os.path.getsize(out_path)} bytes)")

# -------------------------------------------------------------
# Generate 512x512 Addon Icon (icon.png)
# -------------------------------------------------------------
icon_im = Image.new("RGBA", (512, 512), (12, 16, 24, 255))
i_draw = ImageDraw.Draw(icon_im)
draw_gradient(i_draw, 512, 512, "#0a1128", "#1c2541", "#0b132b")

# Outer gold ring
i_draw.ellipse([30, 30, 482, 482], outline=(245, 197, 24, 220), width=6)
i_draw.ellipse([45, 45, 467, 467], fill=(16, 22, 34, 240), outline=(255, 255, 255, 40), width=2)

# Central 30NAMA branding
f_30 = ImageFont.truetype(FONT_BOLD, 100)
i_draw.text((256, 190), "30NAMA", font=f_30, fill=(245, 197, 24, 255), anchor="mm")

# 4K ULTRA HD badge
i_draw.rounded_rectangle([140, 265, 372, 325], radius=12, fill=(245, 197, 24, 255))
f_uhd = ImageFont.truetype(FONT_BOLD, 32)
i_draw.text((256, 295), "4K ULTRA HD", font=f_uhd, fill=(12, 16, 24, 255), anchor="mm")

# Persian subtitle "سینما در خانه"
f_fa_icon = ImageFont.truetype(FONT_BOLD, 30)
i_draw.text((256, 380), reshape_fa("سینما در خانه شما"), font=f_fa_icon, fill=(220, 230, 245, 230), anchor="mm")

addon_icon_path = r"plugin.video.30nama\icon.png"
icon_im.save(addon_icon_path, "PNG", optimize=True)
print(f"Generated Addon Icon: {addon_icon_path} ({os.path.getsize(addon_icon_path)} bytes)")

# -------------------------------------------------------------
# Generate 1920x1080 Fanart Backdrop (fanart.jpg)
# -------------------------------------------------------------
fanart_im = Image.new("RGB", (1920, 1080), (10, 14, 20))
f_draw = ImageDraw.Draw(fanart_im)
for y in range(1080):
    t = y / 1080.0
    # Vignetted cinematic deep gradient
    r = int(10 * (1 - t * 0.4))
    g = int(16 * (1 - t * 0.3) + 6 * t)
    b = int(26 * (1 - t * 0.2) + 12 * t)
    f_draw.line([(0, y), (1920, y)], fill=(r, g, b))

fanart_path = os.path.join(art_dir, "fanart.jpg")
fanart_im.save(fanart_path, "JPEG", quality=92)
print(f"Generated Fanart: {fanart_path} ({os.path.getsize(fanart_path)} bytes)")
print("ALL ARTWORK GENERATION COMPLETE!")
