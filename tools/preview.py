"""Render sample text with a patched LVGL font. usage: preview.py font out.png"""
import sys; sys.path.insert(0, __file__.rsplit('/', 1)[0])
from lvfont import Font
from PIL import Image
font, out = sys.argv[1:3]
b = Font(open(font, 'rb').read())
def draw(text, im, x, base):
    for ch in text:
        g = b.gid(ord(ch))
        if not g: x += 12; continue
        d = b.decode(g)
        for r, l in enumerate(d['px']):
            for c, v in enumerate(l):
                X, Y = x + d['x'] + c, base - d['y'] - d['h'] + r
                if v and 0 <= X < im.width and 0 <= Y < im.height: im.putpixel((X, Y), v * 85)
        x += round(d['adv'] / 16)
im = Image.new('L', (520, 470), 0)
lines = ['WhatsApp · გიორგი', 'გამარჯობა, როგორ ხარ?', 'ხვალ 10:30-ზე შევხვდეთ', 'Hello გიორგი Привет', 'აბგდევზთიკლმნოპჟრსტუ', 'ფქღყშჩცძწჭხჯჰ ჱჲჳჴჵ', 'ᲡᲐᲥᲐᲠᲗᲕᲔᲚᲝ ᲗᲑᲘᲚᲘᲡᲘ', 'Tbilisi თბილისი 2026']
for i, l in enumerate(lines): draw(l, im, 14, 60 + i * 52)
im.save(out)
