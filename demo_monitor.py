#!/usr/bin/env python3
"""
Demo script to test HTML comparison functionality without browser automation.
This demonstrates the core logic of web_monitor.py using simple HTTP requests.
"""

import hashlib
import requests
from pathlib import Path
from urllib.parse import urlparse


class SimpleHTMLMonitor:
    """Simple HTML monitor using requests (no browser)."""

    def __init__(self, html_dir="html_snapshots"):
        self.html_dir = Path(html_dir)
        self.html_dir.mkdir(exist_ok=True)

    def _get_filename_from_url(self, url):
        """Convert URL to a safe filename."""
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        parsed = urlparse(url)
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

    def monitor_url(self, url):
        """Monitor a single URL for changes."""
        print(f"\n🔍 Checking: {url}")

        filename = self._get_filename_from_url(url)
        previous_html = self._load_previous_html(filename)

        try:
            # Fetch HTML using requests
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            current_html = response.text

            # Compare with previous version
            if previous_html is None:
                print("  ℹ️  First time checking this page")
                self._save_html(filename, current_html)
                print(f"  ✅ HTML snapshot saved ({len(current_html)} bytes)")
                print(f"  📝 Note: In full version, a screenshot would be taken here")
            elif previous_html == current_html:
                print("  ✅ No changes detected")
            else:
                print("  ⚠️  CHANGES DETECTED!")
                self._save_html(filename, current_html)
                print(f"  💾 Updated HTML snapshot saved ({len(current_html)} bytes)")
                print(f"  📸 Note: In full version, a screenshot would be taken here")

        except Exception as e:
            print(f"  ❌ Error monitoring {url}: {str(e)}")


def main():
    """Main entry point."""
    urls = [
        "https://www.reyncomslant.nl/nieuws/",
    ]

    monitor = SimpleHTMLMonitor()
    for url in urls:
        monitor.monitor_url(url)

    print("\n✅ Demo complete!")
    print("\nNote: This demo uses simple HTTP requests for testing.")
    print("The full web_monitor.py script uses Playwright for:")
    print("  - JavaScript rendering")
    print("  - Full page screenshots")
    print("  - Better page load handling")


if __name__ == "__main__":
    main()
