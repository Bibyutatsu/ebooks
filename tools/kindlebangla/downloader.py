# /// script
# dependencies = [
#   "requests",
#   "beautifulsoup4",
#   "gdown",
# ]
# ///

import os
import re
import json
import time
import subprocess
import shutil
import requests
import gdown
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs

# Configuration
BASE_URL = "https://www.kindlebangla.com"
BOOKS_INDEX_URL = f"{BASE_URL}/books"
OUTPUT_DIR = "./downloads"
METADATA_FILE = "books_metadata.json"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

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

def sanitize_directory_name(name):
    """
    Cleans up author name to be a safe folder name.
    """
    # Keep alphanumeric characters and common separators
    sanitized = re.sub(r'[\\/*?:"<>|]', "", name)
    return sanitized.strip()

def get_total_pages():
    """
    Fetches the first page of books and parses the pagination to find the total pages.
    """
    print("Checking total pages...")
    try:
        response = requests.get(BOOKS_INDEX_URL, headers=HEADERS, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to fetch books index page: {e}")
        return 1

    soup = BeautifulSoup(response.text, 'html.parser')
    pagination_div = soup.find('div', class_='flex justify-center mt-10 space-x-2')
    if pagination_div:
        text = pagination_div.get_text()
        # Find pagination text like "১ / ৬৪" (1 / 64)
        match = re.search(r'([\u09E6-\u09EF]+)\s*/\s*([\u09E6-\u09EF]+)', text)
        if match:
            # Bengali digits mapping
            bn_digits = {'০':'0','১':'1','২':'2','৩':'3','৪':'4','৫':'5','৬':'6','৭':'7','৮':'8','৯':'9'}
            total_pages_bn = match.group(2)
            total_pages_en = "".join(bn_digits.get(char, char) for char in total_pages_bn)
            return int(total_pages_en)
    return 64  # fallback default if parsing fails

def scrape_book_details_links(total_pages, existing_links=None):
    """
    Crawls the /books listing pages to find all book details page URLs.
    Stops crawling if all links found on a page are already in existing_links.
    """
    if existing_links is None:
        existing_links = []
        
    print(f"Checking for updates against {len(existing_links)} cached book links...")
    new_links = []
    
    for page in range(1, total_pages + 1):
        url = f"{BOOKS_INDEX_URL}?page={page}"
        print(f"Scraping index page {page}/{total_pages}...")
        page_links_found = 0
        new_links_on_page = 0
        try:
            response = requests.get(url, headers=HEADERS, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract links targeting /book/ID
            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href']
                if "/book/" in href:
                    full_url = urljoin(BASE_URL, href)
                    page_links_found += 1
                    
                    if full_url not in existing_links and full_url not in new_links:
                        new_links.append(full_url)
                        new_links_on_page += 1
        except Exception as e:
            print(f"Failed to scrape listing page {page}: {e}")
            break
            
        # If we found links, but none of them were new, we reached the end of updates
        if page_links_found > 0 and new_links_on_page == 0:
            print("No new books found on this page. Cache is up-to-date!")
            break
            
    combined_links = new_links + existing_links
    print(f"Found {len(new_links)} new books. Total library size: {len(combined_links)}")
    return combined_links

def resolve_google_drive_link(download_url):
    """
    Requests the KindleBangla download URL and follows redirect to find the Google Drive URL.
    """
    try:
        # Use a session to persist cookies and follow redirect to Google Drive
        session = requests.Session()
        response = session.get(download_url, headers=HEADERS, timeout=20, allow_redirects=True)
        final_url = response.url
        if "drive.google.com" in final_url:
            return final_url
    except Exception as e:
        print(f"Failed to resolve download URL {download_url}: {e}")
    return None

def download_file_using_requests(file_id, destination_path_or_dir, book_title=None):
    """
    Downloads a single file from Google Drive using python requests.
    Handles large files requiring confirmation tokens.
    Returns the filename if successful.
    """
    download_url = "https://docs.google.com/uc?export=download"
    session = requests.Session()
    
    try:
        # Initial request
        response = session.get(download_url, params={'id': file_id}, headers=HEADERS, stream=True)
        
        # Check for large file download confirmation
        token = None
        for key, value in response.cookies.items():
            if key.startswith('download_warning'):
                token = value
                break
                
        if token:
            params = {'id': file_id, 'confirm': token}
            response = session.get(download_url, params=params, headers=HEADERS, stream=True)

        # Retrieve filename from Content-Disposition header
        content_disposition = response.headers.get('Content-Disposition', '')
        filename = None
        if 'filename=' in content_disposition:
            matches = re.findall(r'filename\*?="?([^";\n]+)"?', content_disposition)
            if matches:
                filename = matches[0]
                if filename.startswith("UTF-8''"):
                    from urllib.parse import unquote
                    filename = unquote(filename[7:])
                try:
                    filename = filename.encode('latin1').decode('utf-8')
                except Exception:
                    pass
        
        # Fallback if filename not found
        if not filename:
            content_type = response.headers.get('Content-Type', '')
            ext = ".pdf"
            if "epub" in content_type:
                ext = ".epub"
            elif "zip" in content_type:
                ext = ".zip"
            
            sanitized_title = "".join(c for c in book_title if c.isalnum() or c in (' ', '_', '-')).strip() if book_title else "downloaded_file"
            filename = f"{sanitized_title}{ext}"

        # Clean/sanitize filename
        filename = re.sub(r'[\\/*?:"<>|]', "", filename).strip()
        
        # Determine output path
        if os.path.isdir(destination_path_or_dir):
            destination_path = os.path.join(destination_path_or_dir, filename)
        else:
            destination_path = destination_path_or_dir
            filename = os.path.basename(destination_path)

        # Write to file
        print(f"Saving to {destination_path} ...")
        first_chunk = True
        with open(destination_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=32768):
                if chunk:
                    if first_chunk:
                        header_sample = chunk[:1024].lower()
                        if b'<html' in header_sample or b'<!doctype html' in header_sample:
                            print(f"Warning: Downloaded content is an HTML block page instead of the file. Google Drive might have blocked us.")
                            f.close()
                            if os.path.exists(destination_path):
                                os.remove(destination_path)
                            return None
                        first_chunk = False
                    f.write(chunk)
                    
        print(f"Successfully downloaded file: {filename}")
        return filename
    except Exception as e:
        print(f"Error downloading file ID {file_id}: {e}")
        return None

def download_file_from_google_drive(drive_url, destination_dir, book_title):
    """
    Downloads the file or folder from Google Drive using gdown to list folder items
    and standard requests to download the files.
    """
    try:
        # Check if the URL is a folder link
        if "/folders/" in drive_url or ("/drive/" in drive_url and "/file/d/" not in drive_url and "id=" not in drive_url):
            print(f"Detected Google Drive folder URL. Listing folder files using gdown...")
            # Get list of files without downloading
            files_to_download = gdown.download_folder(url=drive_url, output=destination_dir, quiet=True, skip_download=True, use_cookies=False)
            
            if files_to_download:
                print(f"Folder contains {len(files_to_download)} files. Downloading them...")
                success = False
                for item in files_to_download:
                    if item.id:
                        # Extract the target filename from the path
                        filename = os.path.basename(item.path)
                        # Fix double-encoding in filename if necessary
                        try:
                            filename = filename.encode('latin1').decode('utf-8')
                        except Exception:
                            pass
                        
                        target_path = os.path.join(destination_dir, filename)
                        
                        # Check if file already exists
                        if os.path.exists(target_path) and os.path.getsize(target_path) > 0:
                            print(f"File already exists, skipping: {filename}")
                            success = True
                            continue
                            
                        # Download using our requests helper
                        res = download_file_using_requests(item.id, target_path, book_title)
                        if res:
                            success = True
                            
                return "folder_downloaded" if success else None
            else:
                print(f"No files found or failed to parse folder contents: {drive_url}")
                return None
        else:
            # Extract file ID for single file
            file_id = None
            parsed_url = urlparse(drive_url)
            match = re.search(r'/file/d/([a-zA-Z0-9_-]+)', parsed_url.path)
            if match:
                file_id = match.group(1)
            else:
                query_params = parse_qs(parsed_url.query)
                if 'id' in query_params:
                    file_id = query_params['id'][0]

            if not file_id:
                print(f"Could not extract file ID from URL: {drive_url}")
                return None

            print(f"Downloading file using requests fallback...")
            return download_file_using_requests(file_id, destination_dir, book_title)
            
    except Exception as e:
        print(f"Error downloading {book_title} ({drive_url}): {e}")
        return None

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
                print(f"Extracted and removed archive: {item}")
        except Exception as e:
            print(f"Error extracting {rar_path}: {e}")

def fix_existing_filenames(root_dir):
    """
    Scans the downloaded directory structure and fixes any corrupted Latin-1 filenames to UTF-8.
    """
    print("Checking and fixing any corrupted filenames in downloads...")
    for root, dirs, files in os.walk(root_dir):
        for name in files:
            try:
                # Try to detect if the filename was incorrectly decoded as Latin-1
                fixed_name = name.encode('latin1').decode('utf-8')
                if fixed_name != name:
                    old_path = os.path.join(root, name)
                    new_path = os.path.join(root, fixed_name)
                    os.rename(old_path, new_path)
                    print(f"Fixed filename: '{name}' -> '{fixed_name}'")
            except Exception:
                pass

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    # Self-healing check for any previously downloaded files with incorrect/corrupted filenames
    fix_existing_filenames(OUTPUT_DIR)
    
    metadata = load_json(METADATA_FILE)
    
    # Step 1: Discover all book details URLs
    total_pages = get_total_pages()
    print(f"Total pages: {total_pages}")
    
    # Step 1: Discover new book details URLs dynamically
    book_details_links_file = "book_details_links.json"
    cached_links = load_json(book_details_links_file).get("links", [])
    
    # Scrape index, stopping when we hit already cached links
    book_details_links = scrape_book_details_links(total_pages, cached_links)
    save_json(book_details_links_file, {"links": book_details_links})

    # Step 2: Extract book titles, authors and resolve Google Drive URLs
    print("\nResolving Google Drive URLs and Author names from book details pages...")
    for idx, url in enumerate(book_details_links, start=1):
        if url in metadata and metadata[url].get("drive_url") and metadata[url].get("author"):
            # Already scraped and resolved
            continue
            
        print(f"[{idx}/{len(book_details_links)}] Parsing: {url}")
        try:
            response = requests.get(url, headers=HEADERS, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find Title
            title_h1 = soup.find('h1', class_='text-4xl font-bold mb-2 text-gray-900 dark:text-white')
            title = title_h1.get_text().strip() if title_h1 else f"Book_{idx}"
            
            # Find Author
            author_h1 = soup.find('h1', class_='text-2xl font-bold mb-2 text-slate-600 dark:text-indigo-500')
            author = author_h1.get_text().strip() if author_h1 else "Unknown Author"
            
            # Find download button/link targeting "/download/..."
            download_href = None
            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href']
                if "/download/" in href:
                    download_href = urljoin(BASE_URL, href)
                    break
            
            drive_url = None
            if download_href:
                print(f"Resolving redirect for {title} by {author}: {download_href}")
                drive_url = resolve_google_drive_link(download_href)
                
            metadata[url] = {
                "title": title,
                "author": author,
                "download_url": download_href,
                "drive_url": drive_url,
                "downloaded": False,
                "local_filename": None
            }
            save_json(METADATA_FILE, metadata)
            # Polite scraping delay
            time.sleep(1)
        except Exception as e:
            print(f"Error parsing details page {url}: {e}")

    # Step 3: Download all resolved books grouped by Author and Book folders
    print("\nStarting book downloads...")
    for url, info in metadata.items():
        drive_url = info.get("drive_url")
        if not drive_url:
            print(f"Skipping {info.get('title', 'Unknown')} (no Google Drive URL resolved)")
            continue
            
        author = info.get("author", "Unknown Author")
        sanitized_author = sanitize_directory_name(author)
        sanitized_title = sanitize_directory_name(info['title'])
        
        # New structure: ./downloads/<Author>/<Book Title>/
        book_dir = os.path.join(OUTPUT_DIR, sanitized_author, sanitized_title)
        
        # Check if we previously downloaded the file in the old location (downloads/<Author>/)
        # and automatically migrate it to the new folder structure!
        if info.get("downloaded") and info.get("local_filename"):
            old_path = os.path.join(OUTPUT_DIR, sanitized_author, info["local_filename"])
            new_path = os.path.join(book_dir, info["local_filename"])
            
            # If the old file exists, migrate it
            if os.path.exists(old_path):
                if not os.path.exists(book_dir):
                    os.makedirs(book_dir)
                os.rename(old_path, new_path)
                print(f"Migrated: '{old_path}' -> '{new_path}'")
                
            # If the download was a folder, all files in that folder might have been downloaded directly to the old author directory
            # We can find all files starting with or matching the book title and move them
            if info["local_filename"] == "folder_downloaded":
                # Check if there are loose files matching the book title in the author directory
                # and move them to the new book directory
                author_dir = os.path.join(OUTPUT_DIR, sanitized_author)
                if os.path.exists(author_dir):
                    for file_in_author in os.listdir(author_dir):
                        if file_in_author.startswith(sanitized_title) and os.path.isfile(os.path.join(author_dir, file_in_author)):
                            if not os.path.exists(book_dir):
                                os.makedirs(book_dir)
                            os.rename(os.path.join(author_dir, file_in_author), os.path.join(book_dir, file_in_author))
                            print(f"Migrated folder item: '{file_in_author}' to '{book_dir}'")
            
        if not os.path.exists(book_dir):
            os.makedirs(book_dir)
            
        if info.get("downloaded"):
            # Idempotency check: verify file existence or extracted book content in book_dir
            if os.path.exists(book_dir):
                files = os.listdir(book_dir)
                if len(files) > 0:
                    local_filename = info.get("local_filename")
                    if local_filename:
                        local_path = os.path.join(book_dir, local_filename)
                        if os.path.exists(local_path):
                            if local_filename.lower().endswith('.rar'):
                                extract_and_cleanup_rar(book_dir)
                            continue
                    book_exts = {'.epub', '.pdf', '.mobi', '.azw3', '.kfx', '.opf', '.txt', '.doc', '.docx', '.jpg', '.png'}
                    has_book_content = any(os.path.splitext(f)[1].lower() in book_exts for f in files)
                    if has_book_content or len(files) > 0:
                        extract_and_cleanup_rar(book_dir)
                        continue
                
        print(f"\nDownloading book: '{info['title']}' by '{author}'")
        filename = download_file_from_google_drive(drive_url, book_dir, info['title'])
        if filename:
            info["downloaded"] = True
            info["local_filename"] = filename
            save_json(METADATA_FILE, metadata)
            extract_and_cleanup_rar(book_dir)
            # Sleep 15s to respect Google Drive rate limits
            print("Sleeping for 15 seconds to respect rate limits...")
            time.sleep(15)
        else:
            # Sleep 60s to cool down after failure or rate limit block
            print("Download failed or rate-limited. Cooling down for 60 seconds...")
            time.sleep(60)

    print("\nAll tasks completed!")

if __name__ == "__main__":
    main()
