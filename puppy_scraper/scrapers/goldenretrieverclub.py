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

        The page uses <strong> tags for field labels followed by text values.

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

        # Collect all content until the next h2 tag
        current = h2_tag.find_next_sibling()
        litter_text_parts = []
        all_text = ""

        while current and current.name != 'h2':
            text = current.get_text(separator=' ', strip=True)
            if text:
                litter_text_parts.append(text)
                all_text += " " + text

            # Look for <strong> tags which contain field labels
            strong_tags = current.find_all('strong') if hasattr(current, 'find_all') else []

            for strong in strong_tags:
                label = strong.get_text(strip=True)
                # Get text after the strong tag (the value)
                next_text = ""

                # Try to get the next text node or element text
                if strong.next_sibling:
                    if isinstance(strong.next_sibling, str):
                        next_text = strong.next_sibling.strip()
                    else:
                        next_text = strong.next_sibling.get_text(strip=True) if hasattr(strong.next_sibling, 'get_text') else ""

                # Also check parent's full text for context
                parent_text = strong.parent.get_text(separator=' ', strip=True) if strong.parent else ""

                # Extract based on label
                if 'Gedekt' in label:
                    match = re.search(r'Gedekt[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})', parent_text)
                    if match:
                        litter['mating_date'] = match.group(1)

                if 'Fokker' in label:
                    match = re.search(r'Fokker[:\s]*([^\n\r]+?)(?=\s*(?:Gedekt|Verwacht|Plaats|Telefoon|E-mail|Website|Reu|Teef|$))', parent_text, re.IGNORECASE)
                    if match:
                        litter['breeder'] = match.group(1).strip()

                if 'Verwacht' in label:
                    match = re.search(r'Verwacht[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})', parent_text)
                    if match:
                        litter['expected_date'] = match.group(1)

                if 'Plaats' in label or 'Woonplaats' in label:
                    match = re.search(r'(?:Plaats|Woonplaats)[:\s]*([^\n\r]+?)(?=\s*(?:Telefoon|E-mail|Website|$))', parent_text, re.IGNORECASE)
                    if match:
                        litter['location'] = match.group(1).strip()

                if 'Telefoon' in label or 'Tel' in label:
                    match = re.search(r'(?:Telefoon|Tel)[:\s]*(\d[\d\-\s]+)', parent_text, re.IGNORECASE)
                    if match:
                        litter['contact_phone'] = match.group(1).strip()

                if 'E-mail' in label or 'Email' in label:
                    match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', parent_text)
                    if match:
                        litter['contact_email'] = match.group(0)

                if 'Website' in label:
                    match = re.search(r'(?:https?://)?(?:www\.)?[\w\.-]+\.\w{2,}(?:/\S*)?', parent_text)
                    if match:
                        litter['contact_website'] = match.group(0).strip()

                if 'Reu' in label:
                    match = re.search(r'Reu[:\s]*([^\n\r]+?)(?=\s*(?:Teef|$))', parent_text, re.IGNORECASE)
                    if match:
                        litter['male_dog'] = match.group(1).strip()[:200]

                if 'Teef' in label:
                    match = re.search(r'Teef[:\s]*([^\n\r]+?)(?=\s*(?:Reu|$))', parent_text, re.IGNORECASE)
                    if match:
                        litter['female_dog'] = match.group(1).strip()[:200]

            current = current.find_next_sibling()

        litter['raw_text'] = ' '.join(litter_text_parts)

        # If we didn't find data via <strong> tags, try regex on all_text
        if not litter['breeder'] and all_text:
            match = re.search(r'Fokker[:\s]*([^\n\r]+?)(?=(?:Gedekt|Verwacht|Plaats|Tel|$))', all_text, re.IGNORECASE)
            if match:
                litter['breeder'] = match.group(1).strip()

        if not litter['mating_date'] and all_text:
            match = re.search(r'Gedekt[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})', all_text, re.IGNORECASE)
            if match:
                litter['mating_date'] = match.group(1)

        if not litter['expected_date'] and all_text:
            match = re.search(r'Verwacht[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})', all_text, re.IGNORECASE)
            if match:
                litter['expected_date'] = match.group(1)

        # Only return litter if we have at least some key information
        if litter['breeder'] or litter['expected_date'] or litter['mating_date']:
            return litter

        return None
