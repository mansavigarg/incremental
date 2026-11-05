"""Derive payment burden and credit bands from the cleaned books."""

import json
from pathlib import Path

import pandas as pd

from config.constants import (
    CREDIT_BAND_NAMES, CREDIT_SCORE_BAND_EDGES, ENGINEERED_CATEGORICAL_COLUMNS,
    ENGINEERED_NUMERIC_COLUMNS, INTEREST_RATE_PERCENT_BY_LOAN_TYPE, TARGET_COLUMN,
)
from loanserve.core.loan_calculations import calculate_monthly_installment
from loanserve.risk_models.cross_validation import score_across_folds
from loanserve.risk_models.feature_pipeline import split_for_modelling
from loanserve.risk_models.tree_models import build_random_forest


def add_engineered_features(records):
    enriched = records.copy()
    # Each row has a different principal, product rate and tenure; the shared domain
    # function remains the single source of the repayment formula.
    enriched["monthly_installment_inr"] = [
        round(calculate_monthly_installment(principal, INTEREST_RATE_PERCENT_BY_LOAN_TYPE[product], int(tenure)), 2)
        for principal, product, tenure in zip(enriched["loan_amount_inr"], enriched["loan_type"], enriched["tenure_months"])
    ]
    enriched["installment_to_income"] = (
        enriched["monthly_installment_inr"] / enriched["monthly_income_inr"]
    ).round(4)
    enriched["credit_band"] = pd.cut(
        enriched["credit_score"], bins=CREDIT_SCORE_BAND_EDGES,
        labels=CREDIT_BAND_NAMES, include_lowest=True,
    ).astype(str)
    return enriched


def write_enriched_file(cleaned_file_path, output_path):
    enriched = add_engineered_features(pd.read_csv(cleaned_file_path))
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    enriched.to_csv(destination, index=False)
    return len(enriched)


def default_rate_by_band(enriched_file_path):
    records = pd.read_csv(enriched_file_path)
    means = records.groupby("credit_band")[TARGET_COLUMN].mean()
    return {band: round(float(means[band]), 4) for band in CREDIT_BAND_NAMES}


def measure_the_lift(enriched_file_path, output_path):
    plain, _, target, _ = split_for_modelling(enriched_file_path)
    enriched, _, _, _ = split_for_modelling(
        enriched_file_path, ENGINEERED_NUMERIC_COLUMNS, ENGINEERED_CATEGORICAL_COLUMNS
    )
    without = score_across_folds(build_random_forest(), plain, target)["mean_roc_auc"]
    with_features = score_across_folds(
        build_random_forest(ENGINEERED_NUMERIC_COLUMNS, ENGINEERED_CATEGORICAL_COLUMNS),
        enriched, target,
    )["mean_roc_auc"]
    result = {"without_engineered": without, "with_engineered": with_features,
              "lift": round(with_features - without, 4)}
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    for source, destination in (
        ("processed_data/loan_applications_cleaned.csv", "processed_data/loan_applications_enriched.csv"),
        ("processed_data/loan_applications_predict_cleaned.csv", "processed_data/loan_applications_predict_enriched.csv"),
    ):
        print(destination, write_enriched_file(source, destination))
    print(default_rate_by_band("processed_data/loan_applications_enriched.csv"))
    print(measure_the_lift("processed_data/loan_applications_enriched.csv", "output/feature_lift.json"))
