#!/usr/bin/env python3
"""
Telegram Notifier Module

Sends notifications to subscribed users when web page changes are detected.
Used by web_monitor.py to notify users via Telegram.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional

import telegram

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Paths
SCRIPT_DIR = Path(__file__).parent.resolve()
CONFIG_FILE = SCRIPT_DIR / "telegram_config.json"
SUBSCRIBERS_FILE = SCRIPT_DIR / "subscribers.json"


def load_config() -> dict:
    """Load configuration from telegram_config.json."""
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {CONFIG_FILE}\n"
            f"Please create it from telegram_config.json.example"
        )

    with open(CONFIG_FILE, "r") as f:
        config = json.load(f)

    if not config.get("bot_token"):
        raise ValueError("bot_token is required in configuration")

    return config


def load_subscribers() -> list[int]:
    """Load subscriber chat IDs from subscribers.json."""
    if not SUBSCRIBERS_FILE.exists():
        return []

    try:
        with open(SUBSCRIBERS_FILE, "r") as f:
            data = json.load(f)
            return data.get("subscribers", [])
    except (json.JSONDecodeError, KeyError):
        return []


def save_subscribers(subscribers: list[int]) -> None:
    """Save subscriber chat IDs to subscribers.json."""
    with open(SUBSCRIBERS_FILE, "w") as f:
        json.dump({"subscribers": subscribers}, f, indent=2)


def add_subscriber(chat_id: int) -> bool:
    """Add a subscriber. Returns True if newly added, False if already exists."""
    subscribers = load_subscribers()
    if chat_id not in subscribers:
        subscribers.append(chat_id)
        save_subscribers(subscribers)
        logger.info(f"Added subscriber: {chat_id}")
        return True
    return False


def remove_subscriber(chat_id: int) -> bool:
    """Remove a subscriber. Returns True if removed, False if not found."""
    subscribers = load_subscribers()
    if chat_id in subscribers:
        subscribers.remove(chat_id)
        save_subscribers(subscribers)
        logger.info(f"Removed subscriber: {chat_id}")
        return True
    return False


def is_subscriber(chat_id: int) -> bool:
    """Check if a chat ID is a subscriber."""
    return chat_id in load_subscribers()


async def send_notification(
    url: str,
    screenshot_path: Optional[Path] = None,
    message: Optional[str] = None
) -> int:
    """
    Send a notification to all subscribers about a page change.

    Args:
        url: The URL that changed
        screenshot_path: Path to the screenshot file (optional)
        message: Custom message (optional, will be auto-generated if not provided)

    Returns:
        Number of subscribers successfully notified
    """
    try:
        config = load_config()
    except (FileNotFoundError, ValueError) as e:
        logger.error(f"Cannot send notification: {e}")
        return 0

    subscribers = load_subscribers()
    if not subscribers:
        logger.info("No subscribers to notify")
        return 0

    bot = telegram.Bot(token=config["bot_token"])

    # Build the notification message
    if message is None:
        message = (
            "🔔 *Change Detected!*\n\n"
            f"A change has been detected on:\n"
            f"🔗 {url}\n\n"
            "Check the screenshot below for details."
        )

    success_count = 0

    for chat_id in subscribers:
        try:
            if screenshot_path and screenshot_path.exists():
                # Send photo with caption
                with open(screenshot_path, "rb") as photo:
                    await bot.send_photo(
                        chat_id=chat_id,
                        photo=photo,
                        caption=message,
                        parse_mode="Markdown"
                    )
            else:
                # Send text message only
                await bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode="Markdown"
                )

            success_count += 1
            logger.info(f"Notification sent to {chat_id}")

        except telegram.error.Forbidden:
            # User blocked the bot, remove from subscribers
            logger.warning(f"User {chat_id} blocked the bot, removing from subscribers")
            remove_subscriber(chat_id)
        except telegram.error.BadRequest as e:
            logger.error(f"Bad request sending to {chat_id}: {e}")
        except Exception as e:
            logger.error(f"Failed to send notification to {chat_id}: {e}")

    return success_count


def notify_change(url: str, screenshot_path: Optional[Path] = None) -> int:
    """
    Synchronous wrapper for send_notification.
    Call this from web_monitor.py when a change is detected.

    Args:
        url: The URL that changed
        screenshot_path: Path to the screenshot file (optional)

    Returns:
        Number of subscribers successfully notified
    """
    try:
        return asyncio.run(send_notification(url, screenshot_path))
    except Exception as e:
        logger.error(f"Error sending notifications: {e}")
        return 0


if __name__ == "__main__":
    # Test the notifier
    print("Telegram Notifier Module")
    print(f"Subscribers file: {SUBSCRIBERS_FILE}")
    print(f"Current subscribers: {load_subscribers()}")
