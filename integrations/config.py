"""Load shared environment variables. All secrets come from the process environment (e.g. .env)."""
import os
from dotenv import load_dotenv

load_dotenv()


def _req(name: str) -> str:
    v = os.getenv(name, "").strip()
    if not v:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return v


def catapult_token() -> str:
    return _req("CATAPULT_TOKEN")


def catapult_base_url() -> str:
    return os.getenv(
        "CATAPULT_BASE_URL", "https://connect-au.catapultsports.com/api/v6"
    ).rstrip("/")


def gymaware_token() -> str:
    """API token (used as HTTP Basic password). See GymAware Cloud Settings > Tokens."""
    return _req("GYMAWARE_TOKEN")


def gymaware_account_id() -> str:
    """Account ID (used as HTTP Basic username). Same Cloud > Settings > Tokens page."""
    return _req("GYMAWARE_ACCOUNT_ID")


def database_url() -> str | None:
    u = os.getenv("DATABASE_URL", "").strip()
    return u or None


# --- Placeholders: wire when tokens and API docs are available ---


def whoop_config() -> dict:
    """Return Whoop OAuth / API settings when WHOOP_* vars are set."""
    return {
        "refresh_token": os.getenv("WHOOP_REFRESH_TOKEN", ""),
        "client_id": os.getenv("WHOOP_CLIENT_ID", ""),
        "client_secret": os.getenv("WHOOP_CLIENT_SECRET", ""),
    }


def vald_config() -> dict:
    """Minimal VALD OAuth identifiers (see also vald_settings)."""
    return {
        "client_id": os.getenv("VALD_CLIENT_ID", ""),
        "client_secret": os.getenv("VALD_CLIENT_SECRET", ""),
    }


def vald_settings() -> dict[str, str]:
    """
    VALD OAuth + regional API bases.

    Defaults target Australia (East) — override for USE/EUW via env or VALD_REGION in docs.
    """
    return {
        "client_id": os.getenv("VALD_CLIENT_ID", "").strip(),
        "client_secret": os.getenv("VALD_CLIENT_SECRET", "").strip(),
        "oauth_token_url": os.getenv(
            "VALD_OAUTH_TOKEN_URL",
            "https://auth.prd.vald.com/oauth/token",
        ).strip(),
        "oauth_audience": os.getenv("VALD_OAUTH_AUDIENCE", "vald-api-external").strip(),
        "api_base_tenants": os.getenv(
            "VALD_API_BASE_TENANTS",
            "https://prd-aue-api-externaltenants.valdperformance.com",
        ).strip(),
        "api_base_profile": os.getenv(
            "VALD_API_BASE_PROFILE",
            "https://prd-aue-api-externalprofile.valdperformance.com",
        ).strip(),
    }


def teamworks_ams_config() -> dict:
    return {
        "base_url": os.getenv("TEAMWORKS_AMS_BASE_URL", "").rstrip("/"),
        "token": os.getenv("TEAMWORKS_AMS_TOKEN", ""),
    }
