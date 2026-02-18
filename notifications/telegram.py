"""
Telegram notification module for sending alerts with photos.
"""
import time
import requests
from pathlib import Path
from typing import Optional
from datetime import datetime

from core.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


class TelegramNotifier:
    """
    Telegram Bot notification sender.
    """

    def __init__(self, bot_token: str = TELEGRAM_BOT_TOKEN, chat_id: str = TELEGRAM_CHAT_ID):
        """
        Initialize Telegram notifier.

        Args:
            bot_token: Telegram Bot API token
            chat_id: Telegram chat ID to send messages to
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_base = f"https://api.telegram.org/bot{bot_token}"

        # Validate configuration
        if not bot_token or bot_token == "your_bot_token_here":
            print("Warning: Telegram bot token not configured")
            self.enabled = False
        elif not chat_id or chat_id == "your_chat_id_here":
            print("Warning: Telegram chat ID not configured")
            self.enabled = False
        else:
            self.enabled = True
            print(f"Telegram notifier initialized (chat_id: {chat_id})")

    def _retry_request(
        self,
        method: str,
        url: str,
        max_retries: int = 3,
        **kwargs
    ) -> Optional[requests.Response]:
        """
        Make an HTTP request with exponential backoff retry.

        Args:
            method: HTTP method (get, post, etc.)
            url: Request URL
            max_retries: Maximum number of retry attempts
            **kwargs: Additional arguments for requests

        Returns:
            Response object or None if all retries failed
        """
        for attempt in range(max_retries):
            try:
                if method.lower() == 'get':
                    response = requests.get(url, timeout=10, **kwargs)
                elif method.lower() == 'post':
                    response = requests.post(url, timeout=10, **kwargs)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                # Check if request was successful
                if response.status_code == 200:
                    return response
                else:
                    print(f"Telegram API error: {response.status_code} - {response.text}")

            except requests.exceptions.RequestException as e:
                print(f"Network error (attempt {attempt + 1}/{max_retries}): {e}")

            # Exponential backoff
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 1s, 2s, 4s
                print(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)

        return None

    def send_message(self, text: str) -> bool:
        """
        Send a text message.

        Args:
            text: Message text

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            print(f"Telegram disabled. Would send: {text}")
            return False

        url = f"{self.api_base}/sendMessage"
        data = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML"
        }

        response = self._retry_request('post', url, data=data)

        if response:
            print(f"Telegram message sent: {text[:50]}...")
            return True
        else:
            print(f"Failed to send Telegram message after retries")
            return False

    def send_photo(
        self,
        photo_path: Path | str,
        caption: Optional[str] = None
    ) -> bool:
        """
        Send a photo.

        Args:
            photo_path: Path to the photo file
            caption: Optional caption for the photo

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            print(f"Telegram disabled. Would send photo: {photo_path}")
            return False

        photo_path = Path(photo_path)

        if not photo_path.exists():
            print(f"Photo not found: {photo_path}")
            return False

        url = f"{self.api_base}/sendPhoto"
        data = {"chat_id": self.chat_id}

        if caption:
            data["caption"] = caption
            data["parse_mode"] = "HTML"

        try:
            with open(photo_path, 'rb') as photo_file:
                files = {"photo": photo_file}
                response = self._retry_request('post', url, data=data, files=files)

            if response:
                print(f"Telegram photo sent: {photo_path.name}")
                return True
            else:
                print(f"Failed to send Telegram photo after retries")
                return False

        except Exception as e:
            print(f"Error sending photo: {e}")
            return False

    def send_alert(
        self,
        chat_id: Optional[str],
        photo_path: Path | str,
        message: str
    ) -> bool:
        """
        Send an alert with a photo (convenience method matching the development plan).

        Args:
            chat_id: Chat ID (uses instance chat_id if None)
            photo_path: Path to the photo file
            message: Alert message

        Returns:
            True if sent successfully, False otherwise
        """
        if chat_id and chat_id != self.chat_id:
            # Temporarily override chat_id
            original_chat_id = self.chat_id
            self.chat_id = chat_id
            result = self.send_photo(photo_path, caption=message)
            self.chat_id = original_chat_id
            return result
        else:
            return self.send_photo(photo_path, caption=message)

    def test_connection(self) -> bool:
        """
        Test the Telegram bot connection.

        Returns:
            True if connection is working, False otherwise
        """
        if not self.enabled:
            print("Telegram not enabled")
            return False

        url = f"{self.api_base}/getMe"
        response = self._retry_request('get', url)

        if response:
            data = response.json()
            if data.get('ok'):
                bot_info = data.get('result', {})
                print(f"✓ Connected to Telegram bot: @{bot_info.get('username')}")
                return True

        print("✗ Failed to connect to Telegram bot")
        return False


# Global notifier instance (singleton pattern)
_notifier_instance: Optional[TelegramNotifier] = None


def get_notifier() -> TelegramNotifier:
    """
    Get the global Telegram notifier instance.

    Returns:
        TelegramNotifier instance
    """
    global _notifier_instance
    if _notifier_instance is None:
        _notifier_instance = TelegramNotifier()
    return _notifier_instance


def send_unknown_visitor_alert(photo_path: Path | str, confidence: float) -> bool:
    """
    Send an unknown visitor alert (convenience function).

    Args:
        photo_path: Path to the visitor's photo
        confidence: Recognition confidence score

    Returns:
        True if sent successfully, False otherwise
    """
    notifier = get_notifier()

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = (
        f"⚠️ <b>Unknown Visitor Detected</b>\n\n"
        f"Time: {timestamp}\n"
        f"Confidence: {confidence:.2f}\n"
    )

    return notifier.send_photo(photo_path, caption=message)
