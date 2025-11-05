"""Scraper for goldenretrieverclub.nl website."""

from typing import List, Dict, Any
from bs4 import BeautifulSoup
import re
import logging

from ..base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class GoldenRetrieverClubScraper(BaseScraper):
    """Scraper for www.goldenretrieverclub.nl expected litters."""

    def __init__(self):
        super().__init__(
            url="https://www.goldenretrieverclub.nl/pupinformatie/verwachte-nesten",
            name="Golden Retriever Club Nederland"
        )

    def parse_litters(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Parse litters from goldenretrieverclub.nl.

        The page uses <h2> tags as separators for each litter entry.

        Args:
            soup: BeautifulSoup object of the page

        Returns:
            List of dictionaries containing litter information
        """
        litters = []

        # Find all h2 tags which mark the beginning of each litter entry
        h2_tags = soup.find_all('h2')

        for h2 in h2_tags:
            try:
                litter_data = self._parse_single_litter(h2)
                if litter_data:
                    litters.append(litter_data)
            except Exception as e:
                logger.warning(f"Error parsing litter entry: {str(e)}")
                continue

        return litters

    def _parse_single_litter(self, h2_tag) -> Dict[str, Any]:
        """
        Parse a single litter entry starting from an h2 tag.

        Args:
            h2_tag: The h2 BeautifulSoup tag marking the litter entry

        Returns:
            Dictionary containing litter information
        """
        litter = {
            'kennel_name': h2_tag.get_text(strip=True),
            'breeder': None,
            'mating_date': None,
            'expected_date': None,
            'location': None,
            'contact_phone': None,
            'contact_email': None,
            'contact_website': None,
            'male_dog': None,
            'female_dog': None,
            'raw_text': []
        }

        # Collect all text content until the next h2 or end of content
        current = h2_tag.find_next_sibling()
        litter_text_parts = []

        while current and current.name != 'h2':
            text = current.get_text(strip=True)
            if text:
                litter_text_parts.append(text)

            # Extract specific fields using patterns
            if 'Gedekt' in text:
                # Extract mating date
                match = re.search(r'Gedekt[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})', text)
                if match:
                    litter['mating_date'] = match.group(1)

            if 'Fokker' in text or 'Breeder' in text:
                # Extract breeder name
                parts = text.split(':', 1)
                if len(parts) > 1:
                    litter['breeder'] = parts[1].strip()

            if 'Verwacht' in text:
                # Extract expected date
                match = re.search(r'Verwacht[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})', text)
                if match:
                    litter['expected_date'] = match.group(1)

            if 'Woonplaats' in text or 'Plaats' in text:
                # Extract location
                parts = text.split(':', 1)
                if len(parts) > 1:
                    litter['location'] = parts[1].strip()

            if 'Tel' in text or 'Telefoon' in text:
                # Extract phone
                match = re.search(r'(\d{2,4}[-\s]?\d{6,})', text)
                if match:
                    litter['contact_phone'] = match.group(1)

            if 'Email' in text or '@' in text:
                # Extract email
                match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
                if match:
                    litter['contact_email'] = match.group(0)

            if 'Website' in text or 'www.' in text.lower() or 'http' in text.lower():
                # Extract website
                match = re.search(r'(?:https?://)?(?:www\.)?[\w\.-]+\.\w{2,}', text.lower())
                if match:
                    litter['contact_website'] = match.group(0)

            # Extract parent dog names
            if 'Reu' in text and ':' in text:
                parts = text.split(':', 1)
                if len(parts) > 1:
                    litter['male_dog'] = parts[1].strip()

            if 'Teef' in text and ':' in text:
                parts = text.split(':', 1)
                if len(parts) > 1:
                    litter['female_dog'] = parts[1].strip()

            current = current.find_next_sibling()

        litter['raw_text'] = ' '.join(litter_text_parts)

        # Only return litter if we have at least some key information
        if litter['breeder'] or litter['expected_date'] or litter['mating_date']:
            return litter

        return None
