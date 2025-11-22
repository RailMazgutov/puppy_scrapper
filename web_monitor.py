#!/usr/bin/env python3
"""
Web Page Monitor Script
Monitors web pages for changes by comparing HTML content and taking screenshots.
Designed to run as a cronjob with configurable URL list.
"""

import os
import sys
import hashlib
import time
import logging
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

# Get the script's directory for resolving relative paths
SCRIPT_DIR = Path(__file__).parent.resolve()
DEFAULT_URLS_FILE = SCRIPT_DIR / "urls.txt"
DEFAULT_LOG_FILE = SCRIPT_DIR / "monitor.log"


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


def setup_logging(log_file=None, verbose=False):
    """Setup logging for both file and console output."""
    log_file = log_file or DEFAULT_LOG_FILE

    # Create logger
    logger = logging.getLogger('web_monitor')
    logger.setLevel(logging.DEBUG)

    # Clear existing handlers
    logger.handlers.clear()

    # File handler - always logs
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    file_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)

    # Console handler - for interactive use
    if verbose or sys.stdout.isatty():
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_format = logging.Formatter('%(message)s')
        console_handler.setFormatter(console_format)
        logger.addHandler(console_handler)

    return logger


def load_urls_from_file(urls_file=None):
    """Load URLs from a configuration file.

    Args:
        urls_file: Path to the URLs file. Defaults to urls.txt in script directory.

    Returns:
        List of URLs to monitor.
    """
    urls_file = Path(urls_file) if urls_file else DEFAULT_URLS_FILE

    if not urls_file.exists():
        raise FileNotFoundError(
            f"URLs file not found: {urls_file}\n"
            f"Please create the file with one URL per line."
        )

    urls = []
    with open(urls_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            # Basic URL validation
            if line.startswith('http://') or line.startswith('https://'):
                urls.append(line)
            else:
                print(f"Warning: Skipping invalid URL on line {line_num}: {line}")

    return urls


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Monitor web pages for changes',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python web_monitor.py                    # Use default urls.txt
  python web_monitor.py -f my_urls.txt     # Use custom URL file
  python web_monitor.py -v                 # Verbose output
  python web_monitor.py --cron             # Cron mode (quiet, log only)
        """
    )
    parser.add_argument(
        '-f', '--file',
        help='Path to URLs configuration file (default: urls.txt)',
        default=None
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    parser.add_argument(
        '--cron',
        action='store_true',
        help='Run in cron mode (suppress console output, log to file only)'
    )
    parser.add_argument(
        '--log-file',
        help='Path to log file (default: monitor.log)',
        default=None
    )

    args = parser.parse_args()

    # Setup logging
    verbose = args.verbose and not args.cron
    logger = setup_logging(args.log_file, verbose)

    logger.info(f"{'='*50}")
    logger.info(f"Web Monitor started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        # Load URLs from file
        urls = load_urls_from_file(args.file)

        if not urls:
            logger.warning("No URLs found in configuration file")
            return 1

        logger.info(f"Loaded {len(urls)} URL(s) to monitor")

        # Create monitor and check URLs
        monitor = WebPageMonitor()
        monitor.monitor_urls(urls)

        logger.info("Monitoring completed successfully")
        return 0

    except FileNotFoundError as e:
        logger.error(str(e))
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
