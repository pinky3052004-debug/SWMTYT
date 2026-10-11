# Daily Pomodoro → YouTube (cron-job.org + GitHub Actions)

1 video per day, in order. One colour for all four presets, then the colour changes:

| Days | Colour | Videos (one per day) |
|---|---|---|
| 1-4   | Soft Sage (green)   | 25/5 (2h) -> 50/10 (4h) -> 30/10 (2h) -> 45/10 (3h40) |
| 5-8   | Soft Sky (blue)     | same order |
| 9-12  | Soft Apricot        | same order |
| 13-16 | Soft Mauve          | same order |
| 17+   | back to Sage        | repeat |

The day number is calculated from the date (Asia/Yangon time) since START_DATE
(default 2026-10-12). To change it: Settings → Variables → Actions → New variable START_DATE = YYYY-MM-DD.

## 1. GitHub secrets (Settings → Secrets and variables → Actions)
YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN

## 2. GitHub token for cron-job.org
Settings → Developer settings → Fine-grained tokens → this repo only → Permissions: **Actions: Read and write**.

## 3. cron-job.org job
- URL: https://api.github.com/repos/OWNER/REPO/actions/workflows/pomodoro.yml/dispatches
- Schedule: every day at your chosen time
- Advanced → Request method: POST
- Headers:
  - Authorization: Bearer YOUR_GITHUB_TOKEN
  - Accept: application/vnd.github+json
  - X-GitHub-Api-Version: 2022-11-28
  - Content-Type: application/json
  - User-Agent: cron-job.org
- Body:
  {"ref":"main","inputs":{"upload":"true","privacy":"private"}}
- Success = HTTP 204

Leave preset/theme out = automatic rotation. To force one, add "preset":"50-10" and/or "theme":"mint" to inputs.

## Title / description / tags
`scripts/metadata.py` builds them automatically for each preset (title, timestamps, "how it works" text, tags).
Edit the wording inside that file. If `assets/music.mp3` exists, the text mentions Lofi + white noise;
if not, it uses a no-music version (so the description never claims music that isn't in the video).
Cycles (video length) are set in the workflow: 25/5 x4 = 2h, 30/10 x3 = 2h, 50/10 x4 = 4h, 45/10 x4 = 3h40.

## Audio order
0:00-0:07  countdown ticks (7..1) -> start chime at 0:07 -> Lofi (assets/music.mp3) fades in and loops until the end.
No music file = countdown sound only.
