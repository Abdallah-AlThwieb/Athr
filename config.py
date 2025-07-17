import os
from pathlib import Path

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    APP_DIR = Path(os.path.dirname(os.path.realpath(__file__)))
    VIEWS_DIR = APP_DIR / "templates"
    STATIC_DIR = APP_DIR / "static"
    # PostgresSQL
    SQLALCHEMY_DATABASE_URI = f'postgresql://{os.environ.get("DATABASE_USERNAME")}:{os.environ.get("DATABASE_PASSWORD")}@localhost/{os.environ.get("DATABASE_NAME")}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Owner data
    OWNER_USERNAME = os.environ.get("OWNER_USERNAME")
    OWNER_EMAIL = os.environ.get("OWNER_EMAIL")
    OWNER_PASSWORD = os.environ.get("OWNER_PASSWORD")
    