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
            data = json.loads(m.group(1))
            print("[DEBUG] Parsed JSON fields:\n", json.dumps(data, indent=2))
            return data
        except json.JSONDecodeError as e:
            print("[DEBUG] JSON decode error:", e)
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
    print("[DEBUG] Fallback parsed fields:\n", json.dumps(parsed, indent=2))
    return parsed

fields = parse_fields(issue.body)
print("[DEBUG] All parsed fields:\n", json.dumps(fields, indent=2))

# ─── FIELD LOOKUP ──────────────────────────────────────────────────────────────
def get_field(keys, default="") -> str:
    for k in keys:
        if k in fields and fields[k]:
            print(f"[DEBUG] get_field '{k}' -> {fields[k]}")
            return fields[k]
    print(f"[DEBUG] get_field {keys} -> default '{default}'")
    return default

# ─── COMMON FIELDS ─────────────────────────────────────────────────────────────
title_en = get_field(['news_title__en', 'title_en'], issue.title)
title_tr = get_field(['news_title__tr', 'title_tr'], title_en)
date_val = get_field(['date'], '')
time_val = get_field(['time'], '')

# ─── NEWS FIELDS ───────────────────────────────────────────────────────────────
desc_en       = get_field(['short_description__en', 'description_en'], '')
desc_tr       = get_field(['short_description__tr', 'description_tr'], '')
content_en    = get_field(['full_content__en', 'content_en'], '')
content_tr    = get_field(['full_content__tr', 'content_tr'], '')
news_image_md = get_field(['image__drag___drop_here', 'image_markdown'], '')

# ─── EVENT FIELDS ──────────────────────────────────────────────────────────────
event_type     = get_field(['event_type'], '')
speaker_name   = get_field(['name'], '')
duration       = get_field(['duration'], '')
location_en    = get_field(['location_en'], '')
location_tr    = get_field(['location_tr'], '')
event_image_md = get_field(['image__optional__drag___drop', 'image_markdown'], '')
description_e  = get_field(['description_en'], '')
description_t  = get_field(['description_tr'], '')

# ─── IMAGE DOWNLOAD ────────────────────────────────────────────────────────────
def download_image(md: str) -> str:
    m = re.search(r"!\[[^\]]*\]\((https?://[^\)]+)\)", md) or \
        re.search(r'<img[^>]+src="(https?://[^\"]+)"', md)
    if not m:
        print("[DEBUG] No image URL found in:", md)
        return ''
    url = m.group(1)
    print("[DEBUG] Downloading image:", url)
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    ctype = resp.headers.get('Content-Type','').split(';')[0]
    ext = mimetypes.guess_extension(ctype) or os.path.splitext(url)[1] or '.png'
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    name = os.path.basename(url).split('?')[0].split('.')[0] + ext
    dest = os.path.join(UPLOADS_DIR, name)
    with open(dest, 'wb') as f:
        f.write(resp.content)
    print("[DEBUG] Saved image to", dest)
    return f"/uploads/{name}"

# ─── RENDER & WRITE CONTENT ────────────────────────────────────────────────────
for lang in ('en', 'tr'):
    lang_suffix = f'__{lang}'
    title = get_field([f'news_title{lang_suffix}', f'event_title{lang_suffix}', f'title{lang_suffix}'], '')
    content = get_field([f'full_content{lang_suffix}'], '')
    description = get_field([f'short_description{lang_suffix}'], '')
    date = get_field(['date'], '')
    time = get_field(['time'], '')
    datetime_str = f'{date}T{time}' if date and time else None
    image_url = get_field(image_keys, '')
    image_path = download_image(image_url)

    is_event = bool(get_field(['event_type'], ''))  # check if event_type is filled
    if is_event:
        template_name = 'event.md.j2'
        out_dir = os.path.join('content', 'events')
        slug = slugify(title)
        filename = os.path.join(out_dir, f'{date}-{slug}', f'index.{lang}.md')
    else:
        template_name = 'news.md.j2'
        out_dir = os.path.join('content', 'news')
        slug = slugify(title)
        filename = os.path.join(out_dir, f'{date}-{slug}', f'index.{lang}.md')

    context = {
        'type': 'event' if is_event else 'news',
        'title': title,
        'date': date,
        'datetime': datetime_str if is_event else None,
        'name': get_field(['name'], None) if is_event else None,
        'duration': get_field(['duration'], None) if is_event else None,
        'location': get_field([f'location_{lang}'], None) if is_event else None,
        'thumbnail': image_path,
        'description': description,
        'content': content,
        'featured': get_field(['featured'], False),
    }

    print(f"[DEBUG] Context for {lang}:\n{json.dumps(context, indent=2)}")
    print(f"[DEBUG] Writing file: {filename}")

    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(env.get_template(template_name).render(context))
