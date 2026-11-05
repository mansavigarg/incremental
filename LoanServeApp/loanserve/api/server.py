"""Persistent factory used by the local server launcher."""

import os
from pathlib import Path
from dotenv import load_dotenv

from loanserve.api.application_factory import create_application


def create_server_application():
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    database = Path(os.getenv('LOANSERVE_API_DATABASE', 'database/api_applications.db'))
    database.parent.mkdir(parents=True, exist_ok=True)
    return create_application(database_url=f'sqlite:///{database.resolve()}')
