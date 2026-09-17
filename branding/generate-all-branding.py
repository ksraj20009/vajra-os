#!/usr/bin/env python3
"""
Vajra OS — Complete branding asset generator.
Generates every PNG asset in branding/ from code (no binary files needed in git).

Outputs:
  branding/icons/vajra-logo-{16,32,48,64,128,256,512}x{...}.png
  branding/icons/vajra-{appstore,files,monitor,screenshot,settings,terminal}-{32,48}.png
  branding/plymouth/{vajra-logo,vajra-watermark,vajra-background,progress-bg,progress-fill}.png
  branding/grub/vajra-grub.png
  branding/wallpapers/vajra-default.png

Design: faceted tricolor diamond (vajra = diamond/thunderbolt).
Saffron crown, white girdle band, green pavilion.
"""
import math, os, sys
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # repo root (script lives in branding/)

# Tricolor palette
SAFFRON = (255, 153, 51, 255)
SAFFRON_LIGHT = (255, 191, 128, 255)
SAFFRON_DEEP = (232, 118, 0, 255)
WHITE = (255, 255, 255, 255)
GREEN = (19, 136, 8, 255)
GREEN_LIGHT = (66, 189, 55, 255)
GREEN_DEEP = (13, 100, 6, 255)
DARK = (10, 10, 26, 255)

def out(path):
    full = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    return full

# --- The Vajra diamond ---
def draw_diamond(size):
    S = size * 8
    img = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx = S // 2
    g1x, g5x = int(S * 0.08), int(S * 0.92)
    t1x, t2x = cx - int(S * 0.16), cx + int(S * 0.16)
    ty = int(S * 0.24)
    gy = int(S * 0.44)
    band = max(int(S * 0.030), 8)
    cy = int(S * 0.94)
    g2x, g4x = cx - int(S * 0.20), cx + int(S * 0.20)
    gyt, gyl = gy - band, gy + band

    # Crown
    d.polygon([(t1x, ty), (t2x, ty), (cx, gyt)], fill=SAFFRON_LIGHT)
    d.polygon([(t1x, ty), (g1x, gyt), (cx, gyt)], fill=SAFFRON)
    d.polygon([(t2x, ty), (cx, gyt), (g5x, gyt)], fill=SAFFRON_DEEP)
    # Girdle band
    d.polygon([(g1x, gyt), (g5x, gyt), (g5x, gyl), (g1x, gyl)], fill=WHITE)
    # Pavilion
    d.polygon([(g1x, gyl), (g2x, gyl), (cx, cy)], fill=GREEN_DEEP)
    d.polygon([(g2x, gyl), (cx, gyl), (cx, cy)], fill=GREEN)
    d.polygon([(cx, gyl), (g4x, gyl), (cx, cy)], fill=GREEN_LIGHT)
    d.polygon([(g4x, gyl), (g5x, gyl), (cx, cy)], fill=GREEN)
    # Facet lines
    lw = max(S // 128, 4)
    soft = (255, 255, 255, 90)
    d.line([(t1x, ty), (cx, gyt)], fill=soft, width=lw)
    d.line([(t2x, ty), (cx, gyt)], fill=soft, width=lw)
    d.line([(g2x, gyl), (cx, cy)], fill=soft, width=lw)
    d.line([(g4x, gyl), (cx, cy)], fill=soft, width=lw)
    # Sparkle
    if size >= 32:
        sx, sy, sr = cx - int(S * 0.10), int(S * 0.15), max(S // 48, 6)
        d.polygon([(sx, sy - sr), (sx + sr // 3, sy - sr // 3), (sx + sr, sy),
                   (sx + sr // 3, sy + sr // 3), (sx, sy + sr), (sx - sr // 3, sy + sr // 3),
                   (sx - sr, sy), (sx - sr // 3, sy - sr // 3)], fill=(255, 255, 255, 235))
    return img.resize((size, size), Image.LANCZOS)

# --- App icon tiles ---
def tile(size):
    img = Image.new('RGBA', (size * 8, size * 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    S = size * 8
    r = S // 5
    d.rounded_rectangle([0, 0, S - 1, S - 1], radius=r, fill=DARK,
                        outline=(255, 153, 51, 70), width=max(S // 64, 2))
    # tricolor accent strip at bottom
    strip_h = max(S // 14, 6)
    y = S - strip_h - r // 2
    w3 = S // 3
    d.rectangle([r // 2, y, r // 2 + w3 - 2, y + strip_h], fill=SAFFRON)
    d.rectangle([r // 2 + w3, y, r // 2 + 2 * w3 - 2, y + strip_h], fill=WHITE)
    d.rectangle([r // 2 + 2 * w3, y, r // 2 + 3 * w3 - 2, y + strip_h], fill=GREEN)
    return img, d, S

def glyph_terminal(d, S):
    sc = 0.16
    x0, y0, x1, y1 = int(S*sc*1.4), int(S*0.26), int(S*(1-sc*1.4)), int(S*0.66)
    d.rounded_rectangle([x0, y0, x1, y1], radius=S//18, outline=WHITE, width=max(S//40, 3))
    lw = max(S // 28, 5)
    d.line([(x0 + S//10, y0 + S//8), (x0 + S//5, y0 + S//5.4)], fill=SAFFRON, width=lw)
    d.line([(x0 + S//5, y0 + S//5.4), (x0 + S//10, y0 + S//3.6)], fill=SAFFRON, width=lw)
    d.line([(x0 + S//3.4, y0 + S//3.6), (x0 + S//2.1, y0 + S//3.6)], fill=WHITE, width=lw)

def glyph_files(d, S):
    x0, y0 = int(S*0.2), int(S*0.28)
    x1, y1 = int(S*0.8), int(S*0.72)
    d.rounded_rectangle([x0, y0 + S//9, x0 + S//4, y0 + S//4], radius=S//22, fill=SAFFRON)
    d.rounded_rectangle([x0, y0 + S//5, x1, y1], radius=S//22, fill=SAFFRON_LIGHT,
                         outline=(255, 255, 255, 120), width=max(S//50, 2))

def glyph_monitor(d, S):
    x0, y0, x1, y1 = int(S*0.18), int(S*0.24), int(S*0.82), int(S*0.62)
    d.rounded_rectangle([x0, y0, x1, y1], radius=S//20, outline=WHITE, width=max(S//36, 3))
    d.rectangle([(x0+x1)//2 - S//12, y1, (x0+x1)//2 + S//12, y1 + S//10], fill=WHITE)
    d.rectangle([int(S*0.38), y1 + S//10, int(S*0.62), y1 + S//10 + S//22], fill=WHITE)
    # pulse line
    pts = [(x0 + (x1-x0)*f, y0 + (y1-y0)*h) for f, h in
           [(0.12, 0.62), (0.3, 0.62), (0.38, 0.3), (0.5, 0.85), (0.62, 0.42), (0.7, 0.62), (0.88, 0.62)]]
    d.line(pts, fill=GREEN_LIGHT, width=max(S//30, 4), joint='curve')

def glyph_screenshot(d, S):
    cx, cy = S//2, int(S*0.50)
    w, h = int(S*0.52), int(S*0.36)
    d.rounded_rectangle([cx-w//2, cy-h//2, cx+w//2, cy+h//2], radius=S//16, outline=WHITE, width=max(S//34, 3))
    d.rounded_rectangle([cx-S//9, cy-h//2-S//14, cx+S//9, cy-h//2], radius=S//24, fill=WHITE)
    r = S//9
    d.ellipse([cx-r, cy-r, cx+r, cy+r], outline=SAFFRON, width=max(S//30, 4))
    d.ellipse([cx+S//6, cy-h//2+S//8, cx+S//6+S//16, cy-h//2+S//8+S//16], fill=SAFFRON_LIGHT)

def glyph_settings(d, S):
    cx, cy, R = S//2, int(S*0.47), int(S*0.26)
    teeth = 8
    for i in range(teeth):
        a = 2 * math.pi * i / teeth
        x1, y1 = cx + (R - S//28) * math.cos(a), cy + (R - S//28) * math.sin(a)
        x2, y2 = cx + (R + S//16) * math.cos(a), cy + (R + S//16) * math.sin(a)
        d.line([(x1, y1), (x2, y2)], fill=WHITE, width=max(S//12, 6))
    d.ellipse([cx-R, cy-R, cx+R, cy+R], outline=WHITE, width=max(S//18, 6))
    d.ellipse([cx-R//2.6, cy-R//2.6, cx+R//2.6, cy+R//2.6], fill=SAFFRON)

def glyph_appstore(d, S):
    cx = S // 2
    # down arrow into a tray
    d.line([(cx, int(S*0.22)), (cx, int(S*0.52))], fill=WHITE, width=max(S//14, 6))
    d.line([(cx - S//8, int(S*0.42)), (cx, int(S*0.52)), (cx + S//8, int(S*0.42))], fill=WHITE, width=max(S//14, 6))
    d.arc([int(S*0.2), int(S*0.3), int(S*0.8), int(S*0.74)], start=15, end=165, fill=SAFFRON, width=max(S//16, 5))
    d.line([(int(S*0.26), int(S*0.66)), (int(S*0.74), int(S*0.66))], fill=SAFFRON, width=max(S//16, 5))

GLYPHS = {'terminal': glyph_terminal, 'files': glyph_files, 'monitor': glyph_monitor,
          'screenshot': glyph_screenshot, 'settings': glyph_settings, 'appstore': glyph_appstore}

def app_icon(name, size):
    img, d, S = tile(size)
    GLYPHS[name](d, S)
    return img.resize((size, size), Image.LANCZOS)

# --- Plymouth boot splash ---
def plymouth_logo(size=256):
    return draw_diamond(size)

def plymouth_watermark(size=128):
    base = draw_diamond(size)
    img = Image.new('RGBA', (size * 3, size), (0, 0, 0, 0))
    img.alpha_composite(base, (0, 0))
    return img

def plymouth_background(w=1920, h=1080):
    img = Image.new('RGBA', (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / h
        r = int(6 + 14 * t); g = int(6 + 6 * t); b = int(17 + 35 * t)
        d.line([(0, y), (w, y)], fill=(r, g, b, 255))
    # soft radial glow behind logo
    glow = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    cx, cy, gr = w // 2, int(h * 0.42), int(h * 0.42)
    for i in range(40, 0, -1):
        rr = int(gr * i / 40)
        gd.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=(255, 153, 51, max(2, 26 - i // 2)))
    glow = glow.filter(__import__('PIL.ImageFilter', fromlist=['GaussianBlur']).GaussianBlur(60))
    img.alpha_composite(glow)
    logo = draw_diamond(int(h * 0.34))
    img.alpha_composite(logo, ((w - logo.width) // 2, int(h * 0.26)))
    return img

def progress_bar(w=400, h=14, filled=False):
    img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = h // 2
    if filled:
        # tricolor gradient: saffron -> white -> green
        for x in range(w):
            t = x / w
            if t < 0.5:
                t1 = t * 2
                c = (int(255 + (255-255)*t1), int(153 + (255-153)*t1), int(51 + (255-51)*t1))
            else:
                t2 = (t - 0.5) * 2
                c = (int(255 + (19-255)*t2), int(255 + (136-255)*t2), int(255 + (8-255)*t2))
            d.rectangle([x, 2, x, h - 3], fill=(*c, 255))
        d.rounded_rectangle([0, 2, w - 1, h - 3], radius=r // 2, outline=WHITE, width=2)
    else:
        d.rounded_rectangle([0, 2, w - 1, h - 3], radius=r // 2, outline=(255, 255, 255, 60), width=2)
    return img

# --- GRUB background ---
def grub_bg(w=640, h=480):
    img = plymouth_background(w, h)
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", w // 16)
    except Exception:
        font = ImageFont.load_default()
    text = "Vajra OS 1.0"
    tw = d.textlength(text, font=font)
    d.text(((w - tw) / 2, int(h * 0.70)), text, font=font, fill=WHITE)
    bw = int(w * 0.6)
    bx = (w - bw) // 2
    by = int(h * 0.82)
    d.rectangle([bx, by, bx + bw // 3, by + 5], fill=SAFFRON)
    d.rectangle([bx + bw // 3, by, bx + 2 * bw // 3, by + 5], fill=WHITE)
    d.rectangle([bx + 2 * bw // 3, by, bx + bw, by + 5], fill=GREEN)
    return img

# --- Wallpaper ---
def wallpaper(w=1920, h=1080):
    img = plymouth_background(w, h)
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
    except Exception:
        font = ImageFont.load_default()
    text = "Dharmo Rakshati Rakshitah"
    tw = d.textlength(text, font=font)
    d.text(((w - tw) / 2, int(h * 0.78)), text, font=font, fill=(160, 160, 170, 255))
    bw = int(w * 0.16)
    bx, by = (w - bw) // 2, int(h * 0.83)
    d.rectangle([bx, by, bx + bw // 3, by + 4], fill=SAFFRON)
    d.rectangle([bx + bw // 3, by, bx + 2 * bw // 3, by + 4], fill=WHITE)
    d.rectangle([bx + 2 * bw // 3, by, bx + bw, by + 4], fill=GREEN)
    return img

# --- Generate everything ---
def main():
    n = 0
    for size in [16, 32, 48, 64, 128, 256, 512]:
        draw_diamond(size).save(out(f'branding/icons/vajra-logo-{size}x{size}.png')); n += 1
    for name in GLYPHS:
        for size in [32, 48]:
            app_icon(name, size).save(out(f'branding/icons/vajra-{name}-{size}x{size}.png')); n += 1
    plymouth_logo(256).save(out('branding/plymouth/vajra-logo.png')); n += 1
    plymouth_watermark(128).save(out('branding/plymouth/vajra-watermark.png')); n += 1
    plymouth_background().save(out('branding/plymouth/vajra-background.png')); n += 1
    progress_bar(filled=False).save(out('branding/plymouth/progress-bg.png')); n += 1
    progress_bar(filled=True).save(out('branding/plymouth/progress-fill.png')); n += 1
    grub_bg().save(out('branding/grub/vajra-grub.png')); n += 1
    wallpaper().save(out('branding/wallpapers/vajra-default.png')); n += 1
    print(f'Generated {n} assets in {os.path.join(ROOT, "branding")}/')

if __name__ == '__main__':
    main()
