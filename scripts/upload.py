#!/usr/bin/env python3
"""Upload a video to YouTube using title/description/tags files from metadata.py.

Scheduled publishing: pass --publish-at HH:MM (Myanmar time). The video is uploaded as
private and YouTube publishes it automatically at the next HH:MM (at least 15 min ahead).

Env vars: YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN
"""
import argparse
import os
from datetime import datetime, timedelta, timezone

MMT = timezone(timedelta(hours=6, minutes=30))  # Myanmar time, no DST


def next_publish_time(hhmm, now=None, min_lead_minutes=15):
    """Next occurrence of HH:MM Myanmar time that is >= min_lead_minutes from now. Returns UTC datetime."""
    hh, mm = (int(x) for x in hhmm.split(":"))
    now = (now or datetime.now(timezone.utc)).astimezone(MMT)
    t = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if t < now + timedelta(minutes=min_lead_minutes):
        t += timedelta(days=1)
    return t.astimezone(timezone.utc)


def main():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--metadata-dir", required=True)
    ap.add_argument("--privacy", default="private", choices=["private", "unlisted", "public"])
    ap.add_argument("--publish-at", default="", help="HH:MM Myanmar time; empty = use --privacy now")
    a = ap.parse_args()

    read = lambda n: open(os.path.join(a.metadata_dir, n), encoding="utf-8").read().strip()
    title, description = read("title.txt"), read("description.txt")
    tags = [t for t in read("tags.txt").splitlines() if t]

    creds = Credentials(
        None,
        refresh_token=os.environ["YT_REFRESH_TOKEN"],
        client_id=os.environ["YT_CLIENT_ID"],
        client_secret=os.environ["YT_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
        # no `scopes=` on purpose: refresh with the scopes the token was originally granted
    )
    yt = build("youtube", "v3", credentials=creds)

    status = {"privacyStatus": a.privacy, "selfDeclaredMadeForKids": False}
    if a.publish_at:
        when = next_publish_time(a.publish_at)
        status["privacyStatus"] = "private"          # required for scheduled publishing
        status["publishAt"] = when.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        print(f"Scheduled to publish at {when.astimezone(MMT):%Y-%m-%d %H:%M} Myanmar time ({status['publishAt']})")

    body = {
        "snippet": {"title": title[:100], "description": description, "tags": tags, "categoryId": "27"},
        "status": status,
    }
    media = MediaFileUpload(a.video, chunksize=32 * 1024 * 1024, resumable=True)
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    resp = None
    while resp is None:
        st, resp = req.next_chunk()
        if st:
            print(f"Uploaded {int(st.progress() * 100)}%")
    print("Done: https://youtu.be/" + resp["id"])


if __name__ == "__main__":
    main()
