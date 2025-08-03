#!/usr/bin/env python3
import os
import re
import unicodedata
import mimetypes
import requests
from pathlib import Path
from github import Github
from jinja2 import Environment, FileSystemLoader

# ─── CONFIG ───────────────────────────────────────────────────────────────────
REPO_NAME    = os.getenv("GITHUB_REPOSITORY")
ISSUE_NUMBER = int(os.getenv("ISSUE_NUMBER", "0"))
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
UPLOADS_DIR  = Path("static/uploads")
CONTENT_DIR  = Path("content")
DEBUG        = True

if not GITHUB_TOKEN or ISSUE_NUMBER == 0:
    raise RuntimeError("GITHUB_TOKEN and ISSUE_NUMBER must be set")

# ─── INIT CLIENT ──────────────────────────────────────────────────────────────
gh    = Github(GITHUB_TOKEN)
repo  = gh.get_repo(REPO_NAME)
issue = repo.get_issue(number=ISSUE_NUMBER)
print(f"[DEBUG] Loaded Issue #{ISSUE_NUMBER}: {issue.title!r}")

# ─── PARSE FIELDS ─────────────────────────────────────────────────────────────
def parse_fields(body: str) -> dict:
    pattern = re.compile(r"^###\s+(.*?)\n+(.+?)(?=\n^###|\Z)", re.MULTILINE | re.DOTALL)
    parsed = {}
    for label, val in pattern.findall(body):
        key = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")
        if "date" in key and "yyyy" in key:
            key = "date"
        parsed[key] = val.strip()
        if DEBUG:
            print(f"[DEBUG] Parsed field '{label}' → '{key}': {parsed[key]!r}")
    return parsed

fields = parse_fields(issue.body)

# ─── FIELD LOOKUP ─────────────────────────────────────────────────────────────
def get_field(keys, default=""):
    if isinstance(keys, str):
        keys = [keys]
    for k in keys:
        if k in fields and fields[k]:
            if DEBUG:
                print(f"[DEBUG] get_field '{k}': {fields[k]!r}")
            return fields[k]
    if DEBUG:
        print(f"[DEBUG] get_field default for {keys}: {default!r}")
    return default

# ─── DETERMINE TYPE ────────────────────────────────────────────────────────────
event_type = get_field('event_type', '')
is_event   = bool(event_type)
print(f"[DEBUG] is_event={is_event}")

# ─── COMMON VALUES ─────────────────────────────────────────────────────────────
title_en = get_field('news_title_en' if not is_event else 'event_title_en', issue.title)
title_tr = get_field('news_title_tr' if not is_event else 'event_title_tr', '')
date_val = get_field('date', '')

raw_time = get_field('time', '')
if raw_time and re.match(r"^\d{2}:\d{2}$", raw_time):
    time_val = raw_time + ":00"
else:
    time_val = raw_time
if DEBUG:
    print(f"[DEBUG] date_val={date_val!r}, time_val={time_val!r}")

# ─── IMAGE DOWNLOAD ────────────────────────────────────────────────────────────
def download_image(md: str) -> str:
    m = re.search(r"!\[[^\]]*\]\((https?://[^\)]+)\)", md)
    if not m:
        m = re.search(r"src=\"(https?://[^\"]+)\"", md)
    if not m:
        return ""
    url = m.group(1)
    if DEBUG:
        print(f"[DEBUG] Downloading image: {url}")
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    content_type = resp.headers.get('Content-Type', '').split(';')[0]
    ext = mimetypes.guess_extension(content_type) or os.path.splitext(url)[1] or '.png'
    filename = os.path.basename(url).split('?')[0] + ext
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    path = UPLOADS_DIR / filename
    path.write_bytes(resp.content)
    local = f"uploads/{filename}"
    if DEBUG:
        print(f"[DEBUG] Saved image to {path} → '{local}' (Content-Type: {content_type})")
    return local

image_md = download_image(get_field(['image_markdown', 'image_drag_drop_here'], ''))

# ─── OUTPUT WRITER ─────────────────────────────────────────────────────────────
# Prepare output directory and slug
folder = 'events' if is_event else 'news'
slug   = unicodedata.normalize('NFKD', title_en).encode('ascii','ignore').decode().lower()
slug   = re.sub(r"[^\w\s-]", '', slug)
slug   = re.sub(r"[-\s]+", '-', slug).strip('-')
out_dir = CONTENT_DIR / folder / f"{date_val}-{slug}"
out_dir.mkdir(parents=True, exist_ok=True)
if DEBUG:
    print(f"[DEBUG] out_dir={out_dir}")

# ─── RENDER OUTPUT ─────────────────────────────────────────────────────────────
if not is_event:
    for lang in ('en', 'tr'):
        desc_key    = f'short_description_{lang}'
        content_key = f'full_content_{lang}'
        desc    = get_field(desc_key, '')
        content = get_field(content_key, '')
        header = [
            '---',
            'type: news',
            f'title: {title_en if lang=='en' else title_tr}',
            f'description: {desc}',
            'featured: false',
            f'date: {date_val}',
            f'thumbnail: {image_md}',
            '---',
            '',
            content
        ]
        out = "\n".join(header)
        path = out_dir / f"index.{lang}.md"
        if DEBUG:
            print(f"[DEBUG] Writing news ({lang}) to: {path}")
        path.write_text(out, encoding='utf-8')
else:
    env = Environment(loader=FileSystemLoader('templates'), autoescape=False)
    tmpl = env.get_template(f"events/{event_type}.md.j2")
    ctx = {
        'type':      event_type,
        'title':     title_en,
        'datetime':  f"{date_val}T{time_val}",
        'speaker':   get_field('name', ''),
        'duration':  get_field('duration', ''),
        'location':  get_field('location_en', ''),
        'thumbnail': image_md,
        'description': get_field('description_en', '')
    }
    if DEBUG:
        print(f"[DEBUG] Rendering event with context: {ctx}")
    out = tmpl.render(**ctx)
    (out_dir / 'index.en.md').write_text(out, encoding='utf-8')

print("[DEBUG] Done.")
