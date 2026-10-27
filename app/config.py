import os

from dotenv import load_dotenv

load_dotenv()


def _env(nombre: str, default: str = "") -> str:
    # Si la variable existe pero está vacía (.env.example), usamos el default.
    return os.getenv(nombre) or default


def whatsapp_token() -> str:
    return _env("WHATSAPP_TOKEN")


def whatsapp_phone_number_id() -> str:
    return _env("WHATSAPP_PHONE_NUMBER_ID")


def whatsapp_verify_token() -> str:
    return _env("WHATSAPP_VERIFY_TOKEN")


def graph_api_version() -> str:
    return _env("GRAPH_API_VERSION", "v21.0")


def gemini_api_key() -> str:
    return _env("GEMINI_API_KEY")


def gemini_model() -> str:
    return _env("GEMINI_MODEL", "gemini-2.5-flash")


def sheets_webapp_url() -> str:
    return _env("SHEETS_WEBAPP_URL")


def sheets_secret() -> str:
    return _env("SHEETS_SECRET")
