"""Logistic baseline fitted, measured and saved with its preparation."""

from pathlib import Path

import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import Pipeline

from config.constants import RANDOM_SEED
from loanserve.risk_models.feature_pipeline import build_feature_pipeline, select_modelling_columns, split_for_modelling


def build_baseline_model():
    return Pipeline([
        ("prepare", build_feature_pipeline()),
        ("classify", LogisticRegression(class_weight="balanced", max_iter=1000, random_state=RANDOM_SEED)),
    ])


def train_baseline_model(cleaned_file_path):
    fitting, holdout, target, holdout_target = split_for_modelling(cleaned_file_path)
    model = build_baseline_model().fit(fitting, target)
    return model, round(float(roc_auc_score(holdout_target, model.predict_proba(holdout)[:, 1])), 4)


def save_model(model, model_path):
    path = Path(model_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, path)
    return str(path)


def load_model(model_path):
    return joblib.load(model_path)


def predict_default_probability(model, records):
    prepared_columns = list(model.named_steps["prepare"].feature_names_in_)
    return model.predict_proba(records.loc[:, prepared_columns])[:, 1]


def write_predictions(model, prediction_file_path, output_path):
    records = pd.read_csv(prediction_file_path)
    predictions = pd.DataFrame({
        "application_id": records["application_id"],
        "default_probability": predict_default_probability(model, records).round(6),
    })
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(path, index=False)
    return len(predictions)


if __name__ == "__main__":
    fitted, score = train_baseline_model("processed_data/loan_applications_cleaned.csv")
    path = save_model(fitted, "artifacts/baseline_model.pkl")
    print(f"holdout ROC-AUC: {score} | saved: {path}")
    print(f"predicted: {write_predictions(load_model(path), 'processed_data/loan_applications_predict_cleaned.csv', 'output/predictions.csv')} applications")
