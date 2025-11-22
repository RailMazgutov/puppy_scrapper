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

### Manual Run

Run the script manually:
```bash
python web_monitor.py
```

With options:
```bash
python web_monitor.py -f my_urls.txt     # Use custom URL file
python web_monitor.py -v                  # Verbose output
python web_monitor.py --cron              # Cron mode (quiet, log only)
```

The script will:
- Check each URL in the configured list
- On first run: Save HTML snapshot and take a screenshot
- On subsequent runs: Compare HTML with previous snapshot
  - If identical: Skip and move to next URL
  - If different: Take a new screenshot and update HTML snapshot

### Automatic Hourly Monitoring (Cron Job)

Set up automatic monitoring that runs every hour:

1. **Configure URLs to monitor:**
   Edit `urls.txt` and add one URL per line:
   ```
   # URLs to monitor (one per line, lines starting with # are comments)
   https://example.com/page1
   https://example.com/page2
   https://example.com/news
   ```

2. **Install the cron job:**
   ```bash
   ./setup_cron.sh install
   ```

3. **Check cron status:**
   ```bash
   ./setup_cron.sh status
   ```

4. **Remove the cron job (when needed):**
   ```bash
   ./setup_cron.sh remove
   ```

### Log Files

When running as a cron job, check these logs:
- `monitor.log` - Main application logs
- `cron.log` - Cron execution logs

## Output

- `html_snapshots/`: Stores HTML content for comparison
- `screenshots/`: Stores screenshots when changes are detected

## Configuration

### URL Configuration (urls.txt)

Edit `urls.txt` to configure which pages to monitor:

```
# URLs to monitor
https://www.reyncomslant.nl/nieuws/
https://example.com/page1
https://example.com/page2
```

Lines starting with `#` are comments. Empty lines are ignored.

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

See `screenshots/www_reyncomslant_nl_nieuws_df4d50d2.png` for an example screenshot captured from https://www.reyncomslant.nl/nieuws/
