from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Reads values from the .env file in the project root
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    read_only_database_url: str
    admin_database_url: str
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""


settings = Settings()