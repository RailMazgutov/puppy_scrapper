"""Scheduler for periodic scraping tasks."""

import time
import logging
from typing import List
from datetime import datetime

from .base_scraper import BaseScraper
from .storage import LitterStorage

logger = logging.getLogger(__name__)


class ScraperScheduler:
    """Manages periodic execution of scrapers."""

    def __init__(self, scrapers: List[BaseScraper], storage: LitterStorage, interval_seconds: int = 3600):
        """
        Initialize the scheduler.

        Args:
            scrapers: List of scraper instances to run
            storage: LitterStorage instance for change detection
            interval_seconds: Interval between scraping runs (default: 3600 = 1 hour)
        """
        self.scrapers = scrapers
        self.storage = storage
        self.interval_seconds = interval_seconds
        self.running = False

    def _log_new_litter(self, litter: dict):
        """
        Log a new litter to the console in a readable format.

        Args:
            litter: Dictionary containing litter information
        """
        print("\n" + "=" * 80)
        print("NEW LITTER DETECTED!")
        print("=" * 80)
        print(f"Source: {litter.get('source', 'Unknown')}")
        print(f"URL: {litter.get('source_url', 'N/A')}")

        if litter.get('kennel_name'):
            print(f"Kennel: {litter['kennel_name']}")

        if litter.get('breeder'):
            print(f"Breeder: {litter['breeder']}")

        if litter.get('location'):
            print(f"Location: {litter['location']}")

        if litter.get('mating_date'):
            print(f"Mating Date: {litter['mating_date']}")

        if litter.get('expected_date'):
            print(f"Expected Date: {litter['expected_date']}")

        if litter.get('male_dog'):
            print(f"Male (Reu): {litter['male_dog']}")

        if litter.get('female_dog'):
            print(f"Female (Teef): {litter['female_dog']}")

        print("\nContact Information:")
        if litter.get('contact_phone'):
            print(f"  Phone: {litter['contact_phone']}")
        if litter.get('contact_email'):
            print(f"  Email: {litter['contact_email']}")
        if litter.get('contact_website'):
            print(f"  Website: {litter['contact_website']}")

        print("=" * 80 + "\n")

    def run_once(self):
        """Execute all scrapers once and detect new litters."""
        logger.info("Starting scraping cycle")
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Running scrapers...")

        all_litters = []

        # Run all scrapers
        for scraper in self.scrapers:
            try:
                litters = scraper.scrape()
                all_litters.extend(litters)
                print(f"  - {scraper.name}: Found {len(litters)} litters")
            except Exception as e:
                logger.error(f"Error running scraper {scraper.name}: {str(e)}")
                print(f"  - {scraper.name}: Error - {str(e)}")

        # Detect new litters
        new_litters = self.storage.detect_new_litters(all_litters)

        if new_litters:
            print(f"\nFound {len(new_litters)} new litter(s)!\n")
            for litter in new_litters:
                self._log_new_litter(litter)
        else:
            print("No new litters detected.\n")

        # Update storage with all current litters
        self.storage.update_litters(all_litters)

        logger.info(f"Scraping cycle completed. Total litters: {len(all_litters)}, New: {len(new_litters)}")

    def run_forever(self):
        """Run the scheduler continuously with the specified interval."""
        self.running = True
        print(f"Scheduler started. Running every {self.interval_seconds} seconds ({self.interval_seconds/3600:.1f} hours)")
        print("Press Ctrl+C to stop\n")

        try:
            while self.running:
                self.run_once()

                # Wait for next cycle
                print(f"Next check at {datetime.fromtimestamp(time.time() + self.interval_seconds).strftime('%Y-%m-%d %H:%M:%S')}")
                time.sleep(self.interval_seconds)

        except KeyboardInterrupt:
            print("\n\nScheduler stopped by user")
            self.running = False
            logger.info("Scheduler stopped by user")

    def stop(self):
        """Stop the scheduler."""
        self.running = False
