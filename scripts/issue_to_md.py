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
    missing = [n for n in ["GITHUB_REPOSITORY","GITHUB_TOKEN","ISSUE_NUMBER"] if not os.getenv(n)]
    raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")

# ─── GITHUB INIT ────────────────────────────────────────────────────────────────
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
        value = "\n".join(lines[1:]).strip()
        # Normalize date field label if form used 'YYYY-MM-DD' hint
        if "date" in key and "yyyy" in label.lower():
            key = "date"
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

# ─── DETECT NEWS VS EVENT ───────────────────────────────────────────────────────
# We use the 'event_type' field: if present => event, otherwise news
event_type = get_field("event_type", "").strip()
is_event   = bool(event_type)

# ─── COMMON FIELDS & NORMALIZATION ──────────────────────────────────────────────
title_en = get_field(["event_title_en","title_en"], issue.title)
title_tr = get_field(["event_title_tr","title_tr"], "")
date_val = get_field("date", "").strip() or issue.created_at.date().isoformat()
raw_time = get_field("time", "").strip()
time_val = raw_time + ":00" if re.match(r"^\d{2}:\d{2}$", raw_time) else raw_time
if DEBUG:
    print(f"[DEBUG] date_val={date_val!r}, time_val={time_val!r}, is_event={is_event}")

# ─── IMAGE HANDLING ─────────────────────────────────────────────────────────────
def download_image(md: str) -> str:
    m = re.search(r"!\[[^\]]*\]\((https?://[^\)]+)\)", md) \
        or re.search(r'src="(https?://[^"]+)"', md)
    if not m:
        return ""
    url = m.group(1)
    if DEBUG:
        print(f"[DEBUG] Downloading image: {url}")
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    ext = mimetypes.guess_extension(resp.headers.get("Content-Type","").split(";")[0]) \
          or Path(url).suffix or ".png"
    fname = f"{ISSUE_NUMBER}_{uuid4().hex[:8]}{ext}"
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    path = UPLOADS_DIR / fname
    path.write_bytes(resp.content)
    local = f"uploads/{fname}"
    if DEBUG:
        print(f"[DEBUG] Saved image to {path} → '{local}'")
    return local

# ─── SLUG & OUTPUT DIRECTORY ────────────────────────────────────────────────────
def make_slug(text: str) -> str:
    slug = unicodedata.normalize("NFKD", text).encode("ascii","ignore").decode().lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[-\s]+", "-", slug).strip("-")
    return f"{slug}-{ISSUE_NUMBER}"

slug   = make_slug(title_en)
subdir = "events" if is_event else "news"
out_dir = CONTENT_DIR / subdir / f"{date_val}-{slug}"
out_dir.mkdir(parents=True, exist_ok=True)
if DEBUG:
    print(f"[DEBUG] out_dir={out_dir}")

# ─── PROCESSORS ─────────────────────────────────────────────────────────────────
class BaseProcessor:
    def write(self, path: Path, text: str):
        path.write_text(text, encoding="utf-8")
        if DEBUG:
            print(f"[DEBUG] Wrote: {path}")

class NewsProcessor(BaseProcessor):
    def render(self):
        image_md = download_image(get_field(["image_markdown","image_drag_drop_here"], ""))
        for lang in ("en","tr"):
            desc = get_field(f"short_description_{lang}", "").strip()
            front = [
                "---",
                "type: news",
                f"title: {title_en if lang=='en' else title_tr}"
            ]
            # description
            if "\n" in desc:
                front.append("description: |")
                front += [f"  {line}" for line in desc.splitlines()]
            else:
                front.append(f"description: {desc}")
            front += [
                "featured: false",
                f"date: {date_val}",
                f"thumbnail: {image_md}",
                "---",
                ""
            ]
            body = get_field(f"full_content_{lang}", "")
            out_file = out_dir / f"index.{lang}.md"
            self.write(out_file, "\n".join(front + [body]))

class EventProcessor(BaseProcessor):
    def render(self):
        env  = Environment(loader=FileSystemLoader("templates"), autoescape=False)
        tmpl = env.get_template("_base.md.j2")
        # Build context from issue fields
        ctx = {
            "type":     event_type,
            "title":    title_en,
            "name":     get_field(["speaker","presenter","name"], ""),
            "datetime": f"{date_val}T{time_val}" if time_val else date_val,
            "duration": get_field("duration",""),
            "location": get_field(["location_en","location"], "")
        }
        rendered = tmpl.render(**ctx)
        # Events only need a single index.md
        out_file = out_dir / "index.md"
        self.write(out_file, rendered)

# ─── DISPATCH ───────────────────────────────────────────────────────────────────
processor = EventProcessor() if is_event else NewsProcessor()
processor.render()
print("[DEBUG] Done.")
