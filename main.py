#!/usr/bin/env python3
"""Main entry point for the puppy scraper application."""

import logging
import sys
import argparse
from puppy_scraper.scrapers import GoldenRetrieverClubScraper, GoldenRetrieverVerenigingScraper
from puppy_scraper.storage import LitterStorage
from puppy_scraper.scheduler import ScraperScheduler


def setup_logging(verbose: bool = False):
    """
    Setup logging configuration.

    Args:
        verbose: If True, set logging level to DEBUG
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('puppy_scraper.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )


def main():
    """Main function to run the puppy scraper."""
    parser = argparse.ArgumentParser(
        description='Scrape golden retriever puppy litter information from Dutch websites'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=3600,
        help='Scraping interval in seconds (default: 3600 = 1 hour)'
    )
    parser.add_argument(
        '--once',
        action='store_true',
        help='Run once and exit (do not schedule periodic runs)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    logger.info("Starting Puppy Scraper Application")

    # Initialize scrapers
    scrapers = [
        GoldenRetrieverClubScraper(),
        GoldenRetrieverVerenigingScraper()
    ]

    # Initialize storage
    storage = LitterStorage()

    # Initialize scheduler
    scheduler = ScraperScheduler(
        scrapers=scrapers,
        storage=storage,
        interval_seconds=args.interval
    )

    print("\n" + "="*80)
    print("GOLDEN RETRIEVER PUPPY LITTER SCRAPER")
    print("="*80)
    print("\nMonitoring websites:")
    for scraper in scrapers:
        print(f"  - {scraper.name}")
        print(f"    {scraper.url}")
    print()

    # Run
    try:
        if args.once:
            print("Running once and exiting...\n")
            scheduler.run_once()
        else:
            scheduler.run_forever()
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        print(f"\nError: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
