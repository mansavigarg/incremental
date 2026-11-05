"""Small CSV store for learning persistence before the database stage."""

import csv
from pathlib import Path

from loanserve.core.entities import create_loan_application
from loanserve.core.exceptions import StorageError


class ApplicationFileStorage:
    def __init__(self, storage_directory):
        self.storage_directory = Path(storage_directory)
        self.storage_directory.mkdir(parents=True, exist_ok=True)

    def save_csv(self, application_records, file_name):
        if not application_records:
            raise StorageError("No application records were given to save")
        path = self.storage_directory / file_name
        try:
            with path.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=application_records[0].keys())
                writer.writeheader()
                writer.writerows(application_records)
        except OSError as error:
            raise StorageError(f"Could not write {path}") from error
        return str(path)

    def load_csv(self, file_name):
        path = self.storage_directory / file_name
        try:
            with path.open(encoding="utf-8", newline="") as stream:
                return list(csv.DictReader(stream))
        except OSError as error:
            raise StorageError(f"Could not read {path}") from error

    def load_applications(self, file_name):
        return [create_loan_application(row) for row in self.load_csv(file_name)]


if __name__ == "__main__":
    store = ApplicationFileStorage("output/day03_storage")
    store.save_csv([{"loan_type": "gold", "loan_amount_inr": 100000, "tenure_months": 12,
                     "monthly_income_inr": 40000, "age_years": 30, "collateral_value_inr": 200000}], "applications.csv")
    print(f"{len(store.load_csv('applications.csv'))} row(s) read back")
