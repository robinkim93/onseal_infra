"""환경설정 — pydantic-settings 로 .env 로드. [delegate 스캐폴딩]"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    postgres_user: str = "onseal"
    postgres_password: str = "change-me"
    postgres_db: str = "onseal"
    postgres_host: str = "db"
    postgres_port: int = 5432

    ollama_host: str = "http://ollama:11434"
    ollama_model: str = "qwen2.5:3b"

    embedding_model: str = "BAAI/bge-m3"
    embedding_dim: int = 1024

    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
