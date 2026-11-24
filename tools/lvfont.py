"""LVGL binary font (lv_font_conv 'bin') reader/writer helpers. bpp/compression per head table."""
import struct

class Bits:
    def __init__(s, data, pos=0): s.d = data; s.p = pos
    def get(s, n):
        v = 0
        for _ in range(n):
            v = (v << 1) | ((s.d[s.p >> 3] >> (7 - (s.p & 7))) & 1); s.p += 1
        return v
    def sget(s, n):
        v = s.get(n)
        return v - (1 << n) if v >> (n - 1) else v

class BitW:
    def __init__(s): s.bits = []
    def put(s, v, n):
        for i in range(n - 1, -1, -1): s.bits.append((v >> i) & 1)
    def bytes(s):
        b = s.bits + [0] * (-len(s.bits) % 8)
        return bytes(int(''.join(map(str, b[i:i+8])), 2) for i in range(0, len(b), 8))

class Font:
    def __init__(s, data):
        s.raw = data; pos = 0; s.tabs = {}; s.order = []
        while pos < len(data):
            ln, tag = struct.unpack('<I4s', data[pos:pos+8])
            s.tabs[tag.decode()] = data[pos:pos+ln]; s.order.append(tag.decode()); pos += ln
        assert pos == len(data)
        h = s.tabs['head']
        (s.i2l, s.gidf, s.advf, s.bpp, s.xyb, s.whb, s.advb, s.comp) = struct.unpack('<8B', h[0x22:0x2a])
        assert (s.i2l, s.bpp, s.comp) == (1, 2, 1)
        c = s.tabs['cmap']; n = struct.unpack('<I', c[8:12])[0]
        s.sub = []
        for i in range(n):
            doff, rs, rl, gido, cnt, fmt = struct.unpack('<IIHHHB', c[12+i*16:12+i*16+15])
            s.sub.append(dict(doff=doff, rs=rs, rl=rl, gido=gido, cnt=cnt, fmt=fmt))
        s.cmap_data_start = 12 + n * 16
        l = s.tabs['loca']; s.nloca = struct.unpack('<I', l[8:12])[0]
        s.loca = list(struct.unpack('<%dI' % s.nloca, l[12:12+4*s.nloca]))
    def gid(s, cp):
        c = s.tabs['cmap']
        for e in s.sub:
            r = cp - e['rs']
            if r < 0 or r >= e['rl']: continue
            if e['fmt'] == 2: return e['gido'] + r
            if e['fmt'] == 0: return e['gido'] + c[e['doff'] + r]
            cps = struct.unpack('<%dH' % e['cnt'], c[e['doff']:e['doff']+2*e['cnt']])
            if r in cps:
                k = cps.index(r)
                if e['fmt'] == 3: return e['gido'] + k
                return e['gido'] + struct.unpack('<H', c[e['doff']+2*e['cnt']+2*k:][:2])[0]
        return 0
    def glyph_bytes(s, gid):
        g = s.tabs['glyf']
        end = s.loca[gid+1] if gid + 1 < s.nloca else len(g)
        return g[s.loca[gid]:end]
    def decode(s, gid):
        d = s.glyph_bytes(gid); b = Bits(d + b'\0\0\0\0')
        adv = b.get(s.advb); x = b.sget(s.xyb); y = b.sget(s.xyb); w = b.get(s.whb); h = b.get(s.whb)
        px, used = rle_decode(b, w, h, s.bpp)
        return dict(adv=adv, x=x, y=y, w=w, h=h, px=px, bits=b.p, nbytes=len(d))
    def encode(s, adv, x, y, w, h, px):
        o = BitW(); o.put(adv, s.advb); o.put(x & ((1 << s.xyb) - 1), s.xyb); o.put(y & ((1 << s.xyb) - 1), s.xyb)
        o.put(w, s.whb); o.put(h, s.whb)
        rle_encode(o, px, w, h, s.bpp)
        return o.bytes()

def rle_decode(b, w, h, bpp):
    n = w * h; out = []; state = 0; prev = 0; cnt = 0; start = b.p
    def nxt():
        nonlocal state, prev, cnt
        if state == 0:
            r = b.get(bpp)
            if b.p - bpp != start and prev == r: cnt = 0; state = 1
            prev = r; return r
        if state == 1:
            v = b.get(1); cnt += 1
            if v == 1:
                r = prev
                if cnt == 11:
                    cnt = b.get(6)
                    if cnt != 0: state = 2
                    else: r = b.get(bpp); prev = r; state = 0
                return r
            r = b.get(bpp); prev = r; state = 0; return r
        r = prev; cnt -= 1
        if cnt == 0: r = b.get(bpp); prev = r; state = 0
        return r
    lines = []
    for yy in range(h):
        line = [nxt() for _ in range(w)]
        if yy: line = [a ^ c for a, c in zip(line, lines[-1])]
        lines.append(line)
    return lines, b.p - start

def rle_encode(o, lines, w, h, bpp):
    px = []
    for yy in range(h):
        px += lines[yy] if yy == 0 else [a ^ c for a, c in zip(lines[yy], lines[yy-1])]
    off = 0
    while off < len(px):
        p = px[off]; same = 1
        while off + same < len(px) and px[off+same] == p: same += 1
        same = min(same, 63 + 10 + 1 + 1)
        off += same
        o.put(p, bpp)
        if same <= 1: continue
        same -= 1
        o.put(p, bpp)
        if same <= 10:
            for i in range(same): o.put(1 if i < same - 1 else 0, 1)
            continue
        same -= 11
        for _ in range(11): o.put(1, 1)
        o.put(same, 6)
