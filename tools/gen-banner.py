#!/usr/bin/env python3
"""Generate the animated terminal banner for the GitHub profile README.

Commands type character by character; output appears at once, the way a real
terminal behaves.

Two properties matter more than the animation itself:

* Every clip rect carries its *final* width as the static attribute, and one
  animation spanning the whole timeline overrides it. A renderer that ignores
  SMIL therefore shows the finished terminal rather than an empty window.
* Glyph advances are pinned with `textLength`, so the cursor lands on the
  character it is typing whatever monospace font the reader happens to have.
"""

import pathlib
import sys

W = 700
FS = 15.0
CW = 9.0
PAD = 28
BAR = 40
ROW = 27
GAP = 13
CURSOR_W = 8.4

THEMES = {
    "dark": {
        "bg": "#0A0E14", "bar": "#10161F", "border": "#222C38",
        "bar_text": "#54647A", "glow": "#2F81F7", "glow_op": "0.17",
        "prompt": "#7EE787", "cmd": "#E6EDF3", "flag": "#D2A8FF",
        "str": "#A5D6FF", "pipe": "#FF7B72",
        "arrow": "#58A6FF", "val": "#A3B5C9", "sep": "#3C4855",
        "key": "#FFA657", "ok": "#7EE787",
    },
    "light": {
        "bg": "#FFFFFF", "bar": "#F6F8FA", "border": "#D1D9E0",
        "bar_text": "#6E7781", "glow": "#0969DA", "glow_op": "0.09",
        "prompt": "#1A7F37", "cmd": "#1F2328", "flag": "#8250DF",
        "str": "#0A3069", "pipe": "#CF222E",
        "arrow": "#0969DA", "val": "#424A53", "sep": "#AFB8C1",
        "key": "#BC4C00", "ok": "#1A7F37",
    },
}

LINES = [
    ("cmd", [("$ ", "prompt"), ("whoami", "cmd")]),
    ("out", [("→ ", "arrow"), ("Arthur Cavini", "key"), (" · ", "sep"),
             ("full-stack dev", "val"), (" · ", "sep"),
             ("MERN + NestJS", "flag"), (" · ", "sep"), ("Brazil", "val")]),
    ("blank", []),
    ("cmd", [("$ ", "prompt"), ("cat ", "cmd"), ("stack.json", "str"),
             (" | ", "pipe"), ("jq ", "cmd"), ("-r ", "flag"),
             ("'.core[]'", "str")]),
    ("out", [("→ ", "arrow"), ("react", "key"), (" · ", "sep"),
             ("node", "val"), (" · ", "sep"), ("nestjs", "val"),
             (" · ", "sep"), ("next.js", "val"), (" · ", "sep"),
             ("typescript", "val"), (" · ", "sep"), ("mongodb", "key")]),
    ("blank", []),
    ("cmd", [("$ ", "prompt"), ("cat ", "cmd"), ("stack.json", "str"),
             (" | ", "pipe"), ("jq ", "cmd"), ("-r ", "flag"),
             ("'.also[]'", "str")]),
    ("out", [("→ ", "arrow"), ("supabase", "key"), (" · ", "sep"),
             ("postgres", "val"), (" · ", "sep"), ("redux", "val"),
             (" · ", "sep"), ("tailwind", "val"), (" · ", "sep"),
             ("docker", "val"), (" · ", "sep"), ("redis", "key")]),
    ("blank", []),
    ("cmd", [("$ ", "prompt"), ("pnpm ", "cmd"), ("test", "flag")]),
    ("checks", [("2,282", "tests passing"), ("6", "years shipping"),
                ("0", "broken Fridays")]),
    ("blank", []),
    ("prompt", [("$ ", "prompt")]),
]

TYPE_RATE = 0.042
PAUSE_BEFORE_OUT = 0.24
PAUSE_AFTER_OUT = 0.36
CHECK_STAGGER = 0.40
TAIL = 0.5

ALT = ("Terminal window. whoami returns: Arthur Cavini, full-stack dev, "
       "MERN plus NestJS, Brazil. Core stack: react, node, nestjs, next.js, "
       "typescript, mongodb. Also: supabase, postgres, redux, tailwind, "
       "docker, redis. pnpm test passes: 2,282 tests passing, 6 years "
       "shipping, 0 broken Fridays.")


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def nchars(segs):
    return sum(len(t) for t, _ in segs)


def text_el(segs, c, x, y):
    spans = "".join(f'<tspan fill="{c[k]}">{esc(t)}</tspan>' for t, k in segs)
    return (f'<text x="{x:.1f}" y="{y:.1f}" textLength="{nchars(segs) * CW:.1f}"'
            f' lengthAdjust="spacing">{spans}</text>')


def layout():
    """Place the lines and resolve every reveal into (start, duration)."""
    y, placed, t = BAR + 26, [], 0.45
    for kind, segs in LINES:
        if kind == "blank":
            y += GAP
            continue
        if kind == "cmd":
            dur = nchars(segs) * TYPE_RATE
            placed.append((kind, segs, y, t, dur))
            t += dur + PAUSE_BEFORE_OUT
        elif kind == "checks":
            placed.append((kind, segs, y, t, 0.0))
            t += (len(segs) - 1) * CHECK_STAGGER + PAUSE_AFTER_OUT
        else:
            placed.append((kind, segs, y, t, 0.0))
            t += PAUSE_AFTER_OUT
        y += ROW
    return placed, y + 14, t + TAIL


def reveal(cid, x, y, full, start, dur, total, steps=None, static=False):
    """A clip rect whose base value is the finished state."""
    rect = (f'<rect x="{x - 3:.1f}" y="{y - FS:.1f}" '
            f'height="{FS + 8:.1f}" width="{full:.1f}"')
    if static:
        return f'<clipPath id="{cid}">{rect}/></clipPath>'

    if steps:
        n = len(steps)
        vals = ["0"] + [f"{w:.1f}" for w in steps] + [f"{full:.1f}"]
        times = ([0.0] + [(start + k * dur / n) / total for k in range(n)]
                 + [1.0])
    else:
        vals = ["0", f"{full:.1f}", f"{full:.1f}"]
        times = [0.0, start / total, 1.0]

    return (f'<clipPath id="{cid}">{rect}>'
            f'<animate attributeName="width" calcMode="discrete" '
            f'values="{";".join(vals)}" '
            f'keyTimes="{";".join(f"{k:.5f}" for k in times)}" '
            f'begin="0s" dur="{total:.2f}s" fill="freeze"/>'
            f'</rect></clipPath>')


def build(theme, static=False):
    c = THEMES[theme]
    x0 = PAD
    placed, height, total = layout()
    defs, body = [], []
    final_cursor = None

    for i, (kind, segs, ly, start, dur) in enumerate(placed):
        cid = f"{theme[0]}{i}"
        n = nchars(segs)
        full = n * CW + 6

        if kind == "checks":
            cx = x0
            for j, (num, label) in enumerate(segs):
                # Orange is reserved for figures, so a word-only check stays plain.
                part = [("✓ ", "ok"), (num, "key" if num[0].isdigit() else "val"),
                        (" ", "val"), (label, "val")]
                pn = nchars(part)
                defs.append(reveal(f"{cid}_{j}", cx, ly, pn * CW + 6,
                                   start + j * CHECK_STAGGER, 0.0, total,
                                   static=static))
                body.append(f'<g clip-path="url(#{cid}_{j})">'
                            f'{text_el(part, c, cx, ly)}</g>')
                cx += (pn + 3) * CW
            continue

        steps = ([min(k + 1, n) * CW + 6 for k in range(n)]
                 if kind == "cmd" else None)
        defs.append(reveal(cid, x0, ly, full, start, dur, total,
                           steps=steps, static=static))
        body.append(f'<g clip-path="url(#{cid})">{text_el(segs, c, x0, ly)}</g>')

        if kind == "cmd" and not static:
            # keyTimes must run 0 to 1, so the track is padded at both ends
            # with the resting position rather than starting mid-timeline.
            pos = [x0 + k * CW for k in range(n + 1)]
            xs = ";".join(f"{v:.1f}" for v in [pos[0]] + pos + [pos[-1]])
            kt = ";".join(
                f"{k:.5f}" for k in
                [0.0] + [(start + i * dur / (n + 1)) / total
                         for i in range(n + 1)] + [1.0])
            body.append(
                f'<rect x="{x0:.1f}" y="{ly - FS + 2:.1f}" '
                f'width="{CURSOR_W:.1f}" height="{FS + 2:.1f}" rx="1" '
                f'fill="{c["prompt"]}" opacity="0">'
                f'<animate attributeName="x" values="{xs}" keyTimes="{kt}" '
                f'calcMode="discrete" begin="0s" dur="{total:.2f}s" fill="freeze"/>'
                f'<set attributeName="opacity" to="0.9" begin="{start:.2f}s"/>'
                f'<set attributeName="opacity" to="0" begin="{start + dur:.2f}s"/>'
                f'</rect>')

        if kind == "prompt":
            final_cursor = (start, ly, x0 + n * CW)

    start, ly, cx = final_cursor
    gate = "" if static else (
        f'<set attributeName="opacity" to="1" begin="{start:.2f}s"/>')
    blink = "" if static else (
        '<animate attributeName="opacity" values="0.9;0.9;0;0" dur="1.1s" '
        'repeatCount="indefinite"/>')
    body.append(
        f'<g opacity="{1 if static else 0}">{gate}'
        f'<rect x="{cx:.1f}" y="{ly - FS + 2:.1f}" width="{CURSOR_W:.1f}" '
        f'height="{FS + 2:.1f}" rx="1" fill="{c["prompt"]}" opacity="0.9">'
        f'{blink}</rect></g>')

    lights = "".join(
        f'<circle cx="{26 + k * 20}" cy="{BAR // 2}" r="6" fill="{col}"/>'
        for k, col in enumerate(("#FF5F57", "#FEBC2E", "#28C840")))
    title = (f'<tspan>~/arthur-cavini</tspan><tspan fill="{c["sep"]}"> · </tspan>'
             f'<tspan>zsh</tspan>')
    nl = chr(10)

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {height}" width="{W}" height="{height}" role="img" aria-label="{ALT}" font-family="ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Monaco, 'Cascadia Mono', Consolas, 'Liberation Mono', monospace" font-size="{FS}">
  <title>{ALT}</title>
  <defs>
    <linearGradient id="gl{theme[0]}" x1="0" y1="0" x2="0.9" y2="1">
      <stop offset="0" stop-color="{c['glow']}" stop-opacity="{c['glow_op']}"/>
      <stop offset="0.6" stop-color="{c['glow']}" stop-opacity="0"/>
    </linearGradient>
    <linearGradient id="hr{theme[0]}" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="{c['prompt']}" stop-opacity="0"/>
      <stop offset="0.45" stop-color="{c['prompt']}" stop-opacity="0.5"/>
      <stop offset="1" stop-color="{c['glow']}" stop-opacity="0"/>
    </linearGradient>
    <clipPath id="wn{theme[0]}">
      <rect x="0.5" y="0.5" width="{W - 1}" height="{height - 1}" rx="11"/>
    </clipPath>
{nl.join('    ' + d for d in defs)}
  </defs>

  <rect x="0.5" y="0.5" width="{W - 1}" height="{height - 1}" rx="11" fill="{c['bg']}"/>
  <g clip-path="url(#wn{theme[0]})">
    <rect width="{W}" height="{height}" fill="url(#gl{theme[0]})"/>
    <rect width="{W}" height="{BAR}" fill="{c['bar']}"/>
    <rect y="{BAR - 1}" width="{W}" height="1" fill="{c['border']}"/>
    <rect y="{BAR}" width="{W}" height="1.5" fill="url(#hr{theme[0]})"/>
    {lights}
    <text x="{W // 2}" y="{BAR / 2 + 4.5:.1f}" font-size="12.5" fill="{c['bar_text']}" text-anchor="middle">{title}</text>
{nl.join('    ' + b for b in body)}
  </g>
  <rect x="0.5" y="0.5" width="{W - 1}" height="{height - 1}" rx="11" fill="none" stroke="{c['border']}"/>
</svg>
'''


if __name__ == "__main__":
    static = "--static" in sys.argv
    here = pathlib.Path(__file__).resolve().parent.parent
    out = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1][0] != "-" \
        else here / "assets"
    out.mkdir(parents=True, exist_ok=True)
    for theme in THEMES:
        p = out / f"terminal-{theme}.svg"
        p.write_text(build(theme, static=static), encoding="utf-8")
        print(f"{p}  {p.stat().st_size:,} bytes")
