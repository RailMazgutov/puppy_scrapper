# Features

## Overview

**puppy_scrapper** is a web page monitoring tool that automatically detects content changes on websites and notifies users via Telegram. It captures screenshots when changes are detected and provides remote management through an interactive Telegram bot.

---

## Core Monitoring

| Feature | Description |
|---------|-------------|
| **HTML Change Detection** | Compares current page content with saved snapshots to identify changes |
| **Full-Page Screenshots** | Captures 1920x1080 screenshots when changes are detected |
| **Multi-URL Support** | Monitor multiple URLs simultaneously from a single configuration file |
| **Persistent Snapshots** | Stores HTML snapshots for accurate comparison across runs |
| **Headless Browser** | Uses Playwright Chromium for JavaScript-rendered page support |

---

## Telegram Bot

### Authentication & Security
- Password-protected access
- Persistent user sessions (survives bot restarts)
- Logout functionality

### Interactive Menu
- Beautiful inline keyboard buttons
- Easy navigation without typing commands
- Quick access to all features

### URL Management
- `/add <url>` - Add new URLs to monitor
- `/remove <url>` - Remove URLs from monitoring
- `/list` - View all monitored URLs
- URL validation (HTTP/HTTPS only)

### Notifications
- `/subscribe` - Enable change notifications
- `/unsubscribe` - Disable notifications
- `/status` - Check subscription status
- Automatic screenshot delivery when changes detected

### Monitoring Control
- `/scan` - Trigger manual monitoring scan
- `/logs` - View last run status and details
- Real-time feedback on scan progress

### Commands Reference

| Command | Description |
|---------|-------------|
| `/start` | Begin authentication |
| `/menu` | Show interactive menu |
| `/list` | Display monitored URLs |
| `/add <url>` | Add URL to monitor |
| `/remove <url>` | Remove URL |
| `/scan` | Trigger manual scan |
| `/subscribe` | Enable notifications |
| `/unsubscribe` | Disable notifications |
| `/status` | Check subscription |
| `/logs` | Show last run details |
| `/help` | Show help message |
| `/logout` | Log out from bot |

---

## Automation

| Feature | Description |
|---------|-------------|
| **Cron Scheduling** | Automatic hourly monitoring via Linux cron |
| **Easy Setup** | One-command cron installation with `setup_cron.sh` |
| **Run Status Tracking** | JSON-based logging of each monitoring cycle |
| **Virtual Environment Support** | Auto-detects and activates Python venv |

### Cron Management Commands
```bash
./setup_cron.sh install   # Install hourly cron job
./setup_cron.sh remove    # Remove cron job
./setup_cron.sh status    # Check cron status
```

---

## Notifications

- **Real-time Alerts** - Instant Telegram notifications when pages change
- **Screenshot Attachments** - Visual proof of changes included
- **Multi-subscriber Support** - Multiple users can receive notifications
- **Change Summary** - Details about which URLs changed

---

## Configuration

### URL Configuration (`urls.txt`)
```
# One URL per line
# Comments start with #
https://example.com/page-to-monitor
https://another-site.com/news
```

### Telegram Configuration (`telegram_config.json`)
```json
{
    "bot_token": "YOUR_BOT_TOKEN",
    "access_password": "YOUR_PASSWORD"
}
```

### Environment Variables
- `HTTP_PROXY` / `HTTPS_PROXY` - Proxy support for network requests

---

## Storage & Output

| Data | Location | Format |
|------|----------|--------|
| Screenshots | `screenshots/` | PNG images |
| HTML Snapshots | `html_snapshots/` | HTML files |
| Subscribers | `subscribers.json` | JSON array |
| Authenticated Users | `authenticated_users.json` | JSON array |
| Run Status | `run_status.json` | JSON object |
| Logs | `monitor.log`, `cron.log` | Text logs |

---

## Technical Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3 |
| Browser Automation | Playwright (Chromium) |
| Telegram Integration | python-telegram-bot (>=20.0) |
| Scheduling | Linux cron |
| Storage | File-based (JSON, HTML, PNG) |

---

## Use Cases

1. **Price Monitoring** - Track price changes on e-commerce sites
2. **News Alerts** - Get notified when news pages update
3. **Availability Tracking** - Monitor product availability
4. **Content Changes** - Track updates to any web page
5. **Competitor Monitoring** - Watch competitor website changes

---

## Quick Start

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

2. Configure URLs in `urls.txt`

3. Set up Telegram bot in `telegram_config.json`

4. Run manually:
   ```bash
   python web_monitor.py
   ```

5. Or set up automated monitoring:
   ```bash
   ./setup_cron.sh install
   ```

6. Start the Telegram bot:
   ```bash
   python telegram_bot.py
   ```
