"""Build a Solar-System style GitHub profile README from a resume.

Run:  python tools/build.py

Writes README.md, preview.html and assets/*.svg. Everything is local and
self-contained: no hosted service, no tracking, no paywall.
"""
import os
import re
import math
import base64
import datetime
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
CACHE = os.path.join(ROOT, "tools", "cache")
os.makedirs(ASSETS, exist_ok=True)
os.makedirs(CACHE, exist_ok=True)

FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"
MONO = "'SFMono-Regular',Consolas,'Liberation Mono',Menlo,monospace"

TXT, MUT = "#e6edf3", "#8b949e"
BLUE, GREEN, PURPLE, CYAN, ORANGE, GOLD = "#58a6ff", "#3fb950", "#a371f7", "#22d3ee", "#f0883e", "#f2c14e"
EDGE = "#30363d"

AVATAR_URL = "https://avatars.githubusercontent.com/u/132209138?s=200&v=4"


# --------------------------------------------------------------------------- #
# utils
# --------------------------------------------------------------------------- #
def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def prng(seed):
    x = seed & 0x7FFFFFFF

    def nxt():
        nonlocal x
        x = (1103515245 * x + 12345) & 0x7FFFFFFF
        return x / 0x7FFFFFFF
    return nxt


def wrap(s, max_chars):
    out, cur = [], ""
    for w in s.split():
        trial = (cur + " " + w).strip()
        if len(trial) <= max_chars:
            cur = trial
        else:
            if cur:
                out.append(cur)
            cur = w
    if cur:
        out.append(cur)
    return out


def txt(x, y, s, size=13, weight=400, fill=TXT, ls=0, anchor="start",
        opacity=1, font=FONT, halo=False):
    a = f' text-anchor="{anchor}"' if anchor != "start" else ""
    o = f' fill-opacity="{opacity}"' if opacity != 1 else ""
    l = f' letter-spacing="{ls}"' if ls else ""
    # dark outline so labels stay legible over stars, lanes and comet tails
    h = (' paint-order="stroke" stroke="#05070e" stroke-width="3.2" '
         'stroke-opacity="0.9" stroke-linejoin="round"') if halo else ""
    return (f'  <text x="{x}" y="{y}" font-family="{font}" font-size="{size}" '
            f'font-weight="{weight}"{l}{h} fill="{fill}"{a}{o}>{esc(s)}</text>\n')


def space_defs(uid, w, h):
    """Shared space background defs: an outward radial gradient plus nebula."""
    return f"""  <defs>
    <radialGradient id="{uid}-bg" cx="50%" cy="44%" r="78%">
      <stop offset="0%" stop-color="#131e36"/>
      <stop offset="34%" stop-color="#0b1220"/>
      <stop offset="68%" stop-color="#070b14"/>
      <stop offset="100%" stop-color="#03050a"/>
    </radialGradient>
    <radialGradient id="{uid}-neb0">
      <stop offset="0%" stop-color="{PURPLE}" stop-opacity="0.26"/>
      <stop offset="55%" stop-color="{PURPLE}" stop-opacity="0.07"/>
      <stop offset="100%" stop-color="{PURPLE}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="{uid}-neb1">
      <stop offset="0%" stop-color="{BLUE}" stop-opacity="0.22"/>
      <stop offset="55%" stop-color="{BLUE}" stop-opacity="0.06"/>
      <stop offset="100%" stop-color="{BLUE}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="{uid}-neb2">
      <stop offset="0%" stop-color="{CYAN}" stop-opacity="0.14"/>
      <stop offset="60%" stop-color="{CYAN}" stop-opacity="0.04"/>
      <stop offset="100%" stop-color="{CYAN}" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="{uid}-edge" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{BLUE}" stop-opacity="0.55"/>
      <stop offset="50%" stop-color="{PURPLE}" stop-opacity="0.30"/>
      <stop offset="100%" stop-color="{CYAN}" stop-opacity="0.40"/>
    </linearGradient>
  </defs>
"""


def space_fill(uid, w, h, rx=20):
    """Background plate: outward gradient + soft nebula blooms."""
    return (f'  <rect width="{w}" height="{h}" rx="{rx}" fill="url(#{uid}-bg)"/>\n'
            f'  <ellipse cx="{int(w * 0.22)}" cy="{int(h * 0.28)}" rx="{int(w * 0.42)}" '
            f'ry="{int(h * 0.6)}" fill="url(#{uid}-neb0)"/>\n'
            f'  <ellipse cx="{int(w * 0.8)}" cy="{int(h * 0.72)}" rx="{int(w * 0.4)}" '
            f'ry="{int(h * 0.55)}" fill="url(#{uid}-neb1)"/>\n'
            f'  <ellipse cx="{int(w * 0.52)}" cy="{int(h * 0.98)}" rx="{int(w * 0.34)}" '
            f'ry="{int(h * 0.32)}" fill="url(#{uid}-neb2)"/>\n')


def stars(uid, w, h, count=150, seed=7, skip=None, twinkle=23):
    """Deterministic starfield. skip = (cx, cy, r) region to leave empty."""
    rnd = prng(seed)
    out = []
    for i in range(count):
        x = 18 + rnd() * (w - 36)
        y = 18 + rnd() * (h - 36)
        if skip and math.hypot(x - skip[0], y - skip[1]) < skip[2]:
            continue
        r = 0.6 + rnd() * 1.25
        op = 0.18 + rnd() * 0.5
        if i % twinkle == 0:
            out.append(
                f'  <circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.2f}" fill="#ffffff" fill-opacity="{op:.2f}">'
                f'<animate attributeName="fill-opacity" values="{op:.2f};{min(0.95, op + 0.45):.2f};{op:.2f}" '
                f'dur="{3 + rnd() * 5:.1f}s" repeatCount="indefinite"/></circle>\n')
        else:
            out.append(f'  <circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.2f}" fill="#ffffff" fill-opacity="{op:.2f}"/>\n')
    return "".join(out)


def get_avatar_b64():
    cached = os.path.join(CACHE, "avatar.b64")
    if os.path.exists(cached):
        return open(cached, encoding="utf-8").read().strip()
    req = urllib.request.Request(AVATAR_URL, headers={"User-Agent": "Mozilla/5.0"})
    raw = urllib.request.urlopen(req, timeout=30).read()
    try:
        from PIL import Image
        import io
        im = Image.open(io.BytesIO(raw)).convert("RGB").resize((200, 200), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=86, optimize=True)
        raw = buf.getvalue()
        mime = "image/jpeg"
    except Exception:
        mime = "image/png"
    b64 = f"data:{mime};base64," + base64.b64encode(raw).decode("ascii")
    open(cached, "w", encoding="utf-8").write(b64)
    return b64


# --------------------------------------------------------------------------- #
# 1. hero: the solar system
# --------------------------------------------------------------------------- #
# key, name, capability, base, light, dark, orbit rx, angle, radius, period, moons, rings
PLANETS = [
    ("merc", "Mercury", "AI Agents & MCP", "#958a7d", "#dcd2c7", "#3b352f", 112, 195, 4.4, 72, 0, False),
    ("ven", "Venus", "LLM Evals & RAG", "#d9b46b", "#f7e5b6", "#7a5c2b", 140, 330, 6.2, 96, 0, False),
    ("ear", "Earth", "AI Product", "#3f7fd0", "#8fd0ff", "#0f3159", 168, 45, 6.4, 120, 1, False),
    ("mar", "Mars", "Rust & Python", "#c1552f", "#ef8f63", "#5d2510", 196, 140, 5.0, 150, 2, False),
    ("jup", "Jupiter", "Data & Analytics", "#d8a76b", "#f4d9b3", "#7d562e", 258, 235, 12.6, 190, 4, False),
    ("sat", "Saturn", "XAI Research", "#e3c98d", "#f8eec8", "#987a3b", 312, 70, 10.4, 230, 0, True),
    ("ura", "Uranus", "Cloud & Infra", "#7fd6da", "#c8f6f7", "#2f7379", 358, 320, 7.4, 270, 0, False),
    ("nep", "Neptune", "Prompt Engineering", "#3f63d0", "#8aa4f6", "#192a72", 396, 175, 7.2, 310, 0, False),
]
# orbits are viewed at an incline, so every ellipse is squashed by the same factor
ORBIT_SQUASH = 0.475

# where each tag sits: (text-anchor, dx, dy) measured from the planet centre
TAGS = {
    "merc": ("end", -17, 0),
    "ven": ("start", 17, 0),
    "ear": ("start", 17, 0),
    "mar": ("end", -17, 0),
    "jup": ("end", -17, 0),
    "sat": ("start", 17, 0),
    "ura": ("start", 17, 0),
    "nep": ("middle", 0, 30),
}


def ellipse_path(rx, ry, deg):
    """Full ellipse path that starts at local (0, 0), for animateMotion."""
    a = math.radians(deg)
    ox, oy = -rx * math.cos(a), -ry * math.sin(a)
    return (f"M 0 0 A {rx:.1f} {ry:.1f} 0 1 1 {2 * ox:.1f} {2 * oy:.1f} "
            f"A {rx:.1f} {ry:.1f} 0 1 1 0 0")


def asteroid_belt(cx, cy, rx, ry, count=132, seed=5):
    """The main belt, sitting between Mars and Jupiter."""
    rnd = prng(seed)
    out = []
    for _ in range(count):
        t = rnd() * 2 * math.pi
        k = 0.962 + rnd() * 0.082
        r = 0.45 + rnd() * 1.15
        op = 0.22 + rnd() * 0.46
        out.append(f'  <circle cx="{cx + rx * k * math.cos(t):.1f}" '
                   f'cy="{cy + ry * k * math.sin(t):.1f}" r="{r:.2f}" '
                   f'fill="#c2ad94" fill-opacity="{op:.2f}"/>\n')
    return "".join(out)


def planet_body(uid, p, r, detail=True):
    """A planet centred on (0, 0): glow, rings or bands, and its moons."""
    key, _n, _c, base, light, dark, rx, ang, rad, period, moons, rings = p
    out = f'<circle r="{r * 1.85:.2f}" fill="{base}" fill-opacity="0.16"/>'
    ring = (f'<g transform="rotate(-19)">'
            f'<ellipse rx="{r * 2.08:.2f}" ry="{r * 0.66:.2f}" fill="none" stroke="{light}" '
            f'stroke-opacity="0.58" stroke-width="{max(1.1, r * 0.16):.2f}"/>'
            f'<ellipse rx="{r * 2.46:.2f}" ry="{r * 0.78:.2f}" fill="none" stroke="{base}" '
            f'stroke-opacity="0.20" stroke-width="0.9"/></g>')
    if rings:
        out += f'<g clip-path="url(#{uid}-satback)">{ring}</g>'
    out += f'<circle r="{r:.2f}" fill="url(#{uid}-{key})"/>'
    out += f'<circle r="{r:.2f}" fill="none" stroke="#ffffff" stroke-opacity="0.16" stroke-width="0.6"/>'
    if key == "ear" and detail:
        out += (f'<ellipse cx="{-r * 0.26:.2f}" cy="{-r * 0.12:.2f}" rx="{r * 0.40:.2f}" '
                f'ry="{r * 0.24:.2f}" fill="{GREEN}" fill-opacity="0.6" '
                f'transform="rotate(-24 {-r * 0.26:.2f} {-r * 0.12:.2f})"/>'
                f'<ellipse cx="{r * 0.36:.2f}" cy="{r * 0.30:.2f}" rx="{r * 0.20:.2f}" '
                f'ry="{r * 0.13:.2f}" fill="{GREEN}" fill-opacity="0.5"/>')
    if key == "jup" and detail:
        for by, bw, op, col in ((-0.44, 0.72, 0.20, light), (-0.16, 0.88, 0.16, dark),
                                (0.18, 0.82, 0.18, light), (0.50, 0.56, 0.14, dark)):
            out += (f'<rect x="{-r * bw:.2f}" y="{r * by - r * 0.09:.2f}" '
                    f'width="{2 * r * bw:.2f}" height="{r * 0.18:.2f}" rx="{r * 0.09:.2f}" '
                    f'fill="{col}" fill-opacity="{op}"/>')
    if rings:
        out += f'<g clip-path="url(#{uid}-satfront)">{ring}</g>'
    if moons:
        mr = r + 5.2
        out += (f'<g><animateTransform attributeName="transform" type="rotate" from="0" to="360" '
                f'dur="{10 + period * 0.14:.0f}s" repeatCount="indefinite"/>')
        for m in range(moons):
            ma = math.radians(20 + m * 360 / moons)
            out += (f'<circle cx="{mr * math.cos(ma):.2f}" cy="{mr * math.sin(ma):.2f}" '
                    f'r="{max(0.9, r * 0.17):.2f}" fill="#dbe4ee" fill-opacity="0.9"/>')
        out += '</g>'
    return out


def build_orbits():
    W, H = 1000, 660
    uid = "solar"
    cx, cy = 500, 296

    s = '<?xml version="1.0" encoding="UTF-8"?>\n'
    s += (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
          f'width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
          f'aria-label="Arshdeep Yadav at the centre of a solar system: eight planets in orbital '
          f'order, each labelled with a capability, two comets carrying his IEEE paper and his Cairn '
          f'project, moons for the systems he shipped">\n')

    pg = ""
    for key, _n, _c, base, light, dark, *_ in PLANETS:
        pg += (f'    <radialGradient id="{uid}-{key}" cx="34%" cy="27%" r="82%">\n'
               f'      <stop offset="0%" stop-color="{light}"/>\n'
               f'      <stop offset="46%" stop-color="{base}"/>\n'
               f'      <stop offset="100%" stop-color="{dark}"/>\n'
               f'    </radialGradient>\n')

    s += space_defs(uid, W, H)
    s += f"""  <defs>
{pg}    <radialGradient id="{uid}-sunglow">
      <stop offset="0%" stop-color="{GOLD}" stop-opacity="0.50"/>
      <stop offset="34%" stop-color="{GOLD}" stop-opacity="0.16"/>
      <stop offset="100%" stop-color="{GOLD}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="{uid}-sunbody" cx="36%" cy="30%">
      <stop offset="0%" stop-color="#fff3c4"/>
      <stop offset="52%" stop-color="{GOLD}"/>
      <stop offset="100%" stop-color="#a8720c"/>
    </radialGradient>
    <linearGradient id="{uid}-ray" x1="0" y1="1" x2="0" y2="0">
      <stop offset="0%" stop-color="{GOLD}" stop-opacity="0.34"/>
      <stop offset="45%" stop-color="{GOLD}" stop-opacity="0.20"/>
      <stop offset="100%" stop-color="{GOLD}" stop-opacity="0"/>
    </linearGradient>
    <filter id="{uid}-soft" x="-40%" y="-40%" width="180%" height="180%">
      <feGaussianBlur stdDeviation="2.4"/>
    </filter>
    <linearGradient id="{uid}-comet-a" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="{GOLD}" stop-opacity="0.60"/>
      <stop offset="40%" stop-color="{GOLD}" stop-opacity="0.18"/>
      <stop offset="100%" stop-color="{GOLD}" stop-opacity="0"/>
    </linearGradient>
    <linearGradient id="{uid}-comet-b" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="{CYAN}" stop-opacity="0.60"/>
      <stop offset="40%" stop-color="{CYAN}" stop-opacity="0.18"/>
      <stop offset="100%" stop-color="{CYAN}" stop-opacity="0"/>
    </linearGradient>
    <clipPath id="{uid}-avatar"><circle cx="{cx}" cy="{cy}" r="32"/></clipPath>
    <clipPath id="{uid}-satback" clipPathUnits="userSpaceOnUse">
      <rect x="-90" y="-70" width="180" height="70"/>
    </clipPath>
    <clipPath id="{uid}-satfront" clipPathUnits="userSpaceOnUse">
      <rect x="-90" y="0" width="180" height="70"/>
    </clipPath>
  </defs>
"""

    # deep space plate
    s += f'  <rect width="{W}" height="{H}" rx="22" fill="url(#{uid}-bg)"/>\n'
    s += f'  <ellipse cx="{cx}" cy="{cy}" rx="440" ry="300" fill="url(#{uid}-neb1)"/>\n'
    s += f'  <ellipse cx="160" cy="132" rx="300" ry="220" fill="url(#{uid}-neb0)"/>\n'
    s += f'  <ellipse cx="880" cy="574" rx="280" ry="200" fill="url(#{uid}-neb2)"/>\n'
    s += f'  <ellipse cx="{cx}" cy="{cy}" rx="310" ry="196" fill="url(#{uid}-sunglow)" opacity="0.26"/>\n'
    s += stars(uid, W, H, 130, seed=11, skip=(cx, cy, 76), twinkle=9)

    # orbital lanes, faintly fading with distance
    for i, p in enumerate(PLANETS):
        rx = p[6]
        ry = rx * ORBIT_SQUASH
        op = 0.21 - i * 0.013
        s += (f'  <ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry:.2f}" fill="none" '
              f'stroke="#8fb6e8" stroke-opacity="{op * 0.3:.3f}" stroke-width="2.5"/>\n'
              f'  <ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry:.2f}" fill="none" '
              f'stroke="#a9c6ea" stroke-opacity="{op:.3f}" stroke-width="1"/>\n')

    # main asteroid belt
    s += (f'  <ellipse cx="{cx}" cy="{cy}" rx="226" ry="{226 * ORBIT_SQUASH:.1f}" fill="none" '
          f'stroke="#c2ad94" stroke-opacity="0.07" stroke-width="11"/>\n')
    s += asteroid_belt(cx, cy, 226, 226 * ORBIT_SQUASH, count=132, seed=5)

    # two comets: the paper and a project, drifting across the frame
    # label, sub, colour, gradient id, x1, y1, x2, y2, dur, begin, anchor, dx, fade-in, fade-out
    comets = [
        ("IEEE 2026", "Satellite ViT XAI", GOLD, "a", -140, 86, 1140, 176, 44, -6, "start", 17, 0.12, 0.73),
        ("Cairn", "graph memory for agents", CYAN, "b", 1140, 456, -140, 472, 58, -22, "end", -17, 0.10, 0.70),
    ]
    for label, sub, color, gid, x1, y1, x2, y2, dur, begin, anchor, dx, fin, fout in comets:
        phi = math.degrees(math.atan2(y2 - y1, x2 - x1))
        s += '  <g>\n'
        s += (f'    <animateMotion dur="{dur}s" begin="{begin}s" repeatCount="indefinite" '
              f'path="M {x1} {y1} L {x2} {y2}"/>\n')
        s += f'    <g transform="rotate({phi + 180:.1f})">\n'
        s += (f'      <path d="M 0 0 C 34 -7 70 -12 108 -14 L 108 14 C 70 12 34 7 0 0 Z" '
              f'fill="url(#{uid}-comet-{gid})"/>\n'
              f'      <circle r="6.5" fill="{color}" fill-opacity="0.22">'
              f'<animate attributeName="r" values="6.5;9.5;6.5" dur="4.5s" repeatCount="indefinite"/></circle>\n'
              f'      <circle r="2.6" fill="#fff6d8"/>\n')
        s += '    </g>\n'
        # the caption fades on the travel clock so it never clips mid-word at the frame edge,
        # while the comet itself keeps flying out of shot
        s += '    <g>\n'
        s += (f'      <animate attributeName="opacity" dur="{dur}s" begin="{begin}s" '
              f'repeatCount="indefinite" values="0;1;1;0" '
              f'keyTimes="0;{fin};{fout};{fout + 0.09:.2f}"/>\n')
        s += '  ' + txt(dx, -3, label, 10, 700, color, 1.3, anchor=anchor, halo=True)
        s += '  ' + txt(dx, 10, sub, 9, 500, "#a8b3c0", 0, anchor=anchor, halo=True)
        s += '    </g>\n'
        s += '  </g>\n'

    # the sun: a breathing corona, a soft ray crown and a heartbeat pulse
    s += f'  <ellipse cx="{cx}" cy="{cy}" rx="310" ry="196" fill="url(#{uid}-sunglow)">'
    s += ('<animate attributeName="opacity" values="0.16;0.34;0.16" dur="9s" '
          'repeatCount="indefinite"/>'
          '<animate attributeName="rx" values="300;326;300" dur="9s" repeatCount="indefinite"/>'
          '</ellipse>\n')
    s += f'  <g transform="translate({cx} {cy})" filter="url(#{uid}-soft)">\n    <g>\n'
    s += ('      <animateTransform attributeName="transform" type="rotate" from="0" to="360" '
          'dur="150s" repeatCount="indefinite"/>\n')
    for i in range(12):
        ln, w = (46, 1.9) if i % 2 == 0 else (32, 1.3)
        s += (f'      <path d="M {-w} -36 L 0 {-36 - ln} L {w} -36 Z" '
              f'fill="url(#{uid}-ray)" transform="rotate({i * 30})"/>\n')
    s += '    </g>\n  </g>\n'
    s += f'  <circle cx="{cx}" cy="{cy}" r="128" fill="url(#{uid}-sunglow)"/>\n'
    # heartbeat: rings leaving the disc, half a cycle apart
    for b in ("0s", "3.75s"):
        s += (f'  <circle cx="{cx}" cy="{cy}" r="44" fill="none" stroke="{GOLD}" '
              f'stroke-opacity="0" stroke-width="2.4">'
              f'<animate attributeName="r" values="44;104" dur="7.5s" begin="{b}" '
              f'repeatCount="indefinite"/>'
              f'<animate attributeName="stroke-opacity" values="0.30;0" dur="7.5s" begin="{b}" '
              f'repeatCount="indefinite"/>'
              f'<animate attributeName="stroke-width" values="2.4;0.3" dur="7.5s" begin="{b}" '
              f'repeatCount="indefinite"/></circle>\n')
    s += f'  <circle cx="{cx}" cy="{cy}" r="41" fill="url(#{uid}-sunbody)"/>\n'
    s += (f'  <circle cx="{cx}" cy="{cy}" r="41" fill="#fff3c4" fill-opacity="0">'
          f'<animate attributeName="fill-opacity" values="0;0.16;0" dur="6s" '
          f'repeatCount="indefinite"/></circle>\n')
    s += (f'  <image x="{cx - 32}" y="{cy - 32}" width="64" height="64" '
          f'clip-path="url(#{uid}-avatar)" xlink:href="{{AVATAR}}"/>\n')
    s += f'  <circle cx="{cx}" cy="{cy}" r="32" fill="{GOLD}" fill-opacity="0.20"/>\n'
    s += (f'  <circle cx="{cx}" cy="{cy}" r="32" fill="none" stroke="#ffe9a8" '
          f'stroke-opacity="0.70" stroke-width="1.6"/>\n')

    # planets: static position on an outer group, motion on an inner one,
    # so renderers without SMIL still draw every planet in its lane
    for p in PLANETS:
        key, name, cap, base, light, dark, rx, ang, r, period, moons, rings = p
        ry = rx * ORBIT_SQUASH
        a = math.radians(ang)
        x0, y0 = cx + rx * math.cos(a), cy + ry * math.sin(a)
        s += f'  <g transform="translate({x0:.2f} {y0:.2f})">\n    <g>\n'
        s += (f'      <animateMotion dur="{period}s" repeatCount="indefinite" '
              f'path="{ellipse_path(rx, ry, ang)}"/>\n')
        s += '      ' + planet_body(uid, p, r) + '\n'
        s += '    </g>\n  </g>\n'

    # tags stay anchored on their own lane, so they never collide while the planets travel
    for p in PLANETS:
        key, name, cap, base, light, dark, rx, ang, r, period, moons, rings = p
        ry = rx * ORBIT_SQUASH
        a = math.radians(ang)
        x0, y0 = cx + rx * math.cos(a), cy + ry * math.sin(a)
        anchor, dx, dy = TAGS[key]
        tx, ty = x0 + dx, y0 + dy
        s += txt(tx, ty - 6, name.upper(), 9, 700, light, 1.5, anchor=anchor,
                 opacity=0.95, font=MONO, halo=True)
        s += txt(tx, ty + 8, cap, 13.5, 600, TXT, 0, anchor=anchor, halo=True)

    # masthead
    s += txt(34, 44, "SOLAR SYSTEM", 11.5, 700, MUT, 3.4, font=MONO)
    s += txt(178, 44, "·  @ARSHDEEP-YADAV", 11.5, 700, "#4d5866", 3.4, font=MONO)
    s += txt(966, 44, "1 STAR  ·  8 PLANETS  ·  2 COMETS", 9.5, 600, "#5c6674", 1.8,
             anchor="end", font=MONO)

    # footer: the thesis, centred
    s += (f'  <rect x="24" y="496" width="{W - 48}" height="140" rx="16" fill="#060910" '
          f'fill-opacity="0.62" stroke="#ffffff" stroke-opacity="0.055"/>\n')
    s += (f'  <rect x="{cx - 20}" y="516" width="40" height="2" rx="1" fill="{GOLD}">'
          f'<animate attributeName="fill-opacity" values="1;0.45;1" dur="5s" '
          f'repeatCount="indefinite"/></rect>\n')
    s += txt(cx, 540, "THE THESIS", 9, 700, MUT, 2.6, anchor="middle", font=MONO)
    s += txt(cx, 566, "Everything here orbits one idea:", 13.5, 500, "#c9d1d9", 0, anchor="middle")
    s += txt(cx, 594, "make AI systems observable enough to trust.", 18.5, 800, TXT, -0.4,
             anchor="middle")
    s += txt(cx, 620, "Planets are capabilities · moons are shipped systems · comets are the work that travels",
             9.5, 500, MUT, 0.2, anchor="middle")

    s += (f'  <rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="21.5" fill="none" '
          f'stroke="url(#{uid}-edge)" stroke-opacity="0.55"/>\n')
    s += '</svg>\n'
    return s.replace("{AVATAR}", get_avatar_b64())


# --------------------------------------------------------------------------- #
# 2. about card
# --------------------------------------------------------------------------- #
def build_about():
    W, H, uid = 1000, 236, "about"
    s = '<?xml version="1.0" encoding="UTF-8"?>\n'
    s += (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
          f'viewBox="0 0 {W} {H}" role="img" aria-label="About Arshdeep Yadav">\n')
    s += space_defs(uid, W, H)
    s += space_fill(uid, W, H, 18)
    s += stars(uid, W, H, 46, seed=23, skip=(500, 118, 240))
    s += f'  <rect x="26" y="24" width="{W - 52}" height="{H - 48}" rx="14" fill="#080b12" fill-opacity="0.55" stroke="{EDGE}"/>\n'
    s += txt(54, 62, "ABOUT", 10.5, 700, MUT, 3.4, font=MONO)
    s += txt(54, 104, "From product scope to production trace.", 25, 800, TXT, -0.6)
    body = ("AI Product Builder and CS engineer (Honors in AI & ML) doing a Hybrid MBA in Generative AI & "
            "Product at IIT Patna. I work the whole span: scope the product, then build the harness, the "
            "memory and the evals that prove the thing actually works.")
    for i, line in enumerate(wrap(body, 74)):
        s += txt(54, 132 + i * 21, line, 13, 400, "#c9d1d9", 0, opacity=0.9)

    facts = [
        ("BASED IN", "Bengaluru, India", BLUE),
        ("STUDYING", "Hybrid MBA @ IIT Patna", PURPLE),
        ("OPEN TO", "AI Product · FDE · AI Engineering", GREEN),
    ]
    for i, (k, v, c) in enumerate(facts):
        y = 74 + i * 44
        s += f'  <circle cx="668" cy="{y - 4}" r="3" fill="{c}"/>\n'
        s += txt(684, y, k, 9.5, 700, MUT, 2.2, font=MONO)
        s += txt(684, y + 17, v, 12.5, 600, TXT, 0)
    s += (f'  <rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="17.5" fill="none" '
          f'stroke="{EDGE}" stroke-opacity="0.9"/>\n')
    s += '</svg>\n'
    return s


# --------------------------------------------------------------------------- #
# 3. project "moon" cards
# --------------------------------------------------------------------------- #
PROJECTS = [
    ("01", "Cairn", "MCP · Graph memory · Markdown/YAML", BLUE,
     "Local, Obsidian-compatible graph memory for agents. Token-bounded wikilink retrieval plus structured "
     "handover stops context loss and token bloat across multi-agent sessions.",
     "github.com/Arshdeep-Yadav/Cairn"),
    ("02", "Prompt OS", "Rust · LLM APIs · RAG · Evals", CYAN,
     "An observable coding-agent harness: transparent execution traces of what the agent did and why, with "
     "iterative eval loops that measure and standardise output reliability.",
     "github.com/Arshdeep-Yadav/promptos"),
    ("03", "Satellite ViT XAI", "PyTorch · ViT · Grad-CAM · LIME", PURPLE,
     "IEEE RMKMATE 2026. Fine-tuned a Vision Transformer on NWPU-RESISC45, then measured explanation clarity "
     "and faithfulness instead of assuming them.",
     "ieeexplore.ieee.org/document/11518743"),
    ("04", "Credit Risk Scoring", "Python · scikit-learn · MySQL · SQL", GREEN,
     "Logistic regression on Lending Club loans, then the coefficients shipped into a MySQL stored procedure "
     "so scoring runs where the data already lives.",
     "github.com/Arshdeep-Yadav/credit-risk-analysis"),
]


def build_project(idx, num, name, stack, color, blurb, link):
    W, H, uid = 480, 186, f"moon{idx}"
    s = '<?xml version="1.0" encoding="UTF-8"?>\n'
    s += (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
          f'viewBox="0 0 {W} {H}" role="img" aria-label="{esc(name)}">\n')
    s += space_defs(uid, W, H)
    s += space_fill(uid, W, H, 16)
    s += stars(uid, W, H, 34, seed=40 + idx, skip=(392, 54, 70))
    s += f'  <rect x="14" y="14" width="{W - 28}" height="{H - 28}" rx="12" fill="#080b12" fill-opacity="0.5" stroke="{EDGE}"/>\n'
    s += txt(32, 42, f"MOON {num}", 9.5, 700, color, 3, font=MONO)
    s += txt(32, 74, name, 21, 800, TXT, -0.4)
    s += txt(32, 95, stack, 10.5, 600, MUT, 0.2)
    for i, line in enumerate(wrap(blurb, 62)[:3]):
        s += txt(32, 120 + i * 16, line, 11, 400, "#c9d1d9", 0, opacity=0.9)
    s += txt(32, 170, "→ " + link, 9.5, 600, color, 0.3, opacity=0.8, font=MONO)
    # decorative planet + moon
    s += (f'  <ellipse cx="392" cy="52" rx="38" ry="14" fill="none" stroke="#ffffff" stroke-opacity="0.16" '
          f'stroke-dasharray="2 5"/>\n'
          f'  <circle cx="392" cy="52" r="18" fill="{color}" fill-opacity="0.16" stroke="{color}" stroke-opacity="0.7"/>\n'
          f'  <circle cx="386" cy="46" r="6" fill="#ffffff" fill-opacity="0.10"/>\n'
          f'  <circle cx="430" cy="52" r="3" fill="{color}" fill-opacity="0.9"/>\n')
    s += (f'  <rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="15.5" fill="none" '
          f'stroke="{EDGE}" stroke-opacity="0.9"/>\n')
    s += '</svg>\n'
    return s


# --------------------------------------------------------------------------- #
# 4. constellation (skills)
# --------------------------------------------------------------------------- #
def build_stack():
    groups = [
        ("PRODUCT & STRATEGY", BLUE, [
            "Product roadmapping", "MVP scoping", "Requirements translation",
            "Cross-functional collaboration", "Sprint planning", "Risk analysis",
            "Stakeholder reporting", "Agile / Kanban", "Jira", "Tableau"]),
        ("AI, ML & AGENTS", CYAN, [
            "LLMs & LLM APIs", "AI agents", "MCP", "RAG", "LLM evals",
            "Harness engineering", "Prompt engineering", "PyTorch", "TensorFlow",
            "Scikit-learn", "Vision Transformers", "Grad-CAM / LIME", "Pandas", "NumPy"]),
        ("ENGINEERING & CLOUD", PURPLE, [
            "Python", "Rust", "SQL", "Java", "C / C++", "JavaScript",
            "REST APIs", "Flask", "Streamlit", "Docker", "Git / GitHub",
            "AWS", "Azure", "GCP"]),
    ]
    W, uid = 1000, "stack"
    col_w = 296
    xs = [34, 34 + col_w + 20, 34 + 2 * (col_w + 20)]
    col_h = [len(items) * 26 + 68 for _l, _c, items in groups]
    H = 96 + max(col_h) + 30

    s = '<?xml version="1.0" encoding="UTF-8"?>\n'
    s += (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
          f'viewBox="0 0 {W} {H}" role="img" aria-label="Technical toolkit">\n')
    s += space_defs(uid, W, H)
    s += space_fill(uid, W, H, 18)
    s += stars(uid, W, H, 60, seed=61)
    s += txt(34, 44, "CONSTELLATION", 10.5, 700, MUT, 3.4, font=MONO)
    s += txt(34, 70, "What I can pick up on day one", 15, 600, "#c9d1d9", 0)
    for gi, (label, color, items) in enumerate(groups):
        x = xs[gi]
        y = 96
        s += (f'  <rect x="{x}" y="{y}" width="{col_w}" height="{col_h[gi]}" rx="12" '
              f'fill="#080b12" fill-opacity="0.45" stroke="{EDGE}"/>\n')
        s += txt(x + 18, y + 26, label, 9.5, 700, color, 2.2, font=MONO)
        for i, it in enumerate(items):
            yy = y + 52 + i * 26
            s += f'  <circle cx="{x + 22}" cy="{yy - 4}" r="2.2" fill="{color}" fill-opacity="0.85"/>\n'
            s += txt(x + 34, yy, it, 11.5, 500, "#dbe4ee", 0)
    s += (f'  <rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="17.5" fill="none" '
          f'stroke="{EDGE}" stroke-opacity="0.9"/>\n')
    s += '</svg>\n'
    return s


# --------------------------------------------------------------------------- #
# 5. flight log (real contribution data)
# --------------------------------------------------------------------------- #
def fetch_contributions():
    url = "https://github.com/users/Arshdeep-Yadav/contributions"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
    cells = {}
    for m in re.finditer(r'data-date="(\d{4}-\d{2}-\d{2})"[^>]*?data-level="(\d)"', html):
        cells[m.group(1)] = int(m.group(2))
    if not cells:
        raise RuntimeError("no contribution cells found")
    total = None
    m = re.search(r'>\s*([\d,]+)\s*</h2>\s*<span[^>]*>\s*contributions', html) or \
        re.search(r'([\d,]+)\s+contributions\s+in the last year', html)
    if m:
        total = int(m.group(1).replace(",", ""))
    return cells, total


FALLBACK_LEVELS = (
    "0000000000000000000000000000000000000000200000100000400000000000000000000000000000000000000000"
    "0000010000010000000002000000000000000000000000000000000001000400000000000000000000002000000000"
    "0000000000040000030000000010000000000000000200000000000000000001100002000004000000000000000000"
    "004000000000000000000000010000000000000000000000000000000000000000000001000002")


def build_log():
    total = active = 0
    try:
        cells, reported = fetch_contributions()
        days = sorted(cells)
        start = datetime.date.fromisoformat(days[0])
        end = datetime.date.fromisoformat(days[-1])
        start -= datetime.timedelta(days=(start.weekday() + 1) % 7)   # back to Sunday
        weeks = ((end - start).days // 7) + 1
        grid = [[0] * weeks for _ in range(7)]
        for d, lvl in cells.items():
            dt = datetime.date.fromisoformat(d)
            grid[(dt.weekday() + 1) % 7][(dt - start).days // 7] = lvl
        active = sum(1 for v in cells.values() if v)
        total = reported if reported else active
    except Exception:
        weeks = 52
        grid = [[int(FALLBACK_LEVELS[r * weeks + c]) if r * weeks + c < len(FALLBACK_LEVELS) else 0
                 for c in range(weeks)] for r in range(7)]
        start = datetime.date(2025, 11, 23)
        total, active = 85, 21

    W, uid = 1000, "log"
    pitch, cell = 15, 12
    gx = int((W - weeks * pitch) / 2)
    gy = 104
    H = gy + 7 * pitch + 62
    colors = ["#10151f", "#0e4429", "#006d32", "#26a641", "#39d353"]

    s = '<?xml version="1.0" encoding="UTF-8"?>\n'
    s += (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
          f'viewBox="0 0 {W} {H}" role="img" aria-label="Contribution activity, last 12 months">\n')
    s += space_defs(uid, W, H)
    s += space_fill(uid, W, H, 18)
    s += stars(uid, W, H, 55, seed=71, skip=(W / 2, gy + 52, 420))
    s += txt(34, 44, "FLIGHT LOG", 10.5, 700, MUT, 3.4, font=MONO)
    s += txt(34, 72, f"{total} contributions  ·  {active} active days  ·  last 12 months", 14, 600, "#c9d1d9", 0)

    seen = set()
    for c in range(weeks):
        d = start + datetime.timedelta(days=c * 7)
        if (d.year, d.month) not in seen:
            seen.add((d.year, d.month))
            s += txt(gx + c * pitch, gy - 10, d.strftime("%b"), 9, 600, MUT, 0.8, opacity=0.8, font=MONO)

    for r in range(7):
        for c in range(weeks):
            s += (f'  <rect x="{gx + c * pitch}" y="{gy + r * pitch}" width="{cell}" height="{cell}" '
                  f'rx="2.6" fill="{colors[min(grid[r][c], 4)]}"/>\n')

    ly = gy + 7 * pitch + 22
    lx = W - 34 - (5 * 16) - 66
    s += txt(lx, ly + 9, "LESS", 9, 700, MUT, 1.2, font=MONO)
    for i in range(5):
        s += f'  <rect x="{lx + 42 + i * 16}" y="{ly}" width="12" height="12" rx="2.6" fill="{colors[i]}"/>\n'
    s += txt(lx + 42 + 5 * 16 + 8, ly + 9, "MORE", 9, 700, MUT, 1.2, font=MONO)
    s += txt(gx, ly + 9, "github.com/Arshdeep-Yadav", 9.5, 600, MUT, 0.6, opacity=0.7, font=MONO)
    s += (f'  <rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="17.5" fill="none" '
          f'stroke="{EDGE}" stroke-opacity="0.9"/>\n')
    s += '</svg>\n'
    return s


# --------------------------------------------------------------------------- #
# 6. contact card
# --------------------------------------------------------------------------- #
def _icon_mail(color):
    return (f'    <rect x="-9" y="-6.5" width="18" height="13" rx="2.4" fill="none" stroke="{color}" stroke-width="1.5"/>\n'
            f'    <path d="M-8.2 -4.6 L0 2.2 L8.2 -4.6" fill="none" stroke="{color}" stroke-width="1.5" '
            f'stroke-linecap="round" stroke-linejoin="round"/>\n')


def _icon_globe(color):
    return (f'    <circle cx="0" cy="0" r="8.2" fill="none" stroke="{color}" stroke-width="1.5"/>\n'
            f'    <ellipse cx="0" cy="0" rx="3.6" ry="8.2" fill="none" stroke="{color}" stroke-width="1.2" stroke-opacity="0.8"/>\n'
            f'    <path d="M-8.2 0 H8.2" stroke="{color}" stroke-width="1.2" stroke-opacity="0.8"/>\n')


def _icon_phone(color):
    return (f'    <rect x="-5.4" y="-9" width="10.8" height="18" rx="2.8" fill="none" stroke="{color}" stroke-width="1.5"/>\n'
            f'    <circle cx="0" cy="5.6" r="1.1" fill="{color}"/>\n')


def build_contact():
    W, H, uid = 1000, 344, "contact"
    s = '<?xml version="1.0" encoding="UTF-8"?>\n'
    s += (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
          f'viewBox="0 0 {W} {H}" role="img" aria-label="Contact Arshdeep Yadav">\n')
    s += space_defs(uid, W, H)
    s += f"""  <defs>
    <radialGradient id="{uid}-halo">
      <stop offset="0%" stop-color="{BLUE}" stop-opacity="0.20"/>
      <stop offset="55%" stop-color="{PURPLE}" stop-opacity="0.07"/>
      <stop offset="100%" stop-color="{PURPLE}" stop-opacity="0"/>
    </radialGradient>
  </defs>
"""
    s += space_fill(uid, W, H, 18)
    s += stars(uid, W, H, 80, seed=97, skip=(500, 100, 300))
    s += f'  <ellipse cx="500" cy="86" rx="360" ry="140" fill="url(#{uid}-halo)"/>\n'

    # availability pill
    label = "OPEN TO WORK"
    tw = len(label) * 7.7
    pw = tw + 46
    px = 500 - pw / 2
    s += (f'  <rect x="{px:.1f}" y="26" width="{pw:.1f}" height="27" rx="13.5" fill="{GREEN}" '
          f'fill-opacity="0.10" stroke="{GREEN}" stroke-opacity="0.42"/>\n')
    s += (f'  <circle cx="{px + 17:.1f}" cy="39.5" r="3.4" fill="{GREEN}">'
          f'<animate attributeName="fill-opacity" values="1;0.25;1" dur="2.6s" repeatCount="indefinite"/></circle>\n')
    s += txt(px + 29, 43.5, label, 9.5, 700, GREEN, 2.2, font=MONO)

    s += txt(500, 100, "Let's build something observable.", 33, 800, TXT, -0.9, anchor="middle")
    s += txt(500, 128, "AI Product · Forward-Deployed AI · AI Engineering  —  Bengaluru or remote",
             12.5, 500, "#c9d1d9", 0.2, anchor="middle", opacity=0.85)

    channels = [
        ("EMAIL", "arshdeep.yadav.work@gmail.com", BLUE, _icon_mail),
        ("PORTFOLIO", "arshdeep.works", PURPLE, _icon_globe),
        ("PHONE", "+91 81152 37909", GREEN, _icon_phone),
    ]
    for i, (label, value, color, icon) in enumerate(channels):
        x, y = 30 + i * 320, 162
        s += (f'  <rect x="{x}" y="{y}" width="300" height="106" rx="14" fill="#080b12" '
              f'fill-opacity="0.62" stroke="{color}" stroke-opacity="0.30"/>\n')
        s += f'  <circle cx="{x + 42}" cy="{y + 53}" r="19" fill="{color}" fill-opacity="0.10" stroke="{color}" stroke-opacity="0.28"/>\n'
        s += f'  <g transform="translate({x + 42} {y + 53})">\n'
        s += icon(color)
        s += '  </g>\n'
        s += txt(x + 74, y + 42, label, 9.5, 700, color, 2.2, font=MONO)
        s += txt(x + 74, y + 68, value, 12.5, 600, TXT, 0)

    s += txt(500, 312, "Bengaluru, India  ·  IST (UTC+5:30)  ·  usually replies within a day",
             10, 600, MUT, 0.9, anchor="middle", opacity=0.62, font=MONO)
    s += (f'  <rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="17.5" fill="none" '
          f'stroke="url(#{uid}-edge)" stroke-opacity="0.55"/>\n')
    s += '</svg>\n'
    return s


# --------------------------------------------------------------------------- #
# README
# --------------------------------------------------------------------------- #
README = """<div align="center">
<img src="./assets/orbits.svg" width="100%" alt="Arshdeep Yadav at the centre of a solar system. Everything here orbits one idea: make AI systems observable enough to trust. Eight planets in orbital order map his capabilities — AI agents and MCP, LLM evals and RAG, AI product, Rust and Python, data and analytics, XAI research, cloud and infra, prompt engineering — each labelled beside its planet. Moons are shipped systems; two comets carry his IEEE paper and his Cairn project." />
</div>

<div align="center"><br /></div>

<div align="center">
<img src="./assets/about.svg" width="100%" alt="About Arshdeep Yadav" />
</div>

<h2 align="center">Moons in orbit</h2>

<div align="center">
<a href="https://github.com/Arshdeep-Yadav/Cairn"><img src="./assets/moon-01.svg" width="49%" alt="Cairn — local graph memory and MCP agent handover" /></a> <a href="https://github.com/Arshdeep-Yadav/promptos"><img src="./assets/moon-02.svg" width="49%" alt="Prompt OS — observable coding agent harness in Rust" /></a>
<a href="https://ieeexplore.ieee.org/document/11518743"><img src="./assets/moon-03.svg" width="49%" alt="Satellite ViT XAI — IEEE RMKMATE 2026" /></a> <a href="https://github.com/Arshdeep-Yadav/credit-risk-analysis"><img src="./assets/moon-04.svg" width="49%" alt="Credit Risk Scoring — logistic regression on Lending Club loans, scored in MySQL" /></a>
</div>

<h2 align="center">Constellation</h2>

<div align="center">
<img src="./assets/stack.svg" width="100%" alt="Product and strategy, AI/ML and agents, engineering and cloud" />
</div>

<h2 align="center">Flight log</h2>

<div align="center">
<img src="./assets/log.svg" width="100%" alt="Contribution activity for the last twelve months" />
</div>

<h2 align="center">Signal me</h2>

<div align="center">
<img src="./assets/contact.svg" width="100%" alt="Contact Arshdeep Yadav — open to AI Product, Forward-Deployed AI and AI Engineering roles" />
</div>

<p align="center">
<a href="mailto:arshdeep.yadav.work@gmail.com">Email</a> &nbsp;·&nbsp;
<a href="https://arshdeep.works">Portfolio</a> &nbsp;·&nbsp;
<a href="https://linkedin.com/in/arshdeep-yadav">LinkedIn</a> &nbsp;·&nbsp;
<a href="https://github.com/Arshdeep-Yadav">GitHub</a> &nbsp;·&nbsp;
<a href="tel:+918115237909">+91 81152 37909</a>
</p>

<hr />

<div align="center">
<sub>Hand-built in SVG — orbits, cards and this page all generated from one Python file</sub>
</div>
"""

PREVIEW_CSS = """
  :root { --bg:#0d1117; --panel:#161b22; --fg:#e6edf3; --muted:#8b949e; --border:#30363d; --link:#58a6ff; }
  * { box-sizing: border-box; }
  body { margin:0; color:var(--fg);
    background:
      radial-gradient(1200px 700px at 50% -10%, rgba(88,166,255,0.16), transparent 68%),
      radial-gradient(900px 620px at 88% 16%, rgba(163,113,247,0.13), transparent 66%),
      radial-gradient(1000px 700px at 6% 74%, rgba(34,211,238,0.09), transparent 66%),
      radial-gradient(1200px 900px at 50% 108%, rgba(63,185,80,0.07), transparent 70%),
      #05070c;
    background-attachment: fixed;
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;
    font-size:16px; line-height:1.5; -webkit-font-smoothing:antialiased; }
  .topbar { display:flex; align-items:center; gap:14px; padding:14px 24px;
    border-bottom:1px solid var(--border); background:rgba(1,4,9,0.82);
    backdrop-filter:blur(12px); position:sticky; top:0; z-index:5; }
  .topbar .repo { font-size:14px; color:var(--muted); }
  .topbar .repo b { color:var(--fg); font-weight:600; }
  .pill { margin-left:auto; font-size:12px; color:var(--muted);
    border:1px solid var(--border); border-radius:999px; padding:3px 10px; }
  .wrap { max-width:1012px; margin:0 auto; padding:26px 24px 90px; }
  .card { background:linear-gradient(180deg, rgba(22,27,34,0.96), rgba(11,16,23,0.96));
    border:1px solid rgba(255,255,255,0.06); border-radius:14px; padding:34px 40px 44px;
    box-shadow:0 40px 120px -50px rgba(88,166,255,0.35), 0 0 0 1px rgba(0,0,0,0.4) inset; }
  .markdown-body h1,.markdown-body h2 { font-weight:600; line-height:1.25; }
  .markdown-body h2 { font-size:1.5em; margin:34px 0 12px; padding-bottom:.3em; border-bottom:1px solid #21262d; }
  .markdown-body h2[align="center"] { border-bottom:0; }
  .markdown-body p { margin:0 0 12px; }
  .markdown-body a { color:var(--link); text-decoration:none; }
  .markdown-body a:hover { text-decoration:underline; }
  .markdown-body sub { font-size:.74em; color:var(--muted); }
  .markdown-body hr { border:0; border-top:1px solid var(--border); margin:26px 0; }
  .markdown-body img { max-width:100%; height:auto; vertical-align:middle; }
  .markdown-body table { border-collapse:collapse; width:100%; }
  .markdown-body table td { padding:6px 10px 6px 0; vertical-align:top; }
  .markdown-body strong { font-weight:600; }
  .note { margin:0 0 18px; font-size:12.5px; color:var(--muted); }
  .note code { background:#1f242c; padding:1px 5px; border-radius:5px; font-size:12px; }
  .gh { display:flex; gap:8px; align-items:center; }
"""


def build_preview(body):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Arshdeep Yadav — GitHub profile README preview</title>
<style>{PREVIEW_CSS}</style>
</head>
<body>
<div class="topbar">
  <svg width="22" height="22" viewBox="0 0 16 16" fill="#e6edf3" aria-hidden="true"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82a7.4 7.4 0 0 1 2-.27c.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8Z"/></svg>
  <span class="repo"><b>Arshdeep-Yadav</b> / Arshdeep-Yadav</span>
  <span class="pill">README.md · local preview</span>
</div>
<div class="wrap">
  <p class="note">Preview of <code>README.md</code>. Commit this folder to a public repo named <code>Arshdeep-Yadav</code> and GitHub renders it on your profile.</p>
  <div class="card markdown-body">
{body}
  </div>
</div>
</body>
</html>
"""


def main():
    files = {
        "orbits.svg": build_orbits(),
        "about.svg": build_about(),
        "stack.svg": build_stack(),
        "log.svg": build_log(),
        "contact.svg": build_contact(),
    }
    for i, (num, name, stack, color, blurb, link) in enumerate(PROJECTS, start=1):
        files[f"moon-{num}.svg"] = build_project(i, num, name, stack, color, blurb, link)

    for name, content in files.items():
        path = os.path.join(ASSETS, name)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        print(f"  assets/{name:<16} {len(content) / 1024:6.1f} KB")

    with open(os.path.join(ROOT, "README.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(README)
    print("  README.md")

    with open(os.path.join(ROOT, "preview.html"), "w", encoding="utf-8", newline="\n") as f:
        f.write(build_preview(README))
    print("  preview.html")


if __name__ == "__main__":
    main()
