import os
import re
import json
import shutil
import zipfile
import subprocess

METADATA_FILE = "books_metadata.json"

def load_json(filepath):
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_json(filepath, data):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def extract_and_cleanup_rar(book_dir):
    """
    Extracts any .rar files in book_dir using bsdtar, flattens single nested directories,
    and removes the .rar files.
    """
    if not os.path.exists(book_dir):
        return
    rar_files = [f for f in os.listdir(book_dir) if f.lower().endswith('.rar')]
    for item in rar_files:
        rar_path = os.path.join(book_dir, item)
        try:
            res = subprocess.run(["bsdtar", "-xf", rar_path, "-C", book_dir], capture_output=True, text=True)
            if res.returncode == 0:
                # Flatten nested directory if the RAR created wrapper folders
                subdirs = [os.path.join(book_dir, d) for d in os.listdir(book_dir) if os.path.isdir(os.path.join(book_dir, d))]
                for sdir in subdirs:
                    for sitem in os.listdir(sdir):
                        src = os.path.join(sdir, sitem)
                        dst = os.path.join(book_dir, sitem)
                        if not os.path.exists(dst):
                            shutil.move(src, dst)
                    try:
                        shutil.rmtree(sdir)
                    except Exception:
                        pass
                if os.path.exists(rar_path):
                    os.remove(rar_path)
                print(f"Extracted and removed redundant archive: {item}")
        except Exception as e:
            print(f"Error extracting {rar_path}: {e}")

def verify_file(filepath):
    filename = os.path.basename(filepath)
    ext = os.path.splitext(filename)[1].lower()
    
    # 1. Check size
    size = os.path.getsize(filepath)
    if size == 0:
        return False, "File is completely empty (0 bytes)."
    
    # 2. Check if file is HTML page posing as another file
    try:
        with open(filepath, 'rb') as f:
            header = f.read(1024)
            if b'<html' in header.lower() or b'<!doctype html' in header.lower():
                return False, "File is an HTML page (likely a Google Drive error/captcha/block page)."
    except Exception as e:
        return False, f"Could not read file header: {e}"
        
    # 3. Format-specific checks
    if ext == '.epub':
        # Epubs must be valid zip files
        if not zipfile.is_zipfile(filepath):
            return False, "Invalid EPUB file (not a valid ZIP archive)."
        try:
            with zipfile.ZipFile(filepath) as z:
                # Check for bad CRC or corrupt structure
                bad_file = z.testzip()
                if bad_file:
                    return False, f"Corrupted ZIP structure (bad file inside: {bad_file})."
        except Exception as e:
            return False, f"Failed to parse ZIP structure: {e}"
            
    elif ext == '.pdf':
        try:
            with open(filepath, 'rb') as f:
                header = f.read(4)
                if header != b'%PDF':
                    return False, f"Invalid PDF file header (starts with {header!r} instead of %PDF)."
        except Exception as e:
            return False, f"Failed to check PDF header: {e}"

    elif ext == '.rar':
        try:
            with open(filepath, 'rb') as f:
                header = f.read(7)
                if not (header.startswith(b'Rar!') or header.startswith(b'RE~#\x07')):
                    return False, f"Invalid RAR file header (starts with {header!r})."
        except Exception as e:
            return False, f"Failed to check RAR header: {e}"
            
    return True, "Valid"

def main():
    downloads_dir = "./downloads"
    if not os.path.exists(downloads_dir):
        print("No downloads directory found.")
        return
        
    metadata = load_json(METADATA_FILE)
    metadata_updated = False

    total_checked = 0
    corrupted_count = 0
    deleted_corrupted_count = 0
    valid_count = 0
    
    print("Starting verification & cleanup of all downloaded files...\n")
    
    # First pass: extract any remaining redundant .rar files
    for root, dirs, files in os.walk(downloads_dir):
        if any(f.lower().endswith('.rar') for f in files):
            extract_and_cleanup_rar(root)
            
    valid_exts = {'.epub', '.pdf', '.jpg', '.png', '.zip', '.rar', '.kfx', '.mobi', '.azw3', '.opf', '.cbz', '.cbr'}
    for root, dirs, files in os.walk(downloads_dir):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext not in valid_exts:
                continue
                
            filepath = os.path.join(root, file)
            total_checked += 1
            is_valid, reason = verify_file(filepath)
            
            if not is_valid:
                corrupted_count += 1
                relative_path = os.path.relpath(filepath, downloads_dir)
                print(f"[CORRUPTED & REMOVED] {relative_path} - {reason}")
                
                # Delete corrupted file
                try:
                    os.remove(filepath)
                    deleted_corrupted_count += 1
                except Exception as e:
                    print(f"Failed to delete corrupted file {filepath}: {e}")

                # Sync metadata so downloader retries if needed
                for url, info in metadata.items():
                    if info.get("local_filename") == file:
                        info["downloaded"] = False
                        metadata_updated = True
            else:
                valid_count += 1

    if metadata_updated:
        save_json(METADATA_FILE, metadata)
        print("Updated books_metadata.json to mark corrupted entries for re-download.")
                
    print(f"\nVerification & cleanup completed.")
    print(f"Total checked: {total_checked}")
    print(f"Valid files: {valid_count}")
    print(f"Corrupted files found & deleted: {deleted_corrupted_count}/{corrupted_count}")

if __name__ == "__main__":
    main()
