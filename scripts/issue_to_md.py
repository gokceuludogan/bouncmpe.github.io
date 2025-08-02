#!/usr/bin/env python3
import os
import re
import unicodedata
import json
import mimetypes
import requests
from github import Github
from jinja2 import Environment, FileSystemLoader

# ─── CONFIG ───────────────────────────────────────────────────────────────────
REPO_NAME     = os.getenv("GITHUB_REPOSITORY")
ISSUE_NUMBER  = int(os.getenv("ISSUE_NUMBER", "0"))
GITHUB_TOKEN  = os.getenv("GITHUB_TOKEN")
TEMPLATES_DIR = "templates"
UPLOADS_DIR   = os.path.join("static", "uploads")

if not GITHUB_TOKEN or ISSUE_NUMBER == 0:
    raise RuntimeError("GITHUB_TOKEN and ISSUE_NUMBER must be set")

# ─── INIT GITHUB CLIENT & ISSUE ───────────────────────────────────────────────
gh    = Github(GITHUB_TOKEN)
repo  = gh.get_repo(REPO_NAME)
issue = repo.get_issue(number=ISSUE_NUMBER)

# ─── PARSE FIELDS ─────────────────────────────────────────────────────────────
def parse_fields(body: str):
    # Try JSON form data
    m = re.search(r"<!--\s*({.*})\s*-->", body or "", re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    # Fallback: headings-based parse
    pattern = re.compile(
        r"^#{1,6}\s+(.*?)\s*\r?\n+(.*?)(?=^#{1,6}\s|\Z)",
        re.MULTILINE | re.DOTALL
    )
    parsed = {}
    for label, val in pattern.findall(body or ""):
        key = re.sub(r"[^a-z0-9_]", "_", label.lower()).strip("_")
        parsed[key] = val.strip()
    if 'date__yyyy_mm_dd' in parsed:
        parsed['date'] = parsed.pop('date__yyyy_mm_dd')
    return parsed

fields = parse_fields(issue.body)

def get_field(names, default=""):
    for n in names:
        if n in fields and fields[n]:
            return fields[n]
    return default

# ─── COMMON ───────────────────────────────────────────────────────────────────
title_en = get_field(['title_en'], issue.title)
title_tr = get_field(['title_tr'], '')
date_val = get_field(['date'], '')
time_val = get_field(['time'], '')

# ─── NEWS ─────────────────────────────────────────────────────────────────────
desc_en       = get_field(['description_en'], '')
content_en    = get_field(['content_en'], '')
news_image_md = get_field(['image_markdown'], '')

# ─── EVENT ────────────────────────────────────────────────────────────────────
event_type     = get_field(['event_type'], '')
speaker_name   = get_field(['name'], '')
duration       = get_field(['duration'], '')
location_en    = get_field(['location_en'], '')
location_tr    = get_field(['location_tr'], '')
event_image_md = get_field(['image_markdown'], '')
description_e  = get_field(['description_en'], '')
description_t  = get_field(['description_tr'], '')

# ─── IMAGE DOWNLOAD ───────────────────────────────────────────────────────────
def download_image(md: str) -> str:
    m = re.search(r"!\[[^\]]*\]\((https?://[^\)]+)\)", md) or \
        re.search(r"<img[^>]+src=\"(https?://[^\"]+)\"", md)
    if not m:
        return ""
    url = m.group(1)
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    ctype = resp.headers.get('Content-Type','').split(';')[0]
    ext = mimetypes.guess_extension(ctype) or os.path.splitext(url)[1] or '.png'
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    base = os.path.basename(url).split('?')[0]
    name = os.path.splitext(base)[0] + ext
    dest = os.path.join(UPLOADS_DIR, name)
    with open(dest, 'wb') as f:
        f.write(resp.content)
    return f"/uploads/{name}"

# ─── BUILD CONTEXT ────────────────────────────────────────────────────────────
is_event    = bool(event_type)
# append :00 for HH:MM:SS
datetime_iso = f"{date_val}T{time_val}:00" if date_val and time_val else ''

ctx = {
    'type':       event_type if is_event else 'news',
    'title':      title_en,
    'name':       speaker_name if is_event else None,
    'datetime':   datetime_iso if is_event else None,
    'date':       date_val if not is_event else None,
    'duration':   duration if is_event else None,
    'location':   location_en if is_event else None,
    'thumbnail':  download_image(event_image_md if is_event else news_image_md),
    'description': description_e if is_event else desc_en,
    'featured':   False if not is_event else None,
    'content':    content_en if not is_event else None,
}

template_file = "event.md.j2" if is_event else "news.md.j2"

# ─── RENDER & WRITE ───────────────────────────────────────────────────────────
env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=False)
tmpl = env.get_template(template_file)
output = tmpl.render(**ctx)

# create slug
slug = unicodedata.normalize("NFKD", title_en)\
       .encode("ascii","ignore")\
       .decode().lower()
slug = re.sub(r"[^\w]+", "-", slug).strip("-")

folder = "events" if is_event else "news"
out_dir = os.path.join("content", folder, f"{date_val}-{slug}")
os.makedirs(out_dir, exist_ok=True)
with open(os.path.join(out_dir, "index.en.md"), "w", encoding="utf-8") as f:
    f.write(output)
