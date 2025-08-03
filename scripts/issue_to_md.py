#!/usr/bin/env python3
import os
import re
import unicodedata
import mimetypes
import requests
import json
from uuid import uuid4
from pathlib import Path
from github import Github
from jinja2 import Environment, FileSystemLoader

# ─── CONFIGURATION ─────────────────────────────────────────────────────────────
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY")
GITHUB_TOKEN      = os.getenv("GITHUB_TOKEN")
GITHUB_EVENT_PATH = os.getenv("GITHUB_EVENT_PATH")

# Determine ISSUE_NUMBER
_issue_num = 0
if GITHUB_EVENT_PATH and os.path.exists(GITHUB_EVENT_PATH):
    with open(GITHUB_EVENT_PATH) as f:
        payload = json.load(f)
        _issue_num = payload.get("issue", {}).get("number", 0)
ISSUE_NUMBER = _issue_num or int(os.getenv("ISSUE_NUMBER", "0"))

# Directories & flags
UPLOADS_DIR = Path("static/uploads")
CONTENT_DIR = Path("content")
DEBUG       = True

# Validate env
missing = [n for n in ["GITHUB_REPOSITORY","GITHUB_TOKEN"] if not os.getenv(n)]
if missing or ISSUE_NUMBER == 0:
    raise RuntimeError(f"Missing required env vars or issue number: {', '.join(missing)} | ISSUE_NUMBER={ISSUE_NUMBER}")

# ─── GITHUB INIT ───────────────────────────────────────────────────────────────
gh    = Github(GITHUB_TOKEN)
repo  = gh.get_repo(GITHUB_REPOSITORY)
issue = repo.get_issue(number=ISSUE_NUMBER)
if DEBUG:
    print(f"[DEBUG] Repo: {GITHUB_REPOSITORY}")
    print(f"[DEBUG] Loaded Issue #{ISSUE_NUMBER}: title='{issue.title}' created_at={issue.created_at}")
    print(f"[DEBUG] Issue body:\n{issue.body}\n{'-'*40}")

# ─── PARSING UTILITIES ──────────────────────────────────────────────────────────
def parse_fields(body: str) -> dict:
    parts = re.split(r"^###\s+", body or "", flags=re.MULTILINE)[1:]
    data = {}
    for part in parts:
        lines = part.splitlines()
        label = lines[0].strip()
        key   = re.sub(r"[^a-z0-9]+","_", label.lower()).strip("_")
        # unify date field
        if key.startswith('date_'):
            key = 'date'
        data[key] = "\n".join(lines[1:]).strip()
        if DEBUG:
            print(f"[DEBUG] Parsed field '{label}' => key='{key}', value={data[key]!r}")
    return data

fields = parse_fields(issue.body)
if DEBUG:
    print(f"[DEBUG] Full parsed fields dict: {json.dumps(fields, indent=2)}")

# Field map with extended keys
FIELD_MAP = {
    'content_kind':    ['event_type', 'content_kind'],
    'title_en':        ['event_title_en', 'news_title_en', 'title_en'],
    'title_tr':        ['event_title_tr', 'news_title_tr', 'title_tr'],
    'date':            ['date'],
    'time':            ['time'],
    'speaker':         ['speaker', 'presenter', 'speaker_presenter_name'],
    'duration':        ['duration'],
    'location_en':     ['location_en', 'location'],
    'location_tr':     ['location_tr', 'location'],
    'short_desc_en':   ['short_description_en', 'description_en'],
    'short_desc_tr':   ['short_description_tr', 'description_tr'],
    'content_en':      ['full_content_en', 'content_en'],
    'content_tr':      ['full_content_tr', 'content_tr'],
    'image_markdown':  ['image_markdown', 'image_drag_drop_here', 'image_optional_drag_drop'],
}

def get_field(name, default=""):
    for key in FIELD_MAP.get(name, [name]):
        if key in fields and fields[key] and not fields[key].startswith('_No response'):
            if DEBUG:
                print(f"[DEBUG] get_field: using '{key}' => '{fields[key]}'")
            return fields[key]
    if DEBUG:
        print(f"[DEBUG] get_field: no value for {name}, defaulting to '{default}'")
    return default

# ─── DETERMINE TYPE ────────────────────────────────────────────────────────────
kind     = get_field('content_kind', 'news')
is_event = (kind != 'news')
print(f"[DEBUG] Content kind: {kind}, is_event={is_event}")

# ─── NORMALIZE COMMON ──────────────────────────────────────────────────────────
title_en = get_field('title_en', issue.title)
title_tr = get_field('title_tr', '')
date_val = get_field('date', issue.created_at.date().isoformat())
raw_time = get_field('time', '').strip()
time_val = raw_time + ":00" if re.match(r"^\d{2}:\d{2}$", raw_time) else raw_time
print(f"[DEBUG] title_en={title_en}, title_tr={title_tr}, date={date_val}, time={time_val}")

# ─── IMAGE HANDLING ─────────────────────────────────────────────────────────────
def download_image(md: str) -> str:
    if DEBUG:
        print(f"[DEBUG] download_image input markdown: {md}")
    m = re.search(r"!\[[^\]]*\]\((https?://[^\)]+)\)", md) or re.search(r"src=\"(https?://[^\"]+)\"", md)
    if not m:
        if DEBUG: print("[DEBUG] No image markdown or src found.")
        return ""
    url = m.group(1)
    if DEBUG: print(f"[DEBUG] Attempting to download image URL: {url}")
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"[DEBUG] Image download failed: {e}")
        return ""
    ext   = mimetypes.guess_extension(resp.headers.get('Content-Type','').split(';')[0]) or Path(url).suffix or '.png'
    fname = f"{ISSUE_NUMBER}_{uuid4().hex[:8]}{ext}"
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    path = UPLOADS_DIR / fname
    path.write_bytes(resp.content)
    print(f"[DEBUG] Saved image to {path}")
    return f"uploads/{fname}"

# ─── SLUG & DIR ─────────────────────────────────────────────────────────────────
def make_slug(text: str) -> str:
    slug = unicodedata.normalize('NFKD', text).encode('ascii','ignore').decode().lower()
    slug = re.sub(r"[^\w\s-]", '', slug)
    slug = re.sub(r"[-\s]+", '-', slug).strip('-')
    return f"{slug}-{ISSUE_NUMBER}"

slug   = make_slug(title_en)
subdir = 'events' if is_event else 'news'
out_dir = CONTENT_DIR / subdir / f"{date_val}-{slug}"
out_dir.mkdir(parents=True, exist_ok=True)
print(f"[DEBUG] Output directory: {out_dir}")

# ─── RENDER ─────────────────────────────────────────────────────────────────────
env = Environment(loader=FileSystemLoader('templates'), autoescape=False)
tmpl_name = 'event.md.j2' if is_event else 'news.md.j2'
tmpl = env.get_template(tmpl_name)
print(f"[DEBUG] Using template: {tmpl_name}")

# Prepare context
ctx = {
    'content_kind':  kind,
    'title':         title_en,
    'date':          date_val,
    'time':          time_val,
    'datetime':      f"{date_val}T{time_val}" if time_val else '',
    'speaker':       get_field('speaker',''),
    'duration':      get_field('duration',''),
    'location':      get_field('location_en',''),
    'description':   get_field('short_desc_en',''),
    'content':       get_field('content_en',''),
    'thumbnail':     download_image(get_field('image_markdown',''))
}
print(f"[DEBUG] Base context: {json.dumps({k:v for k,v in ctx.items() if k!='thumbnail'}, indent=2)}")

# Render both languages
for lang in ('en','tr'):
    lang_ctx = ctx.copy()
    lang_ctx.update({
        'title':       get_field(f'title_{lang}', lang_ctx['title']),
        'description': get_field(f'short_desc_{lang}',''),
        'content':     get_field(f'content_{lang}',''),
        'location':    get_field(f'location_{lang}', lang_ctx['location']),
    })
    print(f"[DEBUG] Rendering for lang={lang}: title={lang_ctx['title']!r}, desc={lang_ctx['description']!r}")
    rendered = tmpl.render(**lang_ctx)
    out_path = out_dir / f"index.{lang}.md"
    out_path.write_text(rendered, encoding='utf-8')
    print(f"[DEBUG] Wrote file: {out_path}\n---\n{rendered[:200]}...\n---")

print("[DEBUG] Processing complete.")
