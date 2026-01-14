#!/usr/bin/env python3
"""Open https://www.google.com in a headless browser and save a screenshot.

Requires: `playwright` and browser binaries (`playwright install`).
"""
from pathlib import Path

from playwright.sync_api import sync_playwright


def main() -> int:
    out_dir = Path("artifacts") / "browser-visits"
    out_dir.mkdir(parents=True, exist_ok=True)
    screenshot = out_dir / "google.png"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://www.google.com", timeout=15000)
        page.screenshot(path=str(screenshot), full_page=True)
        browser.close()

    print(f"Saved screenshot: {screenshot}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
