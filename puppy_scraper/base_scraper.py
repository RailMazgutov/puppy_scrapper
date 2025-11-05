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
        # Use cloudscraper instead of requests to bypass Cloudflare and anti-bot protection
        self.scraper = cloudscraper.create_scraper(
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
            return BeautifulSoup(response.content, 'html.parser')

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
            return BeautifulSoup(page_source, 'html.parser')

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

        # Add a small delay to be polite and avoid rate limiting
        time.sleep(1)

        # Extract base URL for referer
        from urllib.parse import urlparse
        parsed_url = urlparse(self.url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

        # Strategy 1: Try cloudscraper with session establishment
        try:
            logger.debug("Strategy 1: Trying cloudscraper with homepage visit...")
            headers = self._get_headers()

            # Visit homepage first to establish cookies
            try:
                homepage_response = self.scraper.get(
                    base_url,
                    headers=headers,
                    timeout=30,
                    allow_redirects=True
                )
                logger.debug(f"Homepage response: {homepage_response.status_code}")
                time.sleep(0.5)
            except Exception as e:
                logger.warning(f"Homepage visit failed: {str(e)}")

            # Now fetch the actual page
            headers_with_referer = self._get_headers(base_url)
            response = self.scraper.get(
                self.url,
                headers=headers_with_referer,
                timeout=30,
                allow_redirects=True
            )
            response.raise_for_status()
            logger.info(f"✓ Strategy 1 succeeded (status: {response.status_code})")
            return BeautifulSoup(response.content, 'html.parser')
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
                        return BeautifulSoup(response.content, 'html.parser')
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
