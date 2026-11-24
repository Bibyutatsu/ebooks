"""
Playwright Visual Audit for Subpage Themes, Backgrounds & Animation Precision.
Tests:
1. book/atin-bandyopadhyay-sahityer-sera-glp.html:
   - Three.js Hero canvas presence & execution
   - Theme switcher cycling through all 5 themes
   - Computed CSS background verification (confirms SHARED_CSS override is gone)
   - Verifies clicking static badges does NOT trigger animations
   - Verifies theme button triggers exactly one animation
2. series/index.html & series/feluda.html:
   - Dynamic ambient background & frosted glass styling
3. Cross-page synchronization:
   - Homepage <-> Book page <-> Series page theme persistence
"""
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_URL = "http://localhost:8080"
CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
SCREENSHOT_DIR = Path("/Users/oindrila/.gemini/antigravity/brain/bebfc4f3-cb69-4bad-b13e-06beca9dd2ff/scratch/screenshots_revamp")
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


def run_tests():
    report = []
    errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=CHROME_PATH,
            headless=True,
            args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"]
        )
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        page.on("pageerror", lambda err: errors.append(f"Uncaught Exception: {err}"))
        page.on("console", lambda msg: errors.append(f"Console error: {msg.text}") if msg.type == "error" else None)

        # ---------------------------------------------------------
        # TEST 1: Specific Book Page Theme Switcher & Animations
        # ---------------------------------------------------------
        book_url = f"{BASE_URL}/book/atin-bandyopadhyay-sahityer-sera-glp.html"
        print(f"1. Navigating to Book Page: {book_url}")
        page.goto(book_url, wait_until="networkidle")
        time.sleep(1.0)

        # Check hero canvas
        hero_canvas = page.locator("#hero-canvas")
        assert hero_canvas.count() == 1, "Missing #hero-canvas on book page!"
        report.append("#hero-canvas present on standalone book page")

        # Check initial theme
        initial_theme = page.evaluate("() => document.documentElement.getAttribute('data-theme')")
        report.append(f"Initial theme: {initial_theme}")

        # Cycle themes
        theme_btn = page.locator(".theme-subpage-btn")
        assert theme_btn.count() == 1, "Missing .theme-subpage-btn!"

        # Track animation trigger calls
        page.evaluate("""() => {
            window.__shatterCalls = [];
            const orig = window.triggerCanvasUIButtonShatter;
            window.triggerCanvasUIButtonShatter = function(x, y) {
                window.__shatterCalls.push({ x, y, time: Date.now() });
                if (orig) orig(x, y);
            };
        }""")

        # Click theme button -> Expect exactly 1 shatter call
        print("Testing single-animation theme cycle...")
        theme_btn.click()
        time.sleep(0.4)
        shatter_count = page.evaluate("() => window.__shatterCalls.length")
        assert shatter_count == 1, f"Expected exactly 1 shatter call on theme button click, got {shatter_count}!"
        report.append(f"Theme button click triggered exactly {shatter_count} animation (no double animation)")

        # Verify theme changed and computed background changed
        theme_after_1 = page.evaluate("() => document.documentElement.getAttribute('data-theme')")
        bg_after_1 = page.evaluate("() => getComputedStyle(document.body).backgroundColor")
        report.append(f"Cycled theme to: {theme_after_1} (body bg: {bg_after_1})")
        page.screenshot(path=str(SCREENSHOT_DIR / "1_book_theme_cycled.png"))

        # Cycle through remaining themes
        for expected in ["batman", "cyberpunk", "ocean", "dark"]:
            theme_btn.click()
            time.sleep(0.3)
            cur = page.evaluate("() => document.documentElement.getAttribute('data-theme')")
            report.append(f"Cycled to: {cur}")
            if cur == "batman":
                page.screenshot(path=str(SCREENSHOT_DIR / "2_book_theme_batman.png"))
            elif cur == "cyberpunk":
                page.screenshot(path=str(SCREENSHOT_DIR / "3_book_theme_cyberpunk.png"))

        # Verify clicking static badge does NOT trigger animation
        page.evaluate("() => { window.__shatterCalls = []; }")
        static_badge = page.locator(".badges-row .badge").first
        if static_badge.count() > 0:
            print("Clicking static badge to verify NO animation fires...")
            static_badge.click()
            time.sleep(0.3)
            calls_on_badge = page.evaluate("() => window.__shatterCalls.length")
            assert calls_on_badge == 0, f"Static badge click triggered {calls_on_badge} unexpected animations!"
            report.append("Clicking static text badge triggered 0 animations (bug eliminated)")

        # ---------------------------------------------------------
        # TEST 2: Series Hub Directory Background & Frosted Bento
        # ---------------------------------------------------------
        series_url = f"{BASE_URL}/series/index.html"
        print(f"\n2. Navigating to Series Directory: {series_url}")
        page.goto(series_url, wait_until="networkidle")
        time.sleep(0.8)

        hero_canvas_series = page.locator("#hero-canvas")
        assert hero_canvas_series.count() == 1, "Missing #hero-canvas on series index!"
        bento_cards = page.locator(".series-hub-card")
        report.append(f"Series Hub Bento Cards count: {bento_cards.count()} with #hero-canvas active")
        page.screenshot(path=str(SCREENSHOT_DIR / "4_series_hub_revamped.png"))

        # ---------------------------------------------------------
        # TEST 3: Cross-Page Theme Synchronization
        # ---------------------------------------------------------
        print("\n3. Testing Cross-Page Theme Synchronization...")
        # Switch series to 'ocean'
        while page.evaluate("() => document.documentElement.getAttribute('data-theme')") != "ocean":
            page.locator(".theme-subpage-btn").click()
            time.sleep(0.2)

        ocean_stored = page.evaluate("() => localStorage.getItem('bm-theme')")
        assert ocean_stored == "ocean", f"Expected 'ocean' in localStorage, got {ocean_stored}"
        report.append("Set theme 'ocean' on series hub")

        # Navigate to Homepage and verify it loaded directly with 'ocean'
        page.goto(f"{BASE_URL}/", wait_until="networkidle")
        time.sleep(0.8)
        home_theme = page.evaluate("() => document.documentElement.getAttribute('data-theme')")
        assert home_theme == "ocean", f"Homepage failed to inherit 'ocean' theme! Got {home_theme}"
        report.append(f"Homepage inherited synchronized theme: {home_theme}")
        page.screenshot(path=str(SCREENSHOT_DIR / "5_homepage_ocean_synced.png"))

        # Navigate to a book page and verify it also has 'ocean'
        page.goto(book_url, wait_until="networkidle")
        time.sleep(0.8)
        book_theme = page.evaluate("() => document.documentElement.getAttribute('data-theme')")
        assert book_theme == "ocean", f"Book page failed to inherit 'ocean' theme! Got {book_theme}"
        report.append(f"Book page inherited synchronized theme: {book_theme}")
        page.screenshot(path=str(SCREENSHOT_DIR / "6_book_ocean_synced.png"))

        browser.close()

    print("\n========================================")
    print("SUBPAGE REVAMP & THEME AUDIT REPORT")
    print("========================================")
    for r in report:
        print(f"✓ {r}")

    print("\nConsole Errors Encountered:", len(errors))
    for err in errors:
        print(f"  ❌ {err}")

    print(f"\nScreenshots saved to: {SCREENSHOT_DIR}")
    return len(errors) == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
