# -*- coding: utf-8 -*-
"""MANTA — A2 poster (portrait 4961x7016). Hero (poster-sized) + shadow + title."""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 4961, 7016
HERO = "_deliver/poster_hero.png"
OUTF = "TEAMID_Poster.jpg"

def F(sz):
    try:
        return ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", sz)
    except Exception:
        return ImageFont.load_default()

if os.path.exists(HERO):
    im = Image.open(HERO).convert("RGB")
    if im.size != (W, H):
        s = max(W / im.width, H / im.height)
        im = im.resize((int(im.width * s), int(im.height * s)))
        im = im.crop(((im.width - W) // 2, (im.height - H) // 2,
                      (im.width - W) // 2 + W, (im.height - H) // 2 + H))
else:
    im = Image.new("RGB", (W, H), (10, 11, 14))

# --- soft shadow under the feet (ellipse, multiply) ---
sh = Image.new("L", (W, H), 0)
sd = ImageDraw.Draw(sh)
sd.ellipse((W*0.16, H*0.82, W*0.84, H*0.93), fill=150)
sh = sh.filter(ImageFilter.GaussianBlur(120))
dark = Image.new("RGB", (W, H), (0, 0, 0))
im = Image.composite(dark, im, sh)

dr = ImageDraw.Draw(im)
dr.text((W // 2, H - 300), "MANTA", font=F(128), fill=(226, 229, 236), anchor="mm")
im.save(OUTF, "JPEG", quality=90)
print(OUTF, im.size, f"{os.path.getsize(OUTF) / 1e6:.2f} MB")
