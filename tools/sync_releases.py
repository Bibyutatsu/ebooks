"""
Incremental GitHub Releases Synchronization Tool.
Uploads book files (EPUB, KFX, MOBI, PDF) to GitHub Releases on Bibyutatsu/ebooks
and updates catalog.json with high-speed direct CDN download URLs.

Features:
- Idempotent and resumable: never re-uploads existing assets.
- Batched releases: groups assets into release tags (e.g., v1.0-batch-01) to stay well within limits.
- Updates catalog.json with permanent GitHub CDN download URLs.
"""

import os
import sys
import json
import subprocess
from pathlib import Path

REPO = "Bibyutatsu/ebooks"
BATCH_SIZE = 75  # Files per GitHub Release tag for optimal upload reliability


def run_cmd(cmd: list[str]) -> tuple[int, str, str]:
    """Runs a shell command and returns (returncode, stdout, stderr)."""
    res = subprocess.run(cmd, capture_output=True, text=True)
    return res.returncode, res.stdout.strip(), res.stderr.strip()


def get_existing_release_assets(tag: str) -> dict[str, str]:
    """
    Fetches list of assets already uploaded to a release tag.
    Returns a dict mapping filename -> direct download URL.
    """
    code, stdout, _ = run_cmd(["gh", "release", "view", tag, "--repo", REPO, "--json", "assets"])
    if code != 0:
        return {}
    try:
        data = json.loads(stdout)
        assets = {}
        for a in data.get("assets", []):
            name = a.get("name")
            url = a.get("url")
            if name and url:
                assets[name] = url
        return assets
    except Exception:
        return {}


def ensure_release_tag(tag: str, title: str):
    """Ensures a release exists; creates it if not."""
    code, _, _ = run_cmd(["gh", "release", "view", tag, "--repo", REPO])
    if code != 0:
        print(f"Creating release {tag} on {REPO}...")
        create_code, _, stderr = run_cmd([
            "gh", "release", "create", tag,
            "--repo", REPO,
            "--title", title,
            "--notes", f"Ebook distribution assets for {tag}."
        ])
        if create_code != 0:
            print(f"Failed to create release {tag}: {stderr}")
            return False
    return True


def sync_releases(catalog_path: str, dry_run: bool = False, format_filter: str = None):
    """
    Iterates through all books and formats in catalog.json, uploads missing assets,
    and writes CDN download URLs back to catalog.json.
    """
    catalog_file = Path(catalog_path)
    if not catalog_file.exists():
        print(f"Catalog file not found: {catalog_path}")
        return

    with open(catalog_file, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    # Collect all upload tasks
    tasks = []
    base_dir = catalog_file.parent.parent  # /Users/oindrila/Downloads/Epubbooks

    for book in catalog["books"]:
        for fmt_key, fmt_info in book["formats"].items():
            if format_filter and fmt_key != format_filter:
                continue

            rel_path = fmt_info.get("relative_path")
            if not rel_path:
                continue
            full_path = base_dir / rel_path
            if full_path.exists():
                tasks.append({
                    "book_id": book["id"],
                    "fmt": fmt_key,
                    "filename": full_path.name,
                    "filepath": str(full_path),
                    "size": fmt_info.get("size_bytes", 0)
                })

    print(f"Total files indexed for release sync: {len(tasks)}")
    if dry_run:
        print("[DRY-RUN] Will not upload files or modify releases.")

    # Group into batches
    batches = [tasks[i:i + BATCH_SIZE] for i in range(0, len(tasks), BATCH_SIZE)]
    print(f"Divided into {len(batches)} release batches of max {BATCH_SIZE} files.")

    updated_count = 0
    skipped_count = 0

    # Build mapping of book_id + fmt -> download_url
    url_map = {}

    for batch_idx, batch in enumerate(batches, 1):
        tag = f"v1.0-batch-{batch_idx:02d}"
        title = f"Library Assets Batch {batch_idx:02d}"

        if not dry_run:
            if not ensure_release_tag(tag, title):
                continue
            existing_assets = get_existing_release_assets(tag)
        else:
            existing_assets = {}

        to_upload = []
        for item in batch:
            fname = item["filename"]
            if fname in existing_assets:
                url_map[(item["book_id"], item["fmt"])] = existing_assets[fname]
                skipped_count += 1
            else:
                to_upload.append(item)

        if to_upload:
            print(f"[{tag}] Uploading {len(to_upload)} new files...")
            for item in to_upload:
                fpath = item["filepath"]
                fname = item["filename"]
                if dry_run:
                    mock_url = f"https://github.com/{REPO}/releases/download/{tag}/{fname}"
                    url_map[(item["book_id"], item["fmt"])] = mock_url
                    continue

                up_code, _, stderr = run_cmd([
                    "gh", "release", "upload", tag, fpath,
                    "--repo", REPO,
                    "--clobber"
                ])
                if up_code == 0:
                    cdn_url = f"https://github.com/{REPO}/releases/download/{tag}/{fname}"
                    url_map[(item["book_id"], item["fmt"])] = cdn_url
                    updated_count += 1
                else:
                    print(f"  Failed to upload {fname}: {stderr}")

    # Write URLs back to catalog.json
    for book in catalog["books"]:
        for fmt_key, fmt_info in book["formats"].items():
            key = (book["id"], fmt_key)
            if key in url_map:
                fmt_info["download_url"] = url_map[key]

    with open(catalog_file, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)

    print(f"\nSync complete! Updated: {updated_count}, Already synced: {skipped_count}.")
    print(f"Catalog updated with direct CDN links at {catalog_file.resolve()}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Sync ebooks to GitHub Releases")
    parser.add_argument("--catalog", default="./ebooks/catalog.json", help="Path to catalog.json")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without uploading")
    parser.add_argument("--format", default=None, help="Filter by format (e.g. epub)")
    args = parser.parse_args()

    sync_releases(args.catalog, dry_run=args.dry_run, format_filter=args.format)
