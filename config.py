import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration shared by all environments."""

    # ── Flask ──────────────────────────────────────────────
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")

    # ── Database ───────────────────────────────────────────
    DB_HOST: str     = os.getenv("DB_HOST", "localhost")
    DB_PORT: int     = int(os.getenv("DB_PORT", 3307))
    DB_USER: str     = os.getenv("DB_USER", "root")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_NAME: str     = os.getenv("DB_NAME", "election_db")

    # ── Mail (OTP) ─────────────────────────────────────────
    MAIL_SERVER: str    = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT: int      = int(os.getenv("MAIL_PORT", 587))
    MAIL_USE_TLS: bool  = os.getenv("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USERNAME: str  = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD: str  = os.getenv("MAIL_PASSWORD", "")

    # ── Session ────────────────────────────────────────────
    SESSION_COOKIE_HTTPONLY: bool  = True
    SESSION_COOKIE_SAMESITE: str   = "Lax"

    # ── WTF (CSRF) ─────────────────────────────────────────
    WTF_CSRF_ENABLED: bool = True

    @classmethod
    def get_db_config(cls) -> dict:
        """Return dict ที่ส่งเข้า mysql.connector.connect() ได้โดยตรง."""
        return {
            "host":     cls.DB_HOST,
            "port":     cls.DB_PORT,
            "user":     cls.DB_USER,
            "password": cls.DB_PASSWORD,
            "database": cls.DB_NAME,
            "charset":  "utf8mb4",
            "collation": "utf8mb4_unicode_ci",
        }


class DevelopmentConfig(Config):
    DEBUG: bool = True
    SESSION_COOKIE_SECURE: bool = False   # HTTP ได้ใน dev


class ProductionConfig(Config):
    DEBUG: bool = False
    SESSION_COOKIE_SECURE: bool = True    # HTTPS only
    WTF_CSRF_ENABLED: bool = True


# ── เลือก config ตาม FLASK_ENV ─────────────────────────────
_config_map = {
    "development": DevelopmentConfig,
    "production":  ProductionConfig,
}

ActiveConfig = _config_map.get(os.getenv("FLASK_ENV", "development"), DevelopmentConfig)
