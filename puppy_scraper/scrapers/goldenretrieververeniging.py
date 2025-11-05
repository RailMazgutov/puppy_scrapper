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

    def fetch_page(self):
        """
        Override fetch_page to use httpx HTTP/2 directly for this site.
        Cloudscraper returns garbled HTML for this site.
        """
        import httpx

        logger.info(f"Fetching page: {self.url}")

        headers = self._get_headers()

        # Use httpx HTTP/2 directly for this site
        try:
            with httpx.Client(http2=True, follow_redirects=True, timeout=30.0) as client:
                response = client.get(self.url, headers=headers)
                response.raise_for_status()
                logger.info(f"✓ httpx HTTP/2 succeeded (status: {response.status_code})")
                return BeautifulSoup(response.text, 'html.parser')
        except Exception as e:
            logger.error(f"httpx HTTP/2 failed: {str(e)}")
            # Fallback to parent class methods
            return super().fetch_page()

    def parse_litters(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Parse litters from goldenretrieververeniging.nl.

        The page structure uses h2 headers for kennel names followed by
        j-text modules with breeder info and j-table modules with dates.

        Args:
            soup: BeautifulSoup object of the page

        Returns:
            List of dictionaries containing litter information
        """
        litters = []

        # Find all h2 headers that contain "Kennel" - these mark litter entries
        h2_tags = soup.find_all('h2')

        for h2 in h2_tags:
            try:
                h2_text = h2.get_text(strip=True)
                # Look for headers that indicate a kennel/litter
                if 'Kennel' in h2_text or h2_text.strip().endswith(':'):
                    litter_data = self._parse_single_litter_from_h2(h2)
                    if litter_data:
                        litters.append(litter_data)
            except Exception as e:
                logger.warning(f"Error parsing litter from h2: {str(e)}")
                continue

        return litters

    def _parse_single_litter_from_h2(self, h2_tag) -> Dict[str, Any]:
        """
        Parse a single litter entry starting from an h2 tag.

        The structure is:
        - h2: Kennel name
        - Sibling divs containing j-text modules with breeder info
        - Sibling divs containing j-table modules with dates and dog info

        Args:
            h2_tag: The h2 BeautifulSoup tag marking the kennel

        Returns:
            Dictionary containing litter information or None
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
            'raw_text': []
        }

        # Extract kennel name
        h2_text = h2_tag.get_text(strip=True)
        if 'Kennel' in h2_text:
            # Extract kennel name after "Kennel :" or "Kennel:"
            parts = h2_text.split(':', 1)
            if len(parts) > 1:
                litter['kennel_name'] = parts[1].strip()
            else:
                litter['kennel_name'] = h2_text

        # Find the parent hgrid container (which contains multiple cc-matrix divs)
        hgrid = h2_tag.find_parent(class_=re.compile(r'j-hgrid'))
        if not hgrid:
            # Fallback to just the matrix if no hgrid found
            hgrid = h2_tag.find_parent(id=re.compile(r'cc-matrix'))
            if not hgrid:
                return None

        # Collect all text for raw_text
        all_text = hgrid.get_text(strip=True, separator=' ')
        litter['raw_text'] = all_text

        # Find all j-text modules in this hgrid for breeder info
        text_modules = hgrid.find_all(class_=re.compile(r'j-text'))
        for module in text_modules:
            text = module.get_text(separator='\n')

            # Extract breeder
            if 'Fokker' in text and not litter['breeder']:
                match = re.search(r'Fokker\s*:\s*(.+?)(?:\n|$)', text, re.IGNORECASE)
                if match:
                    litter['breeder'] = match.group(1).strip()

            # Extract location
            if 'Woonplaats' in text and not litter['location']:
                match = re.search(r'Woonplaats\s*:\s*(.+?)(?:\n|$)', text, re.IGNORECASE)
                if match:
                    litter['location'] = match.group(1).strip()

            # Extract phone
            if 'Telefoon' in text and not litter['contact_phone']:
                match = re.search(r'Telefoon\s*:\s*(\d[\d\-\s]+)', text, re.IGNORECASE)
                if match:
                    litter['contact_phone'] = match.group(1).strip()

            # Extract email
            if 'E-mail' in text and not litter['contact_email']:
                match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
                if match:
                    litter['contact_email'] = match.group(0)

            # Extract website
            if 'Website' in text and not litter['contact_website']:
                match = re.search(r'(?:https?://)?(?:www\.)?[\w\.-]+\.\w{2,}(?:/\S*)?', text)
                if match:
                    litter['contact_website'] = match.group(0).strip()

            # Extract dog names from sections that have both name and parentage
            # Dog names often come before parentage info in parentheses
            lines = text.split('\n')
            for i, line in enumerate(lines):
                line = line.strip()
                # Look for dog name patterns (all caps, followed by parentage)
                if line.isupper() and len(line) > 5 and not any(keyword in line for keyword in ['HEUPEN', 'ELLEBOGEN', 'DNA', 'SHOW', 'WERK', 'OGEN']):
                    # Check if next line has parentage info
                    if i + 1 < len(lines) and '(' in lines[i + 1]:
                        # Determine if male or female based on context
                        # This is a dog name with parentage
                        dog_info = f"{line} {lines[i+1].strip()}"
                        # Assign to male/female (first one male, second female typically)
                        if not litter['male_dog']:
                            litter['male_dog'] = dog_info[:200]
                        elif not litter['female_dog']:
                            litter['female_dog'] = dog_info[:200]

        # Find all j-table modules in this hgrid for dates
        table_modules = hgrid.find_all(class_=re.compile(r'j-table'))
        for module in table_modules:
            # Extract all table text
            table_text = module.get_text(separator=' ', strip=True)

            # Extract mating date (Dekdatum)
            # Matches both "29 augustus 2025" and "29-08-2025" formats
            if 'Dekdatum' in table_text and not litter['mating_date']:
                # Try format with month name: "29 augustus 2025"
                match = re.search(r'Dekdatum[:\s]*(\d{1,2}\s+\w+\s+\d{4})', table_text, re.IGNORECASE)
                if not match:
                    # Try numeric format: "29-08-2025" or "29/08/2025"
                    match = re.search(r'Dekdatum[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})', table_text, re.IGNORECASE)
                if match:
                    litter['mating_date'] = match.group(1).strip()

            # Extract expected birth date
            # Matches both "30 oktober 2025" and "30-10-2025" formats
            if 'Verwachte geboortedatum' in table_text and not litter['expected_date']:
                # Try format with month name: "30 oktober 2025"
                match = re.search(r'Verwachte geboortedatum[:\s]*(\d{1,2}\s+\w+\s+\d{4})', table_text, re.IGNORECASE)
                if not match:
                    # Try numeric format: "30-10-2025" or "30/10/2025"
                    match = re.search(r'Verwachte geboortedatum[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})', table_text, re.IGNORECASE)
                if match:
                    litter['expected_date'] = match.group(1).strip()

        # Only return if we have at least some key information
        if litter['breeder'] or litter['expected_date'] or litter['mating_date']:
            return litter

        return None
