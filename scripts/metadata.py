#!/usr/bin/env python3
"""Build YouTube title / description / tags for one video (adapts to the preset).

Writes title.txt, description.txt, tags.txt into --outdir.
"""
import argparse
import os

import generate as g

NAMES = {"sage": "Soft Sage", "sky": "Soft Sky", "apricot": "Soft Apricot", "mauve": "Soft Mauve"}


def fmt_min(m):
    return f"{m:g}"


def duration_label(total_min):
    h, m = divmod(int(total_min), 60)
    if h and m:
        return f"{h} Hour {m} Min"
    return f"{h} Hour" if h else f"{m} Min"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--focus", type=float, required=True)
    ap.add_argument("--break", dest="brk", type=float, required=True)
    ap.add_argument("--cycles", type=int, required=True)
    ap.add_argument("--theme", default="sage")
    ap.add_argument("--music", default="assets/music.mp3")
    ap.add_argument("--outdir", required=True)
    a = ap.parse_args()

    F, B, N = fmt_min(a.focus), fmt_min(a.brk), a.cycles
    total_min = N * (a.focus + a.brk)
    dur = duration_label(total_min)
    h, m = divmod(int(total_min), 60)
    hours_words = (f"{h} hour{'s' if h != 1 else ''}" if h else "") + (f" {m} min" if m else "")
    hours_words = hours_words.strip()
    adj = (f"{h}-hour" if h else "") + (f" {m}-minute" if m else "")
    adj = adj.strip()
    has_music = os.path.exists(a.music)
    theme = NAMES.get(a.theme, "Soft Sage")

    chapters, _ = g.build_chapters(round(a.focus * 60), round(a.brk * 60), N, a.focus, a.brk)
    stamps = "\n".join(f"{g.chapter_ts(s)} - {t}" for s, t in chapters)

    lofi = " with Lofi" if has_music else ""
    title = f"{F}/{B} Pomodoro Timer{lofi} | {dur} Study With Me for Deep Focus"

    if has_music:
        intro = (f"Welcome to your dedicated {adj} focus session! 🎧 Today we're combining the classic "
                 f"{F}/{B} Pomodoro technique with relaxing Lofi beats and soft ambient white noise to help "
                 "block out distractions, boost concentration, and ease that overwhelmed-brain feeling.")
        audio = ("🎶 MUSIC & AUDIO:\n"
                 "• Chill Lofi Beats mixed with ambient white noise for maximum concentration.\n"
                 "• Designed to keep your mind engaged without pulling your attention away from your tasks.\n\n---\n\n")
    else:
        intro = (f"Welcome to your dedicated {adj} focus session! ⏱ Today we're using the classic "
                 f"{F}/{B} Pomodoro technique with a clean, calming {theme.lower()} timer to help "
                 "block out distractions and boost concentration.")
        audio = ""

    desc = f"""{intro}

Grab your favorite drink, clear your workspace, and let's lock in together! ✨

---

⏰ TIMESTAMPS
{stamps}

---

💡 HOW THE {F}/{B} POMODORO TECHNIQUE WORKS:
• Work with full focus for {F} minutes.
• Take a complete brain rest for {B} minutes.
• Repeat for {N} full cycles to complete {hours_words} of deep work!

{audio}✨ TIPS FOR THIS SESSION:
1. Write down your top 1–3 priorities before pressing play.
2. Put your phone in 'Do Not Disturb' or in another room.
3. During {B}-minute breaks, step away, stretch, hydrate, and rest your eyes!

🌸 Theme today: {theme}

💬 Let me know in the comments: What are you working on or studying today?

#StudyWithMe #PomodoroTimer #{'LofiStudyMusic' if has_music else 'StudyTimer'} #DeepFocus #StudySession #FocusTimer
"""

    tags = [
        "study with me", f"{F}/{B} pomodoro", f"pomodoro timer{lofi.lower()}",
        f"{dur.lower()} study with me", f"study timer {F} {B}", "focus timer",
        f"study with me pomodoro {dur.lower()}", "productivity timer", "study motivation",
        "pomodoro study with me", "deep focus", "aesthetic study with me",
    ]
    if has_music:
        tags[3:3] = ["lofi study music", "lofi and white noise", "deep focus lofi", "lofi hip hop study beats"]
    tags = [t for t in dict.fromkeys(tags)]
    while len(",".join(tags)) > 480:
        tags.pop()

    os.makedirs(a.outdir, exist_ok=True)
    open(os.path.join(a.outdir, "title.txt"), "w", encoding="utf-8").write(title)
    open(os.path.join(a.outdir, "description.txt"), "w", encoding="utf-8").write(desc)
    open(os.path.join(a.outdir, "tags.txt"), "w", encoding="utf-8").write("\n".join(tags))
    print(title)


if __name__ == "__main__":
    main()
