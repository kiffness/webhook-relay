from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Application configuration loaded from environment variables or a .env file.
    All sensitive values (secrets, tokens) must be set via environment variables
    and should never be hardcoded.
    """

    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

    # GitHub webhook secret - set this in your GitHub repo's webhook settings
    github_webhook_secret: str = ""

    # Slack incoming webhook URL - create one at api.slack.com/apps
    slack_webhook_url: str = ""

    # Number of retry attempts when forwarding to downstream services
    forward_retry_attempts: int = 3

    # Seconds to wait before first retry (doubles on each subsequent attempt)
    forward_retry_backoff: float = 1.0

    # Log level: DEBUG, INFO, WARNING, ERROR
    log_level: str = "INFO"

settings = Settings()