from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    embedding_model: str = Field(default="text-embedding-3-small", alias="EMBEDDING_MODEL")
    chunk_size: int = Field(default=500, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(default=50, alias="CHUNK_OVERLAP")
    top_k: int = Field(default=5, alias="TOP_K")
    upload_dir: str = Field(default="data", alias="UPLOAD_DIR")
    chroma_dir: str = Field(default=".chroma", alias="CHROMA_DIR")
    chroma_collection: str = Field(default="documents", alias="CHROMA_COLLECTION")
    max_upload_size_mb: int = Field(default=5, alias="MAX_UPLOAD_SIZE_MB")

    @property
    def upload_path(self) -> Path:
        return Path(self.upload_dir)

    @property
    def chroma_path(self) -> Path:
        return Path(self.chroma_dir)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
