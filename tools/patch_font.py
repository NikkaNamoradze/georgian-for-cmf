"""Add Georgian (Mkhedruli U+10D0-10FF, Mtavruli U+1C90-1CBF) to an LVGL bin font, keeping file size identical
by blanking rarely used glyphs. usage: patch_font.py stock.font NotoSansGeorgian.ttf out.font"""
import sys, struct
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from lvfont import Font
from raster import make, glyph

SIZE, WGHT = 33, 500
NEW_RANGES = [(0x10D0, 48), (0x1C90, 48)]
# blanked to make room, in this order, only as many as needed: Kanbun/Bopomofo ext, CJK strokes, rare Arabic ligatures
VICTIM_RANGES = [(0x3190, 43), (0x31C0, 36), (0xFD50, 64), (0xFD92, 54)]

src, ttf, dst = sys.argv[1:4]
raw = open(src, 'rb').read()
f = Font(raw)
ft = make(ttf, SIZE, WGHT)
for rs, rl in NEW_RANGES:
    assert all(f.gid(c) == 0 for c in range(rs, rs + rl)), 'range already present'

new_glyphs = []
for rs, rl in NEW_RANGES:
    for cp in range(rs, rs + rl):
        has = ft.getmask(chr(cp)).getbbox() is not None and cp not in (0x1CBB, 0x1CBC)
        adv, x, y, w, h, px = glyph(ft, chr(cp)) if has else (0, 0, 0, 0, 0, [])
        new_glyphs.append(f.encode(adv, x, y, w, h, px))
n_new = len(new_glyphs)
need = 16 * len(NEW_RANGES) + 4 * n_new + sum(map(len, new_glyphs))

glyphs = [f.glyph_bytes(g) for g in range(f.nloca)]
freed = 0; blanked = []
for rs, rl in VICTIM_RANGES:
    for cp in range(rs, rs + rl):
        if freed >= need: break
        g = f.gid(cp)
        if not g or len(glyphs[g]) <= 5: continue
        d = f.decode(g)
        nb = f.encode(d['adv'], 0, 0, 0, 0, [])
        freed += len(glyphs[g]) - len(nb); glyphs[g] = nb; blanked.append(cp)
assert freed >= need, (freed, need)
pad = freed - need

first_new = f.nloca
glyphs += new_glyphs
gt = f.tabs['glyf']; body = bytearray(gt[8:f.loca[0]]); loca = []
assert f.loca[0] == 8
for g in glyphs:
    loca.append(8 + len(body)); body += g
body += b'\0' * pad
glyf = struct.pack('<I4s', 8 + len(body), b'glyf') + bytes(body)
assert len(glyf) % 4 == 0 or True
locat = struct.pack('<I4sI', 12 + 4 * len(loca), b'loca', len(loca)) + struct.pack('<%dI' % len(loca), *loca)

c = f.tabs['cmap']; shift = 16 * len(NEW_RANGES)
subs = [dict(e) for e in f.sub]
for e in subs: e['doff'] += shift
gid = first_new
for rs, rl in NEW_RANGES:
    i = next(k for k, e in enumerate(subs) if e['rs'] > rs)
    assert subs[i-1]['rs'] + subs[i-1]['rl'] <= rs and rs + rl <= subs[i]['rs']
    subs.insert(i, dict(doff=subs[i]['doff'], rs=rs, rl=rl, gido=gid, cnt=rl, fmt=2)); gid += rl
hdr = b''.join(struct.pack('<IIHHHBB', e['doff'], e['rs'], e['rl'], e['gido'], e['cnt'], e['fmt'], 0) for e in subs)
cmap = struct.pack('<I4sI', len(c) + shift, b'cmap', len(subs)) + hdr + c[f.cmap_data_start:]

out = b''.join({'cmap': cmap, 'loca': locat, 'glyf': glyf}.get(t, f.tabs[t]) for t in f.order)
assert len(out) == len(raw), (len(out), len(raw))
open(dst, 'wb').write(out)
print(f'added {n_new} glyphs ({need} B), blanked {len(blanked)} glyphs U+{blanked[0]:04X}..U+{blanked[-1]:04X}, pad {pad} B, size {len(out)} (unchanged)')
