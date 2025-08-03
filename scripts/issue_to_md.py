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

# ─── PARSE FORM DATA ───────────────────────────────────────────────────────────
def parse_fields(body: str) -> dict:
    m = re.search(r"<!--\s*({.*?})\s*-->", body or "", re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
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
print("[DEBUG] Parsed fields:\n", json.dumps(fields, indent=2))

def get_field(keys, default="") -> str:
    for k in keys:
        if k in fields and fields[k]:
            return fields[k]
    return default

# ─── COMMON FIELDS ─────────────────────────────────────────────────────────────
title_en = get_field(['news_title__en', 'title_en'], issue.title)
title_tr = get_field(['news_title__tr', 'title_tr'], title_en)
date_val = get_field(['date'], '')
time_val = get_field(['time'], '')

# ─── IMAGE DOWNLOAD ────────────────────────────────────────────────────────────
def download_image(md: str) -> str:
    m = re.search(r"!\[[^\]]*\]\((https?://[^\)]+)\)", md) or \
        re.search(r'<img[^>]+src="(https?://[^\"]+)"', md)
    if not m:
        return ''
    url = m.group(1)
    print("[DEBUG] Downloading image from:", url)
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    ctype = resp.headers.get('Content-Type','').split(';')[0]
    ext = mimetypes.guess_extension(ctype) or os.path.splitext(url)[1] or '.png'
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    name = os.path.basename(url).split('?')[0].split('.')[0] + ext
    dest = os.path.join(UPLOADS_DIR, name)
    with open(dest, 'wb') as f:
        f.write(resp.content)
    return f"/uploads/{name}"

# ─── RENDER FOR EACH LANGUAGE ──────────────────────────────────────────────────
for lang in ('en', 'tr'):
    event_type = get_field(['event_type'], '')
    is_event = bool(event_type)

    print(f"[DEBUG] Rendering for lang={lang}, is_event={is_event}")

    ctx = {}
    if is_event:
        # EVENT
        ctx = {
            'type':       event_type,
            'title':      title_tr if lang == 'tr' else title_en,
            'name':       get_field(['name'], ''),
            'datetime':   f"{date_val}T{time_val}:00" if date_val and time_val else '',
            'duration':   get_field(['duration'], ''),
            'location':   get_field(['location_tr'], '') if lang == 'tr' else get_field(['location_en'], ''),
            'thumbnail':  download_image(get_field(['image__optional__drag___drop', 'image_markdown'], '')),
            'description': get_field(['description_tr'], '') if lang == 'tr' else get_field(['description_en'], ''),
        }
        template_name = 'event.md.j2'
    else:
        # NEWS
        ctx = {
            'type':       'news',
            'title':      title_tr if lang == 'tr' else title_en,
            'date':       date_val,
            'description': get_field(['short_description__tr'], '') if lang == 'tr' else get_field(['short_description__en'], ''),
            'thumbnail':  download_image(get_field(['image__drag___drop_here', 'image_markdown'], '')),
            'featured':   False,
            'content':    get_field(['full_content__tr'], '') if lang == 'tr' else get_field(['full_content__en'], ''),
        }
        template_name = 'news.md.j2'

    print(f"[DEBUG] Final context for lang={lang}:\n", json.dumps(ctx, indent=2))

    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=False)
    rendered = env.get_template(template_name).render(**ctx)

    raw_title = ctx['title'] or title_en
    slug = unicodedata.normalize('NFKD', raw_title).encode('ascii','ignore').decode().lower()
    slug = re.sub(r"[-\s]+", '-', slug)
    slug = re.sub(r"[^a-z0-9-]", '', slug).strip('-')

    folder = 'events' if is_event else 'news'
    out_dir = os.path.join('content', folder, f"{date_val}-{slug}")
    os.makedirs(out_dir, exist_ok=True)
    filename = f"index.{lang}.md"
    filepath = os.path.join(out_dir, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(rendered)

