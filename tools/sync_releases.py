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


def sync_releases(catalog_path: str, source_dir: str = None, dry_run: bool = False, format_filter: str = None, batch_limit: int = None):
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

    # Resolve downloads base_dir
    default_download_dir = Path.home() / "Downloads" / "Epubbooks"
    if source_dir:
        base_dir = Path(source_dir)
    elif default_download_dir.exists():
        base_dir = default_download_dir
    else:
        base_dir = catalog_file.parent.parent

    # Collect all upload tasks
    tasks = []

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
        if batch_limit and batch_idx > batch_limit:
            print(f"Reached batch limit of {batch_limit}. Stopping.")
            break

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
            asset_name = f"{item['book_id']}.{item['fmt']}"
            item["asset_name"] = asset_name
            if asset_name in existing_assets:
                url_map[(item["book_id"], item["fmt"])] = existing_assets[asset_name]
                skipped_count += 1
            else:
                to_upload.append(item)

        if to_upload:
            print(f"[{tag}] Uploading {len(to_upload)} new files...")
            scratch_dir = Path("/tmp/ebooks_release_upload")
            scratch_dir.mkdir(parents=True, exist_ok=True)
            
            # Prepare files in scratch_dir
            staged_files = []
            for item in to_upload:
                fpath = item["filepath"]
                aname = item["asset_name"]
                if dry_run:
                    mock_url = f"https://github.com/{REPO}/releases/download/{tag}/{aname}"
                    url_map[(item["book_id"], item["fmt"])] = mock_url
                    continue

                tmp_file = scratch_dir / aname
                try:
                    import shutil
                    shutil.copyfile(fpath, tmp_file)
                    staged_files.append((item, tmp_file))
                except Exception as e:
                    print(f"  Failed to stage {aname}: {e}")

            if not dry_run and staged_files:
                # Upload in chunks of 15 files per gh command for high throughput and reliability
                CHUNK_SIZE = 15
                for i in range(0, len(staged_files), CHUNK_SIZE):
                    chunk = staged_files[i:i + CHUNK_SIZE]
                    file_paths = [str(tf) for _, tf in chunk]
                    up_code, _, stderr = run_cmd([
                        "gh", "release", "upload", tag,
                        *file_paths,
                        "--repo", REPO,
                        "--clobber"
                    ])
                    if up_code == 0:
                        for itm, _ in chunk:
                            aname = itm["asset_name"]
                            cdn_url = f"https://github.com/{REPO}/releases/download/{tag}/{aname}"
                            url_map[(itm["book_id"], itm["fmt"])] = cdn_url
                            updated_count += 1
                    else:
                        print(f"  Chunk upload failed on {tag}: {stderr}. Falling back to single uploads...")
                        for itm, tf in chunk:
                            u_code, _, s_err = run_cmd([
                                "gh", "release", "upload", tag, str(tf),
                                "--repo", REPO,
                                "--clobber"
                            ])
                            if u_code == 0:
                                aname = itm["asset_name"]
                                cdn_url = f"https://github.com/{REPO}/releases/download/{tag}/{aname}"
                                url_map[(itm["book_id"], itm["fmt"])] = cdn_url
                                updated_count += 1
                            else:
                                print(f"    Failed single upload {itm['asset_name']}: {s_err}")

                # Clean up scratch files
                for _, tf in staged_files:
                    if tf.exists():
                        tf.unlink()

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
    parser.add_argument("--catalog", default="./catalog.json", help="Path to catalog.json")
    parser.add_argument("--source", default=None, help="Source directory containing downloads/ (defaults to ~/Downloads/Epubbooks)")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without uploading")
    parser.add_argument("--format", default=None, help="Filter by format (e.g. epub)")
    parser.add_argument("--batch-limit", type=int, default=None, help="Limit number of batches to process")
    args = parser.parse_args()

    sync_releases(args.catalog, source_dir=args.source, dry_run=args.dry_run, format_filter=args.format, batch_limit=args.batch_limit)
