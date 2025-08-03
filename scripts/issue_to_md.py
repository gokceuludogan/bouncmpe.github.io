#!/usr/bin/env python3
import os
import re
import unicodedata
import mimetypes
import requests
from pathlib import Path
from github import Github
from jinja2 import Environment, FileSystemLoader

# ─── CONFIGURATION ─────────────────────────────────────────────────────────────
REPO_NAME    = os.getenv("GITHUB_REPOSITORY")
ISSUE_NUMBER = int(os.getenv("ISSUE_NUMBER", "0"))
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
UPLOADS_DIR  = Path("static/uploads")
CONTENT_DIR  = Path("content")
DEBUG        = True

if not GITHUB_TOKEN or ISSUE_NUMBER == 0:
    raise RuntimeError("GITHUB_TOKEN and ISSUE_NUMBER must be set")

# ─── INITIALIZE GITHUB CLIENT ─────────────────────────────────────────────────
gh    = Github(GITHUB_TOKEN)
repo  = gh.get_repo(REPO_NAME)
issue = repo.get_issue(number=ISSUE_NUMBER)
print(f"[DEBUG] Loaded Issue #{ISSUE_NUMBER}: {issue.title!r}")

# ─── PARSE ISSUE BODY INTO FIELDS ────────────────────────────────────────────────
def parse_fields(body: str) -> dict:
    pattern = re.compile(r"^###\s+(.*?)\n+(.+?)(?=\n^###|\Z)", re.MULTILINE | re.DOTALL)
    parsed = {}
    for label, val in pattern.findall(body):
        key = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")
        # normalize date from form heading
        if "date" in key and "yyyy" in key:
            key = "date"
        parsed[key] = val.strip()
        if DEBUG:
            print(f"[DEBUG] Parsed field '{label}' → '{key}': {parsed[key]!r}")
    return parsed

fields = parse_fields(issue.body)

# ─── UTILITY TO GET FIELD VALUES ────────────────────────────────────────────────
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

# ─── DETERMINE IF ISSUE IS NEWS OR EVENT ─────────────────────────────────────────
event_type = get_field('event_type', '')
is_event   = bool(event_type)
print(f"[DEBUG] is_event={is_event}")

# ─── COMMON FIELDS ──────────────────────────────────────────────────────────────
title_en = get_field('news_title_en' if not is_event else 'event_title_en', issue.title)
title_tr = get_field('news_title_tr' if not is_event else 'event_title_tr', '')

# Date & time normalization
date_val = get_field('date', '')
raw_time = get_field('time', '')
if raw_time and re.match(r"^\d{2}:\d{2}$", raw_time):
    time_val = raw_time + ":00"
else:
    time_val = raw_time
if DEBUG:
    print(f"[DEBUG] date_val={date_val!r}, time_val={time_val!r}")

# ─── IMAGE HANDLING FOR NEWS ────────────────────────────────────────────────────
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
    ctype = resp.headers.get('Content-Type','').split(';')[0]
    ext = mimetypes.guess_extension(ctype) or os.path.splitext(url)[1] or '.png'
    fname = os.path.basename(url).split('?')[0] + ext
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    path = UPLOADS_DIR / fname
    path.write_bytes(resp.content)
    local = f"uploads/{fname}"
    if DEBUG:
        print(f"[DEBUG] Saved image to {path} → '{local}'")
    return local

news_image_md = get_field(['image_markdown', 'image_drag_drop_here'], '')
image_md = download_image(news_image_md)

# ─── PREPARE OUTPUT DIRECTORY ───────────────────────────────────────────────────
slug = unicodedata.normalize('NFKD', title_en).encode('ascii','ignore').decode().lower()
slug = re.sub(r"[^\w\s-]", '', slug)
slug = re.sub(r"[-\s]+", '-', slug).strip('-')
subdir = 'events' if is_event else 'news'
out_dir = CONTENT_DIR / subdir / f"{date_val}-{slug}"
out_dir.mkdir(parents=True, exist_ok=True)
if DEBUG:
    print(f"[DEBUG] out_dir={out_dir}")

# ─── GENERATE AND WRITE FILES ───────────────────────────────────────────────────
if not is_event:
    # NEWS: write both languages
    for lang in ('en', 'tr'):
        desc_key    = f'short_description_{lang}'
        content_key = f'full_content_{lang}'
        description = get_field(desc_key, '')
        content     = get_field(content_key, '')
        front = [
            '---',
            'type: news',
            f'title: {title_en if lang=='en' else title_tr}',
            f'description: {description}',
            'featured: false',
            f'date: {date_val}',
            f'thumbnail: {image_md}',
            '---',
            ''
        ]
        body = front + [content]
        out_file = out_dir / f"index.{lang}.md"
        if DEBUG:
            print(f"[DEBUG] Writing news ({lang}) to: {out_file}")
        out_file.write_text("\n".join(body), encoding='utf-8')
else:
    # EVENT: no images
    env = Environment(loader=FileSystemLoader('templates'), autoescape=False)
    template_path = f"events/{event_type}.md.j2"
    tmpl = env.get_template(template_path)
    ctx = {
        'type':        event_type,
        'title':       title_en,
        'date':        date_val,
        'time':        time_val,
        'datetime':    f"{date_val}T{time_val}",
        'speaker':     get_field('name',''),
        'duration':    get_field('duration',''),
        'location':    get_field('location_en',''),
        'description': get_field('description_en','')
    }
    if DEBUG:
        print(f"[DEBUG] Rendering event using {template_path} with context: {ctx}")
    rendered = tmpl.render(**ctx)
    for lang in ('en','tr'):
        out_file = out_dir / f"index.{lang}.md"
        out_file.write_text(rendered, encoding='utf-8')
        print(f"[DEBUG] Wrote event ({lang}) → {out_file}")

print("[DEBUG] Done.")
