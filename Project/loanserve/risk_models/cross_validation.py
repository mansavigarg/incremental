"""Fair comparison of four models on the same stratified folds."""

import json
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

from config.constants import CROSS_VALIDATION_FOLDS, RANDOM_SEED
from loanserve.risk_models.baseline_model import build_baseline_model
from loanserve.risk_models.feature_pipeline import build_feature_pipeline, split_for_modelling
from loanserve.risk_models.tree_models import build_decision_tree, build_random_forest


def build_linear_svm():
    return Pipeline([
        ("prepare", build_feature_pipeline()),
        ("classify", LinearSVC(C=0.1, class_weight="balanced",
                                random_state=RANDOM_SEED, max_iter=10000)),
    ])


def every_model():
    return {
        "logistic_baseline": build_baseline_model(),
        "decision_tree": build_decision_tree(),
        "random_forest": build_random_forest(),
        "linear_svm": build_linear_svm(),
    }


def score_across_folds(model, features, target):
    folds = StratifiedKFold(n_splits=CROSS_VALIDATION_FOLDS, shuffle=True, random_state=RANDOM_SEED)
    scores = cross_val_score(model, features, target, cv=folds, scoring="roc_auc", n_jobs=1)
    return {
        "fold_scores": [round(float(score), 4) for score in scores],
        "mean_roc_auc": round(float(np.mean(scores)), 4),
        "spread": round(float(np.max(scores) - np.min(scores)), 4),
    }


def training_against_holdout(model, cleaned_file_path):
    fitting, holdout, target, holdout_target = split_for_modelling(cleaned_file_path)
    model.fit(fitting, target)
    score = (lambda rows: model.predict_proba(rows)[:, 1]) if hasattr(model, "predict_proba") else model.decision_function
    training_score = roc_auc_score(target, score(fitting))
    holdout_score = roc_auc_score(holdout_target, score(holdout))
    return round(float(training_score), 4), round(float(holdout_score), 4)


def compare_across_folds(cleaned_file_path, output_path):
    fitting, _, target, _ = split_for_modelling(cleaned_file_path)
    results = {name: score_across_folds(model, fitting, target)
               for name, model in every_model().items()}
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(results, indent=2))
    return results


if __name__ == "__main__":
    source = "processed_data/loan_applications_cleaned.csv"
    results = compare_across_folds(source, "output/fold_scores.json")
    for name, row in results.items():
        training, holdout = training_against_holdout(every_model()[name], source)
        print(name, row, training, holdout)
    print("best over five folds:", max(results, key=lambda key: results[key]["mean_roc_auc"]))
