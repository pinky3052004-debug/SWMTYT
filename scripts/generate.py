#!/usr/bin/env python3
"""Pomodoro timer video generator - original "soft card" design.

Usage:
  python scripts/generate.py --focus 50 --break 10 --cycles 4 --theme sage --out out/pomodoro_50_10.mp4
Creates the .mp4 and a chapters .txt file next to it (YouTube chapter format).
"""
import argparse
import math
import os
import random
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1920, 1080
INTRO_SECONDS = 7

# Soft mid-tone base colour per theme (white text/ring sit on top)
THEMES = {
    "sage":    (136, 178, 152),
    "sky":     (132, 170, 210),
    "apricot": (232, 166, 126),
    "mauve":   (188, 146, 172),
}
WHITE = (252, 250, 248)


def mix(c, t, to=(255, 255, 255)):
    return tuple(round(v + (o - v) * t) for v, o in zip(c, to))


BASE = None
_CACHE = {}


def set_theme(name):
    global BASE
    BASE = THEMES[name]
    _CACHE.clear()


set_theme("sage")

FONT_CANDIDATES = {
    "light": ["/usr/share/fonts/truetype/lato/Lato-Light.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-ExtraLight.ttf"],
    "regular": ["/usr/share/fonts/truetype/lato/Lato-Regular.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"],
    "bold": ["/usr/share/fonts/truetype/lato/Lato-Bold.ttf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
}


def font(kind, size):
    for p in FONT_CANDIDATES[kind]:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


F_TIME = font("light", 156)
F_PILL = font("bold", 46)
F_SESSION = font("regular", 38)
F_CHIP_BIG = font("bold", 64)
F_CHIP_SM = font("regular", 28)
F_INTRO = font("light", 230)
F_READY = font("regular", 44)


def fmt(sec):
    return f"{sec // 60:02d}:{sec % 60:02d}"


def chapter_ts(sec):
    h, m, s = sec // 3600, (sec % 3600) // 60, sec % 60
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def build_chapters(focus_s, break_s, cycles, focus_min, break_min):
    """First chapter starts at 0:00 and includes the 7s countdown (YouTube needs >=10s chapters)."""
    chapters, t = [], 0
    for i in range(1, cycles + 1):
        title = f"Session {i} ({focus_min:g} min Focus)"
        if i == 1:
            title = "Countdown & " + title
        chapters.append((t, title))
        t += (INTRO_SECONDS if i == 1 else 0) + focus_s
        last = i == cycles
        chapters.append((t, ("Final Break & Wrap Up" if last else f"Break {i}") + f" ({break_min:g} min)"))
        t += break_s
    return chapters, t


def _icon_layer(draw_fn, color, size=400, S=4, scale=1.0):
    layer = Image.new("RGBA", (size * S, size * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    k = S * scale
    c = tuple(color) + (255,)

    def line(p1, p2, w):
        x1, y1 = p1[0] * k, p1[1] * k
        x2, y2 = p2[0] * k, p2[1] * k
        d.line([(x1, y1), (x2, y2)], fill=c, width=int(w * k))
        r = w * k / 2
        for x, y in ((x1, y1), (x2, y2)):
            d.ellipse([x - r, y - r, x + r, y + r], fill=c)

    def rrect(x1, y1, x2, y2, r):
        d.rounded_rectangle([x1 * k, y1 * k, x2 * k, y2 * k], r * k, fill=c)

    def circle(cx, cy, r):
        d.ellipse([(cx - r) * k, (cy - r) * k, (cx + r) * k, (cy + r) * k], fill=c)

    draw_fn(d, k, c, line, rrect, circle)
    return layer.resize((size, size), Image.LANCZOS)


def _study(d, k, c, line, rrect, circle):
    # desk + leg
    rrect(40, 178, 200, 192, 6)
    rrect(52, 192, 64, 312, 5)
    # laptop (screen tilted back, keyboard on desk)
    rrect(84, 164, 188, 178, 5)
    d.polygon([(88 * k, 166 * k), (102 * k, 166 * k), (84 * k, 88 * k), (70 * k, 91 * k)], fill=c)
    # person
    circle(238, 86, 27)                      # head
    line((238, 134), (246, 208), 46)         # torso
    line((246, 224), (190, 224), 28)         # thigh
    line((190, 224), (186, 298), 24)         # shin
    line((186, 300), (156, 302), 16)         # foot
    line((232, 150), (178, 168), 16)         # arm to keyboard
    # chair
    rrect(272, 134, 286, 236, 7)
    rrect(216, 240, 288, 256, 8)
    rrect(246, 256, 258, 306, 5)
    rrect(214, 304, 294, 318, 7)


def _cup(d, k, c, line, rrect, circle):
    d.ellipse([222 * k, 168 * k, 290 * k, 240 * k], outline=c, width=int(13 * k))  # handle
    d.pieslice([100 * k, 120 * k, 260 * k, 290 * k], 0, 180, fill=c)        # bowl
    rrect(100, 198, 260, 207, 3)                                            # rim
    rrect(78, 298, 282, 312, 7)                                             # saucer
    for dx in (-42, 0, 42):                                                 # steam
        pts = [((180 + dx + 8 * math.sin(i / 6.0)) * k, (60 + i) * k) for i in range(0, 66, 2)]
        d.line(pts, fill=c, width=int(8 * k), joint="curve")


def draw_icon(img, kind, cx, cy, color, scale=1.2):
    fn = _study if kind == "focus" else _cup
    center = (172, 200) if kind == "focus" else (180, 188)
    layer = _icon_layer(fn, color, scale=scale)
    img.paste(layer, (cx - int(center[0] * scale), cy - int(center[1] * scale)), layer)


def make_countdown_wav(path, intro=INTRO_SECONDS):
    """Soft tick for each countdown second (7..1) + a bell-like 'start' chime when the countdown ends."""
    import array
    import wave
    sr = 44100
    n = int((intro + 2.0) * sr)
    buf = [0.0] * n

    def add(t0, freq, dur, amp, decay):
        i0 = int(t0 * sr)
        for i in range(int(dur * sr)):
            if i0 + i >= n:
                break
            t = i / sr
            env = math.exp(-decay * t) * min(1.0, i / (0.004 * sr))   # fast attack, soft decay
            buf[i0 + i] += amp * env * math.sin(2 * math.pi * freq * t)

    for k in range(intro):                       # one tick per displayed number
        add(k, 880.0 if k < intro - 1 else 1174.7, 0.22, 0.32, 22)
    for f, a in ((1046.5, 0.28), (1318.5, 0.22), (1568.0, 0.16)):   # start chime
        add(intro, f, 1.8, a, 3.2)
    pcm = array.array("h", (int(max(-1, min(1, v)) * 32000) for v in buf for _ in (0, 1)))
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def tracked(d, cx, cy, text, fnt, fill, tracking=8, anchor_x="center"):
    widths = [d.textlength(ch, font=fnt) for ch in text]
    total = sum(widths) + tracking * (len(text) - 1)
    x = cx - total / 2 if anchor_x == "center" else cx
    for ch, w in zip(text, widths):
        d.text((x, cy), ch, font=fnt, fill=fill, anchor="lm")
        x += w + tracking


def gradient_bg(top, bottom):
    mask = Image.linear_gradient("L").resize((W, H))
    return Image.composite(Image.new("RGB", (W, H), bottom), Image.new("RGB", (W, H), top), mask)


def decor(img, seed):
    """Soft bokeh circles + thin rings: purely decorative, original layout."""
    rnd = random.Random(seed)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    spots = [(180, 880, 150, 26), (1760, 200, 190, 22), (300, 220, 70, 30), (1650, 860, 110, 28),
             (90, 520, 50, 24), (1840, 560, 60, 24), (700, 1000, 80, 18), (1300, 70, 90, 20)]
    for x, y, r, a in spots:
        x += rnd.randint(-20, 20)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, a))
    for x, y, r in [(1640, 300, 230), (260, 780, 260)]:
        d.ellipse([x - r, y - r, x + r, y + r], outline=(255, 255, 255, 38), width=3)
    layer = layer.filter(ImageFilter.GaussianBlur(3))
    img.paste(layer, (0, 0), layer)


def static_layer(phase, session, cycles, preset_label):
    key = (phase, session, cycles, preset_label)
    if key in _CACHE:
        return _CACHE[key]
    if phase == "focus":
        top, bottom = mix(BASE, 0.10), mix(BASE, -0.12, (0, 0, 0))
    else:  # break: lighter, calmer
        top, bottom = mix(BASE, 0.30), mix(BASE, 0.08)
    img = gradient_bg(top, bottom)
    decor(img, 7 if phase == "focus" else 11)

    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    cx, cy, r = W // 2, 520, 268

    # glass card behind the ring
    d.rounded_rectangle([cx - 430, 215, cx + 430, 855], 70, fill=(255, 255, 255, 30))
    # label pill
    d.rounded_rectangle([cx - 190, 96, cx + 190, 186], 45, fill=(255, 255, 255, 52),
                        outline=(255, 255, 255, 170), width=3)
    img.paste(ov, (0, 0), ov)
    d = ImageDraw.Draw(img)
    tracked(d, cx, 141, "FOCUS" if phase == "focus" else "BREAK", F_PILL, WHITE, tracking=14)

    # ring track (anti-aliased)
    S = 3
    size = (r + 20) * 2 + 8
    layer = Image.new("RGBA", (size * S, size * S), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ld.ellipse([4 * S, 4 * S, (size - 4) * S, (size - 4) * S], outline=(255, 255, 255, 70), width=18 * S)
    layer = layer.resize((size, size), Image.LANCZOS)
    img.paste(layer, (cx - size // 2, cy - size // 2), layer)

    # icon inside ring
    draw_icon(img, phase, cx, 420, WHITE, scale=0.62)
    d = ImageDraw.Draw(img)

    # session text + dots
    tracked(d, cx, 893, f"SESSION {session} OF {cycles}", F_SESSION, WHITE, tracking=8)
    gap = 46
    x0 = cx - gap * (cycles - 1) / 2
    for i in range(1, cycles + 1):
        x = x0 + (i - 1) * gap
        if i < session or (i == session and phase == "break"):
            d.ellipse([x - 11, 953 - 11, x + 11, 953 + 11], fill=WHITE)
        elif i == session:
            d.ellipse([x - 15, 953 - 15, x + 15, 953 + 15], fill=WHITE)
        else:
            d.ellipse([x - 11, 953 - 11, x + 11, 953 + 11], outline=mix(BASE, 0.6), width=3)

    # corner chips
    d.text((96, 92), preset_label, font=F_CHIP_BIG, fill=WHITE, anchor="lm")
    d.text((98, 142), "POMODORO TIMER", font=F_CHIP_SM, fill=mix(BASE, 0.75), anchor="lm")
    d.text((W - 96, 92), "STUDY WITH ME", font=F_CHIP_SM, fill=WHITE, anchor="rm")
    _CACHE[key] = img
    return img


def render_frame(phase, remaining, total, session, cycles, preset_label, elapsed, total_all):
    img = static_layer(phase, session, cycles, preset_label).copy()
    cx, cy, r = W // 2, 520, 268
    frac = remaining / total
    S = 3
    size = (r + 20) * 2 + 8
    layer = Image.new("RGBA", (size * S, size * S), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    if frac > 0:
        ld.arc([4 * S, 4 * S, (size - 4) * S, (size - 4) * S], start=-90, end=-90 + 360 * frac,
               fill=WHITE + (255,), width=18 * S)
    layer = layer.resize((size, size), Image.LANCZOS)
    img.paste(layer, (cx - size // 2, cy - size // 2), layer)
    d = ImageDraw.Draw(img)
    d.text((cx, 600), fmt(remaining), font=F_TIME, fill=WHITE, anchor="mm")
    # overall progress bar
    d.rectangle([0, H - 10, W, H], fill=mix(BASE, 0.18))
    d.rectangle([0, H - 10, int(W * elapsed / total_all), H], fill=WHITE)
    return img


def render_intro(n, preset_label):
    key = ("intro", preset_label)
    if key not in _CACHE:
        img = gradient_bg(mix(BASE, 0.10), mix(BASE, -0.12, (0, 0, 0)))
        decor(img, 3)
        S = 3
        cx, cy, r = W // 2, 500, 255
        layer = Image.new("RGBA", (r * 2 * S + 40, r * 2 * S + 40), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        box = [20, 20, r * 2 * S + 20, r * 2 * S + 20]
        for a in range(0, 360, 4):
            ld.arc(box, a, a + 1.6, fill=WHITE + (255,), width=4 * S)
        layer = layer.resize((layer.width // S, layer.height // S), Image.LANCZOS)
        img.paste(layer, (cx - layer.width // 2, cy - layer.height // 2), layer)
        d = ImageDraw.Draw(img)
        tracked(d, cx, 860, "GET READY", F_READY, WHITE, tracking=16)
        d.text((cx, 930), preset_label + "  POMODORO", font=F_CHIP_SM, fill=mix(BASE, 0.75), anchor="mm")
        _CACHE[key] = img
    img = _CACHE[key].copy()
    d = ImageDraw.Draw(img)
    d.text((W // 2, 500), str(n), font=F_INTRO, fill=WHITE, anchor="mm")
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--focus", type=float, required=True, help="focus minutes")
    ap.add_argument("--break", dest="brk", type=float, required=True, help="break minutes")
    ap.add_argument("--cycles", type=int, default=3)
    ap.add_argument("--theme", default="sage", choices=list(THEMES))
    ap.add_argument("--music", default="assets/music.mp3")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    set_theme(a.theme)
    focus_s, break_s = round(a.focus * 60), round(a.brk * 60)
    preset_label = f"{a.focus:g}/{a.brk:g}"
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    chapters_path = os.path.splitext(a.out)[0] + "_chapters.txt"

    chapters, t = build_chapters(focus_s, break_s, a.cycles, a.focus, a.brk)
    with open(chapters_path, "w", encoding="utf-8") as f:
        f.write("\n".join(f"{chapter_ts(sec)} - {title}" for sec, title in chapters) + "\n")
    print(f"Total length: {chapter_ts(t)}")
    total_all = t

    wav_path = os.path.splitext(a.out)[0] + "_countdown.wav"
    make_countdown_wav(wav_path)
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-framerate", "1", "-i", "-",
           "-i", wav_path]
    if os.path.exists(a.music):
        # countdown sounds first, Lofi fades in right when the countdown ends
        cmd += ["-stream_loop", "-1", "-i", a.music, "-filter_complex",
                f"[2:a]afade=t=in:st=0:d=4,adelay={INTRO_SECONDS * 1000}|{INTRO_SECONDS * 1000}[m];"
                "[1:a][m]amix=inputs=2:duration=longest:normalize=0,alimiter=limit=0.95[a]"]
    else:
        print("No music file found -> countdown sound only")
        cmd += ["-filter_complex", "[1:a]apad[a]"]
    cmd += ["-map", "0:v", "-map", "[a]", "-r", "30", "-c:v", "libx264", "-preset", "veryfast",
            "-tune", "stillimage", "-crf", "20", "-pix_fmt", "yuv420p", "-g", "60",
            "-c:a", "aac", "-b:a", "192k", "-t", str(t), "-movflags", "+faststart", a.out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    def push(img):
        p.stdin.write(img.tobytes())

    elapsed = 0
    for n in range(INTRO_SECONDS, 0, -1):
        push(render_intro(n, preset_label))
        elapsed += 1
    for c in range(1, a.cycles + 1):
        for phase, total in (("focus", focus_s), ("break", break_s)):
            for rem in range(total, 0, -1):
                push(render_frame(phase, rem, total, c, a.cycles, preset_label, elapsed, total_all))
                elapsed += 1
        print(f"session {c}/{a.cycles} rendered", file=sys.stderr)
    p.stdin.close()
    p.wait()
    os.remove(wav_path)
    print("Saved", a.out, "and", chapters_path)


if __name__ == "__main__":
    main()
