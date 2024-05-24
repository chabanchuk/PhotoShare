from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Development settings
dot_env_path = Path(__file__).parent / 'dev.env'
# Production settings
# dot_env_path = Path(__file__).parent / '.env'


class EnvSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=dot_env_path,
                                      env_file_encoding='utf-8',
                                      extra='ignore')

    sqlalchemy_url: str
    secret_256: str
    secret_512: str
    access_algorithm: str
    refresh_algorithm: str
    mail_user: str
    mail_pass: str
    mail_server: str
    mail_port: int
    mail_from: str
    cloudinary_name: str
    cloudinary_api_key: str
    cloudinary_api_secret: str
    refresh_exp: str


# production environment
settings = EnvSettings()

