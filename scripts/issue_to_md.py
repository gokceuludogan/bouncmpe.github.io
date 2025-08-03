import os
import re
import sys
import yaml
import requests
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

# ========== CONFIGURATION ==========
TEMPLATE_DIR = "scripts/templates"
UPLOADS_DIR = "static/uploads"
OUTPUT_DIR = "_news"
DEBUG = True

# ========== HELPERS ==========

def debug_print(msg, data=None):
    if DEBUG:
        print(f"[DEBUG] {msg}")
        if data is not None:
            print(f"{data}")

def parse_issue_body(issue_body):
    """
    Parses GitHub issue body into a dictionary of field names and values.
    Assumes each section is marked by a Markdown heading like '### Field Name'.
    """
    field_pattern = r"### (.+?)\n\n(.*?)(?=\n### |\Z)"
    matches = re.findall(field_pattern, issue_body, re.DOTALL)
    fields = {slugify_title(k.strip()): v.strip() for k, v in matches}
    debug_print("Parsed fields:", fields)
    return fields

def slugify_title(text):
    """Convert header names into consistent field keys."""
    return (
        text.lower()
        .strip()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("(", "")
        .replace(")", "")
    )

def get_field(keys, default=""):
    """Tries multiple keys and returns the first non-empty one."""
    if isinstance(keys, str):
        return fields.get(keys, default).strip()
    for key in keys:
        if key in fields and fields[key].strip():
            return fields[key].strip()
    return default

def download_image(img_tag):
    match = re.search(r'src="([^"]+)"', img_tag)
    if not match:
        return ""
    url = match.group(1)
    debug_print("Downloading image from", url)
    filename = url.split("/")[-1] + ".png"
    path = Path(UPLOADS_DIR) / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    response = requests.get(url)
    if response.status_code == 200:
        with open(path, "wb") as f:
            f.write(response.content)
        return f"/{UPLOADS_DIR}/{filename}"
    return ""

# ========== MAIN ==========

if __name__ == "__main__":
    # Load issue body
    issue_body = Path(".github/issue_body.md").read_text(encoding="utf-8")
    fields = parse_issue_body(issue_body)

    # Determine if it's an event
    event_keys = ['event_type', 'name', 'datetime', 'duration']
    is_event = any(f in fields and fields[f].strip() for f in event_keys)
    debug_print("Template selected:", "event.md.j2" if is_event else "news.md.j2")

    # Setup Jinja
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template_name = "event.md.j2" if is_event else "news.md.j2"
    template = env.get_template(template_name)

    langs = ['en', 'tr']
    for lang in langs:
        context = {
            "type": "event" if is_event else "news",
            "title": get_field([f"{'event_name' if is_event else 'news_title'}__{lang}"]),
            "description": get_field([
                f"description__{lang}" if is_event else f"short_description__{lang}"
            ]),
            "featured": False,
            "date": get_field("date"),
            "datetime": get_field("datetime"),
            "duration": get_field("duration"),
            "location": get_field([f"location__{lang}", "location"]),
            "name": get_field("name"),
            "content": get_field([
                f"full_description__{lang}" if is_event else f"full_content__{lang}"
            ]),
        }

        # Image
        image_field = get_field(["image__drag___drop_here", "image_markdown"])
        context["thumbnail"] = download_image(image_field) if image_field else ""

        debug_print(f"Final context for lang={lang}:", context)

        # Render & write output
        output = template.render(context)
        filename_slug = slugify_title(context["title"])[:64]
        output_path = Path(OUTPUT_DIR) / f"{filename_slug}.{lang}.md"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output, encoding="utf-8")
