"""Base scraper class for website scraping."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
import cloudscraper
import httpx
from bs4 import BeautifulSoup
import hashlib
import logging
import time
from fake_useragent import UserAgent
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Abstract base class for website scrapers."""

    def __init__(self, url: str, name: str):
        """
        Initialize the scraper.

        Args:
            url: The URL to scrape
            name: A friendly name for this scraper
        """
        self.url = url
        self.name = name
        self.ua = UserAgent()
        # Don't create cloudscraper here - create fresh one for each request
        self._scraper = None

    def _get_scraper(self):
        """Get a fresh cloudscraper instance."""
        # Create a new scraper for each request to avoid session issues
        return cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True
            }
        )

    def _get_headers(self, base_url: str = None) -> dict:
        """Generate realistic browser headers."""
        headers = {
            'User-Agent': self.ua.chrome,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'nl-NL,nl;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
            'DNT': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
        }
        if base_url:
            headers['Referer'] = base_url + '/'
        return headers

    def _try_httpx_http2(self, url: str, headers: dict) -> BeautifulSoup:
        """Try fetching with httpx using HTTP/2."""
        logger.info("Trying httpx with HTTP/2...")
        with httpx.Client(http2=True, follow_redirects=True, timeout=30.0) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()

            # Debug logging
            logger.debug(f"httpx response: status={response.status_code}, content_length={len(response.content)}, encoding={response.encoding}")
            logger.debug(f"httpx response headers: {dict(response.headers)}")

            # Handle Brotli compression manually for httpx too
            content_encoding = response.headers.get('content-encoding', '').lower()
            if content_encoding == 'br':
                import brotli
                try:
                    decompressed = brotli.decompress(response.content)
                    text_content = decompressed.decode('utf-8', errors='replace')
                    logger.debug("Manually decompressed Brotli content (httpx)")
                except Exception as e:
                    logger.warning(f"Brotli decompression failed (httpx): {e}")
                    text_content = response.text
            else:
                text_content = response.text

            logger.debug(f"httpx text preview: {text_content[:200] if text_content else 'NO TEXT'}")

            # Use lxml parser - pass text (string) instead of content (bytes)
            soup = BeautifulSoup(text_content, 'lxml')
            logger.debug(f"httpx soup h2 count: {len(soup.find_all('h2'))}")
            return soup

    def _try_selenium(self, url: str) -> BeautifulSoup:
        """Try fetching with Selenium (headless Chrome)."""
        logger.info("Trying Selenium with headless Chrome...")
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument(f'user-agent={self.ua.chrome}')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        driver = None
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)

            # Set page load timeout
            driver.set_page_load_timeout(30)

            # Navigate to the page
            driver.get(url)

            # Wait for content to load (wait for body tag)
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # Give JavaScript time to render
            time.sleep(2)

            # Get the page source
            page_source = driver.page_source
            # Use lxml parser for better encoding handling
            return BeautifulSoup(page_source, 'lxml')

        finally:
            if driver:
                driver.quit()

    def fetch_page(self) -> BeautifulSoup:
        """
        Fetch the web page and return a BeautifulSoup object.
        Uses multiple strategies to bypass anti-bot protection.

        Returns:
            BeautifulSoup object of the page

        Raises:
            Exception: If all fetch strategies fail
        """
        logger.info(f"Fetching page: {self.url}")

        # Add a delay to be polite and avoid rate limiting
        time.sleep(2)

        # Extract base URL for referer
        from urllib.parse import urlparse
        parsed_url = urlparse(self.url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

        # Strategy 1: Try cloudscraper with direct request (like standalone test)
        try:
            logger.debug("Strategy 1: Trying cloudscraper direct request...")
            headers = self._get_headers()

            # Get a fresh scraper instance
            scraper = self._get_scraper()

            # Direct request to the target page (no homepage visit to avoid triggering blocks)
            response = scraper.get(
                self.url,
                headers=headers,
                timeout=30,
                allow_redirects=True
            )
            response.raise_for_status()
            logger.info(f"✓ Strategy 1 succeeded (status: {response.status_code})")

            # Debug logging for cloudscraper
            logger.debug(f"cloudscraper response: content_length={len(response.content)}, encoding={response.encoding}")
            logger.debug(f"cloudscraper content-encoding header: {response.headers.get('content-encoding', 'none')}")

            # Handle Brotli compression manually
            content_encoding = response.headers.get('content-encoding', '').lower()
            if content_encoding == 'br':
                # Manually decompress Brotli
                import brotli
                try:
                    decompressed = brotli.decompress(response.content)
                    text_content = decompressed.decode('utf-8', errors='replace')
                    logger.debug("Manually decompressed Brotli content")
                except Exception as e:
                    logger.warning(f"Brotli decompression failed: {e}, using response.text")
                    text_content = response.text
            else:
                text_content = response.text

            logger.debug(f"cloudscraper text preview: {text_content[:200] if text_content else 'EMPTY'}")

            # Use lxml parser with explicit from_encoding for better handling
            # Pass the text (decoded string) instead of content (bytes) to avoid encoding issues
            soup = BeautifulSoup(text_content, 'lxml')
            h2_count = len(soup.find_all('h2'))
            logger.debug(f"cloudscraper soup: h2_count={h2_count}")

            if h2_count == 0:
                logger.warning(f"No h2 tags found! Soup preview: {str(soup)[:500]}")

            return soup
        except Exception as e1:
            logger.warning(f"Strategy 1 failed: {str(e1)}")

            # Strategy 2: Try httpx with HTTP/2
            try:
                logger.debug("Strategy 2: Trying httpx with HTTP/2...")
                headers = self._get_headers(base_url)
                soup = self._try_httpx_http2(self.url, headers)
                logger.info("✓ Strategy 2 succeeded with httpx HTTP/2")
                return soup
            except Exception as e2:
                logger.warning(f"Strategy 2 failed: {str(e2)}")

                # Strategy 3: Try httpx with HTTP/2 after visiting homepage
                try:
                    logger.debug("Strategy 3: Trying httpx HTTP/2 with homepage visit...")
                    with httpx.Client(http2=True, follow_redirects=True, timeout=30.0) as client:
                        # Visit homepage
                        headers = self._get_headers()
                        client.get(base_url, headers=headers)
                        time.sleep(0.5)

                        # Fetch target page
                        headers_with_referer = self._get_headers(base_url)
                        response = client.get(self.url, headers=headers_with_referer)
                        response.raise_for_status()
                        logger.info(f"✓ Strategy 3 succeeded (status: {response.status_code})")

                        # Handle Brotli compression
                        content_encoding = response.headers.get('content-encoding', '').lower()
                        if content_encoding == 'br':
                            import brotli
                            try:
                                decompressed = brotli.decompress(response.content)
                                text_content = decompressed.decode('utf-8', errors='replace')
                                logger.debug("Manually decompressed Brotli content (Strategy 3)")
                            except Exception as e:
                                logger.warning(f"Brotli decompression failed (Strategy 3): {e}")
                                text_content = response.text
                        else:
                            text_content = response.text

                        # Use lxml parser for better encoding handling
                        return BeautifulSoup(text_content, 'lxml')
                except Exception as e3:
                    logger.warning(f"Strategy 3 failed: {str(e3)}")

                    # Strategy 4: Try Selenium with headless Chrome
                    try:
                        logger.debug("Strategy 4: Trying Selenium with headless Chrome...")
                        soup = self._try_selenium(self.url)
                        logger.info("✓ Strategy 4 succeeded with Selenium")
                        return soup
                    except Exception as e4:
                        logger.error(f"All strategies failed for {self.url}")
                        logger.error(f"  - Strategy 1 (cloudscraper): {str(e1)}")
                        logger.error(f"  - Strategy 2 (httpx HTTP/2): {str(e2)}")
                        logger.error(f"  - Strategy 3 (httpx HTTP/2 with session): {str(e3)}")
                        logger.error(f"  - Strategy 4 (Selenium): {str(e4)}")
                        raise Exception(f"Failed to fetch {self.url} after trying all strategies")

    @abstractmethod
    def parse_litters(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Parse the page and extract litter information.

        Args:
            soup: BeautifulSoup object of the page

        Returns:
            List of dictionaries containing litter information
        """
        pass

    def generate_litter_id(self, litter: Dict[str, Any]) -> str:
        """
        Generate a unique ID for a litter based on its content.

        Args:
            litter: Dictionary containing litter information

        Returns:
            A unique hash string for the litter
        """
        # Create a string from the key fields
        id_string = f"{litter.get('breeder', '')}-{litter.get('mating_date', '')}-{litter.get('expected_date', '')}"
        return hashlib.md5(id_string.encode()).hexdigest()

    def scrape(self) -> List[Dict[str, Any]]:
        """
        Perform the complete scraping operation.

        Returns:
            List of litter dictionaries with added metadata
        """
        try:
            soup = self.fetch_page()

            # Debug: Check if we got content
            h2_tags = soup.find_all('h2')
            logger.debug(f"Found {len(h2_tags)} h2 tags in {self.name}")

            # More debug: check soup content
            body = soup.find('body')
            if body:
                body_text = body.get_text(strip=True)[:200]
                logger.debug(f"Body preview: {body_text}")
            else:
                logger.warning(f"No <body> tag found! HTML preview: {str(soup)[:300]}")

            litters = self.parse_litters(soup)
            logger.debug(f"Parsed {len(litters)} litters from {self.name}")

            # Add metadata to each litter
            for litter in litters:
                litter['source'] = self.name
                litter['source_url'] = self.url
                litter['id'] = self.generate_litter_id(litter)

            logger.info(f"Successfully scraped {len(litters)} litters from {self.name}")
            return litters

        except Exception as e:
            logger.error(f"Error scraping {self.name}: {str(e)}", exc_info=True)
            return []
