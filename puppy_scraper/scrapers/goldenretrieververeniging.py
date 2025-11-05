"""Scraper for goldenretrieververeniging.nl website."""

from typing import List, Dict, Any
from bs4 import BeautifulSoup
import re
import logging

from ..base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class GoldenRetrieverVerenigingScraper(BaseScraper):
    """Scraper for www.goldenretrieververeniging.nl expected litters."""

    def __init__(self):
        super().__init__(
            url="https://www.goldenretrieververeniging.nl/pupinformatie/verwachte-nesten/",
            name="Golden Retriever Vereniging"
        )

    def parse_litters(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Parse litters from goldenretrieververeniging.nl.

        This site may have a different structure, so we'll look for common patterns
        like tables, article tags, or div containers with litter information.

        Args:
            soup: BeautifulSoup object of the page

        Returns:
            List of dictionaries containing litter information
        """
        litters = []

        # Strategy 1: Look for article or section tags
        articles = soup.find_all(['article', 'section'])
        if articles:
            for article in articles:
                try:
                    litter_data = self._parse_article_litter(article)
                    if litter_data:
                        litters.append(litter_data)
                except Exception as e:
                    logger.warning(f"Error parsing article entry: {str(e)}")
                    continue

        # Strategy 2: If no articles found, try h2/h3 based parsing similar to first site
        if not litters:
            header_tags = soup.find_all(['h2', 'h3'])
            for header in header_tags:
                try:
                    litter_data = self._parse_header_litter(header)
                    if litter_data:
                        litters.append(litter_data)
                except Exception as e:
                    logger.warning(f"Error parsing header entry: {str(e)}")
                    continue

        # Strategy 3: Look for table rows
        if not litters:
            tables = soup.find_all('table')
            for table in tables:
                try:
                    table_litters = self._parse_table_litters(table)
                    litters.extend(table_litters)
                except Exception as e:
                    logger.warning(f"Error parsing table: {str(e)}")
                    continue

        return litters

    def _parse_article_litter(self, article) -> Dict[str, Any]:
        """Parse litter from an article/section tag."""
        text = article.get_text()
        return self._extract_litter_data(text, article)

    def _parse_header_litter(self, header) -> Dict[str, Any]:
        """Parse litter starting from a header tag."""
        # Collect text until next header
        text_parts = [header.get_text(strip=True)]
        current = header.find_next_sibling()

        while current and current.name not in ['h1', 'h2', 'h3']:
            text = current.get_text(strip=True)
            if text:
                text_parts.append(text)
            current = current.find_next_sibling()

        full_text = ' '.join(text_parts)
        return self._extract_litter_data(full_text, header)

    def _parse_table_litters(self, table) -> List[Dict[str, Any]]:
        """Parse litters from a table structure."""
        litters = []
        rows = table.find_all('tr')

        for row in rows[1:]:  # Skip header row
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 2:
                text = ' '.join([cell.get_text(strip=True) for cell in cells])
                litter = self._extract_litter_data(text, row)
                if litter:
                    litters.append(litter)

        return litters

    def _extract_litter_data(self, text: str, element) -> Dict[str, Any]:
        """
        Extract litter data from text using common patterns.

        Args:
            text: Text to parse
            element: BeautifulSoup element for additional context

        Returns:
            Dictionary with litter information or None
        """
        litter = {
            'kennel_name': None,
            'breeder': None,
            'mating_date': None,
            'expected_date': None,
            'location': None,
            'contact_phone': None,
            'contact_email': None,
            'contact_website': None,
            'male_dog': None,
            'female_dog': None,
            'raw_text': text
        }

        # Extract kennel name from header if available
        header = element.find(['h1', 'h2', 'h3', 'h4'])
        if header:
            litter['kennel_name'] = header.get_text(strip=True)

        # Extract dates
        date_match = re.search(r'Gedekt[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})', text, re.IGNORECASE)
        if date_match:
            litter['mating_date'] = date_match.group(1)

        expected_match = re.search(r'Verwacht[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})', text, re.IGNORECASE)
        if expected_match:
            litter['expected_date'] = expected_match.group(1)

        # Alternative date patterns
        if not litter['expected_date']:
            expected_match = re.search(r'geboren[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})', text, re.IGNORECASE)
            if expected_match:
                litter['expected_date'] = expected_match.group(1)

        # Extract breeder
        breeder_match = re.search(r'(?:Fokker|Breeder)[:\s]*([^\n\r,]+)', text, re.IGNORECASE)
        if breeder_match:
            litter['breeder'] = breeder_match.group(1).strip()

        # Extract location
        location_match = re.search(r'(?:Woonplaats|Plaats|Locatie)[:\s]*([^\n\r,]+)', text, re.IGNORECASE)
        if location_match:
            litter['location'] = location_match.group(1).strip()

        # Extract contact info
        phone_match = re.search(r'(?:Tel|Telefoon)[:\s]*(\d{2,4}[-\s]?\d{6,})', text, re.IGNORECASE)
        if phone_match:
            litter['contact_phone'] = phone_match.group(1)

        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
        if email_match:
            litter['contact_email'] = email_match.group(0)

        website_match = re.search(r'(?:https?://)?(?:www\.)?[\w\.-]+\.\w{2,}', text.lower())
        if website_match:
            litter['contact_website'] = website_match.group(0)

        # Extract parent dogs
        male_match = re.search(r'(?:Reu|Vader|Father)[:\s]*([^\n\r]+?)(?=(?:Teef|Moeder|Mother)|$)', text, re.IGNORECASE)
        if male_match:
            litter['male_dog'] = male_match.group(1).strip()[:100]  # Limit length

        female_match = re.search(r'(?:Teef|Moeder|Mother)[:\s]*([^\n\r]+?)(?=(?:Reu|Vader|Father)|$)', text, re.IGNORECASE)
        if female_match:
            litter['female_dog'] = female_match.group(1).strip()[:100]  # Limit length

        # Only return if we have meaningful data
        if any([litter['breeder'], litter['expected_date'], litter['mating_date'],
                litter['male_dog'], litter['female_dog']]):
            return litter

        return None
