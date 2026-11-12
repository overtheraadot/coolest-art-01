#!/usr/bin/env python3
"""Koi Through the Torii -- make.fun coolest-art-01 entry.

Draws a single 1024x1024 PNG with nothing but the Python 3 standard
library (zlib for the PNG encoder). No files are read, no network is
touched, and a fixed seed makes the output byte-identical on every run.

The scene: a colossal white-and-orange koi arcs out of still water and
through a vermilion torii gate at dusk, under a crescent moon. Big
shapes, a small palette, no text -- it has to read at a glance and
still land at ~300 px.
"""

import math
import os
import struct
import zlib
from random import Random

SIZE = 1024
HORIZON = 884          # y where sky ends and water begins
SEED = 20261112


# ---------------------------------------------------------------- palette
class Pal:
    SKY = [  # (stop, rgb) gradient, top -> horizon
        (0.00, (10, 15, 55)),
        (0.40, (27, 23, 79)),
        (0.72, (72, 36, 97)),
        (1.00, (140, 60, 92)),
    ]
    RIDGE = (22, 17, 60)
    MOON = (247, 232, 178)
    MOON_EDGE = (255, 247, 219)
    GLOW = (255, 232, 166)
    GATE = (216, 55, 42)
    GATE_LT = (243, 98, 76)
    GATE_DK = (124, 26, 17)
    GATE_TOP = (25, 17, 15)
    KOI_BODY = (248, 243, 231)
    KOI_SPOT = (233, 92, 37)
    KOI_INK = (44, 44, 52)
    KOI_RIM = (43, 32, 27)
    FIN = (250, 213, 179)
    WATER_HI = (12, 44, 60)
    WATER_LO = (6, 17, 30)
    SHIMMER = (64, 144, 170)
    BLOSSOM = (243, 168, 196)
    HAZE = (203, 108, 140)
    SPRAY = (236, 246, 251)


# ---------------------------------------------------------------- canvas
class Canvas:
    """A flat RGB buffer with a few scanline drawing primitives."""

    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.px = bytearray(w * h * 3)

    def hline(self, y, x0, x1, rgb):
        if y < 0 or y >= self.h:
            return
        x0 = max(0, int(x0))
        x1 = min(self.w - 1, int(x1))
        if x1 < x0:
            return
        n = x1 - x0 + 1
        i = (y * self.w + x0) * 3
        self.px[i:i + 3 * n] = bytes(rgb) * n

    def hline_alpha(self, y, x0, x1, rgb, alpha):
        if y < 0 or y >= self.h or alpha <= 0.0:
            return
        if alpha >= 1.0:
            self.hline(y, x0, x1, rgb)
            return
        x0 = max(0, int(x0))
        x1 = min(self.w - 1, int(x1))
        if x1 < x0:
            return
        a = int(alpha * 256)
        ia = 256 - a
        r, g, b = rgb
        i = (y * self.w + x0) * 3
        for _ in range(x1 - x0 + 1):
            self.px[i] = (r * a + self.px[i] * ia) >> 8
            self.px[i + 1] = (g * a + self.px[i + 1] * ia) >> 8
            self.px[i + 2] = (b * a + self.px[i + 2] * ia) >> 8
            i += 3

    def dot(self, x, y, rgb, alpha=1.0):
        if 0 <= x < self.w and 0 <= y < self.h and alpha > 0.0:
            a = int(alpha * 256)
            ia = 256 - a
            i = (y * self.w + x) * 3
            self.px[i] = (rgb[0] * a + self.px[i] * ia) >> 8
            self.px[i + 1] = (rgb[1] * a + self.px[i + 1] * ia) >> 8
            self.px[i + 2] = (rgb[2] * a + self.px[i + 2] * ia) >> 8

    def disc(self, cx, cy, r, rgb, alpha=1.0):
        r = int(r)
        for y in range(max(0, cy - r), min(self.h - 1, cy + r) + 1):
            dy = y - cy
            dx = int(math.sqrt(max(0, r * r - dy * dy)))
            self.hline_alpha(y, cx - dx, cx + dx, rgb, alpha)

    def ellipse(self, cx, cy, rx, ry, rgb, alpha=1.0):
        rx, ry = int(rx), int(ry)
        for y in range(max(0, cy - ry), min(self.h - 1, cy + ry) + 1):
            t = (y - cy) / ry
            dx = int(rx * math.sqrt(max(0.0, 1.0 - t * t)))
            self.hline_alpha(y, cx - dx, cx + dx, rgb, alpha)

    def poly(self, pts, rgb, alpha=1.0):
        """Scanline polygon fill."""
        edges = []
        n = len(pts)
        for i in range(n):
            x0, y0 = pts[i]
            x1, y1 = pts[(i + 1) % n]
            if y0 != y1:
                edges.append((y0, y1, x0, x1))
        ymin = max(0, int(min(p[1] for p in pts)))
        ymax = min(self.h - 1, int(max(p[1] for p in pts)))
        for y in range(ymin, ymax + 1):
            xs = []
            for y0, y1, x0, x1 in edges:
                if (y0 <= y < y1) or (y1 <= y < y0):
                    xs.append(x0 + (y - y0) / (y1 - y0) * (x1 - x0))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                self.hline_alpha(y, math.ceil(xs[i]), math.floor(xs[i + 1]),
                                 rgb, alpha)

    def glow(self, cx, cy, r, rgb, peak):
        """Soft radial glow, quadratic falloff."""
        r2 = r * r
        R, G, B = rgb
        for y in range(max(0, cy - r), min(self.h - 1, cy + r) + 1):
            dy = y - cy
            dy2 = dy * dy
            span = int(math.sqrt(max(0, r2 - dy2)))
            for x in range(max(0, cx - span), min(self.w - 1, cx + span) + 1):
                dx = x - cx
                f = 1.0 - (dx * dx + dy2) / r2
                if f <= 0.0:
                    continue
                a = int(peak * f * f * 256)
                if a <= 0:
                    continue
                ia = 256 - a
                i = (y * self.w + x) * 3
                self.px[i] = (R * a + self.px[i] * ia) >> 8
                self.px[i + 1] = (G * a + self.px[i + 1] * ia) >> 8
                self.px[i + 2] = (B * a + self.px[i + 2] * ia) >> 8

    def thick_polyline(self, pts, radius, rgb, alpha=1.0):
        for x, y in pts:
            self.disc(x, y, radius, rgb, alpha)


def quad_bezier(p0, p1, p2, steps):
    pts = []
    for i in range(steps + 1):
        t = i / steps
        u = 1.0 - t
        pts.append((
            int(u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0]),
            int(u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1]),
        ))
    return pts


def lerp_stops(stops, t):
    for i in range(len(stops) - 1):
        t0, c0 = stops[i]
        t1, c1 = stops[i + 1]
        if t <= t1:
            f = 0.0 if t1 == t0 else (t - t0) / (t1 - t0)
            return tuple(int(c0[k] + (c1[k] - c0[k]) * f) for k in range(3))
    return stops[-1][1]


# ---------------------------------------------------------------- scene
def paint_sky(cv):
    for y in range(HORIZON):
        cv.hline(y, 0, SIZE - 1, lerp_stops(Pal.SKY, y / HORIZON))


def paint_stars(cv, rng):
    for _ in range(160):
        x = rng.randrange(0, SIZE)
        y = rng.randrange(0, 690)
        if (x - 800) ** 2 + (y - 170) ** 2 < 155 ** 2:
            continue
        b = rng.choice([140, 175, 205, 235, 255])
        cv.disc(x, y, rng.choice([1, 1, 1, 2]),
                (b, b, min(255, b + 18)), rng.uniform(0.35, 0.9))


def paint_moon(cv):
    cv.glow(800, 170, 265, Pal.GLOW, 0.30)
    cx, cy, r = 800, 170, 86
    ox, oy, orr = 758, 142, 78          # offset disc that cuts the crescent
    for y in range(cy - r, cy + r + 1):
        dy = y - cy
        dx = int(math.sqrt(max(0, r * r - dy * dy)))
        x0, x1 = cx - dx, cx + dx
        dy2 = y - oy
        if abs(dy2) < orr:
            dx2 = int(math.sqrt(max(0, orr * orr - dy2 * dy2)))
            cut = ox + dx2
            if cut > x0:
                x0 = cut
        if x1 >= x0:
            cv.hline(y, x0, x1, Pal.MOON)
    # bright rim on the crescent's outer edge
    for y in range(cy - r, cy + r + 1):
        dy = y - cy
        dx = int(math.sqrt(max(0, r * r - dy * dy)))
        cv.dot(cx + dx, y, Pal.MOON_EDGE, 0.85)
        cv.dot(cx + dx - 1, y, Pal.MOON_EDGE, 0.45)


def paint_haze(cv):
    for cx, cy, rx, ry, a in [
        (240, 655, 270, 18, 0.06),
        (770, 715, 310, 20, 0.07),
        (520, 782, 230, 15, 0.05),
    ]:
        cv.ellipse(cx, cy, rx, ry, Pal.HAZE, a)


def paint_ridge(cv):
    pts = [
        (0, HORIZON), (0, 836), (118, 790), (212, 824), (330, 760),
        (428, 808), (560, 746), (682, 802), (800, 764), (922, 814),
        (SIZE, 780), (SIZE, HORIZON),
    ]
    cv.poly(pts, Pal.RIDGE)


def paint_gate(cv):
    """Vermilion torii: two curved lintels, centre strut, two pillars."""

    def beam(x0, x1, y_mid, thick, lift, rgb):
        # top edge rises toward the ends (upturned kasagi)
        top = []
        for i in range(25):
            x = x0 + (x1 - x0) * i / 24
            f = ((x - SIZE / 2) / ((x1 - x0) / 2)) ** 2
            top.append((int(x), int(y_mid - lift * f)))
        top.append((x1, y_mid + thick))
        top.append((x0, y_mid + thick))
        cv.poly(top, rgb)

    cv.glow(SIZE // 2, 520, 300, (255, 179, 71), 0.13)   # warm halo
    beam(168, 856, 468, 14, 44, Pal.GATE_TOP)             # black cap
    beam(172, 852, 480, 36, 44, Pal.GATE)                # kasagi
    beam(172, 852, 480, 14, 44, Pal.GATE_LT)             # kasagi highlight
    beam(230, 794, 562, 30, 10, Pal.GATE)                # shimaki
    cv.poly([(498, 516), (526, 516), (526, 562), (498, 562)], Pal.GATE)
    # pillars, slightly tapered, standing in the water
    cv.poly([(264, 546), (318, 546), (324, 910), (258, 910)], Pal.GATE)
    cv.poly([(706, 546), (760, 546), (766, 910), (700, 910)], Pal.GATE)
    # light on the inner edge, shade on the outer edge
    cv.poly([(264, 546), (274, 546), (278, 910), (270, 910)], Pal.GATE_LT)
    cv.poly([(706, 546), (716, 546), (718, 910), (710, 910)], Pal.GATE_LT)
    cv.poly([(308, 546), (318, 546), (324, 910), (316, 910)], Pal.GATE_DK)
    cv.poly([(750, 546), (760, 546), (766, 910), (758, 910)], Pal.GATE_DK)


def paint_water(cv, rng):
    for y in range(HORIZON, SIZE):
        t = (y - HORIZON) / (SIZE - HORIZON)
        c = tuple(int(Pal.WATER_HI[k] + (Pal.WATER_LO[k] - Pal.WATER_HI[k]) * t)
                  for k in range(3))
        cv.hline(y, 0, SIZE - 1, c)
    cv.hline_alpha(HORIZON, 0, SIZE - 1, Pal.SHIMMER, 0.55)
    cv.hline_alpha(HORIZON + 1, 0, SIZE - 1, Pal.SHIMMER, 0.25)
    # pillar reflections, fading with depth
    for x0, x1 in [(260, 322), (702, 762)]:
        for y in range(HORIZON + 2, 1000):
            f = 1.0 - (y - HORIZON) / 130.0
            cv.hline_alpha(y, x0, x1, Pal.GATE, 0.16 * f)
    # moon shimmer: stacked gold dashes, widening and fading downwards
    for k, y in enumerate(range(HORIZON + 4, 1022, 11)):
        f = 1.0 - (y - HORIZON) / 170.0
        if f <= 0:
            break
        wob = int(14 * math.sin(y * 0.09))
        half = int(34 * f + 8)
        cv.hline_alpha(y, 800 + wob - half, 800 + wob + half, Pal.MOON,
                       0.30 * f * (0.6 + 0.4 * ((k * 7) % 3) / 2.0))
    # drifting ripple strokes
    for _ in range(34):
        y = rng.randrange(HORIZON + 8, 1018)
        x = rng.randrange(20, 900)
        ln = rng.randrange(20, 95)
        cv.hline_alpha(y, x, x + ln, Pal.SHIMMER, rng.uniform(0.15, 0.5))


def tapered_ribbon(cv, p0, p1, p2, w0, rgb, alpha=0.9):
    """Slim fin: a Bezier spine whose width tapers to the tip."""
    spine = quad_bezier(p0, p1, p2, 16)
    left, right = [], []
    n = len(spine)
    for i, (x, y) in enumerate(spine):
        j = min(i + 1, n - 1)
        k = max(i - 1, 0)
        dx = spine[j][0] - spine[k][0]
        dy = spine[j][1] - spine[k][1]
        ln = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / ln, dx / ln
        w = w0 * (1.0 - i / (n - 1)) + 2.0
        left.append((int(x + nx * w), int(y + ny * w)))
        right.append((int(x - nx * w), int(y - ny * w)))
    cv.poly(left + list(reversed(right)), rgb, alpha)


def paint_koi(cv, rng):
    # Spine: tail low-left in open water (clear of the left pillar),
    # arcing up through the gate.
    spine = quad_bezier((232, 866), (410, 470), (718, 386), 90)
    # radius profile along the spine: slim tail -> fat belly -> head
    PROF = [(0.00, 13), (0.30, 62), (0.55, 78), (0.80, 64), (1.00, 52)]

    def radius_at(t):
        for i in range(len(PROF) - 1):
            t0, r0 = PROF[i]
            t1, r1 = PROF[i + 1]
            if t <= t1:
                f = 0.0 if t1 == t0 else (t - t0) / (t1 - t0)
                return r0 + (r1 - r0) * f
        return PROF[-1][1]

    # head direction: unit tangent at the snout, and its perpendicular
    hx, hy = spine[-1]
    tx = spine[-1][0] - spine[-6][0]
    ty = spine[-1][1] - spine[-6][1]
    tl = math.hypot(tx, ty)
    tx, ty = tx / tl, ty / tl
    px, py = -ty, tx
    snout = (hx + int(tx * 52), hy + int(ty * 52))

    # tail fins: two tapered ribbons trailing behind the tail
    tail = spine[0]
    tapered_ribbon(cv, (tail[0] - 4, tail[1] - 6), (tail[0] - 70, tail[1] - 42),
                   (tail[0] - 118, tail[1] - 8), 15, Pal.FIN, 0.88)
    tapered_ribbon(cv, (tail[0] - 2, tail[1] + 4), (tail[0] - 44, tail[1] + 48),
                   (tail[0] - 72, tail[1] + 82), 19, Pal.KOI_SPOT, 0.88)

    # dorsal finlets along the upper spine
    for t in (0.30, 0.45, 0.60):
        i = int(t * 90)
        x, y = spine[i]
        r = radius_at(t)
        cv.poly([(x - 14, y - r + 6), (x + 16, y - r + 4),
                 (x + 4, y - r - 34)], Pal.KOI_SPOT, 0.92)

    # body: dark rim pass, then the white body
    for grow, col in ((5, Pal.KOI_RIM), (0, Pal.KOI_BODY)):
        for i, (x, y) in enumerate(spine):
            cv.disc(x, y, int(radius_at(i / 90.0)) + grow, col)

    # head: a rounded ellipse past the spine end, rim arc on the snout side
    hcx = hx + int(tx * 16)
    hcy = hy + int(ty * 16)
    hang = math.atan2(ty, tx)
    ca, sa = math.cos(hang), math.sin(hang)
    head_pts = []
    for k in range(28):
        th = 2 * math.pi * k / 28
        ex, ey = 57 * math.cos(th), 45 * math.sin(th)
        head_pts.append((int(hcx + ex * ca - ey * sa),
                         int(hcy + ex * sa + ey * ca)))
    cv.poly(head_pts, Pal.KOI_BODY)
    arc = []
    for k in range(17):
        th = hang - 1.1 + 2.2 * k / 16
        ex, ey = 59 * math.cos(th), 47 * math.sin(th)
        arc.append((int(hcx + ex * ca - ey * sa),
                    int(hcy + ex * sa + ey * ca)))
    cv.thick_polyline(arc, 3, Pal.KOI_RIM)

    # orange patches: irregular blotches centred on the spine
    for t, frac, col, phase in [
        (0.30, 0.58, Pal.KOI_SPOT, 0.7),
        (0.52, 0.66, Pal.KOI_SPOT, 2.1),
        (0.70, 0.58, Pal.KOI_SPOT, 4.0),
        (0.86, 0.52, Pal.KOI_SPOT, 5.3),
        (0.62, 0.24, Pal.KOI_INK, 1.2),
    ]:
        i = int(t * 90)
        x, y = spine[i]
        r = radius_at(t) * frac
        pts = []
        for k in range(20):
            th = 2 * math.pi * k / 20
            mod = 1.0 + 0.10 * math.sin(3 * th + phase) \
                + 0.06 * math.sin(5 * th + phase * 2)
            pts.append((int(x + r * 1.10 * math.cos(th) * mod),
                        int(y - int(r * 0.15) + r * 0.78 * math.sin(th) * mod)))
        cv.poly(pts, col)

    # pectoral fin tucked under the belly, sweeping back down-left
    b1 = (hcx - int(tx * 30) + int(px * 38), hcy - int(ty * 30) + int(py * 38))
    b2 = (hcx - int(tx * 58) + int(px * 46), hcy - int(ty * 58) + int(py * 46))
    tip = (hcx - int(tx * 78) + int(px * 96), hcy - int(ty * 78) + int(py * 96))
    cv.poly([b1, tip, b2], Pal.KOI_SPOT, 0.92)

    # face: eye with glint, gill arc, mouth dot, two whiskers
    ex = int(hcx + tx * 22 + px * -16)
    ey = int(hcy + ty * 22 + py * -16)
    cv.disc(ex, ey, 10, Pal.KOI_INK)
    cv.disc(ex + 3, ey - 3, 3, (255, 255, 255))
    gill = quad_bezier(
        (hcx - int(tx * 8) + int(px * -38), hcy - int(ty * 8) + int(py * -38)),
        (hcx - int(tx * 34) + int(px * -8), hcy - int(ty * 34) + int(py * -8)),
        (hcx - int(tx * 6) + int(px * 30), hcy - int(ty * 6) + int(py * 30)),
        16)
    cv.thick_polyline(gill, 3, Pal.KOI_SPOT, 0.85)
    cv.disc(snout[0] - 2, snout[1] + 2, 3, Pal.KOI_INK)
    w1 = quad_bezier(snout, (snout[0] + 38, snout[1] - 10),
                     (snout[0] + 72, snout[1] - 34), 14)
    w2 = quad_bezier(snout, (snout[0] + 34, snout[1] + 14),
                     (snout[0] + 60, snout[1] + 42), 14)
    cv.thick_polyline(w1, 2, Pal.KOI_INK, 0.9)
    cv.thick_polyline(w2, 2, Pal.KOI_INK, 0.9)


def paint_splash(cv, rng):
    cx, cy = 232, 866
    for _ in range(26):
        ang = rng.uniform(math.pi * 0.9, math.pi * 2.0)
        d = rng.uniform(10, 95)
        x = int(cx + d * math.cos(ang) * 1.4)
        y = int(cy + d * math.sin(ang) * 0.55)
        cv.disc(x, y, rng.choice([2, 3, 3, 4, 5]), Pal.SPRAY,
                rng.uniform(0.5, 0.95))
    cv.ellipse(200, 876, 40, 9, Pal.SPRAY, 0.28)
    cv.ellipse(264, 880, 32, 8, Pal.SPRAY, 0.22)


def paint_blossoms(cv, rng):
    for _ in range(11):
        x = rng.randrange(40, 980)
        y = rng.randrange(60, 700)
        if (x - 718) ** 2 + (y - 386) ** 2 < 90 ** 2:
            continue
        if (x - 800) ** 2 + (y - 170) ** 2 < 115 ** 2:
            continue  # keep petals off the moon
        ang = rng.uniform(0, math.pi)
        rx, ry = rng.choice([(13, 7), (16, 8), (11, 6)])
        ca, sa = math.cos(ang), math.sin(ang)
        pts = []
        for k in range(20):
            th = 2 * math.pi * k / 20
            ex, ey = rx * math.cos(th), ry * math.sin(th)
            pts.append((int(x + ex * ca - ey * sa), int(y + ex * sa + ey * ca)))
        cv.poly(pts, Pal.BLOSSOM, 0.9)


# ---------------------------------------------------------------- PNG out
def encode_png(cv):
    raw = bytearray()
    for y in range(cv.h):
        raw.append(0)  # filter: none
        raw += cv.px[y * cv.w * 3:(y + 1) * cv.w * 3]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(tag, data):
        out = struct.pack(">I", len(data)) + tag + data
        return out + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", comp)
    png += chunk(b"IEND", b"")
    return png


def main():
    rng = Random(SEED)
    cv = Canvas(SIZE, SIZE)
    paint_sky(cv)
    paint_haze(cv)
    paint_stars(cv, rng)
    paint_moon(cv)
    paint_ridge(cv)
    paint_gate(cv)
    paint_water(cv, rng)
    paint_koi(cv, rng)
    paint_splash(cv, rng)
    paint_blossoms(cv, rng)

    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", ".")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.png")
    data = encode_png(cv)
    with open(path, "wb") as f:
        f.write(data)
    print(f"wrote {path} ({len(data)} bytes)")


if __name__ == "__main__":
    main()
