#!/usr/bin/env python3
"""Upload a video to YouTube using title/description/tags files from metadata.py.

Env vars: YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN
"""
import argparse
import os

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

ap = argparse.ArgumentParser()
ap.add_argument("--video", required=True)
ap.add_argument("--metadata-dir", required=True)
ap.add_argument("--privacy", default="private", choices=["private", "unlisted", "public"])
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
    scopes=["https://www.googleapis.com/auth/youtube.upload"],
)
yt = build("youtube", "v3", credentials=creds)
body = {
    "snippet": {"title": title[:100], "description": description, "tags": tags, "categoryId": "27"},
    "status": {"privacyStatus": a.privacy, "selfDeclaredMadeForKids": False},
}
media = MediaFileUpload(a.video, chunksize=32 * 1024 * 1024, resumable=True)
req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
resp = None
while resp is None:
    status, resp = req.next_chunk()
    if status:
        print(f"Uploaded {int(status.progress() * 100)}%")
print("Done: https://youtu.be/" + resp["id"])
