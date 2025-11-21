# Web Page Monitor

A Python script that monitors web pages for changes by comparing HTML content and taking screenshots when differences are detected.

## Features

- Opens web pages in a headless browser
- Downloads and saves HTML content
- Compares current HTML with previous snapshots
- Takes screenshots when changes are detected
- Organizes screenshots and HTML snapshots in separate folders

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Install Playwright browsers:
```bash
playwright install chromium
```

**Note:** Playwright will automatically download the required Chromium browser.

## Usage

Run the script:
```bash
python web_monitor.py
```

The script will:
- Check each URL in the list (currently monitoring https://www.reyncomslant.nl/nieuws/)
- On first run: Save HTML snapshot and take a screenshot
- On subsequent runs: Compare HTML with previous snapshot
  - If identical: Skip and move to next URL
  - If different: Take a new screenshot and update HTML snapshot

## Output

- `html_snapshots/`: Stores HTML content for comparison
- `screenshots/`: Stores screenshots when changes are detected

## Customization

Edit the `urls` list in `web_monitor.py` to monitor different pages:

```python
urls = [
    "https://www.reyncomslant.nl/nieuws/",
    "https://example.com/page1",
    "https://example.com/page2",
]
```

## How It Works

1. For each URL, the script generates a unique filename based on the domain and URL hash
2. Loads any previously saved HTML snapshot
3. Opens the URL in a headless Chromium browser (via Playwright)
4. Compares current HTML with previous snapshot
5. If different (or first run), takes a screenshot and saves the new HTML snapshot

## Demo

A simplified demo script (`demo_monitor.py`) is included that demonstrates the HTML comparison logic using simple HTTP requests (without browser automation). This is useful for testing the core functionality:

```bash
python demo_monitor.py
```

## Example

See `screenshots/www_reyncomslant_nl_nieuws_demo.png` for an example of the type of screenshot captured by the monitor.
