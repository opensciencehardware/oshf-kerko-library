#!/usr/bin/env python3
"""Build cover images for Kerko items.

For each item in the search index, use the URL from a ``Cover:`` line in the
Zotero Extra field, or else the first page of the item's PDF attachment.
"""
import argparse
import sys
from io import BytesIO
from pathlib import Path

try:
    import requests
    from pdf2image import convert_from_path
    from PIL import Image
    from whoosh import index
except ImportError as exc:
    print(f"[covers] missing dependency: {exc}", file=sys.stderr)
    sys.exit(0)

ATTACHMENTS_DIR = Path("/kerkoapp/instance/kerko/attachments")
SEARCH_INDEX_DIR = Path("/kerkoapp/instance/kerko/index/whoosh")
COVERS_OUTPUT_DIR = Path("/kerkoapp/kerkoapp/static/covers")
COVER_MAX_WIDTH = 300

http_session = requests.Session()
http_session.headers.update({
    "User-Agent": "oshf-kerko-library-covers/1.0",
    "Accept": "image/*,*/*;q=0.8",
})


def print_cover_log(message):
    print(f"[covers] {message}", flush=True)


def download_cover_image(image_url):
    try:
        try:
            response = http_session.get(image_url, timeout=8)
        except requests.exceptions.SSLError:
            response = http_session.get(image_url, timeout=8, verify=False)
        response.raise_for_status()
    except requests.RequestException:
        return None

    content_type = (response.headers.get("Content-Type") or "").lower()
    path = image_url.lower().split("?")[0]
    if "svg" in content_type or path.endswith(".svg") or len(response.content) < 32:
        return None

    try:
        image = Image.open(BytesIO(response.content))
        image.load()
    except Exception:
        return None

    if min(image.size) < 8:
        return None
    return image.convert("RGB")


def find_pdf_attachment_path(item_fields):
    fallback_path = None
    for attachment in item_fields.get("attachments") or []:
        if not isinstance(attachment, dict) or not attachment.get("id"):
            continue
        attachment_path = ATTACHMENTS_DIR / attachment["id"]
        if not attachment_path.is_file():
            continue
        content_type = (attachment.get("data") or {}).get("contentType", "")
        if content_type == "application/pdf":
            return attachment_path
        if not content_type and fallback_path is None:
            fallback_path = attachment_path
    return fallback_path


def parse_zotero_extra_cover_url(item_fields):
    extra = (
        item_fields.get("extra")
        or (item_fields.get("data") or {}).get("extra")
        or ""
    )
    for line in str(extra).splitlines():
        key, separator, value = line.partition(":")
        if separator and key.strip().lower() == "cover":
            cover_url = value.strip()
            if cover_url.startswith("http"):
                return cover_url
    return ""


def write_cover_jpeg(item_id, image):
    image = image.convert("RGB")
    image.thumbnail((COVER_MAX_WIDTH, COVER_MAX_WIDTH * 2), Image.LANCZOS)
    image.save(str(COVERS_OUTPUT_DIR / f"{item_id}.jpg"), "JPEG", quality=85)


def main():
    parser = argparse.ArgumentParser(description="Build item cover images")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rebuild every cover, even if the JPEG already exists",
    )
    args = parser.parse_args()

    COVERS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if not SEARCH_INDEX_DIR.is_dir():
        print_cover_log("search index not found, skipping")
        return 0

    print_cover_log(f"start force={args.force}")

    covers_written = 0
    covers_skipped = 0
    cover_errors = 0
    with index.open_dir(str(SEARCH_INDEX_DIR)).searcher() as searcher:
        for item_fields in searcher.all_stored_fields():
            item_id = item_fields.get("id")
            if not item_id:
                continue
            cover_path = COVERS_OUTPUT_DIR / f"{item_id}.jpg"
            if cover_path.exists() and not args.force:
                covers_skipped += 1
                continue

            cover_url = parse_zotero_extra_cover_url(item_fields)
            if cover_url:
                try:
                    cover_image = download_cover_image(cover_url)
                    if cover_image:
                        write_cover_jpeg(item_id, cover_image)
                        covers_written += 1
                        print_cover_log(f"meta ok zotero_item={item_id} url={cover_url}")
                        continue
                    print_cover_log(
                        f"meta miss zotero_item={item_id} url={cover_url} falling_back=pdf"
                    )
                except Exception as exc:
                    cover_errors += 1
                    print_cover_log(
                        f"meta fail zotero_item={item_id} url={cover_url} error={exc}"
                    )

            pdf_path = find_pdf_attachment_path(item_fields)
            if not pdf_path:
                continue
            try:
                pdf_page = convert_from_path(
                    str(pdf_path),
                    first_page=1,
                    last_page=1,
                    size=(COVER_MAX_WIDTH, None),
                )[0]
                write_cover_jpeg(item_id, pdf_page)
                covers_written += 1
                print_cover_log(f"pdf ok zotero_item={item_id} file={pdf_path.name}")
            except Exception as exc:
                cover_errors += 1
                print_cover_log(
                    f"pdf fail zotero_item={item_id} file={pdf_path.name} error={exc}"
                )

    print_cover_log(
        f"done covers_written={covers_written} skipped={covers_skipped} errors={cover_errors}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
