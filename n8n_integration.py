# -*- coding: utf-8 -*-
"""
Helper for sending messages via n8n webhook.
Environment variables required:
    N8N_WEBHOOK_URL - The full webhook URL to POST to.
    N8N_API_KEY     - (Optional) API key for authentication, sent as Bearer token.
"""

import os
import json

try:
    import requests
except ImportError:
    requests = None

import urllib.request


def send_message_via_n8n(phone: str, message: str) -> None:
    """Send a message through n8n.

    Args:
        phone: Destination phone number (string).
        message: Message body.
    Raises:
        RuntimeError: If required environment variables are missing.
        urllib.error.HTTPError / URLError: If the HTTP request fails.
    """
    webhook_url = os.getenv("N8N_WEBHOOK_URL")
    if not webhook_url:
        raise RuntimeError("N8N_WEBHOOK_URL environment variable not set.")

    api_key = os.getenv("N8N_API_KEY")
    payload = json.dumps({"phone": phone, "message": message}).encode("utf-8")

    # Prefer requests if available; otherwise fall back to Python's stdlib urllib.
    if requests is not None:
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        response = requests.post(webhook_url, headers=headers, data=payload, timeout=10)
        response.raise_for_status()
        return

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    req = urllib.request.Request(webhook_url, data=payload, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=10) as resp:
        resp.read()  # read+close the response body
    return
