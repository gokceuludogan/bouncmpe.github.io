#!/usr/bin/env python3
import os
import re
import unicodedata
import mimetypes
import requests
from uuid import uuid4
from pathlib import Path
from github import Github
from jinja2 import Environment, FileSystemLoader

# ─── CONFIGURATION ─────────────────────────────────────────────────────────────
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY")
ISSUE_NUMBER      = int(os.getenv("ISSUE_NUMBER", "0"))
GITHUB_TOKEN      = os.getenv("GITHUB_TOKEN")
UPLOADS_DIR       = Path("static/uploads")
CONTENT_DIR       = Path("content")
DEBUG             = True

if not GITHUB_REPOSITORY or not GITHUB_TOKEN or ISSUE_NUMBER == 0:
    missing = [n for n in ["GITHUB_REPOSITORY","GITHUB_TOKEN","ISSUE_NUMBER"] if not os.getenv(n) or (n=="ISSUE_NUMBER" and ISSUE_NUMBER==0)]
    raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")

# ─── GITHUB INITIALIZATION ──────────────────────────────────────────────────────
gh    = Github(GITHUB_TOKEN)
repo  = gh.get_repo(GITHUB_REPOSITORY)
issue = repo.get_issue(number=ISSUE_NUMBER)
if DEBUG:
    print(f"[DEBUG] Loaded Issue #{ISSUE_NUMBER}: {issue.title!r}")

# ─── PARSING UTILITIES ──────────────────────────────────────────────────────────
def parse_fields(body: str) -> dict:
    parts = re.split(r"^###\s+", body or "", flags=re.MULTILINE)[1:]
    parsed = {}
    for part in parts:
        lines = part.splitlines()
        label = lines[0].strip()
        key   = re.sub(r"[^a-z0-9]+","_", label.lower()).strip("_")
        if key.startswith('date'):
            key = 'date'
        value = "\n".join(lines[1:]).strip()
        parsed[key] = value
        if DEBUG:
            print(f"[DEBUG] Parsed field '{label}' → '{key}': {value!r}")
    return parsed

fields = parse_fields(issue.body)

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

# ─── DETERMINE CONTENT KIND ─────────────────────────────────────────────────────
content_kind = get_field('content_kind', 'news')  # 'event' expected for events
is_event     = (content_kind == 'event')
if DEBUG:
    print(f"[DEBUG] content_kind={content_kind}, is_event={is_event}")

# ─── COMMON FIELDS & NORMALIZATION ──────────────────────────────────────────────
title_en = get_field(['event_title__en','title_en'], issue.title)
title_tr = get_field(['event_title__tr','title_tr'], '')
date_val = get_field('date', '').strip() or issue.created_at.date().isoformat()
raw_time = get_field('time', '').strip()
time_val = raw_time + ":00" if re.match(r"^\d{2}:\d{2}$", raw_time) else raw_time
if DEBUG:
    print(f"[DEBUG] date_val={date_val!r}, time_val={time_val!r}")

# ─── IMAGE HANDLING ─────────────────────────────────────────────────────────────
def download_image(md: str) -> str:
    m = re.search(r"!\[[^\]]*\]\((https?://[^\)]+)\)", md) or re.search(r"src=\"(https?://[^\"]+)\"", md)
    if not m:
        if DEBUG:
            print("[DEBUG] No image URL found in markdown")
        return ""
    url = m.group(1)
    if DEBUG:
        print(f"[DEBUG] Downloading image: {url}")
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        if DEBUG:
            print(f"[DEBUG] Image download failed: {e}")
        return ""
    ext   = mimetypes.guess_extension(resp.headers.get('Content-Type','').split(';')[0]) or Path(url).suffix or '.png'
    fname = f"{ISSUE_NUMBER}_{uuid4().hex[:8]}{ext}"
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    path = UPLOADS_DIR / fname
    path.write_bytes(resp.content)
    if DEBUG:
        print(f"[DEBUG] Saved image to {path}")
    return f"uploads/{fname}"

# ─── SLUG & OUTPUT DIRECTORY ────────────────────────────────────────────────────
def make_slug(text: str) -> str:
    slug = unicodedata.normalize('NFKD', text).encode('ascii','ignore').decode().lower()
    slug = re.sub(r"[^\w\s-]", '', slug)
    slug = re.sub(r"[-\s]+", '-', slug).strip('-')
    return f"{slug}-{ISSUE_NUMBER}"

slug   = make_slug(title_en)
subdir = 'events' if is_event else 'news'
out_dir = CONTENT_DIR / subdir / f"{date_val}-{slug}"
out_dir.mkdir(parents=True, exist_ok=True)
if DEBUG:
    print(f"[DEBUG] out_dir={out_dir}")

# ─── PROCESSORS ─────────────────────────────────────────────────────────────────
class BaseProcessor:
    def write(self, path: Path, text: str):
        path.write_text(text, encoding='utf-8')
        if DEBUG:
            print(f"[DEBUG] Wrote file: {path}")

class NewsProcessor(BaseProcessor):
    def render(self):
        image_field_md = get_field(['image_markdown', 'image_drag_drop_here'], '')
        image_md       = download_image(image_field_md)

        for lang in ('en','tr'):
            desc_key    = f'short_description_{lang}'
            content_key = f'full_content_{lang}'
            desc        = get_field(desc_key, '').strip()

            front = [
                '---',
                'type: news',
                f"title: {title_en if lang=='en' else title_tr}",
                f"date: {date_val}",
                f"thumbnail: {image_md}"  
            ]
            if '\n' in desc:
                front.append('description: |')
                for line in desc.splitlines(): front.append(f'  {line}')
            else:
                front.append(f'description: {desc}')
            front.extend(['featured: false', '---', ''])

            body = get_field(content_key)
            out_file = out_dir / f"index.{lang}.md"
            self.write(out_file, "\n".join(front + [body]))

class EventProcessor(BaseProcessor):
    def render(self):
        # Debug: start event rendering
        print("[DEBUG] Entering EventProcessor.render()")
        env  = Environment(loader=FileSystemLoader('templates'), autoescape=False)
        tmpl = env.get_template('event_base.md.j2')

        for lang in ('en','tr'):
            # Build context
            ctx = {
                'type':        content_kind,
                'title':       title_en if lang=='en' else title_tr,
                'date':        date_val,
                'time':        time_val,
                'datetime':    f"{date_val}T{time_val}",
                'speaker':     get_field(['speaker','presenter','speaker_presenter_name'], ''),
                'duration':    get_field('duration',''),
                'location':    get_field([f'location_{lang}','location'], ''),
                'description': get_field(f'description_{lang}','')
            }
            print(f"[DEBUG] EventProcessor.context[{lang}] = {ctx}")
            try:
                rendered = tmpl.render(**ctx)
            except Exception as e:
                print(f"[DEBUG] Template rendering error for lang={lang}: {e}")
                raise
            print(f"[DEBUG] Rendered event_base.md.j2 for {lang}:\n{rendered}\n---")
            out_file = out_dir / f"index.{lang}.md"
            self.write(out_file, rendered)
            print(f"[DEBUG] Wrote Event file: {out_file}")

# Dispatch
processor = EventProcessor() if is_event else NewsProcessor()
processor.render()
print("[DEBUG] Processing complete.")
