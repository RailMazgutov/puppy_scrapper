#!/usr/bin/env python3
"""
Telegram Bot for managing URL monitoring list.

This bot allows authenticated users to add or remove URLs from the urls.txt file
used by the web_monitor.py script.

Usage:
    python telegram_bot.py

Configuration:
    Create a telegram_config.json file with:
    {
        "bot_token": "YOUR_TELEGRAM_BOT_TOKEN",
        "access_password": "YOUR_SECRET_PASSWORD"
    }
"""

import asyncio
import json
import logging
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Set

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

# Import notifier for subscriber management
from telegram_notifier import (
    add_subscriber,
    remove_subscriber,
    is_subscriber,
    load_subscribers,
)

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Paths
SCRIPT_DIR = Path(__file__).parent.resolve()
CONFIG_FILE = SCRIPT_DIR / "telegram_config.json"
URLS_FILE = SCRIPT_DIR / "urls.txt"
RUN_STATUS_FILE = SCRIPT_DIR / "run_status.json"
AUTH_USERS_FILE = SCRIPT_DIR / "authenticated_users.json"

# Conversation states
WAITING_PASSWORD = 0

# Store authenticated user IDs
authenticated_users: Set[int] = set()


def load_authenticated_users() -> Set[int]:
    """Load authenticated users from persistent storage."""
    if not AUTH_USERS_FILE.exists():
        return set()

    try:
        with open(AUTH_USERS_FILE, "r") as f:
            data = json.load(f)
            return set(data.get("users", []))
    except (json.JSONDecodeError, IOError):
        return set()


def save_authenticated_users() -> None:
    """Save authenticated users to persistent storage."""
    with open(AUTH_USERS_FILE, "w") as f:
        json.dump({"users": list(authenticated_users)}, f, indent=2)


def add_authenticated_user(user_id: int) -> None:
    """Add a user to authenticated set and persist."""
    authenticated_users.add(user_id)
    save_authenticated_users()


def remove_authenticated_user(user_id: int) -> None:
    """Remove a user from authenticated set and persist."""
    authenticated_users.discard(user_id)
    save_authenticated_users()


def init_authenticated_users() -> None:
    """Initialize authenticated users from persistent storage."""
    global authenticated_users
    authenticated_users = load_authenticated_users()
    logger.info(f"Loaded {len(authenticated_users)} authenticated user(s) from storage")


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
    if not config.get("access_password"):
        raise ValueError("access_password is required in configuration")

    return config


def load_urls() -> list[str]:
    """Load URLs from urls.txt file."""
    if not URLS_FILE.exists():
        return []

    urls = []
    with open(URLS_FILE, "r") as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and comments
            if line and not line.startswith("#"):
                urls.append(line)
    return urls


def save_urls(urls: list[str], preserve_header: bool = True) -> None:
    """Save URLs to urls.txt file, preserving the header comments."""
    header = """# URL Configuration File for Web Page Monitor
# Add one URL per line
# Lines starting with # are comments and will be ignored
# Empty lines are also ignored

# URLs to monitor:
"""

    with open(URLS_FILE, "w") as f:
        if preserve_header:
            f.write(header)
        for url in urls:
            f.write(f"{url}\n")


def is_valid_url(url: str) -> bool:
    """Check if a string is a valid HTTP/HTTPS URL."""
    pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # or IP
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return bool(pattern.match(url))


def is_authenticated(user_id: int) -> bool:
    """Check if a user is authenticated."""
    return user_id in authenticated_users


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /start command - begin authentication."""
    user_id = update.effective_user.id

    if is_authenticated(user_id):
        await update.message.reply_text(
            "You are already authenticated!\n\n"
            "Available commands:\n"
            "/menu - Show interactive menu\n"
            "/list - Show all monitored URLs\n"
            "/add <url> - Add a new URL to monitor\n"
            "/remove <url> - Remove a URL from monitoring\n"
            "/scan - Trigger a manual scan now\n"
            "/subscribe - Get notified when pages change\n"
            "/unsubscribe - Stop receiving notifications\n"
            "/status - Check your subscription status\n"
            "/logs - Show last monitoring run status\n"
            "/help - Show this help message\n"
            "/logout - Log out from the bot"
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "Welcome to the URL Monitor Bot!\n\n"
        "Please enter the access password to authenticate:"
    )
    return WAITING_PASSWORD


async def authenticate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle password authentication."""
    user_id = update.effective_user.id
    password = update.message.text.strip()

    # Delete the password message for security
    try:
        await update.message.delete()
    except Exception:
        pass  # May fail if bot doesn't have delete permission

    config = load_config()

    if password == config["access_password"]:
        add_authenticated_user(user_id)
        logger.info(f"User {user_id} authenticated successfully")
        await update.message.reply_text(
            "Authentication successful!\n\n"
            "Use /menu for an interactive menu, or try:\n"
            "/list - Show all monitored URLs\n"
            "/add <url> - Add a new URL to monitor\n"
            "/remove <url> - Remove a URL from monitoring\n"
            "/scan - Trigger a manual scan now\n"
            "/subscribe - Get notified when pages change\n"
            "/unsubscribe - Stop receiving notifications\n"
            "/status - Check your subscription status\n"
            "/logs - Show last monitoring run status\n"
            "/help - Show this help message\n"
            "/logout - Log out from the bot"
        )
        return ConversationHandler.END
    else:
        logger.warning(f"Failed authentication attempt from user {user_id}")
        await update.message.reply_text(
            "Invalid password. Please try again with /start"
        )
        return ConversationHandler.END


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    user_id = update.effective_user.id

    if not is_authenticated(user_id):
        await update.message.reply_text(
            "You are not authenticated. Please use /start to authenticate."
        )
        return

    await update.message.reply_text(
        "URL Monitor Bot - Help\n\n"
        "Commands:\n"
        "/menu - Show interactive menu\n"
        "/list - Show all monitored URLs\n"
        "/add <url> - Add a new URL to monitor\n"
        "  Example: /add https://example.com\n"
        "/remove <url> - Remove a URL from monitoring\n"
        "  Example: /remove https://example.com\n"
        "/scan - Trigger a manual scan now\n"
        "/subscribe - Get notified when pages change\n"
        "/unsubscribe - Stop receiving notifications\n"
        "/status - Check your subscription status\n"
        "/logs - Show last monitoring run status\n"
        "/help - Show this help message\n"
        "/logout - Log out from the bot\n\n"
        "Note: URLs must start with http:// or https://\n\n"
        "📢 Notifications: When a monitored page changes, subscribers "
        "will receive a screenshot and a link to the page."
    )


async def list_urls(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /list command - show all monitored URLs."""
    user_id = update.effective_user.id

    if not is_authenticated(user_id):
        await update.message.reply_text(
            "You are not authenticated. Please use /start to authenticate."
        )
        return

    urls = load_urls()

    if not urls:
        await update.message.reply_text("No URLs are currently being monitored.")
        return

    message = "Monitored URLs:\n\n"
    for i, url in enumerate(urls, 1):
        message += f"{i}. {url}\n"

    await update.message.reply_text(message)


async def add_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /add command - add a new URL to monitor."""
    user_id = update.effective_user.id

    if not is_authenticated(user_id):
        await update.message.reply_text(
            "You are not authenticated. Please use /start to authenticate."
        )
        return

    if not context.args:
        await update.message.reply_text(
            "Please provide a URL to add.\n"
            "Usage: /add <url>\n"
            "Example: /add https://example.com"
        )
        return

    url = context.args[0].strip()

    if not is_valid_url(url):
        await update.message.reply_text(
            "Invalid URL format. URL must start with http:// or https://\n"
            "Example: /add https://example.com"
        )
        return

    urls = load_urls()

    if url in urls:
        await update.message.reply_text(f"URL is already in the monitoring list:\n{url}")
        return

    urls.append(url)
    save_urls(urls)

    logger.info(f"User {user_id} added URL: {url}")
    await update.message.reply_text(f"URL added successfully:\n{url}")


async def remove_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /remove command - remove a URL from monitoring."""
    user_id = update.effective_user.id

    if not is_authenticated(user_id):
        await update.message.reply_text(
            "You are not authenticated. Please use /start to authenticate."
        )
        return

    if not context.args:
        await update.message.reply_text(
            "Please provide a URL to remove.\n"
            "Usage: /remove <url>\n"
            "Example: /remove https://example.com\n\n"
            "Use /list to see all monitored URLs."
        )
        return

    url = context.args[0].strip()
    urls = load_urls()

    if url not in urls:
        await update.message.reply_text(
            f"URL not found in the monitoring list:\n{url}\n\n"
            "Use /list to see all monitored URLs."
        )
        return

    urls.remove(url)
    save_urls(urls)

    logger.info(f"User {user_id} removed URL: {url}")
    await update.message.reply_text(f"URL removed successfully:\n{url}")


async def logout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /logout command - log out the user."""
    user_id = update.effective_user.id

    if user_id in authenticated_users:
        remove_authenticated_user(user_id)
        logger.info(f"User {user_id} logged out")
        await update.message.reply_text(
            "You have been logged out. Use /start to authenticate again."
        )
    else:
        await update.message.reply_text("You are not currently logged in.")


async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /subscribe command - subscribe to change notifications."""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if not is_authenticated(user_id):
        await update.message.reply_text(
            "You are not authenticated. Please use /start to authenticate."
        )
        return

    if add_subscriber(chat_id):
        logger.info(f"User {user_id} subscribed to notifications (chat_id: {chat_id})")
        await update.message.reply_text(
            "✅ You are now subscribed to change notifications!\n\n"
            "You will receive a message with a screenshot whenever a monitored "
            "page changes.\n\n"
            "Use /unsubscribe to stop receiving notifications."
        )
    else:
        await update.message.reply_text(
            "You are already subscribed to notifications.\n"
            "Use /unsubscribe to stop receiving notifications."
        )


async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /unsubscribe command - unsubscribe from change notifications."""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if not is_authenticated(user_id):
        await update.message.reply_text(
            "You are not authenticated. Please use /start to authenticate."
        )
        return

    if remove_subscriber(chat_id):
        logger.info(f"User {user_id} unsubscribed from notifications (chat_id: {chat_id})")
        await update.message.reply_text(
            "✅ You have been unsubscribed from change notifications.\n\n"
            "Use /subscribe to start receiving notifications again."
        )
    else:
        await update.message.reply_text(
            "You are not currently subscribed to notifications.\n"
            "Use /subscribe to start receiving notifications."
        )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /status command - show subscription status."""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if not is_authenticated(user_id):
        await update.message.reply_text(
            "You are not authenticated. Please use /start to authenticate."
        )
        return

    subscribed = is_subscriber(chat_id)
    subscriber_count = len(load_subscribers())

    status_emoji = "🔔" if subscribed else "🔕"
    status_text = "subscribed" if subscribed else "not subscribed"

    await update.message.reply_text(
        f"📊 *Notification Status*\n\n"
        f"{status_emoji} You are currently *{status_text}* to notifications.\n"
        f"👥 Total subscribers: {subscriber_count}\n\n"
        f"Use /subscribe or /unsubscribe to change your status.",
        parse_mode="Markdown"
    )


def load_run_status() -> dict:
    """Load the latest run status from JSON file."""
    if not RUN_STATUS_FILE.exists():
        return {}

    try:
        with open(RUN_STATUS_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


async def logs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /logs command - show last cronjob run status."""
    user_id = update.effective_user.id

    if not is_authenticated(user_id):
        await update.message.reply_text(
            "You are not authenticated. Please use /start to authenticate."
        )
        return

    run_status = load_run_status()

    if not run_status or "last_run" not in run_status:
        await update.message.reply_text(
            "📋 *Last Run Status*\n\n"
            "No monitoring runs recorded yet.",
            parse_mode="Markdown"
        )
        return

    last_run = run_status["last_run"]

    # Parse timestamps
    start_time = datetime.fromisoformat(last_run["start_time"])
    end_time = datetime.fromisoformat(last_run["end_time"])

    # Format status with emoji
    status = last_run["status"]
    if status == "success":
        status_emoji = "✅"
        status_text = "Success"
    elif status == "completed_with_errors":
        status_emoji = "⚠️"
        status_text = "Completed with errors"
    elif status == "no_urls":
        status_emoji = "📭"
        status_text = "No URLs configured"
    else:
        status_emoji = "❌"
        status_text = f"Error: {status}"

    # Build message
    message = (
        f"📋 *Last Run Status*\n\n"
        f"🕐 *Started:* {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"🏁 *Finished:* {end_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"⏱ *Duration:* {last_run['duration_seconds']:.1f} seconds\n\n"
        f"🌐 *URLs Checked:* {last_run['urls_checked']}\n"
        f"🔄 *Changes Detected:* {last_run['changes_detected']}\n"
        f"❗ *Errors:* {last_run['errors']}\n\n"
        f"{status_emoji} *Status:* {status_text}"
    )

    await update.message.reply_text(message, parse_mode="Markdown")


# Track if a scan is currently running
scan_in_progress = False


async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /scan command - trigger a manual monitoring scan."""
    global scan_in_progress
    user_id = update.effective_user.id

    if not is_authenticated(user_id):
        await update.message.reply_text(
            "You are not authenticated. Please use /start to authenticate."
        )
        return

    if scan_in_progress:
        await update.message.reply_text(
            "⏳ A scan is already in progress. Please wait for it to complete."
        )
        return

    scan_in_progress = True

    await update.message.reply_text(
        "🔍 *Starting manual scan...*\n\n"
        "This may take a few minutes depending on the number of URLs.\n"
        "You will be notified when the scan is complete.",
        parse_mode="Markdown"
    )

    try:
        # Run the web monitor script
        web_monitor_script = SCRIPT_DIR / "web_monitor.py"

        # Run in a subprocess asynchronously
        process = await asyncio.create_subprocess_exec(
            "python3", str(web_monitor_script), "--cron",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(SCRIPT_DIR)
        )

        stdout, stderr = await process.communicate()

        # Load the run status to get results
        run_status = load_run_status()

        if process.returncode == 0 and run_status.get("last_run"):
            last_run = run_status["last_run"]
            result_message = (
                "✅ *Scan completed successfully!*\n\n"
                f"🌐 *URLs Checked:* {last_run['urls_checked']}\n"
                f"🔄 *Changes Detected:* {last_run['changes_detected']}\n"
                f"❗ *Errors:* {last_run['errors']}\n"
                f"⏱ *Duration:* {last_run['duration_seconds']:.1f}s\n\n"
                "Use /logs for more details."
            )
        else:
            error_msg = stderr.decode() if stderr else "Unknown error"
            result_message = (
                f"❌ *Scan failed*\n\n"
                f"Error: {error_msg[:200]}"
            )

        await update.message.reply_text(result_message, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error running scan: {e}")
        await update.message.reply_text(
            f"❌ *Error running scan:*\n{str(e)[:200]}",
            parse_mode="Markdown"
        )
    finally:
        scan_in_progress = False


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /cancel command during conversation."""
    await update.message.reply_text("Authentication cancelled. Use /start to try again.")
    return ConversationHandler.END


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Create the main menu inline keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("📋 List URLs", callback_data="menu_list"),
            InlineKeyboardButton("➕ Add URL", callback_data="menu_add"),
        ],
        [
            InlineKeyboardButton("🔍 Scan Now", callback_data="menu_scan"),
            InlineKeyboardButton("📊 Status", callback_data="menu_status"),
        ],
        [
            InlineKeyboardButton("📜 Last Logs", callback_data="menu_logs"),
            InlineKeyboardButton("🔔 Subscribe", callback_data="menu_subscribe"),
        ],
        [
            InlineKeyboardButton("❓ Help", callback_data="menu_help"),
            InlineKeyboardButton("🚪 Logout", callback_data="menu_logout"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /menu command - show interactive menu."""
    user_id = update.effective_user.id

    if not is_authenticated(user_id):
        await update.message.reply_text(
            "You are not authenticated. Please use /start to authenticate."
        )
        return

    # Check subscription status for personalized menu
    chat_id = update.effective_chat.id
    subscribed = is_subscriber(chat_id)
    sub_status = "🔔 Subscribed" if subscribed else "🔕 Not subscribed"

    await update.message.reply_text(
        f"🤖 *URL Monitor Bot Menu*\n\n"
        f"Current status: {sub_status}\n\n"
        f"Select an option below:",
        reply_markup=get_main_menu_keyboard(),
        parse_mode="Markdown"
    )


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle menu button callbacks."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if not is_authenticated(user_id):
        await query.edit_message_text(
            "Session expired. Please use /start to authenticate again."
        )
        return

    callback_data = query.data

    if callback_data == "menu_list":
        urls = load_urls()
        if not urls:
            message = "📋 *Monitored URLs*\n\nNo URLs are currently being monitored."
        else:
            message = "📋 *Monitored URLs*\n\n"
            for i, url in enumerate(urls, 1):
                message += f"{i}. {url}\n"
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Back to Menu", callback_data="menu_back")
            ]]),
            parse_mode="Markdown"
        )

    elif callback_data == "menu_add":
        await query.edit_message_text(
            "➕ *Add URL*\n\n"
            "To add a URL, use the command:\n"
            "`/add https://example.com`\n\n"
            "Then use /menu to return here.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Back to Menu", callback_data="menu_back")
            ]]),
            parse_mode="Markdown"
        )

    elif callback_data == "menu_scan":
        global scan_in_progress
        if scan_in_progress:
            await query.edit_message_text(
                "⏳ A scan is already in progress. Please wait...",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Back to Menu", callback_data="menu_back")
                ]])
            )
            return

        scan_in_progress = True
        await query.edit_message_text(
            "🔍 *Scanning...*\n\n"
            "Please wait while URLs are being checked.",
            parse_mode="Markdown"
        )

        try:
            web_monitor_script = SCRIPT_DIR / "web_monitor.py"
            process = await asyncio.create_subprocess_exec(
                "python3", str(web_monitor_script), "--cron",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(SCRIPT_DIR)
            )
            await process.communicate()
            run_status = load_run_status()

            if run_status.get("last_run"):
                last_run = run_status["last_run"]
                result_message = (
                    "✅ *Scan Complete!*\n\n"
                    f"🌐 URLs Checked: {last_run['urls_checked']}\n"
                    f"🔄 Changes: {last_run['changes_detected']}\n"
                    f"❗ Errors: {last_run['errors']}\n"
                    f"⏱ Duration: {last_run['duration_seconds']:.1f}s"
                )
            else:
                result_message = "✅ Scan completed."

            await query.edit_message_text(
                result_message,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Back to Menu", callback_data="menu_back")
                ]]),
                parse_mode="Markdown"
            )
        except Exception as e:
            await query.edit_message_text(
                f"❌ Scan error: {str(e)[:100]}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Back to Menu", callback_data="menu_back")
                ]])
            )
        finally:
            scan_in_progress = False

    elif callback_data == "menu_status":
        subscribed = is_subscriber(chat_id)
        subscriber_count = len(load_subscribers())
        status_emoji = "🔔" if subscribed else "🔕"
        status_text = "subscribed" if subscribed else "not subscribed"

        await query.edit_message_text(
            f"📊 *Status*\n\n"
            f"{status_emoji} You are currently *{status_text}*\n"
            f"👥 Total subscribers: {subscriber_count}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Back to Menu", callback_data="menu_back")
            ]]),
            parse_mode="Markdown"
        )

    elif callback_data == "menu_logs":
        run_status = load_run_status()
        if not run_status or "last_run" not in run_status:
            message = "📜 *Last Run*\n\nNo monitoring runs recorded yet."
        else:
            last_run = run_status["last_run"]
            start_time = datetime.fromisoformat(last_run["start_time"])
            status = last_run["status"]
            status_emoji = "✅" if status == "success" else "⚠️" if status == "completed_with_errors" else "❌"

            message = (
                f"📜 *Last Run*\n\n"
                f"🕐 {start_time.strftime('%Y-%m-%d %H:%M')}\n"
                f"🌐 URLs: {last_run['urls_checked']}\n"
                f"🔄 Changes: {last_run['changes_detected']}\n"
                f"❗ Errors: {last_run['errors']}\n"
                f"{status_emoji} Status: {status}"
            )

        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Back to Menu", callback_data="menu_back")
            ]]),
            parse_mode="Markdown"
        )

    elif callback_data == "menu_subscribe":
        if is_subscriber(chat_id):
            remove_subscriber(chat_id)
            await query.edit_message_text(
                "🔕 *Unsubscribed*\n\n"
                "You will no longer receive change notifications.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Back to Menu", callback_data="menu_back")
                ]]),
                parse_mode="Markdown"
            )
        else:
            add_subscriber(chat_id)
            await query.edit_message_text(
                "🔔 *Subscribed!*\n\n"
                "You will receive notifications when pages change.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Back to Menu", callback_data="menu_back")
                ]]),
                parse_mode="Markdown"
            )

    elif callback_data == "menu_help":
        await query.edit_message_text(
            "❓ *Help*\n\n"
            "This bot monitors web pages for changes.\n\n"
            "*Commands:*\n"
            "/menu - Show this menu\n"
            "/list - Show monitored URLs\n"
            "/add <url> - Add a URL\n"
            "/remove <url> - Remove a URL\n"
            "/scan - Trigger manual scan\n"
            "/logs - Show last run details\n"
            "/status - Check subscription\n"
            "/help - Show all commands",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Back to Menu", callback_data="menu_back")
            ]]),
            parse_mode="Markdown"
        )

    elif callback_data == "menu_logout":
        if user_id in authenticated_users:
            remove_authenticated_user(user_id)
        await query.edit_message_text(
            "🚪 *Logged Out*\n\n"
            "Use /start to authenticate again."
        , parse_mode="Markdown")

    elif callback_data == "menu_back":
        subscribed = is_subscriber(chat_id)
        sub_status = "🔔 Subscribed" if subscribed else "🔕 Not subscribed"
        await query.edit_message_text(
            f"🤖 *URL Monitor Bot Menu*\n\n"
            f"Current status: {sub_status}\n\n"
            f"Select an option below:",
            reply_markup=get_main_menu_keyboard(),
            parse_mode="Markdown"
        )


def main() -> None:
    """Start the bot."""
    # Load configuration
    try:
        config = load_config()
    except (FileNotFoundError, ValueError) as e:
        logger.error(f"Configuration error: {e}")
        print(f"Error: {e}")
        return

    # Load authenticated users from persistent storage
    init_authenticated_users()

    # Create the Application
    application = Application.builder().token(config["bot_token"]).build()

    # Add conversation handler for authentication
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            WAITING_PASSWORD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, authenticate)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Add handlers
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("menu", menu))
    application.add_handler(CommandHandler("list", list_urls))
    application.add_handler(CommandHandler("add", add_url))
    application.add_handler(CommandHandler("remove", remove_url))
    application.add_handler(CommandHandler("subscribe", subscribe))
    application.add_handler(CommandHandler("unsubscribe", unsubscribe))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("logs", logs))
    application.add_handler(CommandHandler("scan", scan))
    application.add_handler(CommandHandler("logout", logout))
    application.add_handler(CallbackQueryHandler(menu_callback, pattern="^menu_"))

    # Start the bot
    logger.info("Starting URL Monitor Telegram Bot...")
    print("Bot is running. Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
