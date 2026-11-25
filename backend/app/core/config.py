import os
from typing import List, Union
from pydantic_settings import BaseSettings
from pydantic import field_validator
from pathlib import Path
from dotenv import load_dotenv

# Load .env from root or backend directory
env_path = Path(__file__).resolve().parent.parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()


class Settings(BaseSettings):
    PROJECT_NAME: str = "ONECOUNTRY FITNESS"
    VERSION: str = "2.0.0"
    API_V1_STR: str = "/api"

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+pg8000://postgres:postgres@localhost:5433/gym_db",
    )

    JWT_SECRET_KEY: str = os.getenv(
        "JWT_SECRET_KEY", "supersecretjwtkeyforgymtrainerv1appdevelopmentonly"
    )
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    ADMIN_RECOVERY_KEY: Union[str, None] = os.getenv("ADMIN_RECOVERY_KEY", None)

    CORS_ORIGINS: Union[List[str], str] = os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"
    )

    @field_validator("CORS_ORIGINS", mode="after")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    UPLOAD_DIR: str = os.getenv(
        "UPLOAD_DIR",
        str(Path(__file__).resolve().parent.parent.parent / "uploads"),
    )
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10"))

    # Where photos are kept: "local" (UPLOAD_DIR on disk) or "s3" (any S3-compatible bucket,
    # e.g. Cloudflare R2 or AWS S3). Use "s3" on hosts whose disk is wiped on redeploy (Render).
    STORAGE_BACKEND: str = os.getenv("STORAGE_BACKEND", "local").strip().lower()
    S3_BUCKET: str = os.getenv("S3_BUCKET", "")
    # R2: https://<account_id>.r2.cloudflarestorage.com  ·  AWS S3: leave empty
    S3_ENDPOINT_URL: str = os.getenv("S3_ENDPOINT_URL", "")
    S3_REGION: str = os.getenv("S3_REGION", "auto")
    S3_ACCESS_KEY_ID: str = os.getenv("S3_ACCESS_KEY_ID", "")
    S3_SECRET_ACCESS_KEY: str = os.getenv("S3_SECRET_ACCESS_KEY", "")
    TIMEZONE: str = os.getenv("TIMEZONE", "Asia/Kolkata")

    # Billing defaults
    DEFAULT_CURRENCY: str = os.getenv("DEFAULT_CURRENCY", "INR")
    # Country calling code prepended to 10-digit local numbers for WhatsApp links
    DEFAULT_PHONE_COUNTRY_CODE: str = os.getenv("DEFAULT_PHONE_COUNTRY_CODE", "91")

    # Background scheduler: generates dues and raises absence/fee alerts.
    SCHEDULER_ENABLED: bool = os.getenv("SCHEDULER_ENABLED", "true").lower() in ("1", "true", "yes")
    SCHEDULER_INTERVAL_MINUTES: int = int(os.getenv("SCHEDULER_INTERVAL_MINUTES", "60"))

    # Set to false once your trainer account exists, so nobody else can sign up
    ALLOW_TRAINER_REGISTRATION: bool = os.getenv("ALLOW_TRAINER_REGISTRATION", "true").lower() in ("1", "true", "yes")

    model_config = {"case_sensitive": True}

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"


INSECURE_JWT_SECRETS = {
    "supersecretjwtkeyforgymtrainerv1appdevelopmentonly",
    "generate_and_replace_with_a_64_char_hex_secret_key_in_production",
}


def validate_production_settings(s: "Settings") -> None:
    """Refuse to boot a production deployment with unsafe configuration."""
    if not s.is_production:
        return
    problems = []
    if s.JWT_SECRET_KEY in INSECURE_JWT_SECRETS or len(s.JWT_SECRET_KEY) < 32:
        problems.append("JWT_SECRET_KEY must be a unique random value of at least 32 characters")
    if s.DATABASE_URL.startswith("sqlite"):
        problems.append("DATABASE_URL must point to PostgreSQL in production")
    if s.STORAGE_BACKEND not in ("local", "s3"):
        problems.append("STORAGE_BACKEND must be 'local' or 's3'")
    if s.STORAGE_BACKEND == "s3":
        missing = [
            name
            for name in ("S3_BUCKET", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY")
            if not getattr(s, name)
        ]
        if missing:
            problems.append("STORAGE_BACKEND=s3 needs " + ", ".join(missing))
    if problems:
        raise RuntimeError("Unsafe production configuration: " + "; ".join(problems))


settings = Settings()
