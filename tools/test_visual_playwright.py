"""
Comprehensive Playwright & Chrome Visual Inspector for Bibyutatsu BookStore.
Crosschecks headers, menus, themes, 3D cards, modals, subpages, console errors, and captures screenshots.
"""

import os
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

SCREENSHOT_DIR = Path("/Users/oindrila/.gemini/antigravity/brain/bebfc4f3-cb69-4bad-b13e-06beca9dd2ff/scratch/screenshots")
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
BASE_URL = "http://localhost:8080"


def run_checks():
    errors = []
    warnings = []
    report = []

    def on_console(msg):
        if msg.type == "error":
            # Ignore standard favicon or 404 image errors if any
            errors.append(f"[Console Error] {msg.text}")
        elif msg.type == "warning":
            warnings.append(f"[Console Warning] {msg.text}")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=CHROME_PATH,
            headless=True,
            args=["--disable-web-security", "--no-sandbox"]
        )
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=1.5
        )
        page = context.new_page()
        page.on("console", on_console)
        page.on("pageerror", lambda exc: errors.append(f"[Page Uncaught] {exc}"))

        print("\n--- 1. Testing Homepage (Storefront) ---")
        page.goto(f"{BASE_URL}/", wait_until="networkidle")
        time.sleep(1)

        # Check title and header elements
        title = page.title()
        report.append(f"Homepage Title: {title}")
        header = page.locator("#nav")
        assert header.is_visible(), "Header #nav is not visible"

        search_input = page.locator("#search-input")
        assert search_input.is_visible(), "Search input is not visible"

        stat_count = page.locator("#stat-count-text").text_content()
        report.append(f"Store Stat Pill: {stat_count}")

        # Check book cards render
        cards = page.locator(".book-card")
        card_count = cards.count()
        report.append(f"Rendered Book Cards count: {card_count}")
        assert card_count > 0, "No book cards rendered!"

        # Test hover & 3D tilt on first card
        first_card = cards.first
        first_card.hover()
        time.sleep(0.3)
        transform_val = first_card.evaluate("el => el.style.transform")
        report.append(f"First Card 3D Transform on Hover: {transform_val}")
        page.screenshot(path=str(SCREENSHOT_DIR / "1_homepage_dark.png"))

        # Test Theme Switcher: Switch to Batman
        print("Testing Theme Switcher (Batman)...")
        theme_btn = page.locator("#theme-btn")
        theme_btn.click()
        time.sleep(0.3)
        batman_opt = page.locator('.theme-opt[data-theme="batman"]')
        batman_opt.click()
        time.sleep(0.5)
        current_theme = page.evaluate("() => document.documentElement.getAttribute('data-theme')")
        report.append(f"Switched Theme: {current_theme}")
        page.screenshot(path=str(SCREENSHOT_DIR / "2_homepage_batman.png"))

        # Switch to Cyberpunk
        theme_btn.click()
        time.sleep(0.2)
        page.locator('.theme-opt[data-theme="cyberpunk"]').click()
        time.sleep(0.5)
        page.screenshot(path=str(SCREENSHOT_DIR / "3_homepage_cyberpunk.png"))

        # Switch back to Dark
        theme_btn.click()
        time.sleep(0.2)
        page.locator('.theme-opt[data-theme="dark"]').click()
        time.sleep(0.3)

        # Test Book Detail Modal
        print("Testing Book Detail Modal...")
        first_card.click()
        time.sleep(0.6)
        modal_overlay = page.locator("#book-modal-overlay")
        assert modal_overlay.is_visible(), "Modal overlay did not open!"
        modal_title = page.locator("#modal-body .modal-title").text_content()
        report.append(f"Modal Opened for Book: '{modal_title}'")
        
        # Check download formats in modal
        dl_cards = page.locator(".modal-dl-card")
        report.append(f"Modal Download Formats available: {dl_cards.count()}")
        
        # Test 3D Cover tilt in modal
        modal_cover = page.locator(".modal-cover-wrap")
        if modal_cover.is_visible():
            modal_cover.hover()
            time.sleep(0.2)

        page.screenshot(path=str(SCREENSHOT_DIR / "4_homepage_modal.png"))

        # Close modal
        page.locator("#modal-close-btn").click()
        time.sleep(0.3)

        # Test Search & Filter
        print("Testing Dual-Script Search...")
        search_input.fill("feluda")
        time.sleep(0.5)
        results_count = page.locator("#results-count").text_content()
        report.append(f"Search results for 'feluda': {results_count}")
        page.screenshot(path=str(SCREENSHOT_DIR / "5_homepage_search_feluda.png"))

        # Clear search
        page.locator("#clear-search").click()
        time.sleep(0.3)

        print("\n--- 2. Testing Series Page (series/feluda.html) ---")
        page.goto(f"{BASE_URL}/series/feluda.html", wait_until="networkidle")
        time.sleep(0.8)
        series_title = page.locator("h1").text_content()
        report.append(f"Series Page Heading: {series_title}")

        # Check theme persistence
        series_theme = page.evaluate("() => document.documentElement.getAttribute('data-theme')")
        report.append(f"Series Page Active Theme: {series_theme}")

        # Check reading order cards & 3D tilt
        ro_cards = page.locator(".reading-order-card")
        report.append(f"Reading Order Cards in Feluda: {ro_cards.count()}")
        assert ro_cards.count() > 0, "No reading order cards in series page!"

        # Test mark as read button
        first_read_btn = page.locator(".read-check-btn").first
        first_read_btn.click()
        time.sleep(0.2)
        progress_text = page.locator("#series-progress-count").text_content()
        report.append(f"Series Progress Counter after toggle: '{progress_text}'")

        page.screenshot(path=str(SCREENSHOT_DIR / "6_series_feluda.png"))

        # Test theme toggle in subpage header
        page.locator(".theme-subpage-btn").click()
        time.sleep(0.4)
        page.screenshot(path=str(SCREENSHOT_DIR / "7_series_feluda_theme_cycled.png"))

        print("\n--- 3. Testing Series Hub Directory (series/index.html) ---")
        page.goto(f"{BASE_URL}/series/index.html", wait_until="networkidle")
        time.sleep(0.8)
        hub_cards = page.locator(".series-hub-card")
        report.append(f"Series Hub Universes in Bento Grid: {hub_cards.count()}")
        page.screenshot(path=str(SCREENSHOT_DIR / "8_series_index.png"))

        print("\n--- 4. Testing Standalone Book Page ---")
        page.goto(f"{BASE_URL}/book/abanindranath-tagore-alor-fuloki.html", wait_until="networkidle")
        time.sleep(0.8)
        b_title = page.locator(".book-title").text_content()
        report.append(f"Book Page Title: {b_title}")
        cover_wrap = page.locator(".cover-wrapper")
        assert cover_wrap.is_visible(), "Book cover wrapper not visible!"
        cover_wrap.hover()
        time.sleep(0.3)
        page.screenshot(path=str(SCREENSHOT_DIR / "9_book_page.png"))

        print("\n--- 5. Testing Author Directory (author/index.html) ---")
        page.goto(f"{BASE_URL}/author/index.html", wait_until="networkidle")
        time.sleep(0.8)
        author_input = page.locator("#author-search-input")
        assert author_input.is_visible(), "Author search input not visible!"
        author_input.fill("satyajit")
        time.sleep(0.4)
        visible_authors = page.locator(".author-item:visible").count()
        report.append(f"Filtered Authors for 'satyajit': {visible_authors}")
        page.screenshot(path=str(SCREENSHOT_DIR / "10_author_index_filtered.png"))

        # Test Letter Jump Pill
        author_input.fill("")
        letter_sa = page.locator('.letter-pill[data-letter="স"]')
        if letter_sa.count() > 0:
            letter_sa.click()
            time.sleep(0.4)
            count_sa = page.locator(".author-item:visible").count()
            report.append(f"Authors starting with 'স': {count_sa}")

        # Mobile Viewport Test (375x812)
        print("\n--- 6. Testing Mobile Viewport (iPhone X) ---")
        page.set_viewport_size({"width": 375, "height": 812})
        page.goto(f"{BASE_URL}/", wait_until="networkidle")
        time.sleep(0.8)

        # Check mobile filter drawer button
        drawer_btn = page.locator("#drawer-toggle-btn")
        assert drawer_btn.is_visible(), "Mobile filter drawer toggle button not visible on mobile!"
        drawer_btn.click()
        time.sleep(0.5)
        sidebar = page.locator("#store-sidebar")
        assert "drawer-open" in (sidebar.get_attribute("class") or ""), "Drawer did not open on mobile!"
        page.screenshot(path=str(SCREENSHOT_DIR / "11_mobile_drawer_open.png"))

        page.locator("#drawer-close-btn").click()
        time.sleep(0.3)
        page.screenshot(path=str(SCREENSHOT_DIR / "12_mobile_storefront.png"))

        # Test Back-to-Top button on scroll
        page.evaluate("() => window.scrollTo(0, 1000)")
        time.sleep(0.4)
        btt_btn = page.locator("#back-to-top-btn")
        assert btt_btn.is_visible(), "Back to top button not visible after scroll!"
        page.screenshot(path=str(SCREENSHOT_DIR / "13_mobile_scroll_btt.png"))
        btt_btn.click()
        time.sleep(0.5)

        # Test Subpage on Mobile Viewport
        page.goto(f"{BASE_URL}/series/feluda.html", wait_until="networkidle")
        time.sleep(0.8)
        page.screenshot(path=str(SCREENSHOT_DIR / "14_mobile_series_page.png"))

        browser.close()

    print("\n========================================")
    print("PLAYWRIGHT CHROME AUDIT REPORT")
    print("========================================")
    for r in report:
        print(f"✓ {r}")

    print("\nConsole Errors Encountered:", len(errors))
    for err in errors:
        print(f"  ❌ {err}")

    print("\nConsole Warnings Encountered:", len(warnings))
    for w in warnings:
        print(f"  ⚠️ {w}")

    print(f"\nAll screenshots saved to: {SCREENSHOT_DIR}")
    return len(errors) == 0


if __name__ == "__main__":
    success = run_checks()
    sys.exit(0 if success else 1)
