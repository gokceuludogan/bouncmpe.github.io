#!/usr/bin/env python3
import os
import re
import unicodedata
import json
import mimetypes
import requests
from github import Github

# ─── CONFIG ───────────────────────────────────────────────────────────────────
REPO_NAME     = os.getenv("GITHUB_REPOSITORY")
ISSUE_NUMBER  = int(os.getenv("ISSUE_NUMBER", "0"))
GITHUB_TOKEN  = os.getenv("GITHUB_TOKEN")
UPLOADS_DIR   = os.path.join("static", "uploads")
CONTENT_DIR   = "content"
DEBUG         = True

if not GITHUB_TOKEN or ISSUE_NUMBER == 0:
    raise RuntimeError("GITHUB_TOKEN and ISSUE_NUMBER must be set")

# ─── INIT GITHUB CLIENT & ISSUE ───────────────────────────────────────────────
from github import Github
gh    = Github(GITHUB_TOKEN)
repo  = gh.get_repo(REPO_NAME)
issue = repo.get_issue(number=ISSUE_NUMBER)
print(f"[DEBUG] Loaded Issue #{ISSUE_NUMBER}: {issue.title!r}")

# ─── PARSE FIELDS ─────────────────────────────────────────────────────────────
def parse_fields(body: str) -> dict:
    pattern = re.compile(r"^###\s+(.*?)\n+(.+?)(?=\n^###|\Z)", re.MULTILINE | re.DOTALL)
    parsed = {re.sub(r"[^a-z0-9_]", "_", k.lower()): v.strip()
              for k, v in pattern.findall(body)}
    print("[DEBUG] Parsed fields:", parsed)
    return parsed

fields = parse_fields(issue.body)

def get_field(keys, default=""):
    if isinstance(keys, str): keys = [keys]
    for k in keys:
        if k in fields and fields[k]:
            print(f"[DEBUG] get_field '{k}': {fields[k]}")
            return fields[k]
    print(f"[DEBUG] get_field default for {keys}: {default}")
    return default

# ─── DETERMINE TYPE ────────────────────────────────────────────────────────────
event_type = get_field('event_type', '')
is_event   = bool(event_type)
print(f"[DEBUG] is_event={is_event}")

# ─── COMMON FIELDS ────────────────────────────────────────────────────────────
title_en = get_field('news_title__en' if not is_event else 'event_title__en', issue.title)
title_tr = get_field('news_title__tr' if not is_event else 'event_title__tr', '')
date_val = get_field('date', '')

raw_time = get_field('time', '')
if raw_time and re.match(r"^\d{2}:\d{2}$", raw_time):
    time_val = raw_time + ":00"
else:
    time_val = raw_time
print(f"[DEBUG] date_val={date_val}, time_val={time_val}")

# ─── IMAGE ─────────────────────────────────────────────────────────────────────
def download_image(md: str) -> str:
    m = re.search(r"!\[[^\]]*\]\((https?://[^\)]+)\)", md)
    if not m: m = re.search(r"src=\"(https?://[^\"]+)\"", md)
    if not m: return ""
    url = m.group(1)
    print(f"[DEBUG] Downloading image: {url}")
    resp = requests.get(url, timeout=15); resp.raise_for_status()
    fname = os.path.basename(url).split('?')[0]
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    path = os.path.join(UPLOADS_DIR, fname)
    with open(path, 'wb') as f: f.write(resp.content)
    return f"uploads/{fname}"

image_md = download_image(get_field(['image_markdown','image__drag___drop_here'], ''))

# ─── OUTPUT PATH ──────────────────────────────────────────────────────────────
folder = 'events' if is_event else 'news'
slug   = unicodedata.normalize('NFKD', title_en).encode('ascii','ignore').decode().lower()
slug   = re.sub(r"[^\w\s-]", '', slug)
slug   = re.sub(r"[-\s]+", '-', slug)
out_dir = os.path.join(CONTENT_DIR, folder, f"{date_val}-{slug}")
print(f"[DEBUG] out_dir={out_dir}")
os.makedirs(out_dir, exist_ok=True)

# ─── RENDER ───────────────────────────────────────────────────────────────────
if not is_event:
    # build manual front-matter for news
    header = [
        '---',
        f'type: news',
        f'title: {title_en}',
        'description: >',
        f'  {get_field(["short_description__en"],"")}',
        f'featured: false',
        f'date: {date_val}',
        f'thumbnail: {image_md}',
        '---',
        '',
        get_field(['full_content__en'], '')
    ]
    out = "\n".join(header)
    path = os.path.join(out_dir, 'index.en.md')
    print(f"[DEBUG] Writing news file: {path}")
    with open(path, 'w', encoding='utf-8') as f: f.write(out)
else:
    # event uses Jinja template
    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader('templates'), autoescape=False)
    tmpl = env.get_template(f"events/{event_type}.md.j2")
    ctx = {
        'type':      event_type,
        'title':     title_en,
        'datetime':  f"{date_val}T{time_val}",
        'speaker':   get_field('name',''),
        'duration':  get_field('duration',''),
        'location':  get_field(['location_en','location_tr'],''),
        'thumbnail': image_md,
        'description': get_field('description_en','')
    }
    print("[DEBUG] Rendering event with context:", ctx)
    out = tmpl.render(**ctx)
    path = os.path.join(out_dir, 'index.en.md')
    with open(path, 'w', encoding='utf-8') as f: f.write(out)

print("[DEBUG] Done.")
