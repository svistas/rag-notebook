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
    enable_query_rewrite: bool = Field(default=True, alias="ENABLE_QUERY_REWRITE")
    enable_rerank: bool = Field(default=True, alias="ENABLE_RERANK")
    rerank_top_n: int = Field(default=5, alias="RERANK_TOP_N")
    rewrite_model: str = Field(default="gpt-4o-mini", alias="REWRITE_MODEL")
    rerank_model: str = Field(default="gpt-4o-mini", alias="RERANK_MODEL")
    upload_dir: str = Field(default="data", alias="UPLOAD_DIR")
    chroma_dir: str = Field(default=".chroma", alias="CHROMA_DIR")
    chroma_collection: str = Field(default="documents", alias="CHROMA_COLLECTION")
    max_upload_size_mb: int = Field(default=5, alias="MAX_UPLOAD_SIZE_MB")

    database_url: str = Field(
        default="postgresql+psycopg://rag:rag@localhost:5432/rag_notebook",
        alias="DATABASE_URL",
    )
    jwt_secret: str = Field(default="change-me", alias="JWT_SECRET")
    jwt_cookie_name: str = Field(default="rag_session", alias="JWT_COOKIE_NAME")
    jwt_exp_minutes: int = Field(default=60 * 24 * 7, alias="JWT_EXP_MINUTES")

    @property
    def upload_path(self) -> Path:
        return Path(self.upload_dir)

    @property
    def chroma_path(self) -> Path:
        return Path(self.chroma_dir)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
