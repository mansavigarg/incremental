"""One preparation and split contract shared by all risk models."""

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from config.constants import (
    CATEGORICAL_MODELLING_COLUMNS, HOLDOUT_SHARE, NUMERIC_MODELLING_COLUMNS,
    RANDOM_SEED, TARGET_COLUMN,
)


def build_feature_pipeline(extra_numeric=(), extra_categorical=()):
    numeric = (*NUMERIC_MODELLING_COLUMNS, *extra_numeric)
    categorical = (*CATEGORICAL_MODELLING_COLUMNS, *extra_categorical)
    return ColumnTransformer([
        ("numeric", Pipeline([("impute", SimpleImputer(strategy="median")),
                              ("scale", StandardScaler())]), numeric),
        ("categorical", Pipeline([("impute", SimpleImputer(strategy="most_frequent")),
                                  ("encode", OneHotEncoder(handle_unknown="ignore", sparse_output=False))]), categorical),
    ], sparse_threshold=0)


def select_modelling_columns(records, extra_numeric=(), extra_categorical=()):
    return records.loc[:, [*NUMERIC_MODELLING_COLUMNS, *extra_numeric,
                           *CATEGORICAL_MODELLING_COLUMNS, *extra_categorical]].copy()


def split_for_modelling(cleaned_file_path, extra_numeric=(), extra_categorical=()):
    records = pd.read_csv(cleaned_file_path)
    return train_test_split(
        select_modelling_columns(records, extra_numeric, extra_categorical),
        records[TARGET_COLUMN], test_size=HOLDOUT_SHARE,
        stratify=records[TARGET_COLUMN], random_state=RANDOM_SEED,
    )


if __name__ == "__main__":
    records = pd.read_csv("processed_data/loan_applications_cleaned.csv")
    print(build_feature_pipeline().fit_transform(select_modelling_columns(records)).shape)
