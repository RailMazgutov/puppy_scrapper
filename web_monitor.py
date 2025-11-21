#!/usr/bin/env python3
"""
Web Page Monitor Script
Monitors web pages for changes by comparing HTML content and taking screenshots.
"""

import os
import hashlib
import time
from pathlib import Path
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright


class WebPageMonitor:
    """Monitor web pages for changes."""

    def __init__(self, html_dir="html_snapshots", screenshot_dir="screenshots"):
        """Initialize the monitor with storage directories."""
        self.html_dir = Path(html_dir)
        self.screenshot_dir = Path(screenshot_dir)

        # Create directories if they don't exist
        self.html_dir.mkdir(exist_ok=True)
        self.screenshot_dir.mkdir(exist_ok=True)

    def _get_filename_from_url(self, url):
        """Convert URL to a safe filename."""
        # Use URL hash to create a unique but consistent filename
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        parsed = urlparse(url)
        # Create a readable filename: domain_path_hash
        domain = parsed.netloc.replace('.', '_')
        path = parsed.path.replace('/', '_').strip('_')
        if path:
            return f"{domain}_{path}_{url_hash}"
        return f"{domain}_{url_hash}"

    def _load_previous_html(self, filename):
        """Load previously saved HTML content."""
        html_file = self.html_dir / f"{filename}.html"
        if html_file.exists():
            with open(html_file, 'r', encoding='utf-8') as f:
                return f.read()
        return None

    def _save_html(self, filename, html_content):
        """Save HTML content to file."""
        html_file = self.html_dir / f"{filename}.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

    def _take_screenshot(self, page, filename):
        """Take a screenshot and save it."""
        screenshot_file = self.screenshot_dir / f"{filename}.png"
        page.screenshot(path=str(screenshot_file), full_page=True)
        print(f"  📸 Screenshot saved: {screenshot_file}")
        return screenshot_file

    def monitor_url(self, url, browser):
        """Monitor a single URL for changes."""
        print(f"\n🔍 Checking: {url}")

        filename = self._get_filename_from_url(url)
        previous_html = self._load_previous_html(filename)

        try:
            # Create a new page
            page = browser.new_page(viewport={'width': 1920, 'height': 1080})

            # Load the page
            page.goto(url, wait_until='domcontentloaded', timeout=30000)

            # Give it a moment to fully render
            time.sleep(2)

            # Get current HTML
            current_html = page.content()

            # Compare with previous version
            if previous_html is None:
                print("  ℹ️  First time checking this page")
                self._take_screenshot(page, filename)
                self._save_html(filename, current_html)
                print(f"  ✅ HTML snapshot saved")
            elif previous_html == current_html:
                print("  ✅ No changes detected")
            else:
                print("  ⚠️  CHANGES DETECTED!")
                self._take_screenshot(page, filename)
                self._save_html(filename, current_html)
                print(f"  💾 Updated HTML snapshot saved")

            page.close()

        except Exception as e:
            print(f"  ❌ Error monitoring {url}: {str(e)}")

    def monitor_urls(self, urls):
        """Monitor multiple URLs."""
        print(f"🚀 Starting web page monitoring for {len(urls)} URL(s)")

        # Get proxy settings from environment
        proxy_server = os.environ.get('HTTPS_PROXY') or os.environ.get('HTTP_PROXY')
        proxy_config = None
        if proxy_server:
            proxy_config = {"server": proxy_server}

        with sync_playwright() as p:
            # Launch browser
            browser = p.chromium.launch(
                headless=True,
                proxy=proxy_config,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled'
                ]
            )

            for url in urls:
                self.monitor_url(url, browser)

            browser.close()

        print("\n✅ Monitoring complete!")


def main():
    """Main entry point."""
    # List of URLs to monitor
    urls = [
        "https://www.reyncomslant.nl/nieuws/",
        # Add more URLs to monitor here
        # "https://example.com/page1",
        # "https://example.com/page2",
    ]

    # Create monitor and check URLs
    monitor = WebPageMonitor()
    monitor.monitor_urls(urls)


if __name__ == "__main__":
    main()
