from pydantic import BaseSettings


class Settings(BaseSettings):
    # api definitions
    API_V1_STR: str = ""
    PROJECT_NAME: str = "salted_fileserver_service"

    # mongodb
    DB_URI: str

    # Seaweed connection information
    SEAWEED_MASTER_URL: str
    SEAWEED_VOLUME_SERVER_URL: str

    class Config:
        case_sensitive = True


settings = Settings()
