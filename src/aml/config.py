from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://aml:aml_dev_pass@localhost:5433/aml"
    redis_url: str = "redis://localhost:6380"
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    rules_cache_ttl: int = 3600  # 1 hour
    extraction_min_episodes: int = 10
    confidence_decay_monthly: float = 0.05
    confidence_deactivate_threshold: float = 0.1
    control_group_pct: int = 10  # A/B: % requests without rules

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
