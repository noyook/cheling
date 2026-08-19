"""Unified configuration loader from .env"""
import os
from dotenv import load_dotenv

# Load .env from project root (packages/waybill_sync/core/ -> 仓库根)
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(_SCRIPT_DIR)))
_ENV_PATH = os.path.join(PROJECT_DIR, ".env")
load_dotenv(_ENV_PATH)

# Directories
LOG_DIR = os.path.join(PROJECT_DIR, "logs")
DATA_DIR = os.path.join(PROJECT_DIR, "data")
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)


def get(key: str, default=None, type_fn=str):
    """Get config value by key with optional type conversion."""
    value = os.getenv(key, default)
    if value is None:
        return default
    try:
        return type_fn(value)
    except (ValueError, TypeError):
        return default


# Waybill API
API_BASE = get("WAYBILL_API_BASE", "https://183.95.190.189:8681")
USERNAME = get("WAYBILL_USERNAME", "13971673595")
PASSWORD = get("WAYBILL_PASSWORD", "")
TOKEN_BUFFER_SECONDS = get("TOKEN_BUFFER_SECONDS", 300, int)

# WeCom
WECOM_CORP_ID = get("WECOM_CORP_ID", "")
WECOM_CORP_SECRET = get("WECOM_CORP_SECRET", "")
WECOM_AGENT_ID = get("WECOM_AGENT_ID", "1000033")

# SmartSheet
SMARTSHEET_SHEET_ID = get("SMARTSHEET_SHEET_ID", "tWSwK1")
DTJK_DOCID = get("DTJK_DOCID", "")

__all__ = [
    "get", "PROJECT_DIR", "LOG_DIR", "DATA_DIR",
    "API_BASE", "USERNAME", "PASSWORD", "TOKEN_BUFFER_SECONDS",
    "WECOM_CORP_ID", "WECOM_CORP_SECRET", "WECOM_AGENT_ID",
    "SMARTSHEET_SHEET_ID", "DTJK_DOCID",
]
