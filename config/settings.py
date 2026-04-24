from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://sentinel:sentinel@localhost:5432/sentinel"
    database_url_sync: str = "postgresql://sentinel:sentinel@localhost:5432/sentinel"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Auth — GitHub
    github_client_id: str = ""
    github_client_secret: str = ""

    # Auth — Google
    google_client_id: str = ""
    google_client_secret: str = ""

    # JWT
    jwt_secret_key: str = "change-this-to-a-random-64-char-string"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # LLM
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # LangSmith
    langchain_tracing_v2: bool = True
    langchain_api_key: str = ""
    langchain_project: str = "docker-sentinel"

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333

    # Notifications — Platform Defaults
    slack_webhook_url: str = ""
    sendgrid_api_key: str = ""
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""

    # App
    app_url: str = "http://localhost:3000"
    api_url: str = "http://localhost:8000"
    environment: str = "development"
    log_sql: bool = False

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
