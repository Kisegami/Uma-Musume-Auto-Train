"""
Discord Webhook Utility for UMAT
Sends run completion notifications to Discord via webhook.
"""

import io
import os
import json
import requests
from datetime import datetime
from typing import Optional
from PIL import Image

from utils.core.log import log_info, log_warning, log_error
from utils.core.config_loader import load_main_config


def get_webhook_config() -> dict:
    """Load Discord webhook configuration from config.json"""
    try:
        config = load_main_config()
        return config.get('discord_webhook', {})
    except Exception as e:
        log_error(f"Error loading webhook config: {e}")
        return {}


def is_webhook_enabled() -> bool:
    """Check if Discord webhook is enabled"""
    config = get_webhook_config()
    return config.get('enabled', False) and bool(config.get('webhook_url', ''))


def send_run_complete_webhook(
    run_number: int,
    max_runs: int,
    fans_this_run: int,
    session_total: int,
    today_total: int = 0,
    average_per_run: int = 0,
    screenshot: Optional[Image.Image] = None
) -> bool:
    """
    Send a run completion notification to Discord webhook.
    
    Args:
        run_number: Current run number (1-indexed)
        max_runs: Maximum number of runs configured
        fans_this_run: Fans acquired in this run
        session_total: Total fans in current session
        today_total: Total fans today (optional, defaults to session_total)
        average_per_run: Average fans per run (optional, auto-calculated)
        screenshot: PIL Image to attach (optional)
    
    Returns:
        bool: True if webhook sent successfully, False otherwise
    """
    config = get_webhook_config()
    webhook_url = config.get('webhook_url', '')
    
    if not webhook_url:
        log_warning("Discord webhook URL not configured")
        return False
    
    if not config.get('enabled', False):
        log_info("Discord webhook is disabled")
        return False
    
    if not config.get('notify_on_run_complete', True):
        log_info("Run complete notifications disabled")
        return False
    
    # Calculate defaults if not provided
    if today_total == 0:
        today_total = session_total
    if average_per_run == 0 and run_number > 0:
        average_per_run = session_total // run_number
    
    # Current timestamp
    now = datetime.now()
    timestamp = now.strftime("%I:%M %p")
    
    # Build embed
    embed = {
        "title": f"ðŸŽ‰ Run {run_number}/{max_runs} Complete!",
        "description": "Uma Musume training run finished.",
        "color": 0x2ECC71,  # Green color
        "fields": [
            {
                "name": "ðŸ‘ Fans This Run",
                "value": f"**{fans_this_run:,}**",
                "inline": True
            },
            {
                "name": "ðŸ  Session Total",
                "value": f"**{session_total:,}**",
                "inline": True
            },
            {
                "name": "ðŸ“Š Progress",
                "value": f"**{run_number}/{max_runs}** runs",
                "inline": True
            },
            {
                "name": "ðŸ“… Today Total",
                "value": f"**{today_total:,}**",
                "inline": True
            },
            {
                "name": "ðŸ“ˆ Average/Run",
                "value": f"**{average_per_run:,}**",
                "inline": True
            }
        ],
        "footer": {
            "text": f"UMAT - Uma Musume Auto Train • Today at {timestamp}"
        },
        "timestamp": now.isoformat()
    }
    
    payload = {
        "embeds": [embed]
    }
    
    try:
        # Prepare files for multipart upload if screenshot provided
        if screenshot is not None:
            # Convert PIL Image to bytes
            img_byte_arr = io.BytesIO()
            screenshot.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            
            # Add image to embed
            embed["image"] = {"url": "attachment://screenshot.png"}
            
            # Send with file attachment
            files = {
                'file': ('screenshot.png', img_byte_arr, 'image/png')
            }
            
            response = requests.post(
                webhook_url,
                data={'payload_json': json.dumps(payload)},
                files=files,
                timeout=30
            )
        else:
            # Send without attachment
            response = requests.post(
                webhook_url,
                json=payload,
                timeout=30
            )
        
        if response.status_code in [200, 204]:
            log_info(f"✓ Discord webhook sent successfully for run {run_number}/{max_runs}")
            return True
        else:
            log_warning(f"Discord webhook failed with status {response.status_code}: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        log_warning("Discord webhook timed out")
        return False
    except requests.exceptions.RequestException as e:
        log_error(f"Discord webhook error: {e}")
        return False


def send_test_webhook(webhook_url: str, screenshot: Optional[Image.Image] = None) -> tuple[bool, str]:
    """
    Send a test message to verify webhook URL.
    
    Args:
        webhook_url: Discord webhook URL to test
        screenshot: Optional PIL Image to attach
    
    Returns:
        tuple: (success: bool, message: str)
    """
    if not webhook_url:
        return False, "Webhook URL is empty"
    
    if not webhook_url.startswith("https://discord.com/api/webhooks/"):
        return False, "Invalid webhook URL format"
    
    now = datetime.now()
    timestamp = now.strftime("%I:%M %p")
    
    embed = {
        "title": "ðŸ”” UMAT Webhook Test",
        "description": "This is a test message from Uma Musume Auto Train.",
        "color": 0x3498DB,  # Blue color
        "fields": [
            {
                "name": "Status",
                "value": "✅ Webhook is working!",
                "inline": False
            }
        ],
        "footer": {
            "text": f"UMAT - Uma Musume Auto Train • {timestamp}"
        },
        "timestamp": now.isoformat()
    }
    
    payload = {
        "embeds": [embed]
    }
    
    try:
        # Prepare files for multipart upload if screenshot provided
        if screenshot is not None:
            # Convert PIL Image to bytes
            img_byte_arr = io.BytesIO()
            screenshot.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            
            # Add image to embed
            embed["image"] = {"url": "attachment://test_capture.png"}
            
            files = {
                'file': ('test_capture.png', img_byte_arr, 'image/png')
            }
            
            response = requests.post(
                webhook_url,
                data={'payload_json': json.dumps(payload)},
                files=files,
                timeout=10
            )
        else:
            response = requests.post(
                webhook_url,
                json=payload,
                timeout=10
            )
        
        if response.status_code in [200, 204]:
            return True, "Webhook test successful!"
        elif response.status_code == 401:
            return False, "Invalid webhook token"
        elif response.status_code == 404:
            return False, "Webhook not found (may be deleted)"
        else:
            return False, f"Failed with status {response.status_code}"
            
    except requests.exceptions.Timeout:
        return False, "Request timed out"
    except requests.exceptions.RequestException as e:
        return False, f"Request error: {str(e)}"
