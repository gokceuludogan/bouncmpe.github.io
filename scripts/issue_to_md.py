#!/usr/bin/env python3
import os
import re
import unicodedata
import mimetypes
import requests
import logging
from uuid import uuid4
from pathlib import Path
from github import Github
from jinja2 import Environment, FileSystemLoader, select_autoescape

# ─── CONFIGURATION ─────────────────────────────────────────────────────────────
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY")
ISSUE_NUMBER      = os.getenv("ISSUE_NUMBER")
GITHUB_TOKEN      = os.getenv("GITHUB_TOKEN")
UPLOADS_DIR       = Path("static/uploads")
CONTENT_DIR       = Path("content")

# ─── LOGGING SETUP ───────────────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL))
log = logging.getLogger(__name__)

# ─── VALIDATE ENVIRONMENT ────────────────────────────────────────────────────────
def require_env(var_name):
    val = os.getenv(var_name)
    if not val:
        log.error(f"Missing required environment variable: {var_name}")
        raise RuntimeError(f"Missing required env var: {var_name}")
    return val

GITHUB_REPOSITORY = require_env("GITHUB_REPOSITORY")
GITHUB_TOKEN      = require_env("GITHUB_TOKEN")
ISSUE_NUMBER      = int(require_env("ISSUE_NUMBER"))
log.debug(f"Repo={GITHUB_REPOSITORY}, Issue={ISSUE_NUMBER}")

# ─── GITHUB INITIALIZATION ──────────────────────────────────────────────────────
gh    = Github(GITHUB_TOKEN)
repo  = gh.get_repo(GITHUB_REPOSITORY)
issue = repo.get_issue(number=ISSUE_NUMBER)
log.debug(f"Loaded Issue #{ISSUE_NUMBER}: '{issue.title}'")

# ─── PARSING UTILITIES ──────────────────────────────────────────────────────────
def parse_fields(body: str) -> dict:
    parts = re.split(r"^###\s+", body or "", flags=re.MULTILINE)[1:]
    fields = {}
    for part in parts:
        lines = part.splitlines()
        label = lines[0].strip()
        key = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")
        value = "\n".join(lines[1:]).strip()
        fields[key] = value
        log.debug(f"Parsed field '{label}' → '{key}': {value!r}")
    return fields

fields = parse_fields(issue.body)

def get_field(keys, default=""):
    if isinstance(keys, str):
        keys = [keys]
    for k in keys:
        if k in fields and fields[k]:
            log.debug(f"get_field '{k}' = {fields[k]!r}")
            return fields[k]
    log.debug(f"get_field default for {keys}: {default!r}")
    return default

# ─── CONTENT KIND & SUBTYPE ──────────────────────────────────────────────────────
content_kind = get_field('content_kind', 'news')
is_event = content_kind != 'news'
log.debug(f"Content kind: {content_kind} (is_event={is_event})")

# ─── COMMON FIELDS & NORMALIZATION ───────────────────────────────────────────────
title_en = get_field('title_en', issue.title)
title_tr = get_field('title_tr', '')
date_val = get_field('date', issue.created_at.date().isoformat()).strip()
raw_time = get_field('time', '').strip()
time_val = raw_time + ":00" if re.match(r"^\d{2}:\d{2}$", raw_time) else raw_time
log.debug(f"title_en={title_en!r}, date_val={date_val!r}, time_val={time_val!r}")

# ─── SLUG & OUTPUT DIRECTORY ────────────────────────────────────────────────────
def make_slug(text: str, issue_num: int) -> str:
    slug = unicodedata.normalize('NFKD', text).encode('ascii','ignore').decode().lower()
    slug = re.sub(r"[^\w\s-]", '', slug)
    slug = re.sub(r"[-\s]+", '-', slug).strip('-')
    return f"{slug}-{issue_num}"

slug = make_slug(title_en, ISSUE_NUMBER)
subdir = 'events' if is_event else 'news'
out_dir = CONTENT_DIR / subdir / f"{date_val}-{slug}"
out_dir.mkdir(parents=True, exist_ok=True)
log.debug(f"Output directory: {out_dir}")

# ─── IMAGE HANDLING ─────────────────────────────────────────────────────────────
def download_image(md: str) -> str:
    m = re.search(r"!\[[^\]]*\]\((https?://[^\)]+)\)", md) or \
            re.search(r"src=\"(https?://[^\"]+)\"", md)
    if not m:
        log.debug("No image found in field")
        return ""
    url = m.group(1)
    log.debug(f"Downloading image from {url}")
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    ext = mimetypes.guess_extension(resp.headers.get('Content-Type','').split(';')[0]) or Path(url).suffix or '.png'
    fname = f"{ISSUE_NUMBER}_{uuid4().hex[:8]}{ext}"
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    path = UPLOADS_DIR / fname
    path.write_bytes(resp.content)
    local_path = f"uploads/{fname}"
    log.debug(f"Saved image to {path}")
    return local_path

# ─── JINJA SETUP ─────────────────────────────────────────────────────────────────
env = Environment(loader=FileSystemLoader('templates'),
                   autoescape=select_autoescape(['html','md']),
                   trim_blocks=True, lstrip_blocks=True)

# ─── PROCESSING & RENDERING ──────────────────────────────────────────────────────
class BaseProcessor:
    def write(self, path: Path, text: str):
        path.write_text(text, encoding='utf-8')
        log.info(f"Wrote file: {path}")

class EventProcessor(BaseProcessor):
    def render(self):
        subtype = content_kind
        template_name = f"events/{subtype}.md.j2"
        log.debug(f"Event template selected: {template_name}")
        tmpl = env.get_template(template_name)
        for lang in ('en', 'tr'):
            context = {
                'type':        subtype,
                'title':       title_en if lang=='en' else title_tr,
                'date':        date_val,
                'time':        time_val,
                'datetime':    f"{date_val}T{time_val}" if time_val else None,
                'speaker':     get_field(['speaker','presenter'], ''),
                'duration':    get_field('duration',''),
                'location':    get_field(f'location_{lang}', get_field('location','')), 
                'description': get_field(f'description_{lang}','')
            }
            out_file = out_dir / f"index.{lang}.md"
            log.debug(f"Rendering {out_file} with context: {context}")
            self.write(out_file, tmpl.render(**context))

# Dispatch only for events
if is_event:
    EventProcessor().render()
    log.info("Event processing complete.")
