"""Base scraper class for website scraping."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
import requests
from bs4 import BeautifulSoup
import hashlib
import logging

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
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def fetch_page(self) -> BeautifulSoup:
        """
        Fetch the web page and return a BeautifulSoup object.

        Returns:
            BeautifulSoup object of the page

        Raises:
            requests.RequestException: If the request fails
        """
        logger.info(f"Fetching page: {self.url}")
        response = requests.get(self.url, headers=self.headers, timeout=30)
        response.raise_for_status()
        return BeautifulSoup(response.content, 'html.parser')

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
            litters = self.parse_litters(soup)

            # Add metadata to each litter
            for litter in litters:
                litter['source'] = self.name
                litter['source_url'] = self.url
                litter['id'] = self.generate_litter_id(litter)

            logger.info(f"Successfully scraped {len(litters)} litters from {self.name}")
            return litters

        except Exception as e:
            logger.error(f"Error scraping {self.name}: {str(e)}")
            return []
