from PIL import Image, ImageDraw, ImageFont
def make(path, size, wght):
    f = ImageFont.truetype(path, size=size)
    f.set_variation_by_axes([wght, 100])
    return f
def glyph(f, ch):
    """-> adv(FP12.4), x, y, w, h, lines(2bpp)"""
    W = 96; ox, oy = 24, 64
    im = Image.new('L', (W, W), 0)
    ImageDraw.Draw(im).text((ox, oy), ch, font=f, fill=255, anchor='ls')
    q = im.point(lambda v: (v + 42) // 85)
    bb = q.getbbox()
    adv = round(f.getlength(ch) * 16)
    if not bb: return adv, 0, 0, 0, 0, []
    l, t, r, b = bb
    px = list(q.getdata())
    lines = [px[y*W+l:y*W+r] for y in range(t, b)]
    return adv, l - ox, oy - b, r - l, b - t, lines
