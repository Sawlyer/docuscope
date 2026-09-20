from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "DocuScope"
    secret_key: str = "local-development-secret-change-me"
    access_token_minutes: int = 60
    session_cookie_name: str = "docuscope_session"
    session_cookie_secure: bool = False
    allowed_origins: str = "http://localhost:18000,http://localhost:5173"
    lm_studio_url: str = "http://localhost:1234/api/v1/chat"
    lm_studio_model: str = "minicpm5-1b"
    lm_studio_timeout: float = 45.0
    mock_llm: bool = True
    database_url: str = "postgresql+psycopg://docuscope:docuscope@localhost:15432/docuscope"
    minio_endpoint: str = "localhost:19000"
    minio_access_key: str = "docuscope"
    minio_secret_key: str = "docuscope-local"
    minio_bucket: str = "docuscope-documents"
    minio_secure: bool = False
    embedding_model: str = "intfloat/multilingual-e5-small"
    embedding_cache_dir: str = "/models"
    retrieval_threshold: float = 0.70
    retrieval_limit: int = 5
    max_upload_bytes: int = 15 * 1024 * 1024
    rag_context_max_chars: int = 7000
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
