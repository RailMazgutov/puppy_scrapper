# Golden Retriever Puppy Scraper

A Python application that periodically monitors Dutch golden retriever club websites for new expected litter announcements.

## Features

- **Multiple Scrapers**: Monitors two websites:
  - Golden Retriever Club Nederland (goldenretrieverclub.nl)
  - Golden Retriever Vereniging (goldenretrieververeniging.nl)

- **Change Detection**: Automatically detects new litter announcements
- **Periodic Execution**: Runs hourly (configurable)
- **Detailed Logging**: Logs all new entries to console with full details
- **Persistent Storage**: Tracks previously seen litters to avoid duplicates

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd puppy_scrapper
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Run continuously (checks every hour):
```bash
python main.py
```

### Run once and exit:
```bash
python main.py --once
```

### Change check interval (e.g., every 30 minutes):
```bash
python main.py --interval 1800
```

### Enable verbose logging:
```bash
python main.py --verbose
```

## Output

When a new litter is detected, the application displays:

```
================================================================================
NEW LITTER DETECTED!
================================================================================
Source: Golden Retriever Club Nederland
URL: https://www.goldenretrieverclub.nl/pupinformatie/verwachte-nesten
Kennel: Example Kennel Name
Breeder: John Doe
Location: Amsterdam
Mating Date: 15-10-2024
Expected Date: 15-12-2024
Male (Reu): Champion Dog Name
Female (Teef): Champion Female Name

Contact Information:
  Phone: 06-12345678
  Email: breeder@example.nl
  Website: www.example-kennel.nl
================================================================================
```

## Data Storage

Previous litter data is stored in `data/previous_litters.json` to enable change detection across runs.

## Logging

Application logs are saved to `puppy_scraper.log` in the current directory.

## Architecture

```
puppy_scrapper/
├── puppy_scraper/
│   ├── __init__.py
│   ├── base_scraper.py       # Base scraper class
│   ├── scrapers/
│   │   ├── __init__.py
│   │   ├── goldenretrieverclub.py
│   │   └── goldenretrieververeniging.py
│   ├── storage.py            # Change detection & storage
│   └── scheduler.py          # Periodic execution
├── data/
│   └── previous_litters.json # Stored litter data
├── main.py                   # Application entry point
├── requirements.txt
└── README.md
```

## Adding New Scrapers

To add a new website:

1. Create a new scraper class in `puppy_scraper/scrapers/` inheriting from `BaseScraper`
2. Implement the `parse_litters()` method
3. Add the scraper to the imports in `puppy_scraper/scrapers/__init__.py`
4. Initialize it in `main.py`

## License

See LICENSE file for details.
