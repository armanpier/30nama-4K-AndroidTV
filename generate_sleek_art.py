import os
from PIL import Image, ImageDraw, ImageFont

art_dir = r"plugin.video.30nama\resources\art"
os.makedirs(art_dir, exist_ok=True)

# Card specs: 500 x 750 (standard 2:3 vertical movie poster ratio)
WIDTH, HEIGHT = 500, 750

cards = [
    ("new_releases.png", "#0f2027", "#203a43", "#2c5364", "🎬", "NEW RELEASES", "جدیدترین‌ها"),
    ("movies.png", "#3a1c71", "#d76d77", "#ffaf7b", "🍿", "MOVIES", "فیلم‌های سینمایی"),
    ("series.png", "#141e30", "#243b55", "#4a00e0", "📺", "SERIES", "سریال‌های برتر"),
    ("top_10.png", "#f12711", "#f5af19", "#e65c00", "🔥", "TOP 10", "۱۰ عنوان برتر"),
    ("suggested.png", "#134e5e", "#71b280", "#2e7d32", "⭐", "SUGGESTED", "پیشنهادهای ویژه"),
    ("search.png", "#1a2a6c", "#b21f1f", "#fdbb2d", "🔍", "SEARCH", "جستجوی پیشرفته"),
    ("direct_url.png", "#8a2387", "#e94057", "#f27121", "⚡", "4K DIRECT LINK", "پخش مستقیم 4K"),
    ("account.png", "#1f4037", "#99f2c8", "#00b4db", "👑", "USER ACCOUNT", "حساب کاربری"),
    ("settings.png", "#232526", "#414345", "#485563", "⚙️", "SETTINGS", "تنظیمات افزونه"),
]

for filename, c1, c2, c3, emoji, en_title, fa_title in cards:
    im = Image.new("RGBA", (WIDTH, HEIGHT), (15, 20, 26, 255))
    draw = ImageDraw.Draw(im)
    
    # Draw vertical linear gradient
    for y in range(HEIGHT):
        ratio = y / float(HEIGHT)
        # Parse hex colors
        r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
        r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
        r = int(r1 * (1 - ratio) + r2 * ratio)
        g = int(g1 * (1 - ratio) + g2 * ratio)
        b = int(b1 * (1 - ratio) + b2 * ratio)
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b, 255))
        
    # Draw dark overlay vignette at bottom
    for y in range(HEIGHT // 2, HEIGHT):
        alpha = int(((y - HEIGHT // 2) / float(HEIGHT // 2)) * 200)
        draw.line([(0, y), (WIDTH, y)], fill=(12, 16, 22, alpha))
        
    # Draw elegant rounded card border
    draw.rounded_rectangle([15, 15, WIDTH - 16, HEIGHT - 16], radius=24, outline=(255, 255, 255, 40), width=3)
    
    # Draw 30NAMA branding badge at top
    draw.rectangle([WIDTH // 2 - 60, 35, WIDTH // 2 + 60, 65], fill=(0, 0, 0, 100))
    
    # Text fonts
    try:
        font_large = ImageFont.truetype("arial.ttf", 46)
        font_sub = ImageFont.truetype("arial.ttf", 26)
        font_badge = ImageFont.truetype("arial.ttf", 16)
    except Exception:
        font_large = ImageFont.load_default()
        font_sub = ImageFont.load_default()
        font_badge = ImageFont.load_default()
        
    draw.text((WIDTH // 2, 50), "30NAMA 4K", font=font_badge, fill=(240, 240, 240, 220), anchor="mm")
    
    # Draw central emoji / symbol circle
    cx, cy = WIDTH // 2, HEIGHT // 2 - 30
    draw.ellipse([cx - 90, cy - 90, cx + 90, cy + 90], fill=(255, 255, 255, 20), outline=(255, 255, 255, 60), width=2)
    try:
        font_emoji = ImageFont.truetype("seguiemj.ttf", 80)
        draw.text((cx, cy), emoji, font=font_emoji, fill=(255, 255, 255, 255), anchor="mm")
    except Exception:
        draw.text((cx, cy), emoji, font=font_large, fill=(255, 255, 255, 255), anchor="mm")
        
    # Draw English Title
    draw.text((WIDTH // 2, HEIGHT - 160), en_title, font=font_large, fill=(255, 255, 255, 255), anchor="mm")
    
    # Draw subtle divider
    draw.line([(WIDTH // 2 - 80, HEIGHT - 125), (WIDTH // 2 + 80, HEIGHT - 125)], fill=(255, 255, 255, 120), width=2)
    
    # Draw Subtitle / Persian
    draw.text((WIDTH // 2, HEIGHT - 85), fa_title, font=font_sub, fill=(200, 220, 240, 220), anchor="mm")
    
    out_path = os.path.join(art_dir, filename)
    im.save(out_path, "PNG")
    print(f"Generated {out_path} ({os.path.getsize(out_path)} bytes)")

# Also generate dark fanart backdrop (1920x1080)
fanart_path = os.path.join(art_dir, "fanart.jpg")
fanart_im = Image.new("RGB", (1920, 1080), (14, 18, 23))
f_draw = ImageDraw.Draw(fanart_im)
# Radial gradient or subtle glow
for y in range(1080):
    factor = 1.0 - (y / 1080.0) * 0.4
    f_draw.line([(0, y), (1920, y)], fill=(int(14 * factor), int(22 * factor), int(30 * factor)))
fanart_im.save(fanart_path, "JPEG", quality=90)
print(f"Generated {fanart_path} ({os.path.getsize(fanart_path)} bytes)")
