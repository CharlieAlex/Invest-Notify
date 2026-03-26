from __future__ import annotations

import logging
from pathlib import Path

import requests

from invest_notify.settings import LineSettings

LOGGER = logging.getLogger(__name__)


class LineNotifier:
    def __init__(self, settings: LineSettings):
        self.settings = settings
        self.push_url = "https://api.line.me/v2/bot/message/push"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.settings.access_token}",
        }

    def notify(self, text: str, image_path: Path | None = None) -> bool:
        messages = []

        # Add text message
        messages.append({"type": "text", "text": text})

        # Add image message if image_path is provided
        if image_path and image_path.exists():
            image_url = self._upload_image(image_path)
            if image_url:
                messages.append(
                    {
                        "type": "image",
                        "originalContentUrl": image_url,
                        "previewImageUrl": image_url,
                    }
                )
            else:
                LOGGER.warning("Image upload failed, only text will be sent.")

        payload = {
            "to": self.settings.user_id,
            "messages": messages,
        }

        try:
            response = requests.post(self.push_url, headers=self.headers, json=payload, timeout=15)
            response.raise_for_status()
            LOGGER.info("Line notification sent successfully.")
            return True
        except requests.RequestException as exc:
            LOGGER.error("Failed to send Line notification: %s", exc)
            if hasattr(exc, "response") and exc.response is not None:
                LOGGER.error("Response body: %s", exc.response.text)
            return False

    def _upload_image(self, image_path: Path) -> str | None:
        """Upload image to a public hosting service (catbox.moe) to get an HTTPS URL."""
        try:
            # catbox.moe API: POST to https://catbox.moe/user/api.php
            # reqtype=fileupload, fileToUpload=@file
            url = "https://catbox.moe/user/api.php"
            with open(image_path, "rb") as f:
                data = {"reqtype": "fileupload"}
                files = {"fileToUpload": f}
                response = requests.post(url, data=data, files=files, timeout=30)

                if response.status_code == 200:
                    image_url = response.text.strip()
                    if image_url.startswith("https://"):
                        return image_url
                    else:
                        LOGGER.warning("catbox.moe returned an invalid URL: %s", image_url)
                else:
                    LOGGER.warning(
                        "catbox.moe upload failed (status=%d): %s",
                        response.status_code,
                        response.text,
                    )
        except Exception as exc:
            LOGGER.warning("Failed to upload image to catbox.moe: %s", exc)
        return None


def get_latest_table_text(table_dir: Path) -> str:
    """Read the latest section from the latest month's markdown file."""
    files = sorted(table_dir.glob("*.md"))
    if not files:
        return "No table files found."

    latest_file = files[-1]
    try:
        content = latest_file.read_text(encoding="utf-8")
        sections = content.split("## ")
        if len(sections) < 2:
            return content.strip()

        # The last section is the most recent
        latest_section = "## " + sections[-1].strip()
        return latest_section
    except Exception as exc:
        LOGGER.warning("Error reading table file %s: %s", latest_file, exc)
        return f"Error reading table: {exc}"
