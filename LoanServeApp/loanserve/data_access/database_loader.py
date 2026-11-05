"""SQLite storage for the cleaned application book."""

import sqlite3
from pathlib import Path

import pandas as pd

from loanserve.core.exceptions import StorageError


class ApplicationDatabase:
    def __init__(self, database_path):
        path = Path(database_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row

    def load_from_csv(self, cleaned_file_path):
        path = Path(cleaned_file_path)
        if not path.is_file():
            raise StorageError(f"Cleaned file not found: {path}")
        records = pd.read_csv(path)
        with self.connection:
            records.to_sql("loan_applications", self.connection, if_exists="replace", index=False)
            self.connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_application_id ON loan_applications(application_id)")
        return len(records)

    def find_application(self, application_id):
        row = self.connection.execute("SELECT * FROM loan_applications WHERE application_id = ?", (application_id,)).fetchone()
        return dict(row) if row else None

    def delete_application(self, application_id):
        with self.connection:
            cursor = self.connection.execute("DELETE FROM loan_applications WHERE application_id = ?", (application_id,))
        return cursor.rowcount


if __name__ == "__main__":
    database = ApplicationDatabase("database/loanserve.db")
    print(f"Loaded {database.load_from_csv('processed_data/loan_applications_cleaned.csv')} applications")
    print(f"Sample: {database.find_application('LA000001')['loan_type']}")
    database.connection.close()
