"""Vectorised, auditable cleaning of the supplied application books."""

from pathlib import Path

import pandas as pd

from config.constants import MAXIMUM_CREDIT_SCORE, MINIMUM_CREDIT_SCORE, MODELLING_COLUMNS
from loanserve.core.decorators import measure_duration


class ApplicationCleaner:
    def __init__(self, raw_file_path):
        self.raw_records = pd.read_csv(raw_file_path)

    def fault_reasons(self):
        rows = self.raw_records
        reasons = pd.Series("", index=rows.index, dtype="string")
        checks = (
            (rows["application_id"].duplicated(), "duplicate_application_id"),
            (rows[list(MODELLING_COLUMNS)].isna().any(axis=1), "missing_required_field"),
            (pd.to_numeric(rows["monthly_income_inr"], errors="coerce").le(0), "income_not_positive"),
            (~pd.to_numeric(rows["credit_score"], errors="coerce").between(MINIMUM_CREDIT_SCORE, MAXIMUM_CREDIT_SCORE), "credit_score_out_of_range"),
            (pd.to_datetime(rows["application_date"], format="mixed", errors="coerce").isna(), "unparseable_application_date"),
        )
        for faulty, label in checks:
            reasons.loc[reasons.eq("") & faulty.fillna(False)] = label
        return reasons

    @measure_duration
    def clean_data(self, output_path):
        clean = self.raw_records.loc[self.fault_reasons().eq("")].copy()
        clean["application_date"] = pd.to_datetime(clean["application_date"], format="mixed").dt.strftime("%Y-%m-%d")
        clean["employment_type"] = clean["employment_type"].str.strip().str.lower()
        clean["applicant_city"] = clean["applicant_city"].str.strip()
        for column in ("age_years", "existing_loan_count", "tenure_months"):
            clean[column] = clean[column].astype(int)
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        clean.to_csv(destination, index=False)
        return len(clean)

    def save_rejected_records(self, output_path):
        reasons = self.fault_reasons()
        rejected = self.raw_records.loc[reasons.ne("")].copy()
        rejected["rejection_reason"] = reasons.loc[rejected.index]
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        rejected.to_csv(destination, index=False)
        return len(rejected)


if __name__ == "__main__":
    train = ApplicationCleaner("data/loan_applications_train.csv")
    for name, cleaner, output in (
        ("loan_applications_train.csv", train, "processed_data/loan_applications_cleaned.csv"),
        ("loan_applications_predict.csv", ApplicationCleaner("data/loan_applications_predict.csv"), "processed_data/loan_applications_predict_cleaned.csv"),
    ):
        count = cleaner.clean_data(output)
        print(f"{name} kept {count} in {cleaner.clean_data.last_duration_seconds:.2f}s")
    print(f"rejected {train.save_rejected_records('output/rejected_records.csv')}")
